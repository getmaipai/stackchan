# ruff: noqa: E501
"""The spoken word "lock" locks the robot that heard it with no model call; a spoken code or "unlock" is never accepted or forwarded."""

from __future__ import annotations

import asyncio
import logging

import pytest

from maipai_body.bodies.stackchan import lock_voice
from maipai_body.bodies.stackchan.lock_voice import LockVoice, parse_lock_command
from maipai_body.settings_sim import KITCHEN, build

CODE = "590173"


@pytest.mark.parametrize(
    "phrase",
    [
        "lock",
        "Lock.",
        "lock now",
        "Lock it",
        "lock the robot",
        "StackChan, lock",
        "please lock",
        "lock the screen",
        "lock yourself",
        "Lock up!",
    ],
)
def test_english_words_lock(phrase):
    command = parse_lock_command(phrase)
    assert command is not None and command.lang == "en", phrase


@pytest.mark.parametrize(
    "phrase",
    [
        "bloquear",
        "Bloquear.",
        "bloquea",
        "bloquéate",
        "bloquear ahora",
        "bloquea el robot",
        "por favor bloquear",
        "bloquear la pantalla",
    ],
)
def test_spanish_words_lock(phrase):
    command = parse_lock_command(phrase)
    assert command is not None and command.lang == "es", phrase


@pytest.mark.parametrize(
    "phrase",
    [
        "unlock 1234",
        "unlock",
        "unlock the robot",
        "unlock it 5 9 0 1 7 3",
        "lock 1234",
        "lock with 1234",
        "my code is 1234",
        "the code is one two three four",
        "one two three four",
        "set the code to 4827",
        "open sesame 123456",
        "desbloquear 1234",
        "desbloquear",
        "bloquear 1234",
        "mi código es 1234",
        "lock the door",
        "lock the front door and the back door",
        "can you lock",
        "what does lock mean",
        "block",
        "clock",
        "",
        "   ",
        None,
    ],
)
def test_a_spoken_code_unlock_or_other_sentence_is_never_a_lock_command(phrase):
    assert parse_lock_command(phrase) is None, phrase


def test_the_voice_control_locks_the_unit_that_heard_it(tmp_path):
    backend, units = build(tmp_path, next_unit=True)
    service = backend.polish.lock
    assert service.set_code(KITCHEN, CODE, CODE)["ok"] is True
    voice = LockVoice(lambda: service)
    command = voice.parse("lock")
    assert voice.run(command, KITCHEN) == "" and units[KITCHEN].locked is True
    assert [c for c in units[KITCHEN].calls if c[0] == "self.lock.now"] == [("self.lock.now", {})]


def test_without_a_code_the_robot_says_how_to_set_one_in_the_language_spoken(tmp_path):
    backend, units = build(tmp_path, next_unit=True)
    voice = LockVoice(lambda: backend.polish.lock)
    assert "settings page" in voice.run(voice.parse("lock"), KITCHEN)
    assert "página de ajustes" in voice.run(voice.parse("bloquear"), KITCHEN)
    assert units[KITCHEN].locked is False
    assert (
        LockVoice(lambda: None).run(voice.parse("lock"), KITCHEN)
        == lock_voice.LINES["offline"]["en"]
    )


def test_no_spoken_words_reach_the_unit_or_the_log(tmp_path, caplog):
    backend, units = build(tmp_path, next_unit=True)
    caplog.set_level(logging.DEBUG)
    backend.polish.lock.set_code(KITCHEN, CODE, CODE)
    voice = LockVoice(lambda: backend.polish.lock)
    for said in ("unlock 590173", "lock 590173", "5 9 0 1 7 3", "unlock"):
        assert voice.parse(said) is None
    voice.run(voice.parse("lock"), KITCHEN)
    assert units[KITCHEN].locked is True
    assert "590173" not in caplog.text
    # the only lock tools a voice path can cause are status and now: no set, clear or config
    assert {c[0] for c in units[KITCHEN].calls if c[0].startswith("self.lock.")} <= {
        "self.lock.status",
        "self.lock.set",
        "self.lock.now",
    }


def _bridge(monkeypatch, said, control):
    import maipai_body.bodies.stackchan.turn as turn_module
    from maipai_body.speech.stt_stream import SttStreamResult
    from tests.test_stackchan_turn import (  # type: ignore[import-not-found]
        FakeCapture,
        FakePlayback,
        FakeServer,
        FakeTts,
        FakeTurn,
        InlineExecutor,
        Link,
        Offline,
    )

    class Stt:
        def __init__(self, base, cookie):
            pass

        def run(self, capture, **kwargs):
            return SttStreamResult(kind="final", text=said)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = FakeServer()
    server._loop = loop
    FakeTurn.streams = []
    FakeTts.sentences = []
    monkeypatch.setattr(turn_module, "StackChanAudioPlayback", FakePlayback)
    bridge = turn_module.StackChanTurnBridge(
        server,
        Link(),
        Offline(),
        stt_factory=Stt,
        turn_factory=FakeTurn,
        tts_factory=FakeTts,
        side_executor=InlineExecutor(),
    )
    bridge.lock_control = control
    try:
        loop.run_until_complete(bridge._run("session", "device-7", FakeCapture()))
    finally:
        loop.close()
    return bridge, FakeTurn, FakeTts


class _Spy:
    def __init__(self):
        self.locked: list[str] = []

    def lock_now(self, device_id, lang=None):
        self.locked.append(device_id)
        return {"ok": True}


def test_the_bridge_locks_on_the_word_with_no_model_call(monkeypatch):
    spy = _Spy()
    bridge, turn, tts = _bridge(monkeypatch, "Lock.", LockVoice(lambda: spy))
    assert spy.locked == ["device-7"]
    assert (
        turn.streams == [] and tts.sentences == []
    )  # no model call, and a locked robot has nothing to say
    assert bridge._route_of("lock", "speech", "device-7")[0] == "local command"


@pytest.mark.parametrize(
    "said", ["unlock 1234", "lock 1234", "one two three four", "my code is 1234"]
)
def test_the_bridge_never_forwards_a_spoken_code(monkeypatch, said):
    spy = _Spy()
    bridge, turn, _ = _bridge(monkeypatch, said, LockVoice(lambda: spy))
    assert spy.locked == []
    assert bridge._route_of(said, "speech", "device-7")[0] == "chat"
