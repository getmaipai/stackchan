# ruff: noqa: E501
"""The two USB-C sockets of the virtual unit (scripts/virtual-unit/hw.py): one on the side of the controller, one at the back of the base,
on one shared USB path (bench, 2026-11-18: a computer on the back socket alone gives USB power and the same serial device).
Every combination, each source, the serial rule, the supply model and what the head limiter is told.

The first group needs nothing built. The second plays the scripted port scenarios (scripts/virtual-unit/scenarios.py, PORTS) through the
running view, so the answers are the unit's own limiter and status; it needs the screens renderer and skips without it.
The supply numbers are an assumed model until the bench measures them; the tests pin its shape, not its truth."""

from __future__ import annotations

import importlib.util
import itertools
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

VU = Path(__file__).resolve().parents[2] / "scripts" / "virtual-unit"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, VU / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hw = _load("hw")
scenarios = _load("scenarios")


@pytest.mark.parametrize("side,back", list(itertools.product([False, True], repeat=2)))
def test_every_combination_of_the_two_cables(side, back):
    body = hw.Hardware()
    body.set("side", side, 0)
    body.set("back", back, 0)
    v = body.view()
    assert v["powered_by"] == {(False, False): "battery", (True, False): "side", (False, True): "back", (True, True): "both"}[(side, back)]
    assert v["vbus"] == (side or back) and v["charging"] == (side or back) and v["usb"] == (side or back), "either socket is the same USB input"
    assert v["ports"]["side"]["plugged"] == side and v["ports"]["back"]["plugged"] == back
    assert v["serial_possible"] == side, "here only the side cable goes to a computer; the back one goes to a charger"
    assert v["supply"]["input_ma"] == (2000 if back else 500 if side else 0), "two cables act as the stronger source, never the sum"
    assert v["usb_path"]["both_plugged"] == (side and back) and v["usb_path"]["basis"] == "assumed" and "undefined" in v["usb_path"]["note"]
    assert body.motion_force()[1] == int(side or back), "today either cable counts for the limiter"
    assert v["limiter_cable"]["from"] == [n for n, on in (("side", side), ("back", back)) if on]


def test_the_sockets_hold_separate_cables_and_the_old_cable_name_sets_the_side_one():
    body = hw.Hardware()
    body.set("usb", True, 0)
    assert body.ports["side"]["plugged"] and not body.ports["back"]["plugged"] and body.usb
    body.set("back", True, 0)
    body.set("usb", False, 0)
    assert not body.ports["side"]["plugged"] and body.ports["back"]["plugged"] and body.powered_by == "back" and body.charging
    assert body.usb, "the unit still sees USB: the back socket is the same input"


def test_a_computer_on_the_back_socket_alone_gives_power_and_serial_as_on_the_bench():
    body = hw.Hardware()
    body.set("back_source", "computer", 0)
    body.set("back", True, 0)
    assert body.vbus and body.serial_possible and body.data_from == "back"
    assert body.set("serial", True, 0) is None and body.serial and body.view()["usb_path"]["data"]
    body.set("back", False, 0)
    assert not body.serial and not body.vbus


def test_serial_needs_a_cable_to_a_computer_in_either_socket_and_says_what_to_do():
    body = hw.Hardware()
    assert "plug the USB-C cable in first" in body.set("serial", True, 0)
    body.set("back", True, 0)   # the back cable goes to a charger
    assert "only a computer carries serial data" in body.set("serial", True, 0)
    body.set("side", True, 0)   # the side cable goes to a computer
    assert body.set("serial", True, 0) is None and body.serial and body.data_from == "side"
    body.set("side_source", "charger", 0)
    assert not body.serial, "swapping the computer for a charger ends the serial link"
    assert "source is one of" in body.set("back_source", "wall", 0)


@pytest.mark.parametrize("port", hw.PORTS)
def test_a_12_volt_supply_gives_no_power_and_the_log_says_why(port):
    body = hw.Hardware()
    body.set(f"{port}_source", "supply_12v", 0)
    body.set(port, True, 0)
    v = body.view()
    assert v["ports"][port]["fault"] and not v["ports"][port]["gives_power"] and v["ports"][port]["volts"] == 12.0
    assert v["powered_by"] == "battery" and not v["vbus"] and not v["charging"] and body.motion_force()[1] == 0
    assert "12 V is too much" in body.events[-1] and "unplug it" in body.events[-1]
    body.set("battery", 0, 0)
    body.press_power(0)
    assert "5 V" in body.press_power(10), "a 12 V cable cannot start a unit with an empty battery"


def test_the_supply_model_is_marked_assumed_and_sags_less_with_a_stronger_feed():
    def load_v(side=None, back=None, battery=75):
        body = hw.Hardware()
        body.set("battery", battery, 0)
        for name, source in (("side", side), ("back", back)):
            if source:
                body.set(f"{name}_source", source, 0)
                body.set(name, True, 0)
        s = body.supply()
        assert s["basis"] == "assumed" and s["idle_v"] >= s["load_v"] and abs(s["sag_v"] - (s["idle_v"] - s["load_v"])) < 0.011
        return s
    alone, computer, charger, both = load_v(), load_v(side="computer"), load_v(back="charger"), load_v(side="computer", back="charger")
    assert alone["load_v"] < computer["load_v"] < charger["load_v"] == both["load_v"] <= 5.0, "two cables act as the stronger one (assumed)"
    assert load_v(back="computer") == computer, "the socket does not matter: it is one USB path"
    assert not alone["brownout"] and not both["brownout"]
    assert load_v(side="computer", battery=0)["brownout"], "a 500 mA port alone cannot hold the rail with both servos moving"
    assert load_v(battery=0) == {**load_v(battery=0), "idle_v": 0.0, "load_v": 0.0, "brownout": True}


def test_the_limiter_cable_rule_lives_in_one_place(monkeypatch):
    body = hw.Hardware()
    body.set("back", True, 0)
    assert body.motion_force()[1] == 1 and body.view()["limiter_cable"]["counted_ports"] == ["side", "back"]
    monkeypatch.setattr(hw, "LIMITER_CABLE_PORTS", ("side",))   # the change the firmware track may ask for: back-port power lifts the limit
    assert body.motion_force()[1] == 0 and body.view()["limiter_cable"]["from"] == [] and body.charging
    body.set("side", True, 0)
    assert body.motion_force()[1] == 1
    assert sum("LIMITER_CABLE_PORTS" in line and "for n in" in line for line in (VU / "hw.py").read_text().splitlines()) == 2, "only limiter_cable and its report read the rule"


def test_power_rules_follow_either_cable():
    body = hw.Hardware()
    body.set("battery", 4, 0)
    body.tick(0)
    body.set("back", True, 100)
    assert body.tick(hw.SLEEP_GRACE_MS + 10) is None and body.on, "power on the back port cancels the low-battery sleep"
    assert body.tired_level() == 0


# ---- the scripted scenarios, through the running view -----------------------------------------------------

needs_render = pytest.mark.skipif(not (VU.parents[1] / ".runs" / "vu-screens" / "render").exists(), reason="needs the screens renderer: bash scripts/virtual-unit/build-screens.sh")


@pytest.fixture(scope="module")
def view():
    proc = subprocess.Popen([sys.executable, str(VU / "view.py"), "0"], stdout=subprocess.PIPE, text=True)
    base = proc.stdout.readline().split()[-1]
    time.sleep(0.6)
    yield base
    proc.terminate()
    proc.wait(timeout=10)


def _json(base, path, body=None):
    req = urllib.request.Request(base + path, json.dumps(body).encode()) if body is not None else base + path
    return json.loads(urllib.request.urlopen(req).read())


def _at(state, path):
    for key in path.split("."):
        state = state[key]
    return state


def test_the_scenario_list_covers_every_case_the_owner_named():
    assert set(scenarios.PORTS) >= {"ports-none", "ports-side-only", "ports-back-only", "ports-both", "ports-back-computer-serial", "ports-plug-during-dance", "ports-unplug-during-dance"}
    for name, sc in scenarios.PORTS.items():
        assert sc["expect"] and all(step[0] in ("hw", "call", "advance") for step in sc["steps"]), name


@needs_render
@pytest.mark.parametrize("name", list(scenarios.PORTS))
def test_port_scenario_plays_through_the_view_and_the_unit_agrees(view, name):
    assert name in _json(view, "scenarios")["scenarios"], "the scenario is in the view's list"
    assert _json(view, "scenario", {"name": name}).get("ok"), name
    end = time.time() + 15
    while _json(view, "log")["playing"] and time.time() < end:
        time.sleep(0.1)
    state = _json(view, "state")
    wrong = {path: (_at(state, path), want) for path, want in scenarios.PORTS[name]["expect"].items() if _at(state, path) != want}
    assert not wrong, f"{name}: got, wanted {wrong}"
    status = _json(view, "call", {"name": "self.motion.status", "arguments": {}})    # the unit's own word, through the tool path
    assert status["state"] == state["motion"]["state"] and status["usb"] == state["hw"]["limiter_cable"]["present"]
    assert _json(view, "call", {"name": "self.battery.get_status", "arguments": {}})["charging"] == state["hw"]["charging"]
    if "dance" in scenarios.PORTS[name]["expect"]:   # the dance is a session of the unit's dance simulation: it keeps running through the cable change
        sim = state["dance_sim"]
        assert sim and sim["running"] and sim["step"] >= 1, f"the dance session stopped when the cable changed: {sim}"
        later = _json(view, "state")
        assert later["dance"] == "look_around" and later["dance_sim"]["running"], "and it is still running a moment later"
