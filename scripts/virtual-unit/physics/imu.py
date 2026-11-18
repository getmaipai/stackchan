"""From the IMU numbers the physics model reports to the two inputs the movement limiter takes: carried and orientation.
The rule is the movement limiter's (patch ML01 and maipai_pickup_core.h): carried goes on when the accelerometer norm leaves 1 g by more than 2.5 m/s^2
for 150 ms, and off after 1 s of calm; tilt bands upright (under 15 degrees), tilted (15 to 45), side (over 45) with 5 degrees of hysteresis.
Pure Python, no clock of its own: the caller passes time in ms. Tested by host/tests/test_virtual_unit_physics.py.
Placement: host-side development tool; no firmware change. Upstream: none."""

from __future__ import annotations

import math

G = 9.80665
DEVIATION = 2.5  # m/s^2
ON_MS, OFF_MS = 150, 1000
TILT_ENTER, TILT_EXIT, SIDE_ENTER, SIDE_EXIT = 15.0, 10.0, 45.0, 40.0


class PickupRule:
    def __init__(self) -> None:
        self.carried = False
        self.orient = "upright"
        self._deviant_since: int | None = None
        self._calm_since: int | None = None

    def feed(self, t_ms: int, accel: tuple[float, float, float], tilt_deg: float) -> tuple[bool, str]:
        norm = math.sqrt(sum(a * a for a in accel))
        if abs(norm - G) > DEVIATION:
            self._calm_since = None
            self._deviant_since = t_ms if self._deviant_since is None else self._deviant_since
            if not self.carried and t_ms - self._deviant_since >= ON_MS:
                self.carried = True
        else:
            self._deviant_since = None
            self._calm_since = t_ms if self._calm_since is None else self._calm_since
            if self.carried and t_ms - self._calm_since >= OFF_MS:
                self.carried = False
        self.orient = self._band(tilt_deg)
        return self.carried, self.orient

    def _band(self, tilt: float) -> str:
        was = self.orient
        if tilt >= SIDE_ENTER or (was == "side" and tilt >= SIDE_EXIT):
            return "side"
        if tilt >= TILT_ENTER or (was in ("tilted", "side") and tilt >= TILT_EXIT):
            return "tilted"
        return "upright"
