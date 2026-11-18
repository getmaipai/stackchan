#!/usr/bin/env python3
"""The virtual unit's power model: how much current the robot draws in a state, how long the battery lasts at that draw, how fast it drains and charges as time passes, and a day-of-use
planner. Every number comes from schema/power-model.json and is a placeholder (basis "assumed") until the bench measures it: the unit reads a battery percent and no battery current, so
the real figures come from the level against time at a known load (docs/dev/battery-and-power.md). The model never claims more than that: each result carries its basis.
Usage: python3 scripts/virtual-unit/power_model.py [profile]   prints the hours the battery lasts for a profile (usual, always_listening, desk) and for each state.
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import json
import sys
from pathlib import Path

TABLE = Path(__file__).resolve().parents[2] / "schema" / "power-model.json"


def load(path: Path | None = None) -> dict:
    return json.loads((path or TABLE).read_text())


class PowerModel:
    def __init__(self, table: dict | None = None) -> None:
        self.t = table or load()
        self.ma = {l["id"]: l["ma"] for l in self.t["loads_ma"]}

    @property
    def basis(self) -> str:
        """"assumed" while any number in the table is a placeholder, else "measured"."""
        every = [self.t["battery"], self.t["charge"]] + self.t["loads_ma"]
        return "assumed" if any(x.get("status") != "measured" for x in every) else "measured"

    def usable_mah(self) -> float:
        b = self.t["battery"]
        return b["capacity_mah"] * b["usable_fraction"]

    def draw_ma(self, state) -> float:
        """The draw in mA for a state: a name from the table or a dict with the same keys (brightness 0 to 100, wifi, mic, speaking, servo_moving 0 to 2, camera, ring 0 to 1, screen)."""
        s = self.t["states"][state] if isinstance(state, str) else {**self.t["states"]["idle"], **state}
        ma = self.ma["base"]
        if s.get("screen", True):
            ma += self.ma["brightness_full"] * (s["brightness"] - 50) / 50 if s["brightness"] >= 50 else self.ma["brightness_full"] * (s["brightness"] - 50) / 100
        else:
            ma += self.ma["screen_off"]
        if not s["wifi"]:
            ma += self.ma["wifi_off"]
        if s["mic"]:
            ma += self.ma["mic_listening"]
        if s["speaking"]:
            ma += self.ma["speaking"]
        if s["servo_moving"] or s.get("servos_holding", True):
            ma += self.ma["servos_holding"]
        ma += self.ma["servo_moving"] * s["servo_moving"]
        if s["camera"]:
            ma += self.ma["camera_look"]
        ma += self.ma["ring_full"] * s["ring"]
        return round(max(ma, 10.0), 1)

    def hours_left(self, percent: float, draw_ma: float) -> float:
        return round(self.usable_mah() * percent / 100.0 / draw_ma, 2) if draw_ma > 0 else float("inf")

    def drain_percent(self, draw_ma: float, ms: float) -> float:
        """How many percent the battery loses in `ms` at `draw_ma` (never more than the cable gives back: the caller handles that)."""
        return draw_ma * (ms / 3_600_000.0) / self.usable_mah() * 100.0

    def charge_percent(self, input_ma: float, draw_ma: float, ms: float, percent: float) -> float:
        """How many percent the battery gains in `ms` from a cable that can give `input_ma` while the unit draws `draw_ma`: the charger limit applies and the rate halves above the taper level."""
        c = self.t["charge"]
        into = max(0.0, min(c["limit_ma"], input_ma - draw_ma))
        if percent >= c["taper_above_percent"]:
            into *= c["taper_factor"]
        return into * (ms / 3_600_000.0) / self.usable_mah() * 100.0

    def day(self, profile: str | dict) -> dict:
        """A day of use: hours in each state. Returns the average draw, the hours a full battery lasts at that mix, and whether it lasts the 24 hours."""
        p = self.t["profiles"][profile]["hours"] if isinstance(profile, str) else profile
        total = sum(p.values())
        mah = sum(self.draw_ma(state) * h for state, h in p.items())
        avg = mah / total if total else 0.0
        hours = self.hours_left(100.0, avg)
        return {"basis": self.basis, "hours_total": total, "average_ma": round(avg, 1), "mah_per_day": round(mah / total * 24, 0) if total else 0, "full_battery_lasts_hours": hours, "lasts_a_day": hours >= 24.0}


def main(argv: list[str]) -> int:
    m = PowerModel()
    print(f"basis: {m.basis} (placeholders until the bench measures them)")
    for s in m.t["states"]:
        d = m.draw_ma(s)
        print(f"  {s:18s} {d:6.1f} mA  {m.hours_left(100, d):5.1f} h from full")
    for name in [argv[0]] if argv else m.t["profiles"]:
        r = m.day(name)
        print(f"profile {name}: average {r['average_ma']} mA, a full battery lasts {r['full_battery_lasts_hours']} h ({'a day' if r['lasts_a_day'] else 'less than a day'}), {r['basis']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
