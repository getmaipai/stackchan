"""The virtual unit's body: power button, USB-C cable, Wi-Fi, battery, carried and orientation, and what they do to the screen (the 3D view uses it).
Pure state and timing, no renderer and no clock of its own: the caller passes the fake time in ms. Tested by host/tests/test_virtual_unit_hw.py.

What is real and what is a stand-in (also in docs/dev/virtual-unit-3d.md):
- Real, from the firmware patches: the low-battery ladder (T01: 20 chirp and tired look, 10 spoken ask, 5 sleep after an 8 s grace), the limiter bands
  (ML01, through the tools' own motion handlers), the 40 head moves a minute cap (038), the servo ranges, the status bar fields (bstatus).
- Stand-ins: the boot cover timings (the unit's real boot times are not measured), what the serial cable does (only shown), the dances' head paths
  (the real dances are tables on the unit; these are simple shapes of the same size and speed class).
"""

from __future__ import annotations

import math

LEVEL_TIRED_1, LEVEL_TIRED_2, LEVEL_SLEEP = 20, 10, 5  # patch T01: MB_LEVEL_CHIRP, MB_LEVEL_ASK, MB_LEVEL_SLEEP
SLEEP_GRACE_MS = 8000  # patch T01: MB_SLEEP_GRACE_MS, the words stay on screen this long before the power goes
BOOT_MS, WIFI_MS, HOME_MS = 2000, 1500, 1000  # stand-ins: how long each cover shows after power on
DANCE_MS = 8000
ORIENTS = ("upright", "tilted", "side", "inverted", "unknown")


class Hardware:
    def __init__(self) -> None:
        self.on = True
        self.usb = False  # the cable is plugged into the USB-C port
        self.serial = False  # a computer on the cable is talking to the unit (only meaningful with the cable)
        self.wifi = True
        self.battery = 75
        self.carried = False
        self.orient = "upright"
        self.boot_started: int | None = None
        self.sleep_started: int | None = None
        self.dance = ""
        self.dance_started = 0
        self.events: list[str] = []

    # ---- what the person does ------------------------------------------------------------------------

    def set(self, key: str, value, now: int) -> str | None:
        """Apply one control. Returns a plain sentence when it is refused, else None."""
        if key == "power":
            return self.press_power(now)
        if key == "usb":
            self.usb = bool(value)
            if not self.usb:
                self.serial = False
            self.events.append("cable plugged in" if self.usb else "cable unplugged")
            if self.usb:
                self.sleep_started = None
        elif key == "serial":
            if value and not self.usb:
                return "There is no cable: plug the USB-C cable in first."
            self.serial = bool(value)
        elif key == "wifi":
            self.wifi = bool(value)
            self.events.append("Wi-Fi on" if self.wifi else "Wi-Fi off")
        elif key == "battery":
            self.battery = max(0, min(100, int(value)))
            if self.battery > LEVEL_SLEEP:
                self.sleep_started = None
        elif key == "carried":
            self.carried = bool(value)
        elif key == "orient":
            if value not in ORIENTS:
                return f"orientation is one of {', '.join(ORIENTS)}"
            self.orient = value
        else:
            return f"unknown control {key}"
        return None

    def press_power(self, now: int) -> str | None:
        if self.on:
            self.on, self.boot_started, self.dance = False, None, ""
            self.events.append("power off")
        else:
            if self.battery <= 0 and not self.usb:
                return "The battery is empty and no cable is plugged in. Plug in the USB-C cable or raise the battery."
            self.on, self.boot_started, self.sleep_started = True, now, None
            self.events.append("power on")
        return None

    # ---- derived ---------------------------------------------------------------------------------------

    @property
    def charging(self) -> bool:
        return self.on and self.usb and self.battery < 100

    @property
    def powered_by(self) -> str:
        return "usb" if self.usb else "battery"

    def boot_cover(self, now: int) -> tuple[str, int, int, int] | None:
        """(text, ring, glyph, ms since the cover began) while a boot cover shows, else None."""
        if not self.on or self.boot_started is None:
            return None
        t = now - self.boot_started
        if t < BOOT_MS:
            return ("Starting...", 1, 0, t)
        if self.wifi and t < BOOT_MS + WIFI_MS:
            return ("Connecting to Wi-Fi...", 1, 0, t - BOOT_MS)
        if self.wifi and t < BOOT_MS + WIFI_MS + HOME_MS:
            return ("Connecting to Home...", 1, 0, t - BOOT_MS - WIFI_MS)
        if not self.wifi and t < BOOT_MS + WIFI_MS:
            return ("Wi-Fi setup\\nstackchan-A1B2\\nhttp://192.168.4.1\\nCode: 123456", 2, 1, t - BOOT_MS)
        self.boot_started = None
        return None

    def status_args(self) -> tuple[int, int, int, int, int]:
        """The renderer's bstatus fields: level, charging, wifi up, hub up, mic."""
        return (self.battery, int(self.charging), int(self.wifi), int(self.wifi), 1)

    def tired_level(self) -> int:
        if self.usb or self.battery > LEVEL_TIRED_1:
            return 0
        return 2 if self.battery <= LEVEL_TIRED_2 else 1

    def tick(self, now: int) -> str | None:
        """Time-driven changes. Returns "power_off" when the unit has just gone to sleep on a flat battery (patch T01)."""
        if self.on and not self.usb and self.battery <= LEVEL_SLEEP:
            if self.sleep_started is None:
                self.sleep_started = now
                self.events.append("battery at 5 percent: the words show, then it sleeps")
            elif now - self.sleep_started >= SLEEP_GRACE_MS:
                self.on, self.sleep_started, self.dance = False, None, ""
                self.events.append("power off: battery empty")
                return "power_off"
        if self.dance and now - self.dance_started >= DANCE_MS:
            self.dance = ""
        return None

    def motion_force(self) -> list[int]:
        """The arguments of self.motion.force (carried, usb, level, orientation) so the unit's own limiter answers for this body."""
        return [int(self.carried), int(self.usb), self.battery, ORIENTS.index(self.orient)]

    def view(self) -> dict:
        return {"on": self.on, "usb": self.usb, "serial": self.serial, "wifi": self.wifi, "battery": self.battery, "charging": self.charging,
                "powered_by": self.powered_by, "carried": self.carried, "orient": self.orient, "booting": self.boot_started is not None,
                "sleeping_soon": self.sleep_started is not None, "events": self.events[-6:]}


def dance_offset(name: str, t_ms: int, scale: int, speed_cap: int) -> tuple[float, float]:
    """(yaw, pitch) degrees added to the head by a dance after t_ms. Simple shapes of the right size; `scale` is the limiter's percent of the full
    excursion and `speed_cap` its speed ceiling (1000 is full): both shrink the motion, as the unit's limiter does."""
    k = max(0, scale) / 100.0
    s = 0.3 + 0.7 * min(1.0, max(0, speed_cap) / 1000.0)
    t = t_ms / 1000.0 * s
    if name == "happy":
        return (18 * k * math.sin(t * 5.0), 14 * k * math.sin(t * 10.0))
    if name == "robot":
        step = int(t * 2.2) % 4
        return ((0, 40 * k, 0, -40 * k)[step], (0, 0, 20 * k, 0)[step])
    if name == "panic":
        return (35 * k * math.sin(t * 16.0), 10 * k * math.sin(t * 9.0))
    if name == "look_around":
        return (60 * k * math.sin(t * 1.2), 8 * k * math.sin(t * 0.6))
    return (0.0, 0.0)
