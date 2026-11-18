# ruff: noqa: E501
"""The host tells the unit when its face model finds a face (firmware patch NX05, self.banner.face_seen)."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from maipai_body.bodies.stackchan.face_seen import (
    FAILURE_RETRY_S,
    INTERVAL_S,
    OLD_IMAGE_RETRY_S,
    TOOL,
    FaceSeenSignal,
)
from maipai_body.bodies.stackchan.vision_bridge import StackChanVisionBridge
from maipai_body.hal.errors import BodyLost, NotSupported


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _signal(call, clock):
    """A signal whose "thread" is run by hand, so a test sees exactly when the call goes out."""
    pending = []
    signal = FaceSeenSignal(call, clock=clock, spawn=pending.append)
    return signal, pending


def test_the_report_is_the_banner_tool_with_three_seconds_and_runs_off_the_caller():
    calls = []
    clock = _Clock()
    signal, pending = _signal(lambda name, args: calls.append((name, args)), clock)
    assert signal.note() is True
    assert calls == [] and len(pending) == 1  # nothing went out on the caller's thread
    pending.pop()()
    assert calls == [(TOOL, {"seconds": 3})] and TOOL == "self.banner.face_seen" and signal.sent == 1


def test_at_most_one_report_a_second_and_never_two_at_once():
    calls = []
    clock = _Clock()
    signal, pending = _signal(lambda name, args: calls.append(args), clock)
    assert signal.note() is True
    assert signal.note() is False  # the first one is still on its way
    pending.pop()()
    clock.now += INTERVAL_S - 0.01
    assert signal.note() is False  # under a second since the last one
    clock.now += 0.02
    assert signal.note() is True
    pending.pop()()
    assert len(calls) == 2
    for _ in range(50):  # a face seen five times a second for ten seconds: ten reports
        clock.now += 0.2
        if signal.note():
            pending.pop()()
    assert len(calls) <= 2 + 10


def test_an_older_image_without_the_tool_is_asked_again_only_after_ten_minutes():
    def call(name, args):
        raise NotSupported("StackChan does not support self.banner.face_seen")

    clock = _Clock()
    signal, pending = _signal(call, clock)
    assert signal.note()
    pending.pop()()  # the answer: no such tool
    clock.now += 60
    assert signal.note() is False and not pending
    clock.now += OLD_IMAGE_RETRY_S
    assert signal.note() is True


def test_a_lost_link_never_reaches_the_look_path_and_waits_a_minute():
    def call(name, args):
        raise BodyLost("StackChan did not complete self.banner.face_seen")

    clock = _Clock()
    signal, pending = _signal(call, clock)
    assert signal.note()
    pending.pop()()
    clock.now += FAILURE_RETRY_S - 5
    assert signal.note() is False
    clock.now += 10
    assert signal.note() is True


def test_a_spawn_that_fails_leaves_the_signal_usable():
    def broken(_fn):
        raise RuntimeError("no thread")

    clock = _Clock()
    signal = FaceSeenSignal(lambda n, a: None, clock=clock, spawn=broken)
    assert signal.note() is False
    signal._spawn = lambda fn: fn()
    assert signal.note() is True and signal.sent == 1


def _bridge(faces):
    robot = SimpleNamespace(
        camera=SimpleNamespace(stream_frame=lambda deadline: b"jpeg", frame=lambda: b"jpeg"),
        head=SimpleNamespace(goto=lambda **kw: None, hold=lambda: None),
        lease_holder="",
        lease=SimpleNamespace(acquire=lambda **kw: None, release=lambda **kw: None),
    )
    return StackChanVisionBridge(
        robot,
        detector=SimpleNamespace(detect=lambda frame: faces),
        embedder=None,
        gallery=None,
        decode=lambda data: np.zeros((100, 100, 3), dtype=np.uint8),
    )


def test_the_vision_bridge_reports_a_face_and_nothing_when_there_is_none():
    reports = []
    bridge = _bridge([SimpleNamespace(bbox=(25, 25, 50, 50))])
    bridge.on_face_seen = lambda: reports.append(1)
    assert bridge.track_stream_frame(may_move=lambda: False).detected
    assert reports == [1]
    empty = _bridge([])
    empty.on_face_seen = lambda: reports.append(2)
    assert not empty.track_stream_frame().detected
    assert reports == [1]


def test_a_reporter_that_raises_is_dropped_and_the_look_goes_on():
    bridge = _bridge([SimpleNamespace(bbox=(25, 25, 50, 50))])

    def boom():
        raise RuntimeError("no")

    bridge.on_face_seen = boom
    assert bridge.track_stream_frame(may_move=lambda: False).detected
    assert bridge.on_face_seen is None
    assert bridge.track_stream_frame(may_move=lambda: False).detected


def test_the_bridge_without_a_reporter_is_unchanged():
    assert _bridge([SimpleNamespace(bbox=(25, 25, 50, 50))]).track_stream_frame(may_move=lambda: False).detected
