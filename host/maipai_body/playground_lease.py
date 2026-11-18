"""The playground's control lease and token scope (owner decision 21): one playground session per robot, expiring without heartbeats, and a
scope that keeps lock, update, pairing, key exchange, settings and package tools out of reach. See docs/plan/playground-live.md."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

LEASE_TTL_S = 15.0  # a session that sends no heartbeat for this long loses the robot

# Tool-name prefixes the 'playground' scope never reaches. Everything else goes through the normal controller path (limiter, mute, privacy, lock).
FORBIDDEN_PREFIXES = (
    "self.lock.", "self.firmware.", "self.update.", "self.pair", "self.link.", "self.settings.", "self.pack.", "self.assets.", "self.system.", "self.wifi.",
    "self.reset", "self.factory.",
)
CAMERA_PREFIXES = ("self.camera.", "self.vision.")


def tool_allowed(name: str, *, live_view_allowed: bool = False) -> tuple[bool, str]:
    """Whether the playground scope may call this tool, and the plain reason when not."""
    if any(name.startswith(p) for p in FORBIDDEN_PREFIXES):
        return False, "The playground cannot change the lock, updates, pairing, settings or packs. Do that on the host."
    if any(name.startswith(p) for p in CAMERA_PREFIXES) and not live_view_allowed:
        return False, "The camera is off for the playground. Allow live view on the host first."
    return True, ""


@dataclass
class Lease:
    session: str
    who: str
    started: float
    beat: float


@dataclass
class LeaseLog:
    rows: list[dict] = field(default_factory=list)  # one row per session: unit, who, started, ended, why


class LeaseManager:
    def __init__(self, *, clock: Callable[[], float] = time.monotonic, wall: Callable[[], float] = time.time, ttl: float = LEASE_TTL_S) -> None:
        self._clock, self._wall, self._ttl = clock, wall, ttl
        self._lock = threading.Lock()
        self._leases: dict[str, Lease] = {}
        self.log = LeaseLog()

    def _expire(self, unit: str) -> None:
        lease = self._leases.get(unit)
        if lease is not None and self._clock() - lease.beat > self._ttl:
            self._end(unit, "no heartbeat")

    def _end(self, unit: str, why: str) -> None:
        lease = self._leases.pop(unit, None)
        if lease is not None:
            self.log.rows.append({"unit": unit, "who": lease.who, "started": lease.started, "ended": self._wall(), "why": why})

    def acquire(self, unit: str, session: str, who: str) -> tuple[bool, str]:
        """Take the robot for this session, or refuse in plain words. The same session asking again just renews."""
        with self._lock:
            self._expire(unit)
            held = self._leases.get(unit)
            if held is not None and held.session != session:
                return False, f"Someone else ({held.who}) is controlling this robot from a playground. Wait until they finish, or ask them to disconnect."
            if held is None:
                self._leases[unit] = Lease(session, who, self._wall(), self._clock())
            else:
                held.beat = self._clock()
            return True, ""

    def heartbeat(self, unit: str, session: str) -> bool:
        with self._lock:
            self._expire(unit)
            held = self._leases.get(unit)
            if held is None or held.session != session:
                return False
            held.beat = self._clock()
            return True

    def release(self, unit: str, session: str) -> bool:
        """A clean release when the page disconnects."""
        with self._lock:
            held = self._leases.get(unit)
            if held is None or held.session != session:
                return False
            self._end(unit, "released")
            return True

    def holder(self, unit: str) -> str | None:
        with self._lock:
            self._expire(unit)
            held = self._leases.get(unit)
            return held.who if held else None

    def check(self, unit: str, session: str, tool: str, *, live_view_allowed: bool = False) -> tuple[bool, str]:
        """May this session call this tool on this robot now? (Lease first, then the scope.)"""
        if not self.heartbeat(unit, session):
            return False, "You do not control this robot. Connect to it first (another playground may have it)."
        return tool_allowed(tool, live_view_allowed=live_view_allowed)
