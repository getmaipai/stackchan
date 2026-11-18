# ruff: noqa: E501
"""The virtual unit's body (scripts/virtual-unit/hw.py): power, USB-C cable, Wi-Fi, battery, carried, and what they do to the screen, the limiter and the head.

The first group needs nothing built. The second drives the running browser view over HTTP (a scripted scenario: power cycle, cable, low battery, carried,
dance, the head move cap) and needs the screens renderer (`bash scripts/virtual-unit/build-screens.sh`); it skips without it."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

VU = Path(__file__).resolve().parents[2] / "scripts" / "virtual-unit"
spec = importlib.util.spec_from_file_location("hw", VU / "hw.py")
hw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hw)


def test_power_cycle_runs_the_boot_covers_in_order():
    body = hw.Hardware()
    body.press_power(0)  # off
    assert not body.on and body.boot_cover(10) is None
    body.press_power(1000)  # on
    assert body.boot_cover(1100)[0] == "Starting..."
    assert body.boot_cover(1000 + hw.BOOT_MS + 100)[0] == "Connecting to Wi-Fi..."
    assert body.boot_cover(1000 + hw.BOOT_MS + hw.WIFI_MS + 100)[0] == "Connecting to Home..."
    assert body.boot_cover(1000 + hw.BOOT_MS + hw.WIFI_MS + hw.HOME_MS + 100) is None and body.boot_started is None


def test_without_wi_fi_the_boot_ends_on_the_setup_cover_then_the_face():
    body = hw.Hardware()
    body.set("wifi", False, 0)
    body.press_power(0)
    body.press_power(500)
    assert body.boot_cover(600)[0] == "Starting..."
    assert body.boot_cover(500 + hw.BOOT_MS + 50)[0].startswith("Wi-Fi setup")
    assert body.boot_cover(500 + hw.BOOT_MS + hw.WIFI_MS + 50) is None
    assert body.status_args()[2] == 0  # the status bar shows offline


def test_an_empty_battery_with_no_cable_will_not_power_on_and_says_what_to_do():
    body = hw.Hardware()
    body.set("battery", 0, 0)
    body.press_power(0)
    assert "Plug in the USB-C cable" in body.press_power(10)
    body.set("usb", True, 20)
    assert body.press_power(30) is None and body.on


def test_cable_charging_serial_and_the_unplug_rules():
    body = hw.Hardware()
    assert body.powered_by == "battery" and not body.charging
    assert "plug the USB-C cable in first" in body.set("serial", True, 0)
    body.set("usb", True, 0)
    body.set("serial", True, 0)
    assert body.charging and body.powered_by == "side" and body.serial
    body.set("battery", 100, 0)
    assert not body.charging  # full: the cable stays, charging stops
    body.set("usb", False, 0)
    assert not body.serial  # no cable, no serial


def test_the_low_battery_ladder_matches_patch_t01():
    body = hw.Hardware()
    for level, tired in ((50, 0), (21, 0), (20, 1), (11, 1), (10, 2), (6, 2)):
        body.set("battery", level, 0)
        assert body.tired_level() == tired, level
    body.set("usb", True, 0)
    assert body.tired_level() == 0  # a cable clears the tired look
    body.set("usb", False, 0)
    body.set("battery", 5, 0)
    assert body.tick(1000) is None and body.view()["sleeping_soon"]
    assert body.tick(1000 + hw.SLEEP_GRACE_MS - 1) is None and body.on
    assert body.tick(1000 + hw.SLEEP_GRACE_MS) == "power_off" and not body.on


def test_plugging_in_during_the_sleep_grace_cancels_the_sleep():
    body = hw.Hardware()
    body.set("battery", 4, 0)
    body.tick(0)
    body.set("usb", True, 100)
    assert body.tick(hw.SLEEP_GRACE_MS + 10) is None and body.on


def test_motion_inputs_follow_the_body():
    body = hw.Hardware()
    body.set("carried", True, 0)
    body.set("usb", True, 0)
    body.set("battery", 33, 0)
    body.set("orient", "tilted", 0)
    assert body.motion_force() == [1, 1, 33, 1]
    assert "orientation is one of" in body.set("orient", "sideways", 0)


def test_dances_stay_inside_the_limiters_excursion_and_stop_at_zero():
    full = max(abs(hw.dance_offset("look_around", t, 100, 1000)[0]) for t in range(0, 6000, 50))
    half = max(abs(hw.dance_offset("look_around", t, 50, 1000)[0]) for t in range(0, 6000, 50))
    assert 50 < full <= 60 and half <= 31
    assert hw.dance_offset("happy", 500, 0, 1000) == (0.0, 0.0)  # a carried unit does not dance
    assert hw.dance_offset("nope", 500, 100, 1000) == (0.0, 0.0)


# ---- the running view ---------------------------------------------------------------------------------

needs_render = pytest.mark.skipif(not (VU.parents[1] / ".runs" / "vu-screens" / "render").exists(), reason="needs the screens renderer: bash scripts/virtual-unit/build-screens.sh")


@pytest.fixture
def view():
    proc = subprocess.Popen([sys.executable, str(VU / "view.py"), "0"], stdout=subprocess.PIPE, text=True)
    base = proc.stdout.readline().split()[-1]
    time.sleep(0.6)
    yield base
    proc.terminate()
    proc.wait(timeout=10)


def _get(base, path):
    return urllib.request.urlopen(base + path).read()


def _post(base, path, body):
    req = urllib.request.Request(base + path, json.dumps(body).encode())
    return json.loads(urllib.request.urlopen(req).read())


def _state(base):
    return json.loads(_get(base, "state"))


def _wait(base, test, seconds=6):
    end = time.time() + seconds
    while time.time() < end:
        st = _state(base)
        if test(st):
            return st
        time.sleep(0.15)
    raise AssertionError(f"state never reached the condition: {_state(base)['hw']}")


@needs_render
def test_scripted_body_scenario_power_cable_battery_carried_dance(view):
    st = _state(view)
    assert st["hw"]["on"] and st["motion"]["state"] == "free" and st["yaw_range"] == [-128, 128] and st["pitch_range"] == [3, 87]
    # off: a black screen, tools refused with the way out in the message
    _post(view, "hw", {"key": "power", "value": 1})
    _wait(view, lambda s: not s["hw"]["on"])
    time.sleep(0.3)
    assert _get(view, "frame.png") == _get(view, "frame.png")
    refused = _post(view, "call", {"name": "self.face.bench_emotion", "arguments": {"emotion": "happy"}})
    assert refused["isError"] and "Press its power button" in refused["text"]
    # on: the boot cover shows, then the face
    _post(view, "hw", {"key": "power", "value": 1})
    assert _wait(view, lambda s: s["hw"]["booting"])["hw"]["on"]
    _wait(view, lambda s: not s["hw"]["booting"], seconds=12)
    # a cable: USB powered and charging, the limiter halves the excursion
    _post(view, "hw", {"key": "usb", "value": True})
    st = _wait(view, lambda s: s["hw"]["charging"])
    assert st["hw"]["powered_by"] == "side" and st["motion"]["state"] == "usb_limited" and st["motion"]["scale"] == 50
    # a low battery on its own power: minimal band refuses a dance, in the unit's own words
    _post(view, "hw", {"key": "usb", "value": False})
    _post(view, "hw", {"key": "battery", "value": 12})
    st = _wait(view, lambda s: s["motion"]["battery_band"] == "minimal")
    assert not _post(view, "call", {"name": "self.robot.dance", "arguments": {"name": "happy"}})["ok"]
    # full battery, free: a dance moves the head inside its limits
    _post(view, "hw", {"key": "battery", "value": 100})
    _wait(view, lambda s: s["motion"]["state"] == "free")
    # patch SF51: the four built-in dances are ladder sessions now (eyes, then the nod: the head sways from the third step, 8 s in); the sway itself is step 3 of the beat dance
    assert _post(view, "call", {"name": "self.music.set", "arguments": {"enabled": True}})["ok"]
    assert _post(view, "call", {"name": "self.music.stage", "arguments": {"stage": 3}})["ok"]
    seen = {round(_state(view)["head"]["yaw"]) for _ in range(12) if not time.sleep(0.4)}
    assert max(seen) - min(seen) > 40 and all(-128 <= y <= 128 for y in seen)
    _post(view, "call", {"name": "self.robot.stop_dance", "arguments": {}})
    # carried: head moves are refused
    _post(view, "hw", {"key": "carried", "value": True})
    _wait(view, lambda s: s["motion"]["state"] == "carried")
    moved = _post(view, "call", {"name": "self.robot.set_head_angles", "arguments": {"yaw": 40, "pitch": 20}})
    assert moved["ok"] is False and "held or tilted" in moved["text"]
    _post(view, "hw", {"key": "carried", "value": False})
    _wait(view, lambda s: s["motion"]["state"] == "free")
    # the head move cap: 40 in a minute, the counter shows it
    for i in range(41):
        out = _post(view, "call", {"name": "self.robot.set_head_angles", "arguments": {"yaw": i % 20, "pitch": 10, "speed": 1000}})
    assert out["ok"] is False and "40 head moves" in out["text"]
    assert _state(view)["moves_last_minute"] >= 40
