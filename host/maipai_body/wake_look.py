# ruff: noqa: E501
"""Look around when the wake word is heard (the per-unit setting ``look_on_wake``, default on).

A short head turn so the robot seems to look for the person who called it. It needs no camera frame. On the unit's ``listening`` state
(``StackChanBehavior.render_turn_state``): turn to a face seen in the last 60 s, else glance up 12 degrees, then pan 25 left and 25 right
at 12 up (slow, about 3.3 s in all) and hold center-up through the reply; the turn's own settle brings the head back to level.

This module holds the numbers and the one check that asks the unit (locked? a game playing?). The moves and the gates live in
``app.py`` next to the other head moves, so they share the head gate, the lease and the touch handling.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("maipai_body.wake_look")

PITCH_DEG = 12.0  # up from level: the glance, and every stop of the pan
PAN_DEG = 25.0  # left and right of center
SPEED = 100  # the servo's slowest setting (head_search.MOVE_SPEED): smooth, never a snap
GLANCE_S = 0.5  # the glance up (the first move, made inside the listening state)
# After the glance: (yaw degrees, move seconds, pause seconds). Glance 0.5 + 0.2 here + 1.0 + 1.2 + 0.4 = 3.3 s.
STEPS: tuple[tuple[float, float, float], ...] = (
    (-PAN_DEG, 0.7, 0.3),
    (PAN_DEG, 0.9, 0.3),
    (0.0, 0.4, 0.0),
)
PAUSE_AFTER_GLANCE_S = 0.2
COOLDOWN_S = 15.0  # at most one wake look this often (head_search.SPEAKER_COOLDOWN_S)
UNIT_CHECK_TTL_S = 5.0  # how long an answer from the unit (locked, game) is reused


class UnitCheck:
    """Whether the unit is locked or playing a game, asked through the unit's own tools (``self.lock.status``, ``self.game.list``).

    The answer is reused for UNIT_CHECK_TTL_S so a burst of wakes asks once. A unit that cannot answer, or has no such tool, counts as
    "not locked, not playing": the unit enforces its own lock and ends a game by itself, so this check only adds a polite skip."""

    def __init__(
        self,
        probe: Callable[[], Any],
        device_id: Callable[[], str | None],
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._probe, self._device_id, self._clock = probe, device_id, clock
        self._at = float("-inf")
        self._reason = ""

    def reason(self) -> str:
        """"locked", "playing a game" or ""."""
        now = self._clock()
        if now - self._at < UNIT_CHECK_TTL_S:
            return self._reason
        self._at = now
        self._reason = self._ask()
        return self._reason

    def _ask(self) -> str:
        probe, device_id = self._probe(), self._device_id()
        if probe is None or not device_id:
            return ""
        try:
            lock = probe.call(device_id, "self.lock.status", {}, timeout=1.0)
            if lock.get("ok") is True and lock.get("locked") is True:
                return "locked"
            games = probe.call(device_id, "self.game.list", {}, timeout=1.0)
            playing = games.get("playing")
            if games.get("ok") is True and playing not in (None, False, "", 0, "false"):
                return "playing a game"
        except Exception as exc:  # unit not reachable or no such tool: the unit's own rules still hold
            logger.debug("wake look: the unit check failed (%s)", type(exc).__name__)
        return ""
