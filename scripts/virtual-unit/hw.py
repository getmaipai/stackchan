"""The virtual unit's body: power button, the two USB-C ports, Wi-Fi, battery, carried and orientation, and what they do to the screen (the 3D view uses it).
Pure state and timing, no renderer and no clock of its own: the caller passes the fake time in ms. Tested by host/tests/test_virtual_unit_hw.py.

What is real and what is a stand-in (also in docs/dev/virtual-unit-3d.md):
- Real, from the firmware patches: the low-battery ladder (T01: 20 chirp and tired look, 10 spoken ask, 5 sleep after an 8 s grace), the limiter bands
  (ML01, through the tools' own motion handlers), the 40 head moves a minute cap (038), the servo ranges, the status bar fields (bstatus).
- The unit has two USB-C sockets, one on the side of the controller and one at the back of the base, on ONE shared USB path. Bench evidence
  (2026-11-18): a computer cable in the back socket alone gives the unit USB power and the computer lists the same serial device. So power and
  data are present when either socket has a cable. Both plugged at once is undefined on the real unit; here it is ASSUMED to behave as either
  one (the stronger source feeds, never the sum). Each cable has a source in SOURCES. Every electrical value is ASSUMED until the bench
  measures it: see POWER below.
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

PORTS = ("side", "back")  # two sockets on one USB path: side is on the controller, back is on the base
PORT_NAMES = {"side": "side socket (on the controller)", "back": "back socket (on the base)"}
USB_PATH_NOTE = "two sockets, one USB path: power and data are present when either has a cable (bench: back socket alone gives both). Both plugged: undefined on the unit, assumed here to act as either one, fed by the stronger source"
SOURCES = {  # what the other end of a cable is: label, volts, most current it gives (mA), can carry serial data
    "computer": ("a computer's USB port (5 V, 500 mA)", 5.0, 500, True),
    "charger": ("a 5 V 2 A charger", 5.0, 2000, False),
    "supply_12v": ("a 12 V supply (wrong: the ports take 5 V)", 12.0, 2000, False),
}
# The one place that says which ports count as "a cable is present" for the head limiter (patch ML01 reads one cable flag).
# Both sockets are the same USB input, so either counts. If the firmware track later ties the limit to a measured supply (servo voltage and
# sag) instead of "a cable is present", this tuple and limiter_cable below are the one place to change.
LIMITER_CABLE_PORTS = ("side", "back")
LIMITER_CABLE_RULE = "a 5 V cable in either socket is the same USB input, so either counts as the cable (the firmware reads one cable flag; a rule based on measured supply would replace this)"
# The supply model, every number ASSUMED until measured on the bench: the servo rail is 5.0 V with nothing moving; each thing that feeds it
# has a series resistance, the feeds share the load, and a computer port cannot give more than its 500 mA.
POWER = {"basis": "assumed", "rail_v": 5.0, "ohm": {"battery": 0.30, "computer": 0.45, "charger": 0.12},
         "load_a": {"idle": 0.08, "one_servo": 0.45, "both_servos": 0.90}, "brownout_v": 4.3}


class Hardware:
    def __init__(self) -> None:
        self.on = True
        self.ports = {"side": {"plugged": False, "source": "computer"}, "back": {"plugged": False, "source": "charger"}}
        self.serial = False  # a computer on the side cable is talking to the unit (only meaningful with that cable)
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
        if key == "reset":
            return self.press_reset(now)
        if key == "usb":  # the old name of the side port's cable
            key = "side"
        if key in PORTS:
            port = self.ports[key]
            port["plugged"] = bool(value)
            self.events.append(f"{key} port: " + (f"cable plugged in from {SOURCES[port['source']][0]}" if port["plugged"] else "cable unplugged"))
            self._after_cable_change(key)
        elif key in ("side_source", "back_source"):
            if value not in SOURCES:
                return f"a cable's source is one of {', '.join(SOURCES)}"
            port = self.ports[key[:4]]
            port["source"] = value
            if port["plugged"]:
                self.events.append(f"{key[:4]} port: now fed by {SOURCES[value][0]}")
            self._after_cable_change(key[:4])
        elif key == "serial":
            if value and not any(p["plugged"] for p in self.ports.values()):
                return "There is no cable: plug the USB-C cable in first, in either socket."
            if value and not self.serial_possible:
                return "No plugged cable goes to a computer, and only a computer carries serial data. Choose the computer as a cable's source first."
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

    def _after_cable_change(self, name: str) -> None:
        port = self.ports[name]
        if port["plugged"] and SOURCES[port["source"]][1] > 5.5:
            self.events.append(f"{name} port: {SOURCES[port['source']][1]:.0f} V is too much, the port takes 5 V. It gives no power; unplug it")
        if not self.serial_possible:
            self.serial = False
        if self.vbus:
            self.sleep_started = None

    def press_power(self, now: int) -> str | None:
        if self.on:
            self.on, self.boot_started, self.dance = False, None, ""
            self.events.append("power off")
        else:
            if self.battery <= 0 and not self.vbus:
                return "The battery is empty and no cable gives power. Plug in the USB-C cable (5 V, either port) or raise the battery."
            self.on, self.boot_started, self.sleep_started = True, now, None
            self.events.append("power on")
        return None

    def press_reset(self, now: int) -> str | None:
        """The reset button under the controller: a press restarts a running unit (the boot covers run again). The real button
        also enters download mode on a 3 second hold; the virtual unit has no download mode."""
        if not self.on:
            return "The unit is off, so reset does nothing. Press the power button first."
        self.boot_started, self.sleep_started, self.dance = now, None, ""
        self.events.append("reset pressed: restarting")
        return None

    # ---- derived ---------------------------------------------------------------------------------------

    def feeds(self, name: str) -> bool:
        """A port gives power when a cable is in it and its source is 5 V. A 12 V source is refused (assumed: the input protection opens)."""
        port = self.ports[name]
        return port["plugged"] and SOURCES[port["source"]][1] <= 5.5

    @property
    def usb(self) -> bool:
        """The old single-cable flag: a cable is in a socket (either one: they are the same USB input)."""
        return any(p["plugged"] for p in self.ports.values())

    @property
    def vbus(self) -> bool:
        return any(self.feeds(n) for n in PORTS)

    @property
    def data_from(self) -> str | None:
        """The socket whose cable goes to a computer, or None: serial data comes over that cable (the side one first when both do)."""
        return next((n for n in PORTS if self.ports[n]["plugged"] and SOURCES[self.ports[n]["source"]][3]), None)

    @property
    def serial_possible(self) -> bool:
        return self.data_from is not None

    @property
    def charging(self) -> bool:
        return self.on and self.vbus and self.battery < 100

    @property
    def powered_by(self) -> str:
        fed = [n for n in PORTS if self.feeds(n)]
        return "both" if len(fed) == 2 else fed[0] if fed else "battery"

    @property
    def limiter_cable(self) -> bool:
        """What the head limiter is told about a cable: see LIMITER_CABLE_PORTS, the one place that rule lives."""
        return any(self.feeds(n) for n in LIMITER_CABLE_PORTS)

    def supply(self) -> dict:
        """The servo rail with nothing moving and with both servos moving, from the POWER model. Every number is assumed."""
        cables = sorted((self.ports[n]["source"] for n in PORTS if self.feeds(n)), key=lambda f: -SOURCES[f][2])
        feeds = cables[:1]  # one USB path: with a cable in each socket the stronger source feeds it (assumed), never the sum
        if self.battery > 0:
            feeds.append("battery")
        input_ma = sum(SOURCES[f][2] for f in feeds if f != "battery")
        if not feeds:
            return {"basis": POWER["basis"], "idle_v": 0.0, "load_v": 0.0, "sag_v": 0.0, "input_ma": 0, "brownout": True, "note": "nothing feeds the rail"}
        ohm = 1.0 / sum(1.0 / POWER["ohm"][f] for f in feeds)
        idle = POWER["rail_v"] - POWER["load_a"]["idle"] * ohm
        load = POWER["rail_v"] - POWER["load_a"]["both_servos"] * ohm
        if feeds == ["computer"]:  # no battery to help and the port stops at 500 mA: the rail folds
            load = min(load, POWER["rail_v"] * 0.5 / POWER["load_a"]["both_servos"])
        return {"basis": POWER["basis"], "idle_v": round(idle, 2), "load_v": round(load, 2), "sag_v": round(idle - load, 2), "input_ma": input_ma,
                "brownout": load < POWER["brownout_v"], "fed_by": feeds,
                "note": "5.0 V rail; each feed has an assumed series resistance and the feeds share the load; two cables act as the stronger one"}

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
        if self.vbus or self.battery > LEVEL_TIRED_1:
            return 0
        return 2 if self.battery <= LEVEL_TIRED_2 else 1

    def tick(self, now: int) -> str | None:
        """Time-driven changes. Returns "power_off" when the unit has just gone to sleep on a flat battery (patch T01)."""
        if self.on and not self.vbus and self.battery <= LEVEL_SLEEP:
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
        return [int(self.carried), int(self.limiter_cable), self.battery, ORIENTS.index(self.orient)]

    def view(self) -> dict:
        ports = {n: {"plugged": p["plugged"], "source": p["source"], "source_label": SOURCES[p["source"]][0], "volts": SOURCES[p["source"]][1] if p["plugged"] else 0.0,
                     "gives_power": self.feeds(n), "fault": p["plugged"] and not self.feeds(n)} for n, p in self.ports.items()}
        return {"on": self.on, "usb": self.usb, "serial": self.serial, "serial_possible": self.serial_possible, "wifi": self.wifi, "battery": self.battery,
                "charging": self.charging, "vbus": self.vbus, "powered_by": self.powered_by, "ports": ports, "supply": self.supply(),
                "usb_path": {"vbus": self.vbus, "data": self.serial_possible, "data_from": self.data_from, "both_plugged": all(p["plugged"] for p in self.ports.values()),
                             "basis": "assumed", "note": USB_PATH_NOTE},
                "limiter_cable": {"present": self.limiter_cable, "from": [n for n in LIMITER_CABLE_PORTS if self.feeds(n)], "counted_ports": list(LIMITER_CABLE_PORTS),
                                  "rule": LIMITER_CABLE_RULE},
                "sources": {k: v[0] for k, v in SOURCES.items()},
                "carried": self.carried, "orient": self.orient, "booting": self.boot_started is not None,
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
