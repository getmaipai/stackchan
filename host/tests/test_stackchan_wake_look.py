# ruff: noqa: E501
"""Look around when the wake word is heard (wake_look.py, setting look_on_wake, default on): the sequence, every gate, the cap and the page."""

from __future__ import annotations

import json
import math
import time
from types import SimpleNamespace

import pytest

from maipai_body import i18n, wake_look
from maipai_body.app import StackChanBehavior
from maipai_body.bodies.stackchan.adapter import StackChanRobotAdapter
from maipai_body.bodies.stackchan.fake import FakeStackChanDeviceClient
from maipai_body.bodies.stackchan.profile import CENTER_PITCH_DEG
from maipai_body.settings_sim import KITCHEN, build

UP = CENTER_PITCH_DEG + wake_look.PITCH_DEG


class Rig:
    """A behavior on a fake unit that records every head.set (yaw and pitch in degrees, seconds, speed)."""

    def __init__(self) -> None:
        self.behavior = b = StackChanBehavior(StackChanRobotAdapter(FakeStackChanDeviceClient()).robot)
        b.night_active = lambda: False
        b.wake_look_scale = 0  # the pan runs at once
        self.moves: list[tuple[int, int, float | None, int | None]] = []
        original = b.robot.head.set

        def record(**kw):
            pose = kw["pose"]
            self.moves.append((round(math.degrees(pose.yaw)), round(math.degrees(pose.pitch)), kw.get("duration_s"), kw.get("speed")))
            return original(**kw)

        b.robot.head.set = record

    def wake(self) -> None:
        self.behavior.render_turn_state("listening")
        self.join()

    def join(self) -> None:
        thread = self.behavior._wake_thread
        if thread is not None:
            thread.join(5)

    def pans(self) -> list[tuple[int, int, float | None, int | None]]:
        return [m for m in self.moves if m[3] == wake_look.SPEED]


@pytest.fixture
def rig():
    r = Rig()
    try:
        yield r
    finally:
        r.behavior.close()


def _slow_rig() -> Rig:
    r = Rig()
    r.behavior.wake_look_scale = 1.0  # the pan waits about a second before its first stop: time to interrupt it
    return r


def test_the_setting_is_on_by_default(rig) -> None:
    assert rig.behavior.look_on_wake is True
    assert rig.behavior.look_toward_speaker is False and rig.behavior.look_for_faces is False  # the other two defaults are untouched


def test_the_normal_sequence_and_angles(rig) -> None:
    rig.wake()
    assert rig.moves == [(0, UP, 0.5, 130), (-25, UP, 0.7, 100), (25, UP, 0.9, 100), (0, UP, 0.4, 100)]
    assert rig.behavior.wake_looks == 1
    total = wake_look.GLANCE_S + wake_look.PAUSE_AFTER_GLANCE_S + sum(move + pause for _yaw, move, pause in wake_look.STEPS)
    assert total == pytest.approx(3.3)


def test_a_fresh_face_gets_one_turn_and_no_pan(rig) -> None:
    b = rig.behavior
    b._last_face = (0.7, 0.4, time.monotonic() - 10.0)
    rig.wake()
    assert b.wake_looks == 0 and rig.pans() == []
    assert len(rig.moves) == 1 and rig.moves[0][0] != 0  # one turn toward where the face was


def test_an_old_face_is_not_used(rig) -> None:
    rig.behavior._last_face = (0.7, 0.4, time.monotonic() - 90.0)
    rig.wake()
    assert rig.behavior.wake_looks == 1 and len(rig.pans()) == 3


def test_the_return_to_level_is_the_turns_own_settle(rig) -> None:
    rig.wake()
    before = len(rig.moves)
    rig.behavior.render_turn_state("settle")
    assert len(rig.moves) == before + 1 and rig.moves[-1][:2] == (0, CENTER_PITCH_DEG)


def _skipped(rig, reason: str, caplog) -> None:
    caplog.set_level("INFO")
    rig.wake()
    assert rig.pans() == [] and rig.behavior.wake_looks == 0
    assert reason in caplog.text
    assert not any(m[:2] == (0, UP) for m in rig.moves)  # not even the glance (the plain listening perk still plays)


def test_off_by_the_setting(rig) -> None:
    rig.behavior.look_on_wake = False
    rig.wake()
    assert rig.pans() == [] and rig.behavior.wake_looks == 0 and not any(m[:2] == (0, UP) for m in rig.moves)


def test_skipped_at_night(rig) -> None:
    rig.behavior.night_active = lambda: True
    rig.wake()
    assert rig.pans() == [] and rig.behavior.wake_looks == 0
    assert rig.behavior._wake_look_local_block() == "night or quiet hours"


def test_skipped_when_asleep_or_waking_from_sleep(rig, caplog) -> None:
    rig.behavior.rest_step(time.monotonic() + 1000.0)  # a long quiet spell: asleep
    assert rig.behavior._rest.stage == "asleep"
    _skipped(rig, "asleep or drowsy", caplog)


def test_skipped_when_muted(rig, caplog) -> None:
    rig.behavior.privacy = SimpleNamespace(muted=True, quiet=False, head_blocked=lambda: None)
    _skipped(rig, "muted or full quiet", caplog)


def test_skipped_in_full_quiet(rig, caplog) -> None:
    rig.behavior.privacy = SimpleNamespace(muted=False, quiet=True, head_blocked=lambda: "full quiet")
    _skipped(rig, "muted or full quiet", caplog)


def test_skipped_when_carried_or_tilted(rig, caplog) -> None:
    rig.behavior.pose_held = lambda: True
    _skipped(rig, "carried, tilted or held", caplog)


def test_skipped_when_the_orientation_sensors_are_untrusted(rig, caplog) -> None:
    rig.behavior.orientation = SimpleNamespace(sensors_untrusted=lambda: True, pose="upright")
    _skipped(rig, "carried, tilted or held", caplog)


def test_skipped_when_locked(rig, caplog) -> None:
    rig.behavior.wake_unit_busy = lambda: "locked"
    _skipped(rig, "locked", caplog)


def test_skipped_during_a_game(rig, caplog) -> None:
    rig.behavior.wake_unit_busy = lambda: "playing a game"
    _skipped(rig, "playing a game", caplog)


def test_skipped_during_a_dance(rig, caplog) -> None:
    rig.behavior.dance_active = lambda: True
    _skipped(rig, "a dance is running", caplog)


def test_skipped_when_the_units_seeker_owns_seeking(rig, caplog) -> None:
    rig.behavior.wake_seeker_owns = lambda: True
    _skipped(rig, "seeker owns seeking", caplog)


def test_a_wake_while_another_source_holds_the_head_does_nothing(rig) -> None:
    b = rig.behavior
    b.robot.lease.acquire(priority="expression", holder="remote-controller")
    rig.wake()
    assert rig.moves == [] and b.wake_looks == 0


def test_a_holder_taking_the_head_mid_pan_stops_the_pan() -> None:
    r = _slow_rig()
    try:
        r.behavior.render_turn_state("listening")
        r.behavior.robot.lease.acquire(priority="expression", holder="look-lease")
        r.join()
        assert r.pans() == []
    finally:
        r.behavior.close()


def test_at_most_one_look_every_fifteen_seconds(rig) -> None:
    rig.wake()
    first = len(rig.pans())
    rig.behavior.render_turn_state("settle")
    rig.wake()
    assert rig.behavior.wake_looks == 1 and len(rig.pans()) == first
    rig.behavior._last_wake_look -= wake_look.COOLDOWN_S + 1
    rig.behavior.render_turn_state("settle")
    rig.wake()
    assert rig.behavior.wake_looks == 2


def test_the_head_gate_cap_stops_the_pan(rig) -> None:
    rig.behavior.head_gate._max_moves = 2  # the listening allowance plus one pan move
    rig.wake()
    assert len(rig.pans()) == 1
    assert rig.behavior.head_gate.denied >= 1


def test_a_touch_ends_the_pan() -> None:
    r = _slow_rig()
    try:
        r.behavior.render_turn_state("listening")
        r.behavior.stop_wake_look("a touch")  # what wake_on_touch calls for a head touch
        r.join()
        assert r.pans() == [] and len(r.moves) == 1
    finally:
        r.behavior.close()


def test_a_head_touch_event_reaches_the_pan() -> None:
    r = _slow_rig()
    b = r.behavior
    try:
        b.render_turn_state("listening")
        touch = SimpleNamespace(kind="head_touch", extra={"strong": 1})
        b.event_poll = lambda: [touch, touch]
        b._event_queue_drained = True
        b.wake_on_touch(time.monotonic())
        r.join()
        assert r.pans() == []
    finally:
        b.close()


def test_the_stop_word_or_the_reply_ends_the_pan() -> None:
    for state in ("settle", "thinking"):
        r = _slow_rig()
        try:
            r.behavior.render_turn_state("listening")
            r.behavior.render_turn_state(state)
            r.join()
            assert r.pans() == [], state
        finally:
            r.behavior.close()


def test_the_pan_needs_no_camera_frame(rig) -> None:
    assert rig.behavior._vision is None
    rig.wake()
    assert len(rig.pans()) == 3


class _Probe:
    def __init__(self, replies):
        self.replies = replies
        self.calls: list[str] = []

    def call(self, device_id, name, arguments, timeout=5.0):
        self.calls.append(name)
        reply = self.replies[name]
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_the_unit_check_reads_lock_then_game_and_reuses_its_answer() -> None:
    now = [0.0]
    probe = _Probe({"self.lock.status": {"ok": True, "locked": False}, "self.game.list": {"ok": True, "playing": False}})
    check = wake_look.UnitCheck(lambda: probe, lambda: "unit-1", clock=lambda: now[0])
    assert check.reason() == "" and check.reason() == "" and len(probe.calls) == 2
    probe.replies["self.lock.status"] = {"ok": True, "locked": True}
    assert check.reason() == ""  # the earlier answer is reused for a few seconds
    now[0] = 10.0
    assert check.reason() == "locked"
    probe.replies["self.lock.status"] = {"ok": True, "locked": False}
    probe.replies["self.game.list"] = {"ok": True, "playing": True}
    now[0] = 20.0
    assert check.reason() == "playing a game"
    probe.replies["self.game.list"] = OSError("gone")
    now[0] = 30.0
    assert check.reason() == ""  # a unit that cannot answer does not block (it enforces its own lock)


def test_the_setting_round_trips_through_the_page(tmp_path) -> None:
    backend, _units = build(tmp_path)
    path = f"/api/stackchan/unit/{KITCHEN}/{{}}"

    def saved() -> bool:
        _status, _, body = backend.route_get(path.format("overview"), "en", True)
        return json.loads(body)["saved"]["look_on_wake"]

    assert saved() is True
    seen: list[tuple[str, dict]] = []
    backend.on_saved = lambda device_id, values: seen.append((device_id, values))
    status, payload = backend.route_post(path.format("device"), {"lang": "en", "look_on_wake": False}, True)
    assert status == 200 and payload["look_on_wake"] is False
    assert seen == [(KITCHEN, {"look_on_wake": False})]
    assert saved() is False
    status, _payload = backend.route_post(path.format("device"), {"lang": "en", "look_on_wake": True}, True)
    assert status == 200 and saved() is True


def test_the_page_words_exist_in_english_and_spanish_and_others_fall_back() -> None:
    en, es = i18n.catalog("en"), i18n.catalog("es")
    for key in ("settings.ui.wake_look", "settings.ui.wake_look_help"):
        assert en[key] and es[key] and en[key] != es[key]
        assert i18n.catalog("fr")[key] == en[key]
    assert en["settings.ui.wake_look"] == "Look around when I hear the wake word"


def test_look_toward_the_speaker_keeps_its_own_wake_turn(rig) -> None:
    rig.behavior.look_toward_speaker = True  # the older setting owns the wake turn exactly as before
    rig.wake()
    assert rig.pans() == [] and rig.behavior.wake_looks == 0
    assert rig.moves[0] == (0, CENTER_PITCH_DEG + 15, 0.5, 130)
