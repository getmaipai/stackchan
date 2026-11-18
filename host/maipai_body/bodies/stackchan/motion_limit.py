"""The unit's movement limiter as the host sees it (firmware patch ML01).

The unit refuses or scales every servo target itself, at the one place they all pass. The host reads ``self.motion.status`` so
it does not keep asking for moves that would be refused, and so the settings page can say why the robot is moving gently:

- ``carried``: held or carried: no movement at all.
- ``orientation_limited``: the IMU says it is leaning (small slow moves only) or on its side, face down or upside down (no movement),
  or the orientation reading is missing or stale (gentle moves).
- ``usb_limited``: on a USB cable: half the excursion, gentler speed, no full dance. ("On USB the robot moves gently.")
- ``battery_limited``: the charge is low: it moves more gently as the battery runs low, and not at all under 8 percent.
- ``free``: no restriction beyond the servo's own limits.

The reading is cached for a few seconds; a unit without the tool counts as free (an older firmware limits nothing).
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from maipai_body.hal.errors import NotSupported

logger = logging.getLogger("maipai_body.bodies.stackchan.motion_limit")

STATUS_TOOL = "self.motion.status"
SET_TOOL = "self.motion.set"
USB_CHOICES = ("limited", "off")
STATE_TTL_S = 5.0

# Plain words for the settings page and the log (English; the page has the Spanish).
HELP_EN = "On USB the robot moves gently; on battery it moves freely. It moves more gently as the battery runs low."
STATE_WORDS_EN = {
    "free": "Moving freely.",
    "usb_limited": "Moving gently because it is on USB.",
    "battery_limited": "Moving gently because the battery is low.",
    "carried": "Not moving because it is held or carried.",
    "orientation_limited": "Moving carefully because it is not standing upright.",
}


@dataclass(frozen=True)
class MotionState:
    state: str = "free"
    scale: int = 100
    speed_cap: int = 1000
    dance_max: int = 4
    battery_band: str = "none"
    usb_limit: str = "limited"
    refused_count: int = 0
    orientation: str = "upright"  # upright, tilted, side, inverted or unknown
    tilt_deg: int = 0

    @property
    def hold(self) -> bool:
        """No movement at all (carried, or the battery hold)."""
        return self.scale == 0

    @property
    def not_upright(self) -> bool:
        """The unit is leaning, on its side or upside down (a missing reading is not counted: it only limits)."""
        return self.orientation in ("tilted", "side", "inverted")

    @property
    def dances_ok(self) -> bool:
        return self.dance_max > 0

    @property
    def why(self) -> str:
        return STATE_WORDS_EN.get(self.state, "")


FREE = MotionState()


def parse_status(raw: object) -> MotionState:
    data = raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except ValueError:
            return FREE
    if not isinstance(data, dict) or data.get("ok") is False:
        return FREE
    state = data.get("state")
    if state not in STATE_WORDS_EN:
        return FREE

    def number(key: str, default: int) -> int:
        value = data.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else default

    return MotionState(
        state=state,
        scale=number("scale", 100),
        speed_cap=number("speed_cap", 1000),
        dance_max=number("dance_max", 4),
        battery_band=str(data.get("battery_band", "none")),
        usb_limit=str(data.get("usb_limit", "limited")),
        refused_count=number("refused_count", 0),
        orientation=str(data.get("orientation", "upright")),
        tilt_deg=number("tilt_deg", 0),
    )


class MotionLimit:
    """Reads the unit's limiter state (cached) and sets the USB choice."""

    def __init__(
        self, call: Callable[[str, dict], object], *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._call = call
        self._clock = clock
        self._state = FREE
        self._at = float("-inf")
        self._unsupported = False
        self._last_logged = ""

    @property
    def unsupported(self) -> bool:
        return self._unsupported

    def state(self, *, fresh: bool = False) -> MotionState:
        now = self._clock()
        if self._unsupported or (not fresh and now - self._at < STATE_TTL_S):
            return self._state
        self._at = now
        try:
            self._state = parse_status(self._call(STATUS_TOOL, {}))
        except NotSupported:
            self._unsupported = True
            self._state = FREE
            logger.info("StackChan firmware has no movement limiter; the host treats it as free")
        except Exception:
            logger.debug("StackChan movement status call failed", exc_info=True)
            return self._state  # keep the last reading; the unit refuses on its own either way
        if self._state.state != self._last_logged:
            self._last_logged = self._state.state
            logger.info(
                "StackChan movement: %s (%s)", self._state.state, self._state.why or "no limit"
            )
        return self._state

    def set_usb(self, choice: str) -> bool:
        if choice not in USB_CHOICES:
            raise ValueError("The USB choice is limited or off.")
        try:
            self._call(SET_TOOL, {"usb_limit": choice})
        except NotSupported:
            return False
        self.state(fresh=True)
        return True


__all__ = ["FREE", "HELP_EN", "MotionLimit", "MotionState", "STATE_WORDS_EN", "parse_status"]
