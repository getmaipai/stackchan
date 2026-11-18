"""SLEEP-AUTO-01: dark and quiet means sleep, arrival wakes.

``SleepAutoPolicy`` decides when the body enters or leaves the ``sleep``
state. It sees only a mean luma number (``mean_luma`` reduces a frame to
one float and keeps nothing), the DoA speech flag, a face flag and a knock.
It never touches audio: the wake word stays live because nothing here
pauses the capture or the spotter.

Rules:

* dark (mean luma under ``DARK_LUMA``) and no speech, both for 10 minutes,
  enter sleep. Light alone or sound alone never does: either one resets the
  clock. With no luma reading (the camera is off at watch level ``off``),
  the dark rule cannot run at all.
* a face, speech or a knock wakes within one call.
* quiet hours enter sleep regardless of light and sound, and the
  ``robot.sleep.auto`` setting gates only the dark-and-quiet rule. After a
  wake inside quiet hours the body stays awake until 10 minutes pass with
  no face and no speech.

``DARK_LUMA`` and the 10 minutes are design defaults, UNMEASURED.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from datetime import time as dtime
from typing import Literal

from maipai_body.settings_keys import (
    QUIET_DAYS_KEY,
    QUIET_ENABLED_KEY,
    QUIET_FROM_KEY,
    QUIET_NOW_KEY,
    QUIET_TO_KEY,
)

DARK_LUMA = 25.0  # of 255; UNMEASURED
QUIET_FOR_S = 600.0

SleepEdge = Literal["sleep", "wake"]


def mean_luma(frame: object) -> float:
    """Reduce a frame (H x W or H x W x C array) to its mean value; nothing is kept."""
    import numpy as np

    return float(np.asarray(frame, dtype=np.float32).mean())


def luma_reader(
    camera: object, *, level: Callable[[], str] = lambda: "presence"
) -> Callable[[], float | None]:
    """A luma source over a camera with ``get_frame``. At watch level ``off`` the camera
    is never read; the frame is subsampled and nothing is kept."""

    def read() -> float | None:
        if level() == "off":
            return None
        frame = camera.get_frame()  # type: ignore[attr-defined]
        if frame is None:
            return None
        import numpy as np

        return mean_luma(np.asarray(frame)[::8, ::8])

    return read


def _parse_days(value: object) -> int | None:
    """A list of days (0 Sunday to 6 Saturday) or the bitmask 0 to 127; anything else is no change."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 0 <= value <= 127 else None
    if isinstance(value, (list, tuple)) and all(isinstance(d, int) and not isinstance(d, bool) and 0 <= d <= 6 for d in value):
        mask = 0
        for d in value:
            mask |= 1 << d
        return mask
    return None


def _parse_clock(value: object) -> dtime | None:
    if not isinstance(value, str):
        return None
    try:
        hour, minute = value.split(":")
        return dtime(int(hour), int(minute))
    except ValueError:
        return None


DEFAULT_QUIET_FROM = dtime(21, 0)  # the registry defaults of household.quiet_hours.*
DEFAULT_QUIET_TO = dtime(7, 0)


class QuietHours:
    """The household quiet schedule, like a phone's Do Not Disturb (owner decision 22).

    A window (``household.quiet_hours.from`` and ``.to``), the days it applies to
    (``household.quiet_hours.days``, a list of 0 Sunday to 6 Saturday or the bitmask 0 to 127) and a
    one-tap "Quiet now" (``household.quiet_hours.now``). It is off until a person sets it: with no
    window given there are no quiet hours. Setting a window turns the schedule on;
    ``household.quiet_hours.enabled`` false turns it off again and keeps the window. A window that
    crosses midnight belongs to the day it starts on; equal bounds mean never; a malformed value
    keeps the last good one. Alarms and timers the person set still ring, and the safety cues never
    stop: the unit and the sound service apply those exceptions."""

    def __init__(self, now: Callable[[], datetime] = datetime.now) -> None:
        self._now = now
        self._from: dtime = DEFAULT_QUIET_FROM
        self._to: dtime = DEFAULT_QUIET_TO
        self._days = 0x7F
        self._enabled = False
        self.quiet_now = False

    def apply(self, values: Mapping[str, object]) -> None:
        start = _parse_clock(values.get(QUIET_FROM_KEY))
        end = _parse_clock(values.get(QUIET_TO_KEY))
        if start is not None:
            self._from = start
            self._enabled = True
        if end is not None:
            self._to = end
            self._enabled = True
        days = _parse_days(values.get(QUIET_DAYS_KEY))
        if days is not None:
            self._days = days
        if isinstance(values.get(QUIET_ENABLED_KEY), bool):
            self._enabled = bool(values[QUIET_ENABLED_KEY])
        if isinstance(values.get(QUIET_NOW_KEY), bool):
            self.quiet_now = bool(values[QUIET_NOW_KEY])

    @property
    def days_mask(self) -> int:
        return self._days

    def minutes(self) -> tuple[int, int]:
        """The window as minutes of the local day (from, to), or (-1, -1) when there is none (off, or equal bounds).
        The StackChan keeps quiet hours on its own clock from these (sounds, patch 116)."""
        if not self._enabled or self._from == self._to or self._days == 0:
            return (-1, -1)
        return (self._from.hour * 60 + self._from.minute, self._to.hour * 60 + self._to.minute)

    def active(self) -> bool:
        if self.quiet_now:
            return True
        if not self._enabled or self._from == self._to or self._days == 0:
            return False
        stamp = self._now()
        now = stamp.time()
        weekday = (stamp.weekday() + 1) % 7  # Python Monday is 0; the schedule counts Sunday as 0
        if self._from < self._to:
            return self._from <= now < self._to and bool(self._days >> weekday & 1)
        if now >= self._from:
            return bool(self._days >> weekday & 1)
        if now < self._to:
            return bool(self._days >> ((weekday + 6) % 7) & 1)  # after midnight: the window began yesterday
        return False


@dataclass
class SleepAutoPolicy:
    auto_enabled: bool = True
    asleep: bool = False

    def __post_init__(self) -> None:
        self._dark_since: float | None = None
        self._last_sound: float | None = None
        self._last_activity: float | None = None
        self._was_quiet_hours = False

    def update(
        self,
        now: float,
        *,
        luma: float | None,
        speech: bool,
        face: bool,
        knock: bool = False,
        quiet_hours: bool = False,
    ) -> SleepEdge | None:
        """One presence tick. Returns the edge when the state changes."""
        if self._last_sound is None:
            self._last_sound = now
        if self._last_activity is None:
            self._last_activity = now
        if speech:
            self._last_sound = now
        if speech or face:
            self._last_activity = now

        if luma is not None and luma < DARK_LUMA:
            if self._dark_since is None:
                self._dark_since = now
        else:
            self._dark_since = None

        quiet_edge = quiet_hours and not self._was_quiet_hours
        self._was_quiet_hours = quiet_hours

        if self.asleep:
            if face or speech or knock:
                self.asleep = False
                return "wake"
            return None

        if quiet_hours and (quiet_edge or now - self._last_activity >= QUIET_FOR_S):
            if not (face or speech or knock):
                self.asleep = True
                return "sleep"
        if (
            self.auto_enabled
            and self._dark_since is not None
            and now - self._dark_since >= QUIET_FOR_S
            and now - self._last_sound >= QUIET_FOR_S
            and not face
        ):
            self.asleep = True
            return "sleep"
        return None
