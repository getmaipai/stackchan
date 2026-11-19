"""The unit link over the firmware's pantry tools (firmware patches on fw/unproven2: `self.pantry.status`, `.heard`, `.deny`; the shelf itself goes through `self.assets.*`).

``call(unit, tool, args)`` is any function that calls a tool on one unit (the host passes its per-unit client). Status and the heard list are real; installing a shelf needs the multi-slot
asset transport (`self.assets.install/data/commit` with the MPAH header, docs/plan/installed-set.md B4), which is a separate piece: until it is given as ``installer`` the install
is refused in plain words and the sync leaves the old shelf alone."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

KINDS = ("joke", "riddle", "trivia", "story")


def _dict(reply: Any) -> dict:
    if isinstance(reply, dict):
        return reply
    import json

    try:
        data = json.loads(reply) if isinstance(reply, (str, bytes)) else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


class ToolUnitLink:
    def __init__(self, call: Callable[[str, str, dict], Any], installer: Callable[[str, str, str, bytes], bool] | None = None) -> None:
        self._call, self._installer = call, installer

    def status(self, unit: str) -> list[dict]:
        """One row per kind on each shelf: {"kind", "language", "count", "unheard"}, the shape the refill rule reads."""
        reply = _dict(self._call(unit, "self.pantry.status", {}))
        if reply.get("ok") is not True:
            return []
        rows = []
        for shelf in reply.get("shelves", []):
            counts, unheard = shelf.get("counts", {}) or {}, shelf.get("unheard", {}) or {}
            for kind in KINDS:
                if counts.get(kind) is not None:
                    rows.append({"kind": kind, "language": str(shelf.get("language", "")), "count": int(counts.get(kind) or 0), "unheard": int(unheard.get(kind) or 0), "bytes": int(shelf.get("bytes", 0) or 0)})
        return rows

    def heard_since(self, unit: str, seq: int) -> tuple[list[dict], int]:
        """Everything the unit has heard since ``seq``, in its batches of up to 64; the unit drops what it is told it has been acknowledged."""
        out: list[dict] = []
        counter = seq
        for _ in range(20):  # at most 20 batches a pass: a flood is read over several passes
            reply = _dict(self._call(unit, "self.pantry.heard", {"since": counter}))
            if reply.get("ok") is not True:
                break
            out += [e for e in reply.get("entries", []) if isinstance(e, dict)]
            counter = int(reply.get("counter", counter))
            if not reply.get("more"):
                break
        return out, counter

    def deny(self, unit: str, ids: list[str]) -> bool:
        """Tell the unit to refuse these ids (the first 4 bytes of each, as 8 hex digits). True only when the unit counts every one of them, new or already denied."""
        short = sorted({i[:8] for i in ids if len(i) >= 8})
        if not short:
            return True
        reply = _dict(self._call(unit, "self.pantry.deny", {"ids": ",".join(short)}))
        try:
            return reply.get("ok") is True and int(reply.get("denied", 0)) >= len(short)
        except (TypeError, ValueError):
            return False

    def install_shelf(self, unit: str, kind: str, language: str, body: bytes) -> bool:
        if self._installer is None:
            return False  # the asset transport is not wired yet: the unit keeps its old shelf
        return bool(self._installer(unit, kind, language, body))
