# ruff: noqa: E501
"""The movement limiter (firmware patch ML01): the unit does the limiting; the host reads the state and stops asking.

C tests of the rule live in ``firmware/motion_limit_core_test.c`` (state transitions with debounce, clamping, the speed cap, the hold
when carried, the off switch never overriding carried, the battery ladder with hysteresis and its mix with USB and carried).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir
from test_stackchan_dance_ladder import _args, _chain, _run_chain
from test_stackchan_music_dance import _real_behavior

from maipai_body import i18n
from maipai_body.bodies.stackchan.dance import (
    DanceHooks,
    DanceRunner,
    DanceSettings,
    DanceSituation,
)
from maipai_body.bodies.stackchan.head_gate import HeadMotionGate
from maipai_body.bodies.stackchan.motion_limit import FREE, MotionLimit, parse_status
from maipai_body.hal.errors import NotSupported

HERE = Path(__file__).resolve().parent


def status(state="free", **kw) -> str:
    base = {
        "ok": True,
        "state": state,
        "scale": 100,
        "speed_cap": 1000,
        "dance_max": 4,
        "battery_band": "none",
        "usb_limit": "limited",
        "refused_count": 0,
    }
    return json.dumps({**base, **kw})


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_the_c_core_tests_pass(tmp_path_factory, tmp_path) -> None:
    hal = cores_dir(tmp_path_factory)
    binary = tmp_path / "t"
    built = subprocess.run(
        [
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{hal}",
            str(HERE / "firmware/motion_limit_core_test.c"),
            "-o",
            str(binary),
            "-lm",
        ],
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout


def test_the_status_answer_is_read_and_a_bad_answer_counts_as_free() -> None:
    state = parse_status(status("usb_limited", scale=50, speed_cap=600, dance_max=3))
    assert (
        state.state == "usb_limited"
        and state.scale == 50
        and state.dance_max == 3
        and not state.hold
        and state.dances_ok
    )
    assert parse_status(status("carried", scale=0, dance_max=0)).hold
    assert (
        parse_status("nonsense") == FREE
        and parse_status({"ok": False}) == FREE
        and parse_status(None) == FREE
    )
    assert parse_status(status("flying")) == FREE


def test_the_host_caches_the_state_and_an_old_unit_is_free() -> None:
    calls: list = []
    now = [0.0]

    def call(name, args):
        calls.append(name)
        return status("usb_limited", scale=50, dance_max=3)

    limit = MotionLimit(call, clock=lambda: now[0])
    assert limit.state().state == "usb_limited" and limit.state().state == "usb_limited"
    assert calls == ["self.motion.status"]  # cached
    now[0] += 6.0
    limit.state()
    assert len(calls) == 2

    def old(name, args):
        raise NotSupported(name)

    older = MotionLimit(old, clock=lambda: now[0])
    assert older.state() == FREE and older.unsupported


def test_set_usb_sends_the_choice_and_refuses_other_words() -> None:
    sent: list = []
    limit = MotionLimit(lambda name, args: sent.append((name, args)) or status(), clock=lambda: 0.0)
    assert limit.set_usb("off") and ("self.motion.set", {"usb_limit": "off"}) in sent
    with pytest.raises(ValueError, match="limited or off"):
        limit.set_usb("loose")


def test_the_head_gate_does_not_ask_while_the_unit_is_held_but_a_return_to_center_passes() -> None:
    reason = ["held or carried"]
    gate = HeadMotionGate(must_be_still=lambda: False, motion_hold=lambda: reason[0])
    assert not gate.allow("idle")
    assert not gate.allow(
        "face", response=True
    )  # even an answer to a person: the unit would refuse it
    assert gate.allow("settle", essential=True)
    reason[0] = ""
    assert gate.allow("idle")


def _runner(situation: DanceSituation) -> DanceRunner:
    hooks = DanceHooks(
        start_dance=lambda n: None,
        stop_dance=lambda: None,
        show_face=lambda f: None,
        write_ring=lambda p: None,
        take_ring=lambda: None,
        give_ring_back=lambda: None,
        level_head=lambda: None,
        situation=lambda: situation,
    )
    return DanceRunner(hooks, DanceSettings())


def test_a_dance_is_refused_while_carried_or_when_the_limiter_allows_no_dance_and_says_why() -> (
    None
):
    sit = DanceSituation(battery_percent=90, charging=False)
    for kw in ({"motion": "carried"}, {"motion": "battery_limited", "motion_dance_max": 0}):
        reply = _runner(replace(sit, **kw)).request("auto")
        assert not reply.started and "movement is limited" in reply.why
    assert _runner(replace(sit, motion="usb_limited", motion_dance_max=3)).request("auto").started


def test_a_running_dance_ends_the_moment_the_unit_is_carried() -> None:
    runner = _runner(DanceSituation(battery_percent=90, charging=False, motion="carried"))
    assert runner._interrupt(runner.situation()) == "limited"


def test_on_usb_the_ladder_never_reaches_the_full_dance_and_the_unit_is_still_told_the_steps() -> (
    None
):
    behavior = _real_behavior()
    try:
        w = _chain(behavior)
        behavior.motion_limit = MotionLimit(
            lambda name, args: status("usb_limited", scale=50, speed_cap=600, dance_max=3),
            clock=lambda: 0.0,
        )
        _run_chain(w)
        stages = _args(w, "self.music.stage", "stage")
        assert stages and max(stages) == 3 and stages[-1] == 0
    finally:
        behavior.close()


def test_carried_gives_no_dance_at_all_through_the_whole_chain() -> None:
    behavior = _real_behavior()
    try:
        w = _chain(behavior)
        behavior.motion_limit = MotionLimit(
            lambda name, args: status("carried", scale=0, speed_cap=0, dance_max=0),
            clock=lambda: 0.0,
        )
        _run_chain(w)
        assert not _args(w, "self.music.stage", "stage")
    finally:
        behavior.close()


def test_the_settings_words_exist_in_english_and_spanish_and_say_the_plain_thing() -> None:
    for code in ("en", "es"):
        for key in (
            "title",
            "help",
            "usb",
            "usb_help",
            "state.free",
            "state.usb_limited",
            "state.battery_limited",
            "state.carried",
        ):
            text = i18n.CATALOG[code][f"settings.ui.pol.motion.{key}"]
            assert text.strip() and chr(0x2014) not in text, (code, key)
    assert i18n.CATALOG["en"]["settings.ui.pol.motion.help"].startswith(
        "On USB the robot moves gently; on battery it moves freely."
    )
    assert (
        i18n.CATALOG["es"]["settings.ui.pol.motion.help"]
        != i18n.CATALOG["en"]["settings.ui.pol.motion.help"]
    )
