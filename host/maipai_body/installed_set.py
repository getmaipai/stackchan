"""The installed set of one robot (decision 17): a few slots per kind, chosen on the dashboard, sent to the unit as signed assets and swapped
without a reflash. This module is the host's record and its reconciler; the unit half (`self.assets.*`) is the firmware track's
(docs/plan/installed-set.md).

Until a unit reports the `assets` tools, the host applies the first chosen item of each kind through the pack tools the unit has today
(`self.pack.*`, one pack per kind) and says so plainly for the rest.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from maipai_body.asset_transport import AssetTransport
from maipai_body.packs import MAX_BYTES, TYPES, PackError, PackLibrary

LOG = logging.getLogger(__name__)

# Slots per kind on one robot, and the plain name of the kind. The counts are the host's proposal for the memory budget (decision 11);
# the unit and the virtual unit enforce the same table (docs/plan/installed-set.md). Change them there and here together.
SLOTS: dict[str, int] = {"look": 3, "language": 2, "filler": 1, "sound": 2, "dance": 3, "game": 4, "phrase": 1}
KIND_WORDS = {"look": "Faces", "language": "Languages", "filler": "Thinking sounds", "sound": "Sounds", "dance": "Dances", "game": "Games", "phrase": "Offline phrases"}
UNIT_PACK_BUDGET = 3_000_000  # bytes of installed assets one robot may hold in all (placeholder until the firmware track confirms the memory table)
STARTER_GAMES = 3


class Transport(Protocol):
    """What the reconciler needs from a unit. ``legacy`` is the pack-tool implementation; the `self.assets.*` one comes with the firmware half."""

    def connected(self, unit: str) -> bool: ...
    def multi_slot(self, unit: str) -> bool: ...
    def held(self, unit: str, kind: str) -> list[str]: ...  # sha256 of what the unit holds of this kind
    def install(self, unit: str, kind: str, pack_id: str) -> None: ...  # raises PackError / OSError on failure
    def remove(self, unit: str, kind: str, sha: str | None) -> None: ...


class InstalledStore:
    """``{unit: {"mode": "automatic"|"custom", "chosen": {kind: [pack ids]}, "items": {pack id: {...state}}}}`` in one 0600 file."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text())
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def get(self, unit: str) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._load().get(unit, {})))

    def put(self, unit: str, record: dict[str, Any]) -> None:
        with self._lock:
            data = self._load()
            data[unit] = record
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".installed-")
            with os.fdopen(fd, "w") as handle:
                handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)

    def units(self) -> list[str]:
        with self._lock:
            return sorted(self._load())


class InstalledSets:
    def __init__(self, library: PackLibrary, store: InstalledStore, transport: Transport, *, language: Callable[[str], str] = lambda unit: "en", clock: Callable[[], float] = time.time) -> None:
        self.library, self.store, self.transport, self._language, self._clock = library, store, transport, language, clock

    def _lock(self, unit: str) -> threading.RLock:
        return AssetTransport.lock_for(unit)  # shared with the pantry shelf installer: the unit holds one install session

    # -- the catalog and the defaults -------------------------------------------------------------------------------------
    def catalog(self) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {kind: [] for kind in TYPES}
        for item in self.library.list():
            out[item["type"]].append({"id": item["id"], "name": item["name"], "size": item["size"], "sha256": item["sha256"], "lang": item.get("lang", ""), "signed": item.get("signed", False)})
        return out

    def defaults(self, unit: str) -> dict[str, list[str]]:
        """The person's language, the default face and a starter set of games: what fills the slots on first run and in Automatic mode."""
        catalog, lang = self.catalog(), self._language(unit)
        chosen: dict[str, list[str]] = {}
        languages = [i for i in catalog["language"] if i["lang"] == lang]
        if languages:
            chosen["language"] = [languages[0]["id"]]
        looks = [i for i in catalog["look"] if "default" in i["name"].lower()] or catalog["look"][:1]
        if looks:
            chosen["look"] = [looks[0]["id"]]
        if catalog["game"]:
            chosen["game"] = [i["id"] for i in catalog["game"][:STARTER_GAMES]]
        phrases = [i for i in catalog["phrase"] if i["lang"] == lang]
        if phrases:
            chosen["phrase"] = [phrases[0]["id"]]
        return chosen

    # -- reading and choosing -----------------------------------------------------------------------------------------------
    def view(self, unit: str) -> dict[str, Any]:
        record = self.store.get(unit)
        mode = record.get("mode", "automatic")
        chosen = self.defaults(unit) if mode == "automatic" else record.get("chosen", {})
        catalog = self.catalog()
        by_id = {i["id"]: i for items in catalog.values() for i in items}
        items = record.get("items", {})
        kinds = {}
        for kind in TYPES:
            ids = [i for i in chosen.get(kind, []) if i in by_id]
            kinds[kind] = {
                "label": KIND_WORDS[kind], "slots": SLOTS[kind], "used": len(ids), "catalog": catalog[kind],
                "chosen": [{"id": i, "name": by_id[i]["name"], "size": by_id[i]["size"], "state": items.get(i, {}).get("state", "waiting"), "message": items.get(i, {}).get("message", "")} for i in ids],
            }
        total = sum(c["size"] for k in kinds.values() for c in k["chosen"])
        warnings = self.problems(chosen)
        return {
            "unit": unit, "mode": mode, "connected": self.transport.connected(unit), "multi_slot": self.transport.multi_slot(unit),
            "kinds": kinds, "meter": {"used_bytes": total, "budget_bytes": UNIT_PACK_BUDGET, "percent": min(100, round(100 * total / UNIT_PACK_BUDGET))},
            "warnings": warnings,
            "summary": self._summary(unit, kinds, warnings),
        }

    def _summary(self, unit: str, kinds: dict[str, Any], warnings: list[str]) -> str:
        states = [c["state"] for k in kinds.values() for c in k["chosen"]]
        if warnings:
            return warnings[0]
        if not self.transport.connected(unit) and any(s != "installed" for s in states):
            return "The robot is away. It gets its set the next time it connects."
        if any(s in ("installing", "waiting") for s in states):
            return "Sending your choices to the robot."
        if any(s == "failed" for s in states):
            return "One choice did not reach the robot. It tries again by itself."
        return "The robot has the set you chose." if states else "The robot uses its built-in set."

    def problems(self, chosen: dict[str, list[str]]) -> list[str]:
        """Plain reasons a choice does not fit (empty when it fits)."""
        catalog = self.catalog()
        by_id = {i["id"]: i for items in catalog.values() for i in items}
        out: list[str] = []
        total = 0
        for kind in TYPES:
            ids = chosen.get(kind, [])
            if len(ids) > SLOTS[kind]:
                out.append(f"{KIND_WORDS[kind]}: the robot has room for {SLOTS[kind]} and you picked {len(ids)}. Take one off to add another.")
            for i in ids:
                if i not in by_id or i.split("/", 1)[0] != kind:
                    out.append(f"{KIND_WORDS[kind]}: one choice is no longer in the library. Choose again.")
                else:
                    total += by_id[i]["size"]
        if total > UNIT_PACK_BUDGET:
            out.append(f"Your choices need {total // 1000} KB and the robot keeps at most {UNIT_PACK_BUDGET // 1000} KB in all. Take something off.")
        return out

    def choose(self, unit: str, mode: str, chosen: dict[str, list[str]] | None = None) -> dict[str, Any]:
        """Save a choice (Automatic, or an explicit set that must fit). Returns the view; raises ValueError with the plain reason."""
        if mode not in ("automatic", "custom"):
            raise ValueError("The mode is automatic or custom.")
        record = self.store.get(unit)
        if mode == "custom":
            wanted = {k: list(v) for k, v in (chosen or {}).items() if k in TYPES}
            problems = self.problems(wanted)
            if problems:
                raise ValueError(problems[0])
            record["chosen"] = wanted
        record["mode"] = mode
        self.store.put(unit, record)
        return self.view(unit)

    # -- making the robot match ---------------------------------------------------------------------------------------------
    def reconcile(self, unit: str) -> dict[str, str]:
        """Bring one robot in step with its set: install what is missing, remove what is not chosen. Never raises. Returns {pack id: state}."""
        with self._lock(unit):
            record = self.store.get(unit)
            chosen = self.defaults(unit) if record.get("mode", "automatic") == "automatic" else record.get("chosen", {})
            items: dict[str, Any] = record.setdefault("items", {})
            result: dict[str, str] = {}
            if not self.transport.connected(unit):
                for ids in chosen.values():
                    for i in ids:
                        if items.get(i, {}).get("state") != "installed":
                            items[i] = {"state": "waiting", "message": "The robot is away. It is sent when it connects."}
                self.store.put(unit, record)
                return {i: s["state"] for i, s in items.items()}
            multi = self.transport.multi_slot(unit)
            catalog = self.catalog()
            sha_of = {i["id"]: i["sha256"] for items_ in catalog.values() for i in items_}
            for kind in TYPES:
                ids = [i for i in chosen.get(kind, []) if i in sha_of]
                held = set(self.transport.held(unit, kind))
                apply = ids if multi else ids[:1]
                for i in ids:
                    if i not in apply:
                        items[i] = {"state": "waiting", "message": "This robot's software holds one of these at a time. The others wait for its next update."}
                        continue
                    if sha_of[i] in held:
                        items[i] = {"state": "installed", "message": ""}
                    else:
                        attempts = int(items.get(i, {}).get("tries", 0)) + 1
                        items[i] = {"state": "installing", "message": "", "tries": attempts}
                        try:
                            self.transport.install(unit, kind, i)
                            items[i] = {"state": "installed", "message": "", "tries": 0}
                        except (PackError, OSError, TimeoutError, Exception) as error:  # a bad signature, a lost connection, power loss: tried again later
                            items[i] = {"state": "failed", "message": str(error)[:160] or "The robot did not take it. It tries again by itself.", "tries": attempts}
                for sha in held:
                    if not multi and ids and sha_of.get(ids[0]) != sha or (multi and sha not in {sha_of[i] for i in ids}):
                        try:
                            self.transport.remove(unit, kind, sha)
                        except Exception:
                            LOG.debug("could not remove an unused %s from %s", kind, unit[-5:], exc_info=True)
                if not ids and held:
                    try:
                        self.transport.remove(unit, kind, None)
                    except Exception:
                        LOG.debug("could not clear %s on %s", kind, unit[-5:], exc_info=True)
            keep = {i for ids in chosen.values() for i in ids}
            record["items"] = {i: s for i, s in items.items() if i in keep}
            record["reconciled_at"] = self._clock()
            self.store.put(unit, record)
            return {i: s["state"] for i, s in record["items"].items()}

    def pending(self) -> list[str]:
        """Units whose set is not fully installed (the retry loop asks them again)."""
        out = []
        for unit in self.store.units():
            if any(s.get("state") != "installed" for s in self.store.get(unit).get("items", {}).values()):
                out.append(unit)
        return out
