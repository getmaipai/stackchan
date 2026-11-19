"""The power model of the virtual unit (scripts/virtual-unit/power_model.py, schema/power-model.json): the draw by state, the hours a battery lasts, the drain on the battery and the charge on a
cable as the fake clock runs, the day planner, and that every number is marked a placeholder until the bench measures it. The drain is off unless asked for."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VU = ROOT / "scripts" / "virtual-unit"
sys.path.insert(0, str(VU))
import power_model as pm  # noqa: E402


def _hw():
    spec = importlib.util.spec_from_file_location("hw", VU / "hw.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_number_is_a_placeholder_until_measured():
    m = pm.PowerModel()
    assert m.basis == "assumed"
    t = json.loads((ROOT / "schema" / "power-model.json").read_text())
    assert all(x["status"] in ("placeholder", "measured") for x in t["loads_ma"] + [t["battery"], t["charge"]])
    measured = json.loads(json.dumps(t))
    for x in measured["loads_ma"] + [measured["battery"], measured["charge"]]:
        x["status"] = "measured"
    assert pm.PowerModel(measured).basis == "measured"


def test_the_draw_follows_the_load_in_the_right_order():
    m = pm.PowerModel()
    d = {s: m.draw_ma(s) for s in m.t["states"]}
    assert d["asleep"] < d["idle"] < d["listening"] < d["talking"] < d["moving"] < d["dance"], d
    assert d["idle_dim_no_wifi"] < d["idle"]
    assert m.draw_ma({"brightness": 100}) > m.draw_ma({"brightness": 50}) > m.draw_ma({"brightness": 10})
    assert m.draw_ma({"wifi": False}) < m.draw_ma({})
    assert m.draw_ma({"servo_moving": 2}) - m.draw_ma({"servo_moving": 0}) == 2 * m.ma["servo_moving"]


def test_hours_and_the_day_planner():
    m = pm.PowerModel()
    assert m.hours_left(100, 100) == round(m.usable_mah() / 100, 2)
    assert m.hours_left(50, 100) == round(m.usable_mah() / 200, 2)
    day = m.day("usual")
    assert day["basis"] == "assumed" and day["average_ma"] > 0 and day["full_battery_lasts_hours"] > 0
    assert m.day({"asleep": 24})["full_battery_lasts_hours"] > m.day({"dance": 24})["full_battery_lasts_hours"]


def test_drain_is_off_unless_asked_for_and_follows_the_load_when_on():
    hw = _hw().Hardware()
    hw.battery = 80
    hw.tick(0)
    hw.tick(3_600_000)
    assert hw.battery == 80, "the battery stays where the person put it"
    hw.set("drain", True, 3_600_000)
    hw.tick(3_600_000)
    hw.tick(3_600_000 + 1_800_000)      # half an hour on the battery
    idle_loss = 80 - hw.battery
    assert idle_loss > 5, idle_loss
    hw2 = _hw().Hardware()
    hw2.battery = 80
    hw2.set("drain", True, 0)
    hw2.dance, hw2.dance_started = "happy", 0
    hw2.tick(0)
    hw2.tick(60_000)                    # a minute of dance, far under the dance's own length
    hw2.dance = "happy"
    hw2.dance_started = 10**9
    hw2.tick(1_800_000)
    assert 80 - hw2.battery > idle_loss, "a dance drains faster than a quiet face"


def test_a_cable_charges_with_a_taper_and_the_hours_are_not_shown_on_a_cable():
    hw = _hw().Hardware()
    hw.battery = 40
    hw.set("drain", True, 0)
    hw.set("back", True, 0)
    assert hw.vbus and hw.hours_left() is None
    hw.tick(0)
    hw.tick(1_800_000)
    low_gain = hw.battery - 40
    hw.battery = 90
    hw._bat_f = 90.0
    hw.tick(1_800_000)
    hw.tick(3_600_000)
    high_gain = hw.battery - 90
    assert low_gain > 0 and 0 <= high_gain < low_gain, (low_gain, high_gain)


def test_a_flat_battery_runs_the_units_own_low_battery_ladder():
    hw = _hw().Hardware()
    hw.battery = 6
    hw.set("drain", True, 0)
    hw.tick(0)
    seen = None
    for minute in range(1, 120):
        out = hw.tick(minute * 60_000)
        if out == "power_off":
            seen = minute
            break
    assert seen is not None and not hw.on, "the level falls to 5 percent, the words show and the unit powers off after its grace"
