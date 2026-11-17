# ruff: noqa: E501
"""Which optional tools a unit has: asked once, remembered, asked again after a while or a reconnect.

The firmware grows tools one release at a time (overlays, packs, filler sounds, listening cues). The host
builds its half first and must not break or nag on a unit that does not have a tool yet, so every optional
feature asks here. A unit that answers a probe with an error saying the tool is unknown is *without* the
feature; a unit that cannot be reached is *unknown* (nothing is remembered, nothing is sent).

When a real tool list is available (``tool_list(device_id) -> set of names or None``) it is used instead of
probing.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from typing import Any

from maipai_body.hal.errors import BodyLost

RECHECK_S = 90.0  # a unit without a tool is asked again after this long (it may have been updated)

# One probe per feature: a read-only tool the feature always ships with.
PROBES: dict[str, tuple[str, dict[str, Any]]] = {
    "overlay": ("self.overlay.status", {}),
    "pack": ("self.pack.status", {"type": "look"}),
    "filler": ("self.filler.status", {}),
    "prefs": ("self.prefs.get", {}),
    "look": ("self.look.status", {}),  # who turns the head toward faces: this unit's seeker and its owner lease
    "pages": ("self.pages.status", {}),  # the swipe pages and the control sheet (firmware patches P10 to P13)
    "remote": ("self.remote.session", {"active": False, "label": ""}),  # the remote cue: glyph, banner, message bubble
}


def unwrap(reply: object) -> dict[str, Any]:
    """The tool's answer as a dict, whatever the link wrapped it in (same rules as the picture faces)."""
    from maipai_body.picture_faces import _unwrap

    return _unwrap(reply)


def is_unknown_tool(reply: dict[str, Any]) -> bool:
    return reply.get("ok") is not True and "unknown tool" in str(reply.get("error", "")).lower()


class ToolProbe:
    def __init__(
        self,
        call: Callable[..., object],
        *,
        tool_list: Callable[[str], set[str] | None] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._call, self._tool_list, self._clock = call, tool_list, clock
        self._seen: dict[tuple[str, str], tuple[bool, float]] = {}
        self._lock = threading.Lock()

    def forget(self, device_id: str) -> None:
        """A unit connected again: ask afresh."""
        with self._lock:
            for key in [k for k in self._seen if k[0] == device_id]:
                del self._seen[key]

    def has(self, device_id: str, feature: str) -> bool | None:
        """True, False, or None when the unit cannot be reached right now."""
        probe, probe_args = PROBES[feature]
        if self._tool_list is not None:
            names = self._tool_list(device_id)
            if names is not None:
                return probe in names
        now = self._clock()
        with self._lock:
            known = self._seen.get((device_id, feature))
        if known is not None and (known[0] or now - known[1] < RECHECK_S):
            return known[0]
        try:
            reply = unwrap(self._call(probe, dict(probe_args), device_id=device_id, timeout=3.0))
        except (BodyLost, OSError, TimeoutError):
            return None
        have = not is_unknown_tool(reply)
        with self._lock:
            self._seen[(device_id, feature)] = (have, now)
        return have

    def call(self, device_id: str, name: str, arguments: dict[str, Any], timeout: float = 5.0) -> dict[str, Any]:
        return unwrap(self._call(name, arguments, device_id=device_id, timeout=timeout))


def dumps(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)
