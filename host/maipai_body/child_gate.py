"""Whether a child is near any unit, as Home last said (the `child_present` hub command). Shared by the command bus gate
and the packages that must not act while a child is near. Notes expire, so a missing refresh ends the hold."""

from __future__ import annotations

import threading
import time

_LOCK = threading.Lock()
_UNTIL: dict[str, float] = {}
_CLOCK = time.monotonic


def note(device_id: str, present: bool, seconds: float = 300.0) -> None:
    with _LOCK:
        if present:
            _UNTIL[device_id] = _CLOCK() + max(1.0, float(seconds))
        else:
            _UNTIL.pop(device_id, None)


def present_for(device_id: str) -> bool:
    with _LOCK:
        return _UNTIL.get(device_id, 0.0) > _CLOCK()


def any_present() -> bool:
    with _LOCK:
        now = _CLOCK()
        return any(until > now for until in _UNTIL.values())
