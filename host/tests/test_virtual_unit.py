"""Virtual unit: tool parity with the firmware patches, and the protocol over the real LVGL face (skipped when the renderer is not built)."""
import importlib.util
import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VU = ROOT / "scripts" / "virtual-unit"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, VU / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_tool_list_matches_firmware_patches():
    ext = _load("tools_extract")
    listed = json.loads((ROOT / "schema" / "tools.json").read_text())
    assert listed["tools"] == ext.extract(), "schema/tools.json is stale: run python3 scripts/virtual-unit/tools_extract.py"
    assert listed["count"] == len(listed["tools"]) >= 100


def _rgb(png: bytes):
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", png[16:24])
    raw = zlib.decompress(png[png.index(b"IDAT") + 4 : png.rindex(b"IEND") - 8])
    return w, h, raw


needs_render = pytest.mark.skipif(not (ROOT / ".runs" / "vu-build" / "render").exists(), reason="renderer not built (scripts/fw-face-render/build.sh)")


@needs_render
def test_parity_every_firmware_tool_answers_and_gaps_are_explicit():
    vu = _load("vunit")
    with vu.VirtualUnit() as u:
        assert len(u.tools_list()) == len(u.tool_names) >= 100
        out = u.call("self.audio.notify", {})
        assert out["isError"] and "not simulated" in out["text"]
        assert u.call("self.nope", {})["isError"]


@needs_render
def test_emotion_speak_snapshot_fake_clock_and_touch():
    vu = _load("vunit")
    with vu.VirtualUnit() as u:
        assert u.call("self.face.bench_emotion", {"emotion": "happy"}) == {"ok": True}
        u.advance(1200)
        png = u.snapshot()
        w, h, _ = _rgb(png)
        assert (w, h) == (320, 240)
        assert u.count(0, 0, 320, 240)["lit"] > 500  # a face is drawn
        t0 = u.now_ms
        assert u.call("self.face.bench_speak", {"level": 70, "seconds": 2}) == {"ok": True}
        u.advance(500)
        assert u.now_ms == t0 + 500
        u.advance(3000)  # speech ends on the fake clock, with no real waiting
        u.touch(160, 4, 200)
        assert u.touches[-1][1:3] == (160, 4)
        assert u.call("self.face.bench_emotion", {"emotion": "x"})["isError"]


@needs_render
def test_process_protocol():
    p = subprocess.Popen([sys.executable, str(VU / "vunit.py"), "serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    def rpc(i, m, params=None):
        p.stdin.write(json.dumps({"id": i, "method": m, "params": params or {}}) + "\n"); p.stdin.flush()
        return json.loads(p.stdout.readline())["result"]
    assert rpc(1, "initialize")["serverInfo"]["name"] == "StackChan"
    assert len(rpc(2, "tools/list")["tools"]) >= 100
    assert rpc(3, "sim/advance", {"ms": 700})["now_ms"] == 2200
    assert rpc(4, "sim/snapshot")["png_base64"]
    p.stdin.close(); p.wait(timeout=10)


@needs_render
def test_golden_frames_and_layout_scenarios():
    out = subprocess.run([sys.executable, str(VU / "scenarios.py")], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


@needs_render
def test_browser_view_serves_frame_and_calls():
    import time
    import urllib.request
    p = subprocess.Popen([sys.executable, str(VU / "view.py"), "0"], stdout=subprocess.PIPE, text=True)
    try:
        base = p.stdout.readline().split()[-1]
        time.sleep(0.5)
        png = urllib.request.urlopen(base + "frame.png?1").read()
        assert png[:4] == b"\x89PNG"
        req = urllib.request.Request(base + "call", json.dumps({"name": "self.face.bench_emotion", "arguments": {"emotion": "sad"}}).encode())
        assert json.loads(urllib.request.urlopen(req).read()) == {"ok": True}
        assert b"Virtual StackChan" in urllib.request.urlopen(base).read()
    finally:
        p.terminate(); p.wait(timeout=10)


@needs_render
def test_head_motion_on_the_fake_clock_and_the_move_cap():
    vu = _load("vunit")
    with vu.VirtualUnit() as u:
        assert u.call("self.robot.get_head_angles") == {"yaw": 0, "pitch": 0}
        assert u.call("self.robot.set_head_angles", {"yaw": 60, "speed": 100})["ok"]
        u.advance(300)
        mid = u.call("self.robot.get_head_angles")
        assert 0 < mid["yaw"] < 60 and mid["pitch"] == 0
        u.advance(600)
        assert u.call("self.robot.get_head_angles")["yaw"] == 60
        assert u.call("self.robot.set_head_angles", {"yaw": 500, "pitch": 500})["yaw"] == 128  # clamped to the range
        for _ in range(60):
            u.call("self.robot.set_head_angles", {"yaw": 1})
        assert u.call("self.robot.set_head_angles", {"yaw": 2})["ok"] is False
        u.advance(61000)
        assert u.call("self.robot.set_head_angles", {"yaw": 2})["ok"] is True


@needs_render
def test_ring_lights_and_battery():
    vu = _load("vunit")
    with vu.VirtualUnit() as u:
        args = {f"led_{i}_{c}": (i * 20 if c == "red" else 0) for i in range(12) for c in ("red", "green", "blue")}
        assert u.call("self.robot.set_led_colors", args)["ok"]
        assert u.leds[3] == (60, 0, 0)
        assert u.call("self.robot.set_led_colors", {"led_0_red": 1})["isError"]
        u.call("self.battery.simulate", {"level": 12})
        assert u.call("self.battery.get_status")["percent"] == 12
