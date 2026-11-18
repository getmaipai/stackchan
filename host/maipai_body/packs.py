# ruff: noqa: E501
"""One pack loader for every optional data set: looks, languages, fillers, sounds, dances, games.

A pack is one file: a magic line, one line of JSON (the header) and the payload.

    MAIPACK1\\n
    {"format": 1, "type": "look", "name": "Pixel", "version": 3, "size": 51234,
     "sha256": "<hex of the payload>", "signature": "<optional hex>", "signer": "<optional>"}\\n
    <payload: a zip file, whatever the type needs inside>

The host holds the library (a folder per type, mode 700) and, per unit, the one *active* pack of each type. Only
the active pack is sent to a unit; the unit keeps it, frees the one before it, and has a built-in fallback for
each type, so it is complete with no host. The size gate is here, with plain sentences in English and Spanish,
so a pack that would not fit is refused before anything is sent. The transport is the picture-face transport
(``picture_faces``: the same reply unwrapping and chunk size), with these unit tools, which the firmware ships
in a later release (a unit without them is flagged and the choice waits on the host):

    self.pack.status  {"type": "look"}                      -> {"ok": true, "held": bool, "sha256": "...", "name": "..."}
                      (language adds "lang", phrase adds "clips": how many of the sixteen came from the pack)
    self.pack.begin   {"type", "name", "version", "size", "sha256"}
    self.pack.data    {"at": 0, "b64": "..."}               (CHUNK_BYTES raw bytes per call)
    self.pack.commit  {}
    self.pack.remove  {"type": "look"}                      (back to the built-in one)

Nothing here ships a pack: the library starts empty, and a pack the owner imports never leaves the host except
to that owner's own unit.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import re
import tempfile
import threading
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maipai_body.hal.errors import BodyLost
from maipai_body.picture_faces import CHUNK_BYTES
from maipai_body.unit_tools import ToolProbe, is_unknown_tool, unwrap

logger = logging.getLogger("maipai_body.packs")

MAGIC = b"MAIPACK1\n"
FORMAT = 1
TYPES = ("look", "language", "filler", "sound", "dance", "game", "phrase")
# The types the host keeps in step with the unit's settings (its language, "While it thinks", its voice) and not only with a
# person's explicit choice: the host works out the pack each one should hold (``pack_auto.AutoPacks``) and sends it on connect
# and whenever a setting that decides it changes. The other types are sent only when a person activates a pack.
MANAGED = ("language", "filler", "phrase")
# The most one pack of each type may hold, in bytes (look: about 1 MB; fillers: under 400 KB).
MAX_BYTES: dict[str, int] = {
    "look": 1_000_000,
    "language": 200_000,
    "filler": 400_000,
    "sound": 400_000,
    "dance": 100_000,
    "game": 200_000,
    "phrase": 150_000,
}
MAX_LIBRARY_BYTES = 40_000_000  # everything held on the host; the unit only ever holds the active ones
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.\-]{0,39}$")

SAY: dict[str, tuple[str, str]] = {
    "bad_file": (
        "That file is not a pack. Choose a .maipack file that was exported from this page or from a pack author.",
        "Ese archivo no es un paquete. Elige un archivo .maipack exportado desde esta página o por un autor de paquetes.",
    ),
    "bad_type": (
        "That pack type is not known ({kind}). Packs can be: {types}.",
        "No conozco ese tipo de paquete ({kind}). Los paquetes pueden ser: {types}.",
    ),
    "bad_name": (
        "The pack name must be 1 to 40 letters, numbers, spaces, dots, dashes or underscores. Rename it and import again.",
        "El nombre del paquete debe tener de 1 a 40 letras, números, espacios, puntos, guiones o guiones bajos. Cámbialo e importa de nuevo.",
    ),
    "bad_sum": (
        "The pack is damaged: its contents do not match its checksum. Export it again from where it came from.",
        "El paquete está dañado: su contenido no coincide con su suma de verificación. Expórtalo de nuevo desde donde vino.",
    ),
    "bad_sig": (
        "The pack's signature is not valid, so it was not imported. Get the pack again from its author.",
        "La firma del paquete no es válida, así que no se importó. Vuelve a obtener el paquete de su autor.",
    ),
    "too_big": (
        "That {kind} pack is {size} KB, and the robot keeps at most {limit} KB for one. Use a smaller or simpler pack.",
        "Ese paquete de {kind} pesa {size} KB y el robot guarda como máximo {limit} KB. Usa un paquete más pequeño o más simple.",
    ),
    "library_full": (
        "The pack library is full ({limit} MB). Delete a pack you do not use, then import again.",
        "La biblioteca de paquetes está llena ({limit} MB). Borra un paquete que no uses e importa de nuevo.",
    ),
    "unknown": (
        "That pack is not in the library. Reload the list and choose again.",
        "Ese paquete no está en la biblioteca. Recarga la lista y elige de nuevo.",
    ),
    "wrong_type": (
        "That pack is a {have} pack, not a {want} pack. Choose a {want} pack.",
        "Ese paquete es de {have}, no de {want}. Elige un paquete de {want}.",
    ),
    "soon": (
        "Chosen. This unit gets the pack with its next update; it will be sent then.",
        "Elegido. Esta unidad recibe el paquete con su próxima actualización; se enviará entonces.",
    ),
    "kept": (
        "Chosen. The unit is not connected; the pack is sent when it connects.",
        "Elegido. La unidad no está conectada; el paquete se envía cuando se conecte.",
    ),
    "sent": ("Chosen and sent to the unit.", "Elegido y enviado a la unidad."),
    "send_failed": (
        "The unit did not take the pack. Try again; if it keeps failing, restart the robot.",
        "La unidad no aceptó el paquete. Inténtalo de nuevo; si sigue fallando, reinicia el robot.",
    ),
}


class PackError(ValueError):
    def __init__(self, message: str, code: str = "") -> None:
        super().__init__(message)
        self.code = code


def say(lang: str | None, code: str, **values: object) -> str:
    english, spanish = SAY[code]
    return (spanish if (lang or "").lower().startswith("es") else english).format(**values)


def _fail(lang: str | None, code: str, **values: object) -> PackError:
    return PackError(say(lang, code, **values), code)


# ---- the file ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Pack:
    type: str
    name: str
    version: int
    sha256: str
    payload: bytes
    signature: str = ""
    signer: str = ""
    voice: str = ""
    lang: str = ""

    @property
    def size(self) -> int:
        return len(self.payload)


def zip_payload(files: dict[str, bytes], *, stored: bool = False) -> bytes:
    """A payload from named byte strings (a zip, deflated; ``stored`` keeps the bytes as they are, for audio that is already compressed)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), data, compress_type=zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED)
    return buf.getvalue()


MAX_UNZIPPED_BYTES = 64 * 1024 * 1024  # everything a pack may unpack to, however small it is on the wire
MAX_UNZIPPED_FILES = 2000


def unzip_payload(payload: bytes) -> dict[str, bytes]:
    """Open a pack's zip with limits: file count, total size (declared and actually read) and safe names."""
    out: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_UNZIPPED_FILES:
            raise PackError(
                f"The pack holds more than {MAX_UNZIPPED_FILES} files, so it was refused. Get a smaller pack from its author.",
                "bad_zip",
            )
        for info in infos:
            if info.filename.startswith("/") or ".." in info.filename.split("/") or "\\" in info.filename:
                raise PackError("The pack has an unsafe file name, so it was refused. Get the pack again from its author.", "bad_zip")
        if sum(info.file_size for info in infos) > MAX_UNZIPPED_BYTES:
            raise PackError(
                f"The pack unpacks to more than {MAX_UNZIPPED_BYTES // (1024 * 1024)} MB, so it was refused. Get a smaller pack from its author.",
                "bad_zip",
            )
        total = 0
        for info in infos:
            with archive.open(info) as handle:
                data = handle.read(MAX_UNZIPPED_BYTES - total + 1)
            total += len(data)
            if total > MAX_UNZIPPED_BYTES:
                raise PackError(
                    f"The pack unpacks to more than {MAX_UNZIPPED_BYTES // (1024 * 1024)} MB, so it was refused. Get a smaller pack from its author.",
                    "bad_zip",
                )
            out[info.filename] = data
    return out


def make_pack(kind: str, name: str, payload: bytes, *, version: int = 1, voice: str = "", lang: str = "", signature: str = "", signer: str = "") -> Pack:
    return Pack(kind, name, int(version), hashlib.sha256(payload).hexdigest(), payload, signature, signer, voice, lang)


def encode(pack: Pack) -> bytes:
    header: dict[str, Any] = {
        "format": FORMAT, "type": pack.type, "name": pack.name, "version": pack.version,
        "size": pack.size, "sha256": pack.sha256,
    }  # fmt: skip
    for key in ("signature", "signer", "voice", "lang"):
        if getattr(pack, key):
            header[key] = getattr(pack, key)
    return MAGIC + json.dumps(header, sort_keys=True, separators=(",", ":")).encode() + b"\n" + pack.payload


def decode(data: bytes, lang: str | None = None, *, verify: Callable[[str, str, str], bool] | None = None) -> Pack:
    """Read and check a pack file: magic, header, type, name, size gate, checksum, optional signature."""
    if not data.startswith(MAGIC):
        raise _fail(lang, "bad_file")
    rest = data[len(MAGIC) :]
    cut = rest.find(b"\n")
    if cut < 0 or cut > 4096:
        raise _fail(lang, "bad_file")
    try:
        header = json.loads(rest[:cut])
    except ValueError:
        raise _fail(lang, "bad_file") from None
    if not isinstance(header, dict) or header.get("format") != FORMAT:
        raise _fail(lang, "bad_file")
    payload = rest[cut + 1 :]
    kind = header.get("type")
    if kind not in TYPES:
        raise _fail(lang, "bad_type", kind=str(kind)[:20], types=", ".join(TYPES))
    name = header.get("name")
    if not isinstance(name, str) or not _NAME.match(name):
        raise _fail(lang, "bad_name")
    version = header.get("version", 1)
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise _fail(lang, "bad_file")
    if len(payload) > MAX_BYTES[kind]:
        raise _fail(lang, "too_big", kind=kind, size=-(-len(payload) // 1000), limit=MAX_BYTES[kind] // 1000)
    digest = hashlib.sha256(payload).hexdigest()
    if header.get("size") != len(payload) or header.get("sha256") != digest:
        raise _fail(lang, "bad_sum")
    signature, signer = str(header.get("signature", "")), str(header.get("signer", ""))
    if signature and verify is not None and not verify(digest, signature, signer):
        raise _fail(lang, "bad_sig")
    return Pack(kind, name, version, digest, payload, signature, signer, str(header.get("voice", "")), str(header.get("lang", "")))


# ---- the library ---------------------------------------------------------------------------------


def default_root() -> Path:
    return Path.home() / ".config" / "maipai" / "stackchan-packs"


def default_filler_root() -> Path:
    return Path.home() / ".config" / "maipai" / "stackchan-fillers"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "pack"


def _private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


class PackLibrary:
    """Packs on disk: one folder per type, files named ``<slug>.maipack``; fillers have their own folder."""

    def __init__(self, root: Path | None = None, *, filler_root: Path | None = None, verify: Callable[[str, str, str], bool] | None = None) -> None:
        self.root = Path(root) if root else default_root()
        self.filler_root = Path(filler_root) if filler_root else (default_filler_root() if root is None else self.root / "filler")
        self._verify = verify
        self._lock = threading.RLock()

    def folder(self, kind: str) -> Path:
        return self.filler_root if kind == "filler" else self.root / kind

    def _path(self, pack_id: str) -> Path:
        kind, _, slug = pack_id.partition("/")
        if kind not in TYPES or not re.fullmatch(r"[a-z0-9][a-z0-9\-]*", slug):
            raise PackError(say(None, "unknown"), "unknown")
        return self.folder(kind) / f"{slug}.maipack"

    def _read(self, path: Path) -> Pack | None:
        try:
            return decode(path.read_bytes(), None, verify=self._verify)
        except (OSError, PackError):
            return None

    def list(self, kind: str | None = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for one in TYPES:
            if kind is not None and one != kind:
                continue
            folder = self.folder(one)
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob("*.maipack")):
                pack = self._read(path)
                if pack is not None and pack.type == one:
                    out.append(self.describe(f"{one}/{path.stem}", pack))
        return out

    @staticmethod
    def describe(pack_id: str, pack: Pack) -> dict[str, Any]:
        return {
            "id": pack_id, "type": pack.type, "name": pack.name, "version": pack.version, "size": pack.size,
            "sha256": pack.sha256, "signed": bool(pack.signature), "voice": pack.voice, "lang": pack.lang,
        }  # fmt: skip

    def total_bytes(self) -> int:
        return sum(p["size"] for p in self.list())

    def get(self, pack_id: str, lang: str | None = None) -> Pack:
        try:
            path = self._path(pack_id)
        except PackError:
            raise _fail(lang, "unknown") from None
        pack = self._read(path)
        if pack is None:
            raise _fail(lang, "unknown")
        return pack

    def add(self, pack: Pack, lang: str | None = None) -> dict[str, Any]:
        """Keep a pack (already checked). The same name replaces the older one."""
        with self._lock:
            slug = _slug(pack.name if not pack.voice else f"{pack.name}-{pack.voice}")
            pack_id = f"{pack.type}/{slug}"
            path = self._path(pack_id)
            old = path.stat().st_size if path.exists() else 0
            if self.total_bytes() - old + pack.size > MAX_LIBRARY_BYTES:
                raise _fail(lang, "library_full", limit=MAX_LIBRARY_BYTES // 1_000_000)
            _private_dir(path.parent)
            fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".pack-")
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(encode(pack))
                os.chmod(tmp, 0o600)
                os.replace(tmp, path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            return self.describe(pack_id, pack)

    def import_bytes(self, data: bytes, lang: str | None = None) -> dict[str, Any]:
        return self.add(decode(data, lang, verify=self._verify), lang)

    def export(self, pack_id: str, lang: str | None = None) -> tuple[str, bytes]:
        pack = self.get(pack_id, lang)
        return f"{pack_id.replace('/', '-')}.maipack", encode(pack)

    def delete(self, pack_id: str, lang: str | None = None) -> None:
        with self._lock:
            try:
                path = self._path(pack_id)
            except PackError:
                raise _fail(lang, "unknown") from None
            if not path.exists():
                raise _fail(lang, "unknown")
            path.unlink()


# ---- which pack each unit uses, and sending only that one ----------------------------------------


class ActiveStore:
    """``{device_id: {type: pack_id}}`` in one small file (mode 600)."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else Path.home() / ".config" / "maipai" / "stackchan-packs-active.json"
        self._lock = threading.Lock()

    def _load(self) -> dict[str, dict[str, str]]:
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def get(self, device_id: str) -> dict[str, str]:
        with self._lock:
            return dict(self._load().get(device_id, {}))

    def set(self, device_id: str, kind: str, pack_id: str | None) -> None:
        with self._lock:
            data = self._load()
            mine = data.setdefault(device_id, {})
            if pack_id is None:
                mine.pop(kind, None)
            else:
                mine[kind] = pack_id
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".active-")
            with os.fdopen(fd, "w") as handle:
                handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)

    def forget_pack(self, pack_id: str) -> None:
        with self._lock:
            data = self._load()
            changed = False
            for mine in data.values():
                for kind in [k for k, v in mine.items() if v == pack_id]:
                    del mine[kind]
                    changed = True
            if changed:
                fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".active-")
                with os.fdopen(fd, "w") as handle:
                    handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
                os.chmod(tmp, 0o600)
                os.replace(tmp, self.path)


class PackService:
    """The page's pack actions: list, import, export, delete, choose the active pack per unit, push only that.

    A person's explicit choice (``active``) always wins. For the managed types (language, filler, phrase) with no explicit
    choice, ``auto`` says which pack the unit's own settings call for (``pack_auto.AutoPacks``), or none; the unit holds only
    what is wanted and is told to drop what is not (its flash cache and PSRAM are small)."""

    def __init__(
        self,
        probe: ToolProbe,
        library: PackLibrary | None = None,
        active: ActiveStore | None = None,
        *,
        chunk: int = CHUNK_BYTES,
        auto: Callable[[str], dict[str, str | None]] | None = None,
    ) -> None:
        self.probe = probe
        self.library = library or PackLibrary()
        self.active = active or ActiveStore()
        self._chunk = chunk
        self.auto = auto
        self._push_lock = threading.Lock()  # one unit conversation at a time: pieces of two packs must never interleave

    # -- the library (host wide) --

    def library_view(self) -> dict[str, Any]:
        return {
            "packs": self.library.list(),
            "types": list(TYPES),
            "limits": {k: v for k, v in MAX_BYTES.items()},
            "used": self.library.total_bytes(),
            "capacity": MAX_LIBRARY_BYTES,
        }

    def import_pack(self, b64: object, lang: str | None = None) -> dict[str, Any]:
        try:
            data = base64.b64decode(str(b64 or ""), validate=True)
        except (ValueError, TypeError):
            raise _fail(lang, "bad_file") from None
        return {"pack": self.library.import_bytes(data, lang), **self.library_view()}

    def export_pack(self, pack_id: object, lang: str | None = None) -> dict[str, Any]:
        name, data = self.library.export(str(pack_id or ""), lang)
        return {"filename": name, "b64": base64.b64encode(data).decode("ascii")}

    def delete_pack(self, pack_id: object, lang: str | None = None) -> dict[str, Any]:
        pid = str(pack_id or "")
        self.library.delete(pid, lang)
        self.active.forget_pack(pid)
        return self.library_view()

    # -- which pack each type should hold --

    def wanted(self, device_id: str) -> dict[str, str | None]:
        """Type -> pack id the unit should hold (None: the built-in set). Explicit choices first, then the managed types' own."""
        out: dict[str, str | None] = dict(self.active.get(device_id))
        if self.auto is not None:
            try:
                chosen = self.auto(device_id)
            except Exception:
                logger.debug("pack choice for unit %s failed", device_id[-5:], exc_info=True)
                chosen = {}
            for kind in MANAGED:
                if kind not in out and kind in chosen:
                    out[kind] = chosen[kind]
        return out

    def unit_state(self, device_id: str) -> dict[str, dict[str, Any]]:
        """What the unit says it holds, per type (one status call each); a type the unit cannot answer for is left out."""
        out: dict[str, dict[str, Any]] = {}
        for kind in TYPES:
            try:
                reply = unwrap(self.probe.call(device_id, "self.pack.status", {"type": kind}, 4.0))
            except (BodyLost, OSError, TimeoutError):
                break
            if reply.get("ok") is True:
                out[kind] = {k: reply.get(k) for k in ("held", "name", "size", "sha256", "cached", "cache", "cache_on", "writing", "fallback", "booted", "lang", "clips")}
        return out

    # -- one unit --

    def view(self, device_id: str, lang: str | None = None) -> dict[str, Any]:
        ready = self.probe.has(device_id, "pack")
        want = self.wanted(device_id)
        unit: dict[str, dict[str, Any]] = self.unit_state(device_id) if ready is True else {}
        rows: dict[str, dict[str, Any]] = {}
        for kind in TYPES:
            pid = want.get(kind)
            pack = None
            if pid:
                try:
                    pack = self.library.get(pid)
                except PackError:
                    pack = None
            held = unit.get(kind, {})
            rows[kind] = {
                "wanted": pid,
                "wanted_name": pack.name if pack else "",
                "wanted_size": pack.size if pack else 0,
                "explicit": kind in self.active.get(device_id),
                "held": bool(held.get("held")),
                "held_name": held.get("name") or "",
                "held_size": held.get("size") or 0,
                "cache": held.get("cache") or "",
                "cached": bool(held.get("cached")),
                "fallback": held.get("fallback", True) if held else True,
                "in_sync": bool(held) and ((pack is None and not held.get("held")) or (pack is not None and held.get("sha256") == pack.sha256)),
            }
        return {
            **self.library_view(),
            "active": self.active.get(device_id),
            "wanted": want,
            "unit": unit,
            "rows": rows,
            "unit_ready": ready is True,
            "reachable": ready is not None,
        }

    def activate(self, device_id: str, kind: object, pack_id: object, lang: str | None = None) -> dict[str, Any]:
        """Choose the active pack of one type for one unit (``pack_id`` empty: back to the built-in)."""
        if kind not in TYPES:
            raise _fail(lang, "bad_type", kind=str(kind)[:20], types=", ".join(TYPES))
        pid = str(pack_id) if pack_id else None
        if pid is not None:
            have = self.library.get(pid, lang)
            if have.type != kind:
                raise _fail(lang, "wrong_type", have=have.type, want=kind)
        self.active.set(device_id, str(kind), pid)
        ready = self.probe.has(device_id, "pack")
        out = {"ok": True, "active": self.active.get(device_id), "unit_ready": ready is True}
        if ready is None:
            return {**out, "pushed": False, "message": say(lang, "kept")}
        if ready is False:
            return {**out, "pushed": False, "pending": True, "message": say(lang, "soon")}
        try:
            self._push_type(device_id, str(kind), lang)
        except PackError as error:
            return {**out, "pushed": False, "message": str(error)}
        return {**out, "pushed": True, "message": say(lang, "sent")}

    def _tool(self, device_id: str, name: str, arguments: dict[str, Any], timeout: float = 8.0) -> dict[str, Any]:
        return self.probe.call(device_id, name, arguments, timeout)

    def _push_type(self, device_id: str, kind: str, lang: str | None) -> None:
        pid = self.wanted(device_id).get(kind)
        with self._push_lock:
            if pid is None:
                self._tool(device_id, "self.pack.remove", {"type": kind})
                return
            pack = self.library.get(pid, lang)
            begin = self._tool(device_id, "self.pack.begin", {"type": kind, "name": pack.name, "version": pack.version, "size": pack.size, "sha256": pack.sha256})
            if begin.get("ok") is not True:
                raise PackError(str(begin.get("error") or say(lang, "send_failed")), "send_failed")
            for at in range(0, pack.size, self._chunk):
                piece = pack.payload[at : at + self._chunk]
                reply = self._tool(device_id, "self.pack.data", {"at": at, "b64": base64.b64encode(piece).decode("ascii")})
                if reply.get("ok") is not True:
                    raise PackError(str(reply.get("error") or say(lang, "send_failed")), "send_failed")
            done = self._tool(device_id, "self.pack.commit", {}, timeout=15.0)
            if done.get("ok") is not True:
                raise PackError(str(done.get("error") or say(lang, "send_failed")), "send_failed")

    def _ensure(self, device_id: str, kind: str, pid: str | None) -> str:
        """Make the unit hold ``pid`` for ``kind`` (None: nothing, the built-in set). Returns what was done: kept, sent, removed, none."""
        held = unwrap(self.probe.call(device_id, "self.pack.status", {"type": kind}))
        if held.get("ok") is not True:
            return "none"
        if pid is None:
            if held.get("held") is not True:
                return "none"
            self._push_type(device_id, kind, None)
            return "removed"
        pack = self.library.get(pid)
        if held.get("held") is True and held.get("sha256") == pack.sha256:
            return "kept"
        self._push_type(device_id, kind, None)
        return "sent"

    def sync_types(self, device_id: str, kinds: tuple[str, ...] | list[str]) -> dict[str, str]:
        """Bring the unit's pack of each given type in step with what is wanted (a setting changed). Never raises."""
        done: dict[str, str] = {}
        if self.probe.has(device_id, "pack") is not True:
            return done
        want = self.wanted(device_id)
        for kind in kinds:
            if kind not in TYPES:
                continue
            try:
                done[kind] = self._ensure(device_id, kind, want.get(kind))
            except (BodyLost, PackError, OSError, TimeoutError):
                logger.debug("pack %s not brought in step on unit %s", kind, device_id[-5:], exc_info=True)
                done[kind] = "failed"
        return done

    def sync(self, device_id: str) -> None:
        """When a unit connects: send each wanted pack the unit does not already hold, and drop a managed pack that is not wanted
        (a pack the person chose is sent; so is the one the unit's language, thinking sound and voice call for). Nothing else is sent."""
        self.probe.forget(device_id)
        if self.probe.has(device_id, "pack") is not True:
            return
        want = self.wanted(device_id)
        kinds = [k for k in TYPES if k in want or k in MANAGED]
        for kind in kinds:
            try:
                self._ensure(device_id, kind, want.get(kind))
            except (BodyLost, PackError, OSError, TimeoutError):
                logger.debug("pack %s not sent to unit %s", kind, device_id[-5:], exc_info=True)


__all__ = [
    "MAX_BYTES", "PackError", "PackLibrary", "PackService", "ActiveStore", "Pack", "TYPES",
    "decode", "encode", "make_pack", "is_unknown_tool", "zip_payload", "unzip_payload",
]  # fmt: skip
