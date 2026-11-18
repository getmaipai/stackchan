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

    def __init__(self, state="free", rtt=0.02, noise=0.1):
        self.now, self.rtt, self.state, self.noise = 0.0, rtt, state, noise
        self.hist = {"pitch": [(0.0, 10.0)], "yaw": [(0.0, 0.0)]}
        self.calls, self.rng, self.sim = [], random.Random(3), {}
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

        st = self.sim.setdefault(joint, {"q": math.radians(self.hist[joint][0][1]), "dq": 0.0, "t": 0.0})
        inertia = cal.head_inertia_pitch(self.desc) if joint == "pitch" else cal.head_inertia_yaw(self.desc)
        kp, kv = self.TRUE[joint]
        grav = cal.gravity_coefficient(self.desc, joint)
        dt = 0.001
        while st["t"] < t:
            target = math.radians(next(c for (tt, c) in reversed(self.hist[joint]) if tt <= st["t"]))
            u = max(-self.TORQUE, min(self.TORQUE, kp * (target - st["q"]) - kv * st["dq"]))
            fr = 0.003 * (1 if st["dq"] > 0 else -1 if st["dq"] < 0 else 0)
            st["dq"] += (u - self.DAMPING * st["dq"] - fr + grav * math.sin(st["q"])) / inertia * dt
            st["q"] += st["dq"] * dt
            st["t"] += dt
        return math.degrees(st["q"]) + self.rng.gauss(0, self.noise)

    def _answer(self, name, args):
        if name == "self.motion.status":
            return {"ok": True, "state": self.state, "reasons": "on a USB cable" if self.state == "usb_limited" else ""}
        if name == "self.motion.set":
            self.state = "free" if args.get("usb_limit") == "off" else "usb_limited"
            return {"ok": True}
        if name == "self.robot.set_head_angles":
            for joint in ("yaw", "pitch"):
                if joint in args:
                    self.hist[joint].append((self.now, float(args[joint])))
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
    code, lines = _run(link, out, ["pitch", "yaw"])
    assert code == 0
    rows = list(csv.DictReader(out.open()))
    assert list(rows[0]) == ["joint", "move_id", "t_ms", "cmd_deg", "meas_deg", "rtt_ms"]
    assert {r["joint"] for r in rows} == {"pitch", "yaw"} and len(rows) > 400
    assert any("median round trip" in line for line in lines)
    recs = cal.load_recording(out)
    fitted, err = cal.fit_joints(recs, cal.mjcf.load(), rounds=25)
    assert err**0.5 < 0.6
    assert abs(fitted["pitch_kp"] - 0.62) / 0.62 < 0.15 and abs(fitted["yaw_kp"] - 0.45) / 0.45 < 0.25


def test_a_cable_limited_unit_is_refused_with_the_way_out_and_can_be_lifted_for_the_run(tmp_path):
    link = SimLink(state="usb_limited")
    code, lines = _run(link, tmp_path / "x.csv", ["pitch"])
    assert code == 2 and "usb-limit-off" in lines[0] and not (tmp_path / "x.csv").exists()
    code, _ = _run(link, tmp_path / "y.csv", ["pitch"], usb_limit_off=True)
    assert code == 0 and link.state == "usb_limited"  # restored at the end
    assert ("self.motion.set", {"usb_limit": "off"}) in link.calls and ("self.motion.set", {"usb_limit": "limited"}) in link.calls


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
