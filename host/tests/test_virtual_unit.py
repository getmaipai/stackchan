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
    assert listed["tools"] == ext.extract(), (
        "schema/tools.json is stale: run python3 scripts/virtual-unit/tools_extract.py"
    )
    assert listed["count"] == len(listed["tools"]) >= 100


def _rgb(png: bytes):
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", png[16:24])
    raw = zlib.decompress(png[png.index(b"IDAT") + 4 : png.rindex(b"IEND") - 8])
    return w, h, raw


needs_render = pytest.mark.skipif(
    not (ROOT / ".runs" / "vu-build" / "render").exists(),
    reason="renderer not built (scripts/fw-face-render/build.sh)",
)


@needs_render
def test_parity_every_firmware_tool_answers_and_gaps_are_explicit():
    vu = _load("vunit")
    with vu.VirtualUnit() as u:
        assert len(u.tools_list()) == len(u.tool_names) >= 100
        assert u.call("self.audio.notify", {}).get(
            "text", ""
        ) == "" or "not simulated" not in u.call("self.audio.notify", {}).get("text", "")
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
    p = subprocess.Popen(
        [sys.executable, str(VU / "vunit.py"), "serve"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )

    def rpc(i, m, params=None):
        p.stdin.write(json.dumps({"id": i, "method": m, "params": params or {}}) + "\n")
        p.stdin.flush()
        return json.loads(p.stdout.readline())["result"]

    assert rpc(1, "initialize")["serverInfo"]["name"] == "StackChan"
    assert len(rpc(2, "tools/list")["tools"]) >= 100
    assert rpc(3, "sim/advance", {"ms": 700})["now_ms"] == 2200
    assert rpc(4, "sim/snapshot")["png_base64"]
    p.stdin.close()
    p.wait(timeout=10)


@needs_render
def test_golden_frames_and_layout_scenarios():
    out = subprocess.run([sys.executable, str(VU / "scenarios.py")], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


@needs_render
def test_browser_view_serves_frame_and_calls():
    import time
    import urllib.request

    p = subprocess.Popen(
        [sys.executable, str(VU / "view.py"), "0"], stdout=subprocess.PIPE, text=True
    )
    try:
        base = p.stdout.readline().split()[-1]
        time.sleep(0.5)
        png = urllib.request.urlopen(base + "frame.png?1").read()
        assert png[:4] == b"\x89PNG"
        req = urllib.request.Request(
            base + "call",
            json.dumps(
                {"name": "self.face.bench_emotion", "arguments": {"emotion": "sad"}}
            ).encode(),
        )
        assert json.loads(urllib.request.urlopen(req).read()) == {"ok": True}
        page = urllib.request.urlopen(base).read().decode()
        words = json.loads((Path(__file__).resolve().parents[2] / "docs" / "legal" / "affiliation.json").read_text())
        assert "<title>MaiPai for StackChan: virtual unit</title>" in page and words["short"] in page, "the page carries the project's name and the short affiliation notice"
        tools = json.loads(urllib.request.urlopen(base + "tools").read())
        assert len(tools["tools"]) >= 100 and any(t["user_only"] for t in tools["tools"])
        if tools[
            "touch"
        ]:  # the screens renderer is built: a tap and a swipe reach the unit's own touch code
            for body in (
                {"kind": "tap", "x": 160, "y": 120},
                {"kind": "swipe", "x": 160, "y": 230, "x2": 160, "y2": 120},
            ):
                post = urllib.request.Request(base + "touch", json.dumps(body).encode())
                assert json.loads(urllib.request.urlopen(post).read())["ok"]
            log = json.loads(urllib.request.urlopen(base + "log").read())["log"]
            assert [e["name"] for e in log if e["name"].startswith("touch.")] == [
                "touch.tap",
                "touch.swipe",
            ]
        assert (
            "face-happy"
            in json.loads(urllib.request.urlopen(base + "scenarios").read())["scenarios"]
        )
    finally:
        p.terminate()
        p.wait(timeout=10)


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
        assert (
            u.call("self.robot.set_head_angles", {"yaw": 500, "pitch": 500})["yaw"] == 128
        )  # clamped to the range
        for _ in range(60):
            u.call("self.robot.set_head_angles", {"yaw": 1})
        assert u.call("self.robot.set_head_angles", {"yaw": 2})["ok"] is False
        u.advance(61000)
        assert u.call("self.robot.set_head_angles", {"yaw": 2})["ok"] is True


@needs_render
def test_ring_lights_and_battery():
    vu = _load("vunit")
    with vu.VirtualUnit() as u:
        args = {
            f"led_{i}_{c}": (i * 20 if c == "red" else 0)
            for i in range(12)
            for c in ("red", "green", "blue")
        }
        assert u.call("self.robot.set_led_colors", args)["ok"]
        assert u.leds[3] == (60, 0, 0)
        assert u.call("self.robot.set_led_colors", {"led_0_red": 1})["isError"]
        u.call("self.battery.simulate", {"level": 12})
        assert u.call("self.battery.get_status")["percent"] == 12


@needs_render
def test_face_consistency_across_styles_has_no_new_violation():
    out = subprocess.run(
        [sys.executable, str(VU / "face_consistency.py")], capture_output=True, text=True
    )
    assert out.returncode == 0, out.stdout + out.stderr


@needs_render
def test_bench_check_dry_runs():
    out = subprocess.run(
        [sys.executable, str(VU / "bench_checks.py")], capture_output=True, text=True
    )
    assert out.returncode == 0, out.stdout + out.stderr


@pytest.mark.skipif(
    not (ROOT / ".runs" / "vu-screens" / "render").exists(), reason="screens renderer not built"
)
def test_first_run_flow_by_taps_ends_with_the_answers():
    vu = _load("vunit")
    with vu.VirtualUnit(profile="screens") as u:
        u.raw("frun start")
        u.advance(600)
        for tap in ((56, 98), (56, 98)):  # language English, name StackChan (the first one shown, index 6 since the firmware made it the default)
            u.tap(*tap)
            u.advance(300)
        u.raw("frun wifi")  # the Wi-Fi cover reports done
        u.advance(300)
        for tap in (
            (160, 180),  # route B, Custom (patch UX19): the three ways open
            (160, 70),
            (160, 220),
            (160, 190),
        ):  # MaiPai Home (the first of the three ways), a tap on the privacy "Got it" button
            u.tap(*tap)
            u.advance(300)
        u.advance(2500)  # "All set!" closes itself after 2 s
        u._sync()
        assert "firstrun finished 0 6 0" in u.output


@pytest.mark.skipif(
    not (ROOT / ".runs" / "vu-screens" / "render").exists(), reason="screens renderer not built"
)
def test_a_recording_replays_the_same_gestures_on_the_unit(tmp_path):
    """A recording saved by the 3D view (waits, touches, tool calls) replays through the unit's own gesture code."""
    sc = _load("scenarios")
    rec = tmp_path / "r.json"
    rec.write_text(
        json.dumps(
            {
                "version": 1,
                "name": "r",
                "steps": [
                    {
                        "wait_ms": 0,
                        "touch": {
                            "kind": "swipe",
                            "x": 160,
                            "y": 230,
                            "x2": 160,
                            "y2": 120,
                            "ms": 250,
                        },
                    },
                    {
                        "wait_ms": 400,
                        "call": {
                            "name": "self.face.bench_emotion",
                            "arguments": {"emotion": "happy"},
                        },
                    },
                ],
            }
        )
    )
    steps = sc.load_recording(rec)
    assert steps[0] == ("raw", "pswipe 160 230 160 120 250") and ("advance", 400) in steps
    with sc.vunit.VirtualUnit(profile="screens") as u:
        sc.run(u, steps)
        u.advance(300)
        u.raw("pstate")
        u._sync()
        assert any(
            line.startswith("pstate") and "sheet 1" in line for line in u.output
        )  # the swipe up opened the sheet
