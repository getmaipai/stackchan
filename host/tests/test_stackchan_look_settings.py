"""Look toward the speaker / Look for faces default off; a refused head move never raises."""

from __future__ import annotations

import test_stackchan_ambient_rarity as rarity

from maipai_body.app import StackChanBehavior
from maipai_body.bodies.stackchan.adapter import StackChanRobotAdapter
from maipai_body.bodies.stackchan.fake import FakeStackChanDeviceClient
from maipai_body.hal.errors import NotPermitted
from maipai_body.hal.seam import HeadPose


def _fresh(vision):
    behavior = rarity._behavior(vision)
    behavior.look_toward_speaker = behavior.look_for_faces = False  # the shipped defaults
    return behavior


def test_the_shipped_defaults_are_off():
    behavior = StackChanBehavior(StackChanRobotAdapter(FakeStackChanDeviceClient()).robot)
    try:
        assert behavior.look_toward_speaker is False and behavior.look_for_faces is False
    finally:
        behavior.close()


def test_ten_minutes_of_movement_starts_no_search_while_off():
    vision = rarity._Vision()
    behavior = _fresh(vision)
    try:
        behavior._baseline.learn(rarity.ROOM, 0.0)
        starts = rarity._run(behavior, vision, 1000.0, 600.0, motion=lambda t: 0.5)
        assert starts == []
        behavior.look_for_faces = True
        assert rarity._run(behavior, vision, 1700.0, 900.0, motion=lambda t: 0.5)
    finally:
        behavior.close()


def test_a_head_move_without_a_lease_is_skipped_not_raised():
    behavior = _fresh(rarity._Vision())
    try:
        calls = []

        def refuse(**_kwargs):
            calls.append(1)
            raise NotPermitted("robot part 'head.set' needs a control lease")

        behavior.robot.head.set = refuse
        behavior._active.set()  # inside a turn whose own lease is already gone
        behavior._move_head_slowly(HeadPose(), 0.4)  # must not raise
        assert len(calls) >= 1
    finally:
        behavior.close()


def test_no_hub_url_skips_the_check_in_cleanly(monkeypatch, caplog):
    import threading
    from types import SimpleNamespace

    from maipai_body import app

    monkeypatch.setenv("MAIPAI_HUB_HOST", "1")
    monkeypatch.delenv("MAIPAI_HUB_URL", raising=False)
    assert app._no_hub_configured()
    before = threading.active_count()
    caplog.set_level("INFO")
    voice = SimpleNamespace(session_listeners=[])
    app._start_robot_checkin(voice, SimpleNamespace(), SimpleNamespace(), threading.Event())
    assert threading.active_count() == before
    assert "check-in is off" in caplog.text
    monkeypatch.setenv("MAIPAI_HUB_URL", "http://192.0.2.1:3000")
    assert not app._no_hub_configured()
