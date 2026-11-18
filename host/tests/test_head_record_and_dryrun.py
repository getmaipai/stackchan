# ruff: noqa: E501
"""The bench recording script (scripts/fw-head-record.py) against a simulated servo and against the virtual unit, the fit of its CSV, and the host half of the
carried and dance-stop dry run (the browser half runs in the sandbox: Run the carried and dance-stop check)."""

from __future__ import annotations

import csv
import importlib.util
import json
import random
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VU = ROOT / "scripts" / "virtual-unit"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rec = _load("fw_head_record", ROOT / "scripts" / "fw-head-record.py")
cal = _load("calibrate_for_record", VU / "physics" / "calibrate.py")


class SimLink:
    """A unit whose heads follow the servo equation of calibrate.py, on a fake clock the recorder advances through `sleep` and each call's round trip."""

    TRUE = {"pitch": (0.62, 0.0065), "yaw": (0.45, 0.0045)}
    DAMPING, TORQUE = 0.003, 0.12
    SPEED_CAP = ACCEL_CAP = None  # the servo's own setpoint rate limit (degrees a second, a second squared); None: the setpoint is the command

    def __init__(self, state="free", rtt=0.02, noise=0.1):
        self.now, self.rtt, self.state, self.noise = 0.0, rtt, state, noise
        self.hist = {"pitch": [(0.0, 10.0)], "yaw": [(0.0, 0.0)]}
        self.calls, self.rng, self.sim = [], random.Random(3), {}
        self.limit = state == "usb_limited"   # the USB limit really in force: the excursion around the rest pose is halved (the status text may not say so)
        self.desc = cal.mjcf.load()

    def clock(self):
        return self.now

    def sleep(self, s):
        self.now += s

    def call(self, name, args=None):
        self.calls.append((name, args))
        self.now += self.rtt / 2
        out = self._answer(name, args or {})
        self.now += self.rtt / 2
        return out

    def _angle(self, joint, t):
        """Integrate this joint's servo equation up to time t (the same equation as calibrate.simulate) with the latest command, applied when it arrived."""
        import math

        st = self.sim.setdefault(joint, {"q": math.radians(self.hist[joint][0][1]), "dq": 0.0, "t": 0.0, "ref": self.hist[joint][0][1], "rv": 0.0})
        inertia = cal.head_inertia_pitch(self.desc) if joint == "pitch" else cal.head_inertia_yaw(self.desc)
        kp, kv = self.TRUE[joint]
        grav = cal.gravity_coefficient(self.desc, joint)
        dt = 0.001
        while st["t"] < t:
            goal = next(c for (tt, c) in reversed(self.hist[joint]) if tt <= st["t"])
            if self.SPEED_CAP is None:
                st["ref"] = goal
            else:
                err = goal - st["ref"]
                want = math.copysign(min(self.SPEED_CAP, math.sqrt(2.0 * self.ACCEL_CAP * abs(err))), err) if err else 0.0
                st["rv"] += max(-self.ACCEL_CAP * dt, min(self.ACCEL_CAP * dt, want - st["rv"]))
                st["ref"] += st["rv"] * dt
            target = math.radians(st["ref"])
            u = max(-self.TORQUE, min(self.TORQUE, kp * (target - st["q"]) - kv * st["dq"]))
            fr = 0.003 * (1 if st["dq"] > 0 else -1 if st["dq"] < 0 else 0)
            st["dq"] += (u - self.DAMPING * st["dq"] - fr + grav[0] * math.sin(st["q"]) + grav[1] * math.cos(st["q"])) / inertia * dt
            st["q"] += st["dq"] * dt
            st["t"] += dt
        return math.degrees(st["q"]) + self.rng.gauss(0, self.noise)

    def _answer(self, name, args):
        if name == "self.motion.status":
            return {"ok": True, "state": self.state, "reasons": "on a USB cable" if self.state == "usb_limited" else "", "usb_limit": "limited" if self.limit else "off"}
        if name == "self.motion.set":
            self.limit = args.get("usb_limit") != "off"
            self.state = "usb_limited" if self.limit else "free"
            return {"ok": True}
        if name == "self.robot.set_head_angles":
            for joint in ("yaw", "pitch"):
                if joint in args:
                    rest = 10.0 if joint == "pitch" else 0.0
                    goal = float(args[joint])
                    self.hist[joint].append((self.now, rest + (goal - rest) * 0.5 if self.limit else goal))
            return {"ok": True}
        if name == "self.robot.get_head_angles":
            return {j: round(self._angle(j, self.now), 2) for j in ("yaw", "pitch")}
        return {"ok": False, "error": "unknown"}


def _run(link, out, axes, **kw):
    lines = []
    code = rec.record(link, axes, out, hold_s=kw.pop("hold_s", 1.2), log=lines.append, clock=link.clock, sleep=link.sleep, **kw)
    return code, lines


def test_the_move_set_has_small_and_large_steps_both_ways_on_both_axes_inside_the_limits():
    moves = rec.move_list(["pitch", "yaw"])
    pitch = [a for ax, a in moves if ax == "pitch"]
    yaw = [a for ax, a in moves if ax == "yaw"]
    assert all(5 <= a <= 85 for a in pitch) and all(-128 <= a <= 128 for a in yaw)
    steps = [abs(b - a) for a, b in zip(pitch, pitch[1:])]
    assert min(steps) <= 20 and max(steps) >= 60
    assert min(yaw) < 0 < max(yaw) and min(abs(b - a) for a, b in zip(yaw, yaw[1:])) <= 15


def test_recording_a_simulated_servo_writes_the_csv_and_the_fit_recovers_the_gains(tmp_path):
    link = SimLink()
    out = tmp_path / "head.csv"
    code, lines = _run(link, out, ["pitch"])
    assert code == 0
    rows = list(csv.DictReader(out.open()))
    assert list(rows[0]) == ["joint", "move_id", "t_ms", "cmd_deg", "meas_deg", "rtt_ms"]
    assert {r["joint"] for r in rows} == {"pitch"} and len(rows) > 200
    assert any("median round trip" in line for line in lines)
    recs = cal.load_recording(out)
    fitted, err = cal.fit_joints(recs, cal.mjcf.load(), rounds=60)
    assert err**0.5 < 0.6
    quals = cal.quality(recs, cal.mjcf.load(), fitted)
    assert all(q["rms_pct_of_step"] < 5 for q in quals.values()), quals


def test_a_cable_limited_unit_is_refused_with_the_way_out_and_can_be_lifted_for_the_run(tmp_path):
    link = SimLink(state="usb_limited")
    code, lines = _run(link, tmp_path / "x.csv", ["pitch"])
    assert code == 2 and "usb-limit-off" in lines[-1] and not (tmp_path / "x.csv").exists()
    code, _ = _run(link, tmp_path / "y.csv", ["pitch"], usb_limit_off=True)
    assert code == 0 and link.state == "usb_limited"  # restored at the end
    assert ("self.motion.set", {"usb_limit": "off"}) in link.calls and ("self.motion.set", {"usb_limit": "limited"}) in link.calls


class StaleStatusLink(SimLink):
    """The real unit's trouble: the status says `free` while the USB limit still halves the head."""

    def _answer(self, name, args):
        out = super()._answer(name, args)
        if name == "self.motion.status":
            out = {**out, "state": "free", "reasons": ""}
        return out


def test_a_limit_the_status_does_not_show_is_found_by_the_head_reach_and_lifted_explicitly(tmp_path):
    link = StaleStatusLink(state="usb_limited")
    code, lines = _run(link, tmp_path / "a.csv", ["pitch"])
    assert code == 2 and "percent" in lines[-1] and "usb-limit-off" in lines[-1]   # refused although the status says free
    code, lines = _run(link, tmp_path / "b.csv", ["pitch"], usb_limit_off=True)
    assert code == 0 and link.limit is True   # the limit is back
    assert ("self.motion.set", {"usb_limit": "off"}) in link.calls
    assert any("after the restore" in line for line in lines)
    rows = list(csv.DictReader((tmp_path / "b.csv").open()))
    peak = max(float(r["meas_deg"]) for r in rows if r["cmd_deg"] == "70")
    assert peak > 60   # the recorded large step really reached


class StuckLimitLink(SimLink):
    """A unit that ignores the request to set the limit off."""

    def _answer(self, name, args):
        if name == "self.motion.set":
            return {"ok": True}
        return super()._answer(name, args)


def test_a_limit_that_does_not_lift_stops_the_run_and_says_so(tmp_path):
    link = StuckLimitLink(state="usb_limited")
    code, lines = _run(link, tmp_path / "c.csv", ["pitch"], usb_limit_off=True)
    assert code == 2 and "still covers only" in lines[-1] and not (tmp_path / "c.csv").exists()


class WontRestoreLink(SimLink):
    """A unit whose limit does not come back when asked."""

    def _answer(self, name, args):
        if name == "self.motion.set" and args.get("usb_limit") == "limited":
            return {"ok": True}
        return super()._answer(name, args)


def test_a_restore_that_did_not_take_is_caught_by_the_same_reach_test(tmp_path):
    link = WontRestoreLink(state="usb_limited")
    code, lines = _run(link, tmp_path / "d.csv", ["pitch"], usb_limit_off=True)
    assert code == 5 and any("may not be restored" in line for line in lines)


def test_head_moves_stay_under_the_units_cap_of_forty_a_minute(tmp_path):
    link = SimLink()
    _run(link, tmp_path / "z.csv", ["pitch", "yaw"], hold_s=1.0)  # one second a move: the pacing must slow it down
    sets = [1 for n, _ in link.calls if n == "self.robot.set_head_angles"]
    assert len(sets) > 20 and link.now > 24  # more than 30 moves a minute were never sent


needs_render = pytest.mark.skipif(not (ROOT / ".runs" / "vu-screens" / "render").exists(), reason="needs the screens renderer")


@pytest.fixture
def view():
    proc = subprocess.Popen([sys.executable, str(VU / "view.py"), "0"], stdout=subprocess.PIPE, text=True)
    base = proc.stdout.readline().split()[-1]
    time.sleep(0.6)
    yield base
    proc.terminate()
    proc.wait(timeout=10)


def _post(base, path, body):
    return json.loads(urllib.request.urlopen(urllib.request.Request(base + path, json.dumps(body).encode())).read())


def _state(base):
    return json.loads(urllib.request.urlopen(base + "state").read())


@needs_render
def test_the_recorder_runs_against_the_virtual_unit(view, tmp_path):
    out = tmp_path / "vu.csv"
    link = rec.HttpLink(view)
    lines = []
    code = rec.record(link, ["pitch"], out, hold_s=0.25, log=lines.append)
    assert code == 0
    rows = list(csv.DictReader(out.open()))
    assert len(rows) > 30 and {r["joint"] for r in rows} == {"pitch"}
    assert max(float(r["meas_deg"]) for r in rows) > 60  # the pitch 70 and 80 steps were followed
    assert cal.load_recording(out)["pitch"]["samples"]


@needs_render
def test_host_half_of_the_dry_run_a_lift_stops_the_dance_and_a_tilt_holds_the_unit_still(view):
    assert _post(view, "call", {"name": "self.robot.dance", "arguments": {"name": "happy"}})["ok"]
    time.sleep(0.4)
    assert _state(view)["dance"] == "happy"
    for _ in range(5):  # a lift: the accelerometer leaves 1 g for more than 150 ms
        _post(view, "imu", {"accel": [0, 0, 16.0], "tilt_deg": 0})
        time.sleep(0.1)
    end = time.time() + 2.0
    while time.time() < end and _state(view)["dance"]:
        time.sleep(0.1)
    st = _state(view)
    assert st["hw"]["carried"] and st["motion"]["state"] == "carried" and st["dance"] == ""
    _post(view, "imu", {"accel": [0, 0, 9.8], "tilt_deg": 80})
    time.sleep(0.3)
    assert _state(view)["hw"]["orient"] == "side"
    refused = _post(view, "call", {"name": "self.robot.set_head_angles", "arguments": {"yaw": 30, "pitch": 20}})
    assert refused["ok"] is False
    assert not _post(view, "call", {"name": "self.robot.dance", "arguments": {"name": "happy"}})["ok"]


# ---- what bench window 4 found: replies of the real unit -----------------------------------------------

class FakeSerialModule:
    """fw-serial.py as the real unit behaves: the first call after the port opens is answered Unknown tool; set_head_angles answers a bare true; the head does not follow."""

    def __init__(self):
        self.calls = []
        self.first = True

    def open_port(self):
        return object()

    def call(self, port, name, args=None, wait=5.0):
        self.calls.append(name)
        if self.first:
            self.first = False
            return {"text": "Unknown tool"}
        if name == "self.robot.set_head_angles":
            return True  # a bare true
        if name == "self.robot.get_head_angles":
            return {"yaw": 3, "pitch": 5}  # the head sits still: the unit ignored the moves while idle
        if name == "self.motion.status":
            return {"ok": True, "state": "free"}
        return {"ok": True}


def test_the_serial_link_warms_up_and_reads_a_bare_true_as_ok():
    mod = FakeSerialModule()
    link = rec.SerialLink(mod=mod, port=object())
    assert mod.calls[0] == "self.robot.get_head_angles"  # the throwaway call went first
    assert link.call("self.robot.set_head_angles", {"pitch": 10}) == {"ok": True}
    assert link.call("self.robot.get_head_angles") == {"yaw": 3, "pitch": 5}


def test_a_head_that_did_not_follow_is_reported_and_the_script_exits_nonzero(tmp_path):
    link = rec.SerialLink(mod=FakeSerialModule(), port=object())
    ticks = {"t": 0.0}
    lines = []
    code = rec.record(link, ["pitch"], tmp_path / "flat.csv", hold_s=0.5, log=lines.append, clock=lambda: ticks.__setitem__("t", ticks["t"] + 0.05) or ticks["t"], sleep=lambda s: ticks.__setitem__("t", ticks["t"] + s))
    assert code == 3 and any("the head did not follow" in line and "idle" in line for line in lines)
    assert (tmp_path / "flat.csv").exists()  # the samples are kept


def test_calibrate_says_no_movement_and_exits_nonzero_on_flat_data(tmp_path, capsys):
    path = tmp_path / "flat.csv"
    rows = ["joint,move_id,t_ms,cmd_deg,meas_deg,rtt_ms"] + [f"pitch,{i // 20},{i * 50},{10 if i < 40 else 70},5,200" for i in range(80)]
    path.write_text("\n".join(rows) + "\n")
    assert cal.main([str(path)]) == 3
    assert "no movement in the recording" in capsys.readouterr().err


def test_the_fit_finds_a_servo_speed_cap_separate_from_the_gain_and_reports_its_quality(tmp_path):
    """The bench saw the head cover only 40 to 46 percent of a step in 0.6 s: a setpoint rate limit, not a soft gain."""
    class Capped(SimLink):
        SPEED_CAP, ACCEL_CAP = 120.0, 1500.0

    link = Capped()
    out = tmp_path / "capped.csv"
    code, _ = _run(link, out, ["pitch"], hold_s=1.5)
    assert code == 0
    recs = cal.load_recording(out)
    desc = cal.mjcf.load()
    fitted, err = cal.fit_joints(recs, desc, rounds=60)
    assert abs(fitted["pitch_speed_cap_deg_s"] - 120.0) / 120.0 < 0.35, fitted
    quals = cal.quality(recs, desc, fitted)
    assert quals["pitch"]["rms_pct_of_step"] < 5 and quals["pitch"]["step_deg"] >= 50
    # a recording of a head that follows a cap fitted without caps would miss: the gate sees the difference
    no_caps = dict(fitted, pitch_speed_cap_deg_s=1e6, pitch_accel_cap_deg_s2=1e9)
    assert cal.quality(recs, desc, no_caps)["pitch"]["rms_deg"] > quals["pitch"]["rms_deg"]


def test_a_poor_fit_is_reported_and_refused_for_writing(tmp_path, capsys, monkeypatch):
    rng = random.Random(5)
    rows = ["joint,move_id,t_ms,cmd_deg,meas_deg,rtt_ms"]
    for i in range(160):  # the head follows nothing like a servo: it wanders by tens of degrees whatever is commanded
        rows.append(f"pitch,{i // 40},{i * 50},{10 if (i // 40) % 2 == 0 else 70},{rng.uniform(5, 75):.0f},200")
    path = tmp_path / "wander.csv"
    path.write_text("\n".join(rows) + "\n")
    robots = tmp_path / "robots"
    robots.mkdir()
    original = (cal.HERE / "robots" / "stackchan.robot.json").read_text()
    (robots / "stackchan.robot.json").write_text(original)
    monkeypatch.setattr(cal, "HERE", tmp_path)
    assert cal.main([str(path), "--write"]) == 4
    assert "not written" in capsys.readouterr().err
    assert (robots / "stackchan.robot.json").read_text() == original


class BenchSerialModule(FakeSerialModule):
    """A bench build: self.bench.set_head answers the read-back angles; the ordinary head move would be ignored while idle."""

    def __init__(self, bench=True):
        super().__init__()
        self.bench = bench
        self.sent = []

    def call(self, port, name, args=None, wait=5.0):
        self.sent.append((name, args))
        if self.first:
            self.first = False
            return {"text": "Unknown tool"}
        if name == "self.bench.set_head":
            return {"ok": True, "yaw": 0, "pitch": args.get("pitch", 5), "read_back": True} if self.bench else {"text": "Unknown tool"}
        if name == "self.robot.set_head_angles":
            return True
        return {"ok": True}


def test_the_serial_link_moves_the_head_with_the_bench_tool_when_the_build_has_it():
    mod = BenchSerialModule(bench=True)
    link = rec.SerialLink(mod=mod, port=object())
    reply = link.move("pitch", 60)
    assert reply["read_back"] is True
    name, args = [x for x in mod.sent if x[0] == "self.bench.set_head"][0]
    assert args == {"pitch": 60, "speed": 1000, "hold_ms": 0}  # speed at the tool's top, no hold: the recorder samples itself
    assert not [x for x in mod.sent if x[0] == "self.robot.set_head_angles"]


def test_the_serial_link_falls_back_to_the_ordinary_head_move_on_a_build_without_the_bench_tool():
    mod = BenchSerialModule(bench=False)
    link = rec.SerialLink(mod=mod, port=object())
    assert link.move("pitch", 60) == {"ok": True}  # a bare true
    assert link.has_bench_head is False
    link.move("pitch", 10)
    assert len([x for x in mod.sent if x[0] == "self.bench.set_head"]) == 1  # asked once, then not again
    assert [x for x in mod.sent if x[0] == "self.robot.set_head_angles"]
