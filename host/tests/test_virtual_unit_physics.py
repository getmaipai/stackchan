# ruff: noqa: E501
"""The optional physics mode of the virtual unit: the robot description, the model text built from it, the IMU rule, the calibration, and the host endpoints.
The engine itself (a WebAssembly build the browser loads on demand) is not run here; the page was checked in the browser."""

from __future__ import annotations

import importlib.util
import json
import math
import random
import re
import subprocess
import sys
import time
import urllib.request
import xml.dom.minidom
from pathlib import Path

import pytest

VU = Path(__file__).resolve().parents[2] / "scripts" / "virtual-unit"
PH = VU / "physics"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mjcf = _load("mjcf", PH / "mjcf.py")
imu = _load("imu", PH / "imu.py")
calibrate = _load("calibrate", PH / "calibrate.py")
vunit = _load("vunit_for_physics", VU / "vunit.py")


def test_every_parameter_is_marked_measured_or_assumed_with_a_note():
    desc = mjcf.load()
    for key, entry in desc["params"].items():
        assert entry["src"] in ("measured", "assumed"), key
        assert entry["note"], key
        assert "v" in entry, key
    groups = mjcf.provenance(desc)
    assert groups["measured"] and groups["assumed"]
    assert "pitch_kp" in groups["assumed"] and "mass_total" in groups["measured"]


def test_the_masses_add_up_to_the_measured_total():
    desc = mjcf.load()
    assert math.isclose(mjcf.total_mass(desc), mjcf.value(desc, "mass_total"), abs_tol=1e-6)


def test_the_model_text_is_well_formed_and_carries_the_real_limits_and_sizes():
    desc = mjcf.load()
    text = mjcf.mjcf(desc)
    doc = xml.dom.minidom.parseString(text)
    joints = {j.getAttribute("name"): j for j in doc.getElementsByTagName("joint") if j.getAttribute("type") == "hinge"}
    assert set(joints) == {"yaw", "pitch"}
    yr, pr = (list(map(float, joints[n].getAttribute("range").split())) for n in ("yaw", "pitch"))
    assert [round(math.degrees(v)) for v in yr] == list(vunit.YAW_RANGE) and [round(math.degrees(v)) for v in pr] == list(vunit.PITCH_RANGE)
    head = next(g for g in doc.getElementsByTagName("geom") if g.getAttribute("name") == "head")
    assert [round(float(v) * 2, 4) for v in head.getAttribute("size").split()] == [0.0155, 0.054, 0.054]  # depth, width, height of the CoreS3
    forces = [a.getAttribute("forcerange") for a in doc.getElementsByTagName("position")]
    assert len(forces) == 2 and all(f == "-0.12 0.12" for f in forces)  # the torque limit
    sensors = {s.getAttribute("name") for s in doc.documentElement.getElementsByTagName("sensor")[0].childNodes if s.nodeType == 1}
    assert {"imu_accel", "imu_gyro", "base_accel", "yaw_force", "pitch_force"} <= sensors
    # the head is above the pitch axis so that the whole robot is 70.5 mm tall with the head upright
    top = float(re.search(r'name="yaw_link" pos="0 0 ([-\d.e]+)"', text).group(1))
    assert top > 0


def test_the_sensor_order_the_driver_reads_matches_the_model_text():
    names = re.findall(r"<(?:accelerometer|gyro|jointpos|actuatorfrc) name=\"(\w+)\"", mjcf.mjcf(mjcf.load()))
    assert names == ["imu_accel", "imu_gyro", "yaw_pos", "pitch_pos", "yaw_force", "pitch_force", "base_accel"]
    js = (PH / "physics.js").read_text()
    assert "S = {accel: 0, gyro: 3, yawPos: 6, pitchPos: 7, yawF: 8, pitchF: 9, baseAccel: 10}" in js


def test_pickup_rule_needs_150_ms_to_go_on_and_a_second_of_calm_to_go_off():
    rule = imu.PickupRule()
    rest = (0.0, 0.0, 9.81)
    assert rule.feed(0, rest, 0) == (False, "upright")
    assert rule.feed(100, (0, 0, 14.0), 0)[0] is False  # a bump of 100 ms is not a pickup
    assert rule.feed(150, rest, 0)[0] is False
    for t in range(1000, 1200, 20):
        out = rule.feed(t, (0, 0, 14.0), 0)
    assert out[0] is True
    assert rule.feed(1300, rest, 0)[0] is True and rule.feed(2200, rest, 0)[0] is True
    assert rule.feed(2400, rest, 0)[0] is False


def test_orientation_bands_have_hysteresis():
    rule = imu.PickupRule()
    rest = (0.0, 0.0, 9.81)
    seen = [rule.feed(i * 100, rest, tilt)[1] for i, tilt in enumerate((5, 14, 16, 12, 9, 50, 42, 38, 12, 5))]
    assert seen == ["upright", "upright", "tilted", "tilted", "upright", "side", "side", "tilted", "tilted", "upright"]


def _recording(true, noise=0.15, seed=2):
    desc = mjcf.load()
    inertia = calibrate.head_inertia_pitch(desc)
    t = list(range(0, 2400, 10))
    cmd = [0 if x < 100 else 40 if x < 700 else 10 if x < 1300 else 60 for x in t]  # a step up, a step back, a large step
    sim = calibrate.simulate(t, cmd, 0, inertia, true[0], true[1], true[2], true[3], mjcf.value(desc, "joint_friction"))
    rng = random.Random(seed)
    return {"joint": "pitch", "samples": [{"t_ms": a, "cmd_deg": b, "meas_deg": m + rng.gauss(0, noise)} for a, b, m in zip(t, cmd, sim)]}, inertia, desc


def test_calibration_recovers_the_servo_gain_from_a_noisy_bench_recording():
    true = [0.62, 0.0065, 0.003, 0.12]
    rec, inertia, desc = _recording(true)
    start = [mjcf.value(desc, k) for k in ("pitch_kp", "pitch_kv", "joint_damping", "torque_limit")]
    theta, err = calibrate.fit(rec, inertia, start, mjcf.value(desc, "joint_friction"))
    assert math.sqrt(err) < 0.25  # about the noise
    assert abs(theta[0] - true[0]) / true[0] < 0.1


def test_calibration_writes_fitted_values_as_measured(tmp_path, monkeypatch):
    rec, _, _ = _recording([0.62, 0.0065, 0.003, 0.12])
    path = tmp_path / "rec.json"
    path.write_text(json.dumps(rec))
    robots = tmp_path / "robots"
    robots.mkdir()
    (robots / "stackchan.robot.json").write_text((PH / "robots" / "stackchan.robot.json").read_text())
    monkeypatch.setattr(calibrate, "HERE", tmp_path)
    assert calibrate.main([str(path), "--write"]) == 0
    fitted = json.loads((robots / "stackchan.robot.json").read_text())["params"]["pitch_kp"]
    assert fitted["src"] == "measured" and "rec.json" in fitted["note"]


def test_the_playground_names_the_engine_only_in_the_third_party_files():
    record = json.loads((PH / "THIRD-PARTY-physics-engine.json").read_text())
    assert record["license"] == "Apache-2.0" and re.search(r"@\d+\.\d+\.\d+/", record["module"])  # a pinned version, not a tag
    root = Path(__file__).resolve().parents[2]
    for name in ("THIRD-PARTY.md", "NOTICE"):
        assert record["name"] in (root / name).read_text(), name
    name = record["name"].lower()
    skip = {"THIRD-PARTY.md", "NOTICE", "THIRD-PARTY-physics-engine.json"}
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout.decode().split("\0")
    for rel in tracked:
        path = root / rel
        if not rel or not rel.startswith(("scripts/virtual-unit/", "docs/dev/virtual-unit", "docs/plan/physics-playground", "docs/plan/spec-proposals/robot-description")):
            continue  # the playground's own files; older design notes may name the engine in passing
        if Path(rel).name in skip or path.suffix in (".png", ".gif", ".wasm", ".bin", ".glb") or not path.is_file():
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        stripped = text.lower().replace("<" + name, "").replace("</" + name, "")  # the model file format's own root tag
        assert name not in stripped, f"{rel} names the engine; only THIRD-PARTY.md and NOTICE may"


needs_render = pytest.mark.skipif(not (VU.parents[1] / ".runs" / "vu-screens" / "render").exists(), reason="needs the screens renderer")


@needs_render
def test_host_serves_the_model_and_turns_imu_numbers_into_carried_and_orientation():
    proc = subprocess.Popen([sys.executable, str(VU / "view.py"), "0"], stdout=subprocess.PIPE, text=True)
    try:
        base = proc.stdout.readline().split()[-1]
        time.sleep(0.6)
        assert b"<mujoco" in urllib.request.urlopen(base + "physics/model.xml").read()
        assert json.loads(urllib.request.urlopen(base + "physics/engine.json").read())["version"]

        def post(path, body):
            return json.loads(urllib.request.urlopen(urllib.request.Request(base + path, json.dumps(body).encode())).read())

        def state():
            return json.loads(urllib.request.urlopen(base + "state").read())

        assert post("imu", {"accel": [0, 0, 9.81], "tilt_deg": 0, "t": 0})["carried"] is False
        out = None
        for _ in range(6):
            out = post("imu", {"accel": [0, 0, 15.0], "tilt_deg": 0})
            time.sleep(0.1)
        assert out["carried"] is True
        time.sleep(0.3)
        assert state()["motion"]["state"] == "carried" and state()["physics"]["driven"]
        post("imu/off", {})
        assert state()["physics"]["driven"] is False
    finally:
        proc.terminate()
        proc.wait(timeout=10)
