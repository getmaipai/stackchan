"""A sentence that says the wake phrase is sent to the unit as no_barge with its length (patch SF29)."""

import asyncio
import json
import threading

import numpy as np

from maipai_body.bodies.stackchan import barge
from maipai_body.bodies.stackchan.turn import StackChanAudioPlayback
from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer
from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore


def test_the_phrase_check_ignores_case_and_punctuation():
    phrases = barge.wake_phrases()
    assert barge.says_wake_phrase("Say, \"Hey MaiPai!\" to wake me.", phrases)
    assert not barge.says_wake_phrase("Say hello to the room.", phrases)
    assert barge.MIN_MS <= barge.no_barge_ms("Hey maipai") <= barge.MAX_MS


def test_the_unit_gets_no_barge_and_the_length_on_that_sentence_only():
    sent = []

    class Socket:
        async def send(self, message):
            if isinstance(message, str):
                sent.append(json.loads(message))

    server = XiaozhiServer(PairingStore(), robot=None)
    server._sessions = {"unit-a": Socket()}
    server._session_ids = {"unit-a": "s"}
    server._session_authorized = lambda _d: True
    asyncio.run(server.send_audio("unit-a", [], sentence_start=True, start=False, stop=False, caption="Say hey maipai", no_barge_ms=3000))
    asyncio.run(server.send_audio("unit-a", [], sentence_start=True, start=False, stop=False, caption="Hello there"))
    first, second = [m for m in sent if m.get("state") == "sentence_start"]
    assert first["no_barge"] is True and first["duration_ms"] == 3000
    assert "no_barge" not in second


def test_the_playback_marks_only_the_sentence_with_the_phrase():
    playback = StackChanAudioPlayback(object(), "unit-a")
    playback.caption("Say hey maipai to wake me.")
    marked = dict(playback._no_barge)
    playback.caption("It is sunny today.")
    assert marked and set(marked) == set(playback._no_barge)
    assert all(playback._caption_args(piece).get("no_barge_ms") for piece in marked)
    assert "no_barge_ms" not in playback._caption_args("It is sunny today.")
