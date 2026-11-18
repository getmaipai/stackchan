"""scripts/fw-power-run.py: the chain of power_log calls, the safety stops and the numbers it prints (a fake unit, no hardware)."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("fw_power_run", ROOT / "scripts" / "fw-power-run.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["fw_power_run"] = mod
spec.loader.exec_module(mod)


def fake_unit(tmp_path: Path, levels: list[int], temp: int = 30, vbat: int = 3900) -> str:
    """A command that answers power_log like the unit: one row per call, the next level each call."""
    script = tmp_path / "unit.py"
    state = tmp_path / "state.json"
    state.write_text("0")
    script.write_text(
        "import json,sys\n"
        f"s=int(open({str(state)!r}).read()); open({str(state)!r},'w').write(str(s+1))\n"
        f"L={levels!r}\n"
        "lvl=L[min(s,len(L)-1)]\n"
        f"row=[0,lvl,0,0,{vbat},0,4300,2,0,0,0,{temp},{temp},90000]\n"
        "print(json.dumps({'ok':True,'interval_s':30,'columns':14,'rows':[row]}))\n"
    )
    return f"{sys.executable} {script} {{name}} {{json}}"


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += s


def args(tmp_path: Path, call: str, minutes: float = 10, **kw):
    ns = mod.argparse.Namespace(load="face only", minutes=minutes, out=str(tmp_path / "run.csv"), seconds=30, interval=30, call=call, floor=10, max_temp=55, min_vbat=3300)
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


class Tick(Clock):
    """Each clock read advances 30 s, so every call of the loop is 30 s of run."""

    def __call__(self) -> float:
        self.t += 30
        return self.t


def test_a_drain_run_writes_rows_and_prints_the_slope(tmp_path, capsys):
    call = fake_unit(tmp_path, [100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85, 84, 83, 82, 81, 80, 79, 78])
    assert mod.run(args(tmp_path, call, minutes=8), clock=Tick()) == 0
    rows = list(csv.reader((tmp_path / "run.csv").open()))
    assert rows[0][:3] == ["wall_s", "load", "t_s"] and len(rows) > 3 and rows[1][1] == "face only"
    out = capsys.readouterr().out
    assert "slope: -" in out and "percent per hour" in out


def test_a_hot_servo_stops_the_run(tmp_path, capsys):
    call = fake_unit(tmp_path, [80, 79, 78], temp=56)
    assert mod.run(args(tmp_path, call, minutes=30), clock=Tick()) == 2
    assert "stopped early" in capsys.readouterr().out


def test_a_low_level_on_the_battery_stops_the_run(tmp_path, capsys):
    call = fake_unit(tmp_path, [12, 9, 8])
    assert mod.run(args(tmp_path, call, minutes=30), clock=Tick()) == 2
    assert "under the floor" in capsys.readouterr().out


def test_a_low_battery_voltage_stops_the_run(tmp_path, capsys):
    call = fake_unit(tmp_path, [50, 49], vbat=3200)
    assert mod.run(args(tmp_path, call, minutes=30), clock=Tick()) == 2


def test_slope_and_minutes_between():
    pts = [(0.0, 100), (600.0, 90), (1200.0, 80), (1800.0, 70)]
    assert round(mod.slope_per_hour(pts)) == -60
    assert mod.minutes_between([(0.0, 100), (600.0, 60), (1200.0, 20)], 100, 20) == 20.0
    assert mod.minutes_between(pts, 100, 20) is None
    assert mod.slope_per_hour([(0.0, 50)]) is None


def test_a_failed_call_says_what_to_do(tmp_path):
    bad = f"{sys.executable} -c \"import sys; sys.exit(3)\" {{name}} {{json}}"
    try:
        mod.run(args(tmp_path, bad), clock=Tick())
    except RuntimeError as exc:
        assert "Check the unit is on" in str(exc)
    else:
        raise AssertionError("a failed call must raise")


def test_the_limits_are_checked(capsys):
    assert mod.main(["--load", "x", "--minutes", "5", "--out", "/tmp/x.csv", "--seconds", "300", "--interval", "5"]) == 1
    assert "at most 40 rows" in capsys.readouterr().err
    assert json.dumps({"a": 1})
