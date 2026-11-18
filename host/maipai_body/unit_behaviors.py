# ruff: noqa: E501
"""Touch and reaction handling for every connected unit after the first (decision 16, docs/plan/per-unit-behavior.md, step 2).

The first unit keeps the host's main behavior object. Every other unit gets its own behavior object built for that unit's robot handle, so a tap, pat or
shake on it shows that unit's reaction and wakes that unit, and nothing reaches the others.

A unit's event queue is read once, by the host's other-unit poll (privacy, timers). That poll hands every event list to ``feed`` here, so the queue is never
read twice and no event is lost to a second reader. One thread ticks the extra units; one unit failing never stops another.
What this step does not do for an extra unit: spoken reactions (the host speaks reactions only with one unit connected), rest and idle moves (step 4), and
face search (it reads one camera)."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

LOG = logging.getLogger(__name__)
TICK_S = 0.2
MAX_PENDING = 200  # events held per unit between ticks; a flood drops the oldest, never grows without bound


def _unit_scope(device_id: str):
    """While one unit's behavior runs, every call it makes (a face, a tool) names that unit, never the first one."""
    from contextlib import contextmanager

    from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

    @contextmanager
    def scope():
        token = ACTIVE_UNIT.set(device_id)
        try:
            yield
        finally:
            ACTIVE_UNIT.reset(token)

    return scope()


class _Slot:
    def __init__(self, behavior: Any) -> None:
        self.behavior = behavior
        self.events: deque = deque(maxlen=MAX_PENDING)
        self.lock = threading.Lock()

    def drain(self) -> list:
        with self.lock:
            out = list(self.events)
            self.events.clear()
        return out


class UnitBehaviors:
    def __init__(
        self,
        *,
        primary_id: Callable[[], str | None],
        connected: Callable[[], list[str]],
        make_behavior: Callable[[str], Any],
        clock: Callable[[], float] = time.monotonic,
        scope: Callable[[str], Any] | None = None,
    ) -> None:
        self._primary_id, self._connected, self._make, self._clock = primary_id, connected, make_behavior, clock
        self._scope = scope or _unit_scope
        self._slots: dict[str, _Slot] = {}
        self._lock = threading.Lock()

    def _slot(self, device_id: str) -> _Slot:
        with self._lock:
            slot = self._slots.get(device_id)
            if slot is None:
                behavior = self._make(device_id)
                slot = _Slot(behavior)
                behavior.event_poll = slot.drain  # the behavior's own poll reads what the host's poll handed over
                self._slots[device_id] = slot
            return slot

    def feed(self, device_id: str, events: list) -> None:
        """The other-unit poll's hook: queue one unit's new events for its behavior. Never called for the first unit."""
        if not device_id or device_id == self._primary_id():
            return
        slot = self._slot(device_id)
        with slot.lock:
            slot.events.extend(events)

    def tick(self) -> None:
        """One pass over the extra units: touch, then the reaction timer. A raise in one unit is logged and the next unit still runs."""
        now = self._clock()
        live = set(self._connected())
        with self._lock:
            gone = [d for d in self._slots if d not in live or d == self._primary_id()]
            for device_id in gone:
                del self._slots[device_id]  # a unit that left, or became the first unit, is rebuilt when it comes back
            slots = list(self._slots.items())
        for device_id, slot in slots:
            behavior = slot.behavior
            try:
                with self._scope(device_id):
                    behavior.wake_on_touch(now)
                    tick = getattr(behavior, "reaction_tick", None)
                    if tick is not None:
                        tick()
            except Exception:
                behavior._warn_limited("unit-loop", f"the touch loop of unit {device_id[-5:]} failed")

    def run(self, stop_event: threading.Event) -> None:
        while not stop_event.wait(TICK_S):
            try:
                self.tick()
            except Exception:
                LOG.warning("the per-unit behavior loop failed", exc_info=True)

    def start(self, stop_event: threading.Event) -> threading.Thread:
        thread = threading.Thread(target=self.run, args=(stop_event,), name="stackchan-unit-behaviors", daemon=True)
        thread.start()
        return thread

    def units(self) -> list[str]:
        with self._lock:
            return sorted(self._slots)
