"""The installed set in the virtual unit (owner decision 17; docs/plan/installed-set.md B1 to B5): slots per kind from schema/asset-kinds.json, a RAM flash pool with the real geometry
(382 data sectors of 4,096 bytes), the 128 byte asset header with a signature, an install streamed in pieces and committed atomically, swap, remove, abort, and the answers of the
self.assets.* tools with the pair `error` and `error_es` and a `code`. Loading an active item reports its PSRAM cost to the memory model (internal RAM is zero); freeing releases it.

What is assumed until the firmware track writes the unit's core: the error codes and texts (marked below), the directory ring (not modeled: one atomic directory write), and the signing key (a
test key made at run time from a fixed seed, no key is stored in the repository). Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import base64
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KINDS_FILE = ROOT / "schema" / "asset-kinds.json"
HEADER = struct.Struct("<8sII32s8sBBHI40s8sII8s")   # 128 bytes (docs/plan/installed-set.md B4)
assert HEADER.size == 128
MAGIC = b"MPAH1\0\0\0"
PIECE = 2048
BOARD = b"STACKCHN"


def _test_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b"FAKETESTKEY asset signing for the virtual unit").digest())


def test_public_key():
    from cryptography.hazmat.primitives import serialization

    return _test_key().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def make_asset(kind: str, name: str, body: bytes, *, version: int = 1, code: str = "", psram: int = 0, flags: int = 0, board: bytes = BOARD, kinds: list[dict] | None = None) -> tuple[bytes, bytes, bytes]:
    """A signed asset as the host would build it: (header 128 bytes, signature 64 bytes, body)."""
    table = kinds or json.loads(KINDS_FILE.read_text())["kinds"]
    index = [k["kind"] for k in table].index(kind)
    flash = -(-len(body) // 4096) * 4096
    header = HEADER.pack(MAGIC, version, len(body), hashlib.sha256(body).digest(), board.ljust(8, b"\0"), index, 1, flags, 0, name.encode().ljust(40, b"\0"), code.encode().ljust(8, b"\0"), psram, flash, b"\0" * 8)
    return header, _test_key().sign(header), body


def err(code: str, en: str, es: str) -> dict:
    return {"ok": False, "code": code, "error": en, "error_es": es}   # codes and texts ASSUMED until the unit's core exists


class AssetStore:
    def __init__(self, u=None, kinds: dict | None = None) -> None:
        self.u = u
        cfg = kinds or json.loads(KINDS_FILE.read_text())
        self.pool = cfg["pool"]
        self.kinds = cfg["kinds"]
        self.free = [True] * self.pool["sectors"]
        self.items: dict[str, list[dict | None]] = {k["kind"]: [None] * k["max_slots"] for k in self.kinds}
        self.active: dict[str, int] = {}
        self.inflight: dict | None = None
        self.events: list[tuple[int, str, dict]] = []
        self.cut_at: int | None = None   # a power cut after this many pieces (injected by a test)
        self.loaded: dict[str, str] = {}   # kind -> memory item id while its active item is loaded
        self.public = test_public_key()

    # ---- helpers -------------------------------------------------------------------------------------------------------------------

    def _kind(self, name: str) -> dict | None:
        return next((k for k in self.kinds if k["kind"] == name), None)

    def _emit(self, event: str, **kw) -> None:
        self.events.append((self.u.now_ms if self.u else 0, event, kw))

    def free_bytes(self) -> int:
        return sum(self.free) * self.pool["sector_bytes"]

    def _alloc(self, sectors: int) -> list[int] | None:
        run = [i for i, f in enumerate(self.free) if f]
        return run[:sectors] if len(run) >= sectors else None

    def _release_load(self, kind: str) -> None:
        mem_id = self.loaded.pop(kind, None)
        if mem_id and self.u is not None and getattr(self.u, "_memory", None) is not None:
            self.u._memory.close(mem_id)

    def _load_active(self, kind: str) -> None:
        """The consumer asks for the active item: its PSRAM cost is loaded (internal RAM none); a swapped-out or removed item frees it."""
        self._release_load(kind)
        slot = self.active.get(kind)
        item = self.items[kind][slot] if slot is not None else None
        if item and self.u is not None and item["psram"] > 0:
            self.u.memory.open(f"asset.{kind}", psram=item["psram"], flash=item["flash"])
            self.loaded[kind] = f"asset.{kind}"
        if item and kind == "style" and self.u is not None and getattr(self.u, "_proc", None) is not None:
            try:
                self.u.raw("style " + json.loads(item["body"].decode()).get("base", "big_eyes"))   # the renderer draws one of the baked styles: the recipe names it
            except ValueError:
                pass
        if self.u is not None:
            self._emit("assets_state", kind=kind, active=None if item is None else item["name"])

    # ---- the tools (docs/plan/installed-set.md B5) ----------------------------------------------------------------------------------------

    def list(self) -> dict:
        kinds = []
        for k in self.kinds:
            items = []
            for slot, it in enumerate(self.items[k["kind"]]):
                if it:
                    items.append({"slot": slot, "name": it["name"], "code": it["code"], "version": it["version"], "bytes": it["bytes"], "sha8": it["sha"][:8], "active": self.active.get(k["kind"]) == slot,
                                  "loaded": self.loaded.get(k["kind"]) is not None and self.active.get(k["kind"]) == slot, "state": "ok", "psram_bytes": it["psram"]})
            kinds.append({"kind": k["kind"], "max_slots": k["max_slots"], "max_item_bytes": k["max_item_bytes"], "active_slot": self.active.get(k["kind"], -1), "items": items})
        out = {"ok": True, "v": 1, "region_bytes": self.pool["sectors"] * self.pool["sector_bytes"], "free_bytes": self.free_bytes(), "dir_ok": True, "kinds": kinds}
        if self.inflight:
            out["install"] = {"kind": self.inflight["kind"], "slot": self.inflight["slot"], "got": self.inflight["got"]}
        return out

    def install(self, kind: str, slot: int, header_b64: str, sig_b64: str) -> dict:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        k = self._kind(kind)
        if k is None:
            return err("kind_unknown", f"That kind is not known: use one of {', '.join(x['kind'] for x in self.kinds)}.", "Ese tipo no existe: usa uno de la lista.")
        if self.inflight:
            return err("busy", "An install is already running. Finish it or abort it first.", "Ya hay una instalación en curso. Termínala o abórtala primero.")
        try:
            raw, sig = base64.b64decode(header_b64), base64.b64decode(sig_b64)
        except ValueError:
            return err("bad_header", "The header is not valid base64: send it again.", "La cabecera no es base64 válido: envíala otra vez.")
        if len(raw) != 128:
            return err("bad_header", "The header must be 128 bytes: rebuild the asset.", "La cabecera debe tener 128 bytes: vuelve a crear el recurso.")
        try:
            Ed25519PublicKey.from_public_bytes(self.public).verify(sig, raw)
        except (InvalidSignature, ValueError):
            return err("bad_signature", "The signature does not match: the asset is not installed. Get it again from the catalog.", "La firma no coincide: el recurso no se instala. Vuelve a pedirlo del catálogo.")
        magic, version, length, sha, board, kidx, fmt, flags, minfw, name_b, code_b, psram, flash, _ = HEADER.unpack(raw)
        if magic != MAGIC:
            return err("bad_header", "That is not an asset header.", "Eso no es una cabecera de recurso.")
        if board == b"\0" * 8 or board.rstrip(b"\0") != BOARD:
            return err("wrong_board", "This asset is for another robot board.", "Este recurso es para otra placa de robot.")
        if kidx >= len(self.kinds) or self.kinds[kidx]["kind"] != kind:
            return err("wrong_kind", "The header says a different kind than the one asked for.", "La cabecera dice otro tipo del que se pidió.")
        name = name_b.rstrip(b"\0").decode(errors="replace")
        if length > k["max_item_bytes"]:
            return err("too_big", f"That {kind} is {length:,} bytes; the most one may be is {k['max_item_bytes']:,}.", f"Ese {kind} pesa {length:,} bytes; el máximo es {k['max_item_bytes']:,}.")
        slots = self.items[kind]
        same = next((i for i, it in enumerate(slots) if it and it["name"] == name), None)
        if slot < 0:
            slot = same if same is not None else next((i for i, it in enumerate(slots) if it is None), -1)
        if slot < 0 or slot >= len(slots):
            return err("slots_full", f"All {k['max_slots']} {kind} slots are used: remove one first.", f"Los {k['max_slots']} espacios de {kind} están usados: quita uno primero.")
        if slots[slot] is not None and same != slot:
            return err("slot_busy", "That slot already holds another item: pick a free slot or remove it.", "Ese espacio ya tiene otro elemento: elige uno libre o quítalo.")
        if same is not None and slots[same]["version"] > version:
            return err("older_version", "A newer version of this item is already installed.", "Ya hay una versión más nueva de este elemento.")
        need = -(-length // self.pool["sector_bytes"])
        freed = len(slots[slot]["sectors"]) if slots[slot] else 0
        if need > sum(self.free) + freed:
            return err("pool_full", f"There is not enough room: {need * 4096:,} bytes needed, {self.free_bytes() + freed * 4096:,} free. Remove something first.", "No hay espacio suficiente. Quita algo primero.")
        self.inflight = {"kind": kind, "slot": slot, "name": name, "code": code_b.rstrip(b"\0").decode(), "version": version, "length": length, "sha": sha, "psram": psram, "flash": flash, "got": 0, "buf": bytearray(), "pieces": 0}
        self._emit("asset_wanted", kind=kind, name=name)
        return {"ok": True, "slot": slot, "accept_bytes": length, "piece_bytes": PIECE}

    def data(self, at: int, b64: str) -> dict:
        s = self.inflight
        if s is None:
            return err("no_install", "No install is running: start one first.", "No hay una instalación en curso: empieza una.")
        if at != s["got"]:
            return err("bad_offset", f"The piece starts at {at} but the unit has {s['got']}: continue from there.", f"La pieza empieza en {at} pero el robot tiene {s['got']}: continúa desde ahí.")
        piece = base64.b64decode(b64)
        if len(piece) > PIECE or s["got"] + len(piece) > s["length"]:
            return err("bad_piece", "That piece is too long.", "Esa pieza es demasiado larga.")
        s["buf"] += piece
        s["got"] += len(piece)
        s["pieces"] += 1
        if self.cut_at is not None and s["pieces"] >= self.cut_at:
            self.cut_at = None
            self.power_cycle()
            return err("power_cut", "The robot lost power while it was installing: send the item again.", "El robot se quedó sin energía mientras instalaba: envía el elemento otra vez.")
        if s["length"] and (s["got"] * 10 // s["length"]) > ((s["got"] - len(piece)) * 10 // s["length"]):
            self._emit("asset_progress", name=s["name"], percent=s["got"] * 100 // s["length"])
        return {"ok": True, "got": s["got"]}

    def commit(self) -> dict:
        s = self.inflight
        if s is None:
            return err("no_install", "No install is running: start one first.", "No hay una instalación en curso: empieza una.")
        if s["got"] != s["length"]:
            return err("incomplete", f"Only {s['got']} of {s['length']} bytes arrived: send the rest.", f"Solo llegaron {s['got']} de {s['length']} bytes: envía el resto.")
        if hashlib.sha256(bytes(s["buf"])).digest() != s["sha"]:
            self.inflight = None
            self._emit("asset_failed", name=s["name"], code="bad_hash")
            return err("bad_hash", "The item arrived damaged and was not installed. Try again.", "El elemento llegó dañado y no se instaló. Inténtalo de nuevo.")
        kind, slot = s["kind"], s["slot"]
        old = self.items[kind][slot]
        sectors = self._alloc(-(-s["length"] // self.pool["sector_bytes"]) or 1) if s["length"] else []
        if sectors is None and old:   # the old item is dropped first when there is no room beside it
            for i in old["sectors"]:
                self.free[i] = True
            sectors = self._alloc(-(-s["length"] // self.pool["sector_bytes"]))
            old = None
        if sectors is None:
            self.inflight = None
            return err("pool_full", "There is not enough room left: remove something first.", "No queda espacio: quita algo primero.")
        for i in sectors:
            self.free[i] = False
        self.items[kind][slot] = {"name": s["name"], "code": s["code"], "version": s["version"], "bytes": s["length"], "sha": s["sha"].hex(), "psram": s["psram"], "flash": s["flash"], "sectors": sectors, "body": bytes(s["buf"])}
        if old:
            for i in old["sectors"]:
                self.free[i] = True
        self.active.setdefault(kind, slot)
        if self.active.get(kind) == slot:
            self._load_active(kind)
        self.inflight = None
        self._emit("asset_done", kind=kind, name=s["name"])
        return {"ok": True, "slot": slot}

    def remove(self, kind: str, slot: int) -> dict:
        k = self._kind(kind)
        if k is None or not 0 <= slot < len(self.items[kind]) or self.items[kind][slot] is None:
            return err("no_item", "There is nothing in that slot.", "No hay nada en ese espacio.")
        it = self.items[kind][slot]
        for i in it["sectors"]:
            self.free[i] = True
        self.items[kind][slot] = None
        if self.active.get(kind) == slot:
            self.active.pop(kind, None)
            nxt = next((i for i, x in enumerate(self.items[kind]) if x), None)
            if nxt is not None:
                self.active[kind] = nxt
            self._load_active(kind)
        return {"ok": True}

    def swap(self, kind: str, slot: int) -> dict:
        k = self._kind(kind)
        if k is None or not 0 <= slot < len(self.items[kind]) or self.items[kind][slot] is None:
            return err("no_item", "There is nothing in that slot.", "No hay nada en ese espacio.")
        self.active[kind] = slot
        self._load_active(kind)
        return {"ok": True, "active": slot}

    def abort(self) -> dict:
        self.inflight = None
        return {"ok": True}

    def power_cycle(self) -> None:
        """Power lost: an install in flight is gone, what the directory holds stays, and the active items load again."""
        self.inflight = None
        for kind in list(self.loaded):
            self._release_load(kind)
        for kind in self.active:
            self._load_active(kind)

    # ---- the state panel -------------------------------------------------------------------------------------------------------------------

    def slots(self) -> dict:
        """Slots used out of slots available per kind, the pool, and what is loaded (for the virtual robot's state panel and the ledger)."""
        return {"kinds": {k["kind"]: {"used": sum(1 for it in self.items[k["kind"]] if it), "slots": k["max_slots"], "active": (self.items[k["kind"]][self.active[k["kind"]]] or {}).get("name") if k["kind"] in self.active else None} for k in self.kinds},
                "pool_free_bytes": self.free_bytes(), "pool_bytes": self.pool["sectors"] * self.pool["sector_bytes"], "loaded": dict(self.loaded)}


BASE_STYLES = ("big_eyes", "eyes_only", "stock", "classic", "minimal")


def face_catalog(n: int = 20) -> list[tuple[str, bytes, bytes, bytes]]:
    """Twenty faces of the catalog as signed style assets (header, signature, body): each recipe names one of the baked styles the renderer draws and a small tweak."""
    out = []
    for i in range(n):
        body = json.dumps({"base": BASE_STYLES[i % len(BASE_STYLES)], "tweak": i}, separators=(",", ":")).encode()
        out.append(("face-%02d" % (i + 1), *make_asset("style", "face-%02d" % (i + 1), body, psram=512, code="")))
    return out


def install_all(store: AssetStore, kind: str, header: bytes, sig: bytes, body: bytes, slot: int = -1) -> dict:
    """What the host does: install, push the pieces in order, commit."""
    r = store.install(kind, slot, base64.b64encode(header).decode(), base64.b64encode(sig).decode())
    if not r.get("ok"):
        return r
    for at in range(0, len(body), PIECE):
        r = store.data(at, base64.b64encode(body[at : at + PIECE]).decode())
        if not r.get("ok"):
            return r
    return store.commit()
