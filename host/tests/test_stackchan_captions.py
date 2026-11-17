"""Subtitle text from real replies: each spoken sentence reaches the unit as ``tts sentence_start`` with its exact words."""

from __future__ import annotations

import asyncio
import json
import threading
from types import SimpleNamespace

from maipai_body.bodies.stackchan import captions
from maipai_body.bodies.stackchan.turn import LEAD_FRAMES, StackChanAudioPlayback
from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer


class FakeUnitServer:
    """Records what the unit would get: (kind, caption) per send_audio call."""

    def __init__(self, loop):
        self._loop = loop
        self.calls = []

    async def send_audio(self, device_id, frames, *, sentence_start=False, start=True, stop=True, prebuffer=3, caption=None):
        self.calls.append((len(frames), sentence_start, caption))

    async def stop_audio(self, device_id):
        pass

    @property
    def captions(self):
        return [c for _n, _s, c in self.calls if c]


def _run(sentences, frames_per_sentence=LEAD_FRAMES + 4):
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    server = FakeUnitServer(loop)

    async def nap(_s):
        await asyncio.sleep(0)

    playback = StackChanAudioPlayback(server, "dev-1", clock=lambda: 0.0, sleeper=lambda _s: None, async_sleep=nap)
    try:
        for text in sentences:
            playback.caption(text)
            with playback._lock:
                playback._add_packets_locked([b"x"] * frames_per_sentence)
                playback._kick_locked()
            playback.end_sentence()
        playback.stop_playing()
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)
        loop.close()
    return server


def test_each_sentence_arrives_with_its_text_in_order():
    server = _run(["Hello there.", "How are you today?", "Fine, thanks."])
    assert server.captions == ["Hello there.", "How are you today?", "Fine, thanks."]


def test_tags_never_appear_in_subtitle_text():
    server = _run(["[happy] Great news <b>today</b>.", "{overlay:rain} It rains."])
    assert server.captions == ["Great news today.", "It rains."]
    assert not any(ch in c for c in server.captions for ch in "[]<>{}")


def test_spanish_and_accented_text_pass_through_the_wire():
    server = _run(["¿Cómo estás? Muy bien, gracias."])
    assert server.captions == ["¿Cómo estás? Muy bien, gracias."]
    sent = []

    class WS:
        async def send(self, data):
            sent.append(data)

    stub = SimpleNamespace(
        _sessions={"d": WS()},
        _session_ids={"d": "s"},
        _speaking=set(),
        _session_authorized=lambda _d: True,
        _json=lambda ws, sid, kind, payload, extra=None: ws.send(json.dumps({"session_id": sid, "type": kind, **payload})),
    )
    asyncio.run(XiaozhiServer.send_audio(stub, "d", [b"f"], sentence_start=True, start=False, stop=False, caption="Está lloviendo, mañana más."))
    message = json.loads(sent[0])
    assert message["type"] == "tts" and message["state"] == "sentence_start"
    assert message["text"] == "Está lloviendo, mañana más."


def test_a_sentence_without_text_sends_no_text_field():
    sent = []

    class WS:
        async def send(self, data):
            sent.append(data)

    stub = SimpleNamespace(
        _sessions={"d": WS()},
        _session_ids={"d": "s"},
        _speaking=set(),
        _session_authorized=lambda _d: True,
        _json=lambda ws, sid, kind, payload, extra=None: ws.send(json.dumps({"type": kind, **payload})),
    )
    asyncio.run(XiaozhiServer.send_audio(stub, "d", [b"f"], sentence_start=True, start=False, stop=False))
    assert "text" not in json.loads(sent[0])


def test_long_sentences_split_at_clause_boundaries_within_200_characters():
    clause = "the quick brown fox jumps over the lazy dog near the quiet river bank"
    long = ", ".join([clause] * 6) + "."
    parts = captions.pieces(long)
    assert len(parts) >= 2 and all(len(p) <= captions.MAX_CAPTION_CHARS for p in parts)
    assert all(p.endswith(",") or p.endswith(".") for p in parts)  # cut after a comma, never mid-word
    assert " ".join(parts) == long
    server = _run([long])
    assert server.captions == parts  # every piece reaches the unit, in order


def test_an_unbroken_run_is_hard_cut_and_empty_text_sends_nothing():
    assert [len(p) for p in captions.pieces("a" * 450)] == [200, 200, 50]
    assert captions.pieces("   ") == [] and captions.pieces("[happy]") == []
    assert _run([""]).captions == []
