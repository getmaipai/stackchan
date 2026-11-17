# ruff: noqa: E501
"""Who turns the head toward faces: this robot (default), my Home hub, or nobody.

Exactly one party drives face seeking at a time. The unit has its own seeker (firmware patch S10: a motion look at the current view
after the wake word, one bounded search over five pan stops, and a gentle follow). A host that does its own tracking takes the
unit's owner lease so the unit never double-drives:

    self.look.claim   {"owner": "home-hub", "ttl_s": 15}  -> {"ok": true, ...}   renewed every 5 s while the hub's tracking runs
    self.look.release {"owner": "home-hub"}               -> {"ok": true}
    self.look.status  {}                                  -> {"ok": true, "owner": "unit" | "host" | "none", "lease_owner", ...}

The rules, all in this file:

- The setting is "Who turns toward faces": ``robot`` (default), ``hub`` or ``off`` (per unit, ``face_owner``).
- The host claims the lease only when the setting says ``hub``, a Home hub is configured (a host with no Home URL, the local
  ``llm`` brain, never claims) and the hub's tracking really runs (the camera feed is up, a look setting is on, watching is not off).
  Anything else releases a lease this host holds. A claim that fails because another host holds it is not retried hard: the
  next heartbeat tries again, and the unit's own seeker stays off only while a lease is valid.
- The host's own face search (``look_toward_speaker``, ``look_for_faces``) runs when the hub owns seeking, and also when the robot
  owns it but this unit cannot do it yet (no ``self.look.status`` tool, an older unit): nothing regresses until the unit updates.
- A unit that has no look tool is never sent a claim; the page then says "coming with the next unit update".
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterable
from typing import Any

from maipai_body.hal.errors import BodyLost
from maipai_body.unit_tools import ToolProbe, is_unknown_tool

logger = logging.getLogger("maipai_body.look_owner")

LEASE_OWNER = "home-hub"  # the name the unit sees; lowercase letters, digits, dash, dot, underscore
LEASE_TTL_S = 15
HEARTBEAT_S = 5.0
OWNERS = ("robot", "hub", "off")


class LookOwner:
    def __init__(
        self,
        probe: ToolProbe,
        get: Callable[[str], dict[str, Any]],
        *,
        hub_configured: Callable[[], bool],
        tracking: Callable[[], bool],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.probe, self._get, self._hub, self._tracking, self._clock = probe, get, hub_configured, tracking, clock
        self._held: dict[str, float] = {}  # device id -> when we last sent a claim the unit accepted
        self._lock = threading.Lock()
        self.last_state: dict[str, str] = {}

    # -- the setting -------------------------------------------------------------------------------------------------
    def setting(self, device_id: str) -> str:
        owner = self._get(device_id).get("face_owner", "robot")
        return owner if owner in OWNERS else "robot"

    def unit_has_tool(self, device_id: str) -> bool | None:
        return self.probe.has(device_id, "look")

    def host_may_search(self, device_id: str) -> bool:
        """Whether this host's own face search may move the head for this unit now."""
        owner = self.setting(device_id)
        if owner == "hub":
            return True
        if owner == "robot":
            return self.unit_has_tool(device_id) is False  # an older unit cannot seek itself: keep what worked before
        return False

    def wants_lease(self, device_id: str) -> bool:
        return self.setting(device_id) == "hub" and bool(self._hub()) and bool(self._tracking())

    # -- the lease ---------------------------------------------------------------------------------------------------
    def tick(self, device_id: str) -> str:
        """Claim, renew or release as the rules say. Returns what happened (for logs and tests):
        "claimed", "renewed", "released", "idle", "waiting" (not due yet), "unsupported", "busy", "unreachable"."""
        want = self.wants_lease(device_id)
        with self._lock:
            held_at = self._held.get(device_id)
        if not want:
            if held_at is None:
                return self._note(device_id, "idle")
            return self.release(device_id)
        have = self.unit_has_tool(device_id)
        if have is None:
            return self._note(device_id, "unreachable")
        if have is False:
            return self._note(device_id, "unsupported")
        now = self._clock()
        if held_at is not None and now - held_at < HEARTBEAT_S:
            return self._note(device_id, "waiting")
        try:
            reply = self.probe.call(device_id, "self.look.claim", {"owner": LEASE_OWNER, "ttl_s": LEASE_TTL_S})
        except (BodyLost, OSError, TimeoutError):
            with self._lock:
                self._held.pop(device_id, None)  # the unit lets the lease lapse by itself after its ttl
            return self._note(device_id, "unreachable")
        if reply.get("ok") is True:
            with self._lock:
                self._held[device_id] = now
            return self._note(device_id, "renewed" if held_at is not None else "claimed")
        with self._lock:
            self._held.pop(device_id, None)
        if is_unknown_tool(reply):
            return self._note(device_id, "unsupported")
        logger.info("the unit's face seeking is held by another host (%s); this host tries again at the next heartbeat", reply.get("error", ""))
        return self._note(device_id, "busy")

    def release(self, device_id: str) -> str:
        """Give the lease back (a setting changed, tracking stopped, or the host is closing)."""
        with self._lock:
            had = self._held.pop(device_id, None) is not None
        if not had:
            return self._note(device_id, "idle")
        try:
            self.probe.call(device_id, "self.look.release", {"owner": LEASE_OWNER})
        except (BodyLost, OSError, TimeoutError):
            pass  # the unit's ttl ends it in at most 15 s
        return self._note(device_id, "released")

    def forget(self, device_id: str) -> None:
        """The unit connected again (it may have rebooted: a lease is never kept over a reboot). Claim again at the next tick."""
        with self._lock:
            self._held.pop(device_id, None)

    def close(self, devices: Iterable[str]) -> None:
        for device_id in list(devices):
            self.release(device_id)

    def _note(self, device_id: str, state: str) -> str:
        self.last_state[device_id] = state
        return state

    # -- what the page shows -----------------------------------------------------------------------------------------
    def view(self, device_id: str) -> dict[str, Any]:
        have = self.unit_has_tool(device_id)
        with self._lock:
            held = device_id in self._held
        return {
            "face_owner": self.setting(device_id),
            "unit_ready": have is True,
            "reachable": have is not None,
            "lease_held": held,
            "state": self.last_state.get(device_id, "idle"),
            "host_search": self.host_may_search(device_id),
        }


class LookLeaseRunner:
    """The heartbeat: every 5 s each connected unit gets its tick; the host's own face search flags follow the owner."""

    def __init__(self, owner: LookOwner, devices: Callable[[], Iterable[str]], stop: threading.Event, *, apply: Callable[[str], None] | None = None) -> None:
        self.owner, self.devices, self.stop, self.apply = owner, devices, stop, apply

    def run_once(self) -> None:
        for device_id in list(self.devices()):
            try:
                self.owner.tick(device_id)
                if self.apply is not None:
                    self.apply(device_id)
            except Exception:
                logger.debug("face seeking heartbeat failed for %s", device_id[-5:], exc_info=True)

    def run(self) -> None:
        while not self.stop.wait(HEARTBEAT_S):
            self.run_once()
        self.owner.close(self.devices())
