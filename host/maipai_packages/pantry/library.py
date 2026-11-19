"""The master library (docs/design/content-pantry.md, section 6): plain files in the host's data folder, one JSON Lines file per language and kind, the rejected
ids, a heard history per unit and a counter of model calls per day. Nothing leaves the home. The dashboard reads and edits it; the sync builds shelves from it."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path

from maipai_packages.pantry.record import Record


ID_RE = re.compile(r"[0-9a-f]{16}")  # a record id: 8 bytes as lowercase hex


def check_id(id_hex: object) -> str:
    """The id when it is 16 lowercase hex digits; otherwise a ValueError that says what to do (the dashboard shows it as a 400)."""
    if not isinstance(id_hex, str) or not ID_RE.fullmatch(id_hex):
        raise ValueError("A record id is 16 lowercase hex digits. Pick a row from the list and try again.")
    return id_hex


class Library:
    def __init__(self, folder: Path, *, clock: Callable[[], float] = time.time) -> None:
        self.folder = Path(folder)
        self._clock = clock
        self._lock = threading.RLock()
        self._refill_locks: dict[tuple[str, str], threading.RLock] = {}
        self.folder.mkdir(parents=True, exist_ok=True)

    def refill_lock(self, kind: str, language: str) -> threading.RLock:
        """One lock per kind and language: two refills of the same shelf run one after the other, never side by side."""
        with self._lock:
            return self._refill_locks.setdefault((kind, language), threading.RLock())

    # -- records --------------------------------------------------------------------------------------------------------
    def _file(self, language: str, kind: str) -> Path:
        return self.folder / f"{language}-{kind}.jsonl"

    def records(self, kind: str | None = None, language: str | None = None) -> list[Record]:
        out = []
        with self._lock:
            for path in sorted(self.folder.glob("*-*.jsonl")):
                lang, _, rest = path.stem.partition("-")
                if (language and lang != language) or (kind and rest != kind):
                    continue
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        try:
                            out.append(Record.from_json(json.loads(line)))
                        except (ValueError, KeyError):
                            continue  # a damaged line is skipped, never fatal
        return out

    def add(self, records: list[Record]) -> int:
        with self._lock:
            by_file: dict[Path, list[Record]] = {}
            for record in records:
                by_file.setdefault(self._file(record.language, record.kind), []).append(record)
            for path, group in by_file.items():
                with path.open("a", encoding="utf-8") as handle:
                    for record in group:
                        handle.write(json.dumps(record.to_json(), ensure_ascii=False) + "\n")
        return len(records)

    def _rewrite(self, drop: set[str]) -> int:
        removed = 0
        with self._lock:
            for path in self.folder.glob("*-*.jsonl"):
                lines = path.read_text(encoding="utf-8").splitlines()
                keep = []
                for line in lines:
                    try:
                        rid = json.loads(line).get("id")
                    except ValueError:
                        rid = None
                    if rid in drop:
                        removed += 1
                    else:
                        keep.append(line)
                if len(keep) != len(lines):
                    tmp = path.with_suffix(".tmp")
                    tmp.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
                    os.replace(tmp, path)
        return removed

    def delete(self, id_hex: str) -> bool:
        """Remove a record from the library. It may be generated again later; use never_again to keep it out."""
        return self._rewrite({check_id(id_hex)}) > 0

    def never_again(self, id_hex: str) -> bool:
        """Remove it and keep its id on the rejected list, so it is never generated, stored or offered again."""
        check_id(id_hex)
        self._rewrite({id_hex})
        with self._lock:
            ids = self.refused()
            ids.add(id_hex)
            self._write_json("rejected.json", sorted(ids))
        return True

    def refused(self) -> set[str]:
        stored = self._read_json("rejected.json", [])
        return {x for x in stored if isinstance(x, str) and ID_RE.fullmatch(x)} if isinstance(stored, list) else set()  # a damaged entry is skipped, never fatal

    def refused_ids(self) -> set[bytes]:
        return {bytes.fromhex(x) for x in self.refused()}

    # -- what each unit has been told to refuse ---------------------------------------------------------------------------
    def denied_on(self, unit: str) -> set[str]:
        stored = self._read_json(f"denied-{_safe(unit)}.json", [])
        return {x for x in stored if isinstance(x, str) and ID_RE.fullmatch(x)} if isinstance(stored, list) else set()

    def note_denied(self, unit: str, ids: list[str]) -> None:
        with self._lock:
            self._write_json(f"denied-{_safe(unit)}.json", sorted(self.denied_on(unit) | {i for i in ids if ID_RE.fullmatch(i)}))

    # -- heard ----------------------------------------------------------------------------------------------------------
    def heard(self, unit: str) -> dict[str, dict]:
        return self._read_json(f"heard-{_safe(unit)}.json", {})

    def note_heard(self, unit: str, entries: list[dict]) -> int:
        """Entries from the unit's heard list: {"id": low 32 bits as hex, "counter": n, "deny": bool}. Matched to full ids by the low 32 bits."""
        known = {r.id_hex[:8]: r.id_hex for r in self.records()}
        with self._lock:
            heard = self.heard(unit)
            added = 0
            for entry in entries:
                if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not re.fullmatch(r"[0-9a-f]{8,16}", entry["id"]):
                    continue  # not a record id: skipped, never fatal
                full = known.get(entry["id"][:8])
                if full is None:
                    continue
                try:
                    counter = int(entry.get("counter", 0))
                except (TypeError, ValueError):
                    continue
                row = heard.setdefault(full, {"n": 0, "counter": 0})
                row["n"] += 1
                row["counter"] = max(int(row["counter"]), counter)
                row["at"] = int(self._clock())
                added += 1
                if entry.get("deny") or entry.get("denied"):
                    ids = self.refused()
                    ids.add(full)
                    self._write_json("rejected.json", sorted(ids))
            self._write_json(f"heard-{_safe(unit)}.json", heard)
        return added

    def unheard(self, unit: str, kind: str, language: str) -> list[Record]:
        heard, refused = self.heard(unit), self.refused()
        return [r for r in self.records(kind, language) if r.id_hex not in heard and r.id_hex not in refused]

    # -- model call budget ----------------------------------------------------------------------------------------------
    def calls_today(self) -> int:
        row = self._read_json("calls.json", {})
        return int(row.get("n", 0)) if row.get("day") == _day(self._clock()) else 0

    def note_calls(self, n: int) -> None:
        with self._lock:
            self._write_json("calls.json", {"day": _day(self._clock()), "n": self.calls_today() + n})

    # -- the last dedupe and filter report (for the dashboard) ---------------------------------------------------------
    def save_report(self, report: dict) -> None:
        self._write_json("last-report.json", report)

    def last_report(self) -> dict:
        return self._read_json("last-report.json", {})

    # -- files ----------------------------------------------------------------------------------------------------------
    def _read_json(self, name: str, default):
        try:
            return json.loads((self.folder / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default

    def _write_json(self, name: str, value) -> None:
        tmp = (self.folder / name).with_suffix(".tmp")
        tmp.write_text(json.dumps(value), encoding="utf-8")
        os.replace(tmp, self.folder / name)


def _safe(unit: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in unit)


def _day(now: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(now))
