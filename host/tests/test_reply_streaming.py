"""Streamed replies: the first sentence is spoken while the rest is still being written."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

import maipai_body.bodies.stackchan.turn as turn_module
from maipai_body.bodies.stackchan.turn import StackChanTurnBridge
from maipai_body.brain.interface import TurnRequest
from maipai_body.brain.own_llm import OwnLLMBrain
from maipai_body.config import LlmConfig
from maipai_body.speech.reply_stream import SentenceSplitter, TagStripper
from maipai_body.speech.stt_stream import SttStreamResult
from tests.test_stackchan_turn import (
    FakeCapture,
    FakePlayback,
    FakeServer,
    Link,
    Offline,
)


class FakeStt:
    def __init__(self, base, cookie):
        pass

    def run(self, capture):
        return SttStreamResult(kind="final", text="hello")


class Tts:
    """Records each sentence spoken and what time it started."""

    spoken: list[str] = []
    times: list[float] = []

    def __init__(self, base, cookie, playback):
        self.playback = playback

    def speak(self, text, *, stop_event=None):
        Tts.spoken.append(text)
        Tts.times.append(time.monotonic())
        hook = getattr(self.playback, "on_first_audio", None)
        if hook is not None:
            hook()


def run_bridge(monkeypatch, stream, *, filler_after_s=1.2, setup=None):
    """Run one turn whose brain yields ``stream(bridge)``; returns (bridge, calls)."""
    Tts.spoken, Tts.times = [], []
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = FakeServer()
    server._loop = loop
    monkeypatch.setattr(turn_module, "StackChanAudioPlayback", FakePlayback)
    holder: dict = {}
    canceled: list = []

    class Turn:
        def __init__(self, base, cookie):
            pass

        def stream(self, text, **kwargs):
            return stream(holder["bridge"])

        def cancel(self, turn_id):
            canceled.append(turn_id)
            return True

    bridge = StackChanTurnBridge(
        server, Link(), Offline(), stt_factory=FakeStt, turn_factory=Turn, tts_factory=Tts
    )
    bridge.filler_after_s = filler_after_s
    plain = []
    bridge._speak_plain_error = lambda playback, base, cookie: plain.append(True)
    bridge._offline_line = lambda playback: plain.append("offline")
    holder["bridge"] = bridge
    if setup:
        setup(bridge)
    loop.run_until_complete(bridge._run("session", "02:00:00:00:00:15", FakeCapture()))
    loop.close()
    return SimpleNamespace(bridge=bridge, plain=plain, canceled=canceled)


def deltas(*parts, final=None):
    for part in parts:
        yield SimpleNamespace(delta_text=part, turn_id="t1", reply_text=None)
    yield SimpleNamespace(
        reply_text=final if final is not None else "".join(parts), turn_id="t1", delta_text=None
    )


# --- the two text pieces -------------------------------------------------------------------


def test_splitter_cuts_sentences_as_they_complete_and_keeps_abbreviations():
    splitter = SentenceSplitter()
    assert splitter.feed("Hello th") == []
    assert splitter.feed("ere.") == []  # no space after the full stop yet: maybe "3.5"
    assert splitter.feed(" How are") == ["Hello there."]
    assert splitter.feed(" you? Dr. Smith is in. ok") == ["How are you?", "Dr. Smith is in."]
    assert splitter.flush() == ["ok"]


def test_stripper_removes_a_tag_split_across_chunks():
    seen: list[str] = []
    stripper = TagStripper(on_tag=seen.append)
    out = stripper.feed("Hi [mo") + stripper.feed("od: joy") + stripper.feed("] there.")
    assert out == "Hi  there."
    assert seen == ["mood: joy"]
    long_text = "Not a tag [1 and then a very long span of text that never closes at all ok"
    stripper = TagStripper()
    assert stripper.feed(long_text) == "Not a tag "  # a bracket run past 60 characters is dropped, never spoken (section 8.4)
    assert stripper.flush() == "" and stripper.dropped == 1


def test_stripper_drops_an_unfinished_tag_at_the_end_but_keeps_plain_brackets():
    stripper = TagStripper()
    assert stripper.feed("Fine [mood") == "Fine "
    assert stripper.flush() == ""
    other = TagStripper()
    other.feed("a [2")
    assert other.flush() == "[2"


# --- the bridge ----------------------------------------------------------------------------


def test_normal_stream_speaks_each_sentence_in_order(monkeypatch):
    run_bridge(monkeypatch, lambda b: deltas("Hello th", "ere. How are", " you? Fine."))
    assert Tts.spoken == ["Hello there.", "How are you?", "Fine."]


def test_first_sentence_is_spoken_before_the_reply_has_finished(monkeypatch):
    gate = threading.Event()
    state: dict = {}

    def stream(bridge):
        yield SimpleNamespace(delta_text="One. Two", turn_id="t1", reply_text=None)
        state["spoken_when_waiting"] = None
        deadline = time.monotonic() + 3
        while not Tts.spoken and time.monotonic() < deadline:
            time.sleep(0.01)
        state["spoken_when_waiting"] = list(Tts.spoken)
        gate.set()
        yield SimpleNamespace(delta_text=" is next.", turn_id="t1", reply_text=None)
        yield SimpleNamespace(reply_text="One. Two is next.", turn_id="t1", delta_text=None)

    run_bridge(monkeypatch, stream)
    assert state["spoken_when_waiting"] == ["One."]
    assert Tts.spoken == ["One.", "Two is next."]


def test_tags_split_across_chunks_are_never_spoken(monkeypatch):
    run_bridge(monkeypatch, lambda b: deltas("Nice [moo", "d:joy] day. [over", "lay:wave]Bye."))
    assert Tts.spoken == ["Nice day.", "Bye."]
    assert all("[" not in line and "]" not in line for line in Tts.spoken)


def test_a_stream_that_ends_without_punctuation_still_speaks_the_rest(monkeypatch):
    run_bridge(monkeypatch, lambda b: deltas("Sure. Here it", " is with no stop"))
    assert Tts.spoken == ["Sure.", "Here it is with no stop"]


def test_mid_stream_error_speaks_what_was_complete_then_the_plain_failure(monkeypatch):
    def stream(bridge):
        yield SimpleNamespace(delta_text="Done one. Half a sen", turn_id="t1", reply_text=None)
        raise RuntimeError("link dropped")

    result = run_bridge(monkeypatch, stream)
    assert Tts.spoken == ["Done one."]
    assert result.plain == [True]


def test_error_before_any_sentence_goes_to_the_usual_error_path(monkeypatch):
    def stream(bridge):
        raise RuntimeError("link dropped")
        yield  # pragma: no cover

    result = run_bridge(monkeypatch, stream)
    assert Tts.spoken == []
    assert result.plain == [True]


def test_cancel_stops_speaking_and_cancels_the_hub_turn(monkeypatch):
    def stream(bridge):
        yield SimpleNamespace(delta_text="First. ", turn_id="t9", reply_text=None)
        deadline = time.monotonic() + 3
        while not Tts.spoken and time.monotonic() < deadline:
            time.sleep(0.01)
        bridge._cancel_events["session"].set()
        yield SimpleNamespace(delta_text="Never spoken. ", turn_id="t9", reply_text=None)
        yield SimpleNamespace(reply_text="First. Never spoken.", turn_id="t9", delta_text=None)

    result = run_bridge(monkeypatch, stream)
    assert "Never spoken." not in Tts.spoken
    assert result.canceled == ["t9"]


def test_a_brain_that_does_not_stream_is_spoken_from_its_final_reply(monkeypatch):
    run_bridge(
        monkeypatch,
        lambda b: iter([SimpleNamespace(reply_text="All at once. [mood:joy]Two parts.")]),
    )
    assert Tts.spoken == ["All at once.", "Two parts."]


def test_slow_first_sentence_calls_the_thinking_cue_and_hook_once(monkeypatch):
    calls: list[str] = []

    def setup(bridge):
        bridge.on_slow_reply = lambda _v: calls.append("hook")
        bridge.expression_sink = lambda state, mood=None: calls.append(state)
        bridge._side = SimpleNamespace(
            submit=lambda fn, *a, **k: fn(*a, **k), shutdown=lambda **k: None
        )

    def stream(bridge):
        time.sleep(0.7)
        yield from deltas("Late. Reply.")

    run_bridge(monkeypatch, stream, filler_after_s=0.3, setup=setup)
    assert calls.count("hook") == 1
    assert Tts.spoken == ["Late.", "Reply."]


def test_a_fast_first_sentence_never_calls_the_hook(monkeypatch):
    calls: list[str] = []
    run_bridge(
        monkeypatch,
        lambda b: deltas("Quick. Reply."),
        setup=lambda b: setattr(b, "on_slow_reply", lambda _v: calls.append("hook")),
    )
    assert calls == []


def test_timings_are_logged_without_the_words(monkeypatch, caplog):
    caplog.set_level("INFO")
    run_bridge(monkeypatch, lambda b: deltas("Secret words here. More."))
    text = caplog.text
    assert "first sentence ready" in text and "first audio" in text and "first token" in text
    assert "Secret" not in text


# --- the model endpoint (fake streaming server) --------------------------------------------


class Endpoint(BaseHTTPRequestHandler):
    mode = "stream"

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        self.server.payload = json.loads(self.rfile.read(size))
        self.send_response(200)
        if self.mode == "plain":
            body = json.dumps(
                {"choices": [{"message": {"content": "Whole one. Whole two."}}]}
            ).encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_header("Content-Type", "text/event-stream")
        if self.mode == "break":
            self.send_header("Content-Length", "100000")  # promised, never delivered
        self.end_headers()
        chunks = ["First one. Sec", "ond one [mo", "od:joy]. Third"]
        for text in chunks:
            item = json.dumps({"choices": [{"delta": {"content": text}}]})
            self.wfile.write(f"data: {item}\n\n".encode())
            self.wfile.flush()
        if self.mode == "break":
            self.connection.close()
            return
        self.wfile.write(b"data: [DONE]\n\n")

    def log_message(self, *_a):
        pass


@pytest.fixture
def endpoint():
    made = []

    def start(mode):
        handler = type("H", (Endpoint,), {"mode": mode})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        made.append(server)
        return server, f"http://127.0.0.1:{server.server_port}"

    yield start
    for server in made:
        server.shutdown()


def spoken_through_bridge(monkeypatch, url):
    brain = OwnLLMBrain(LlmConfig(url=url, model="m", timeout_seconds=2))
    run_bridge(monkeypatch, lambda b: brain.stream_turn(TurnRequest("hi")))


def test_endpoint_stream_is_requested_and_spoken_in_order_with_tags_removed(
    monkeypatch, endpoint
):
    server, url = endpoint("stream")
    spoken_through_bridge(monkeypatch, url)
    assert server.payload["stream"] is True
    assert Tts.spoken == ["First one.", "Second one.", "Third"]


def test_endpoint_that_does_not_stream_falls_back_to_the_whole_reply(monkeypatch, endpoint):
    _server, url = endpoint("plain")
    spoken_through_bridge(monkeypatch, url)
    assert Tts.spoken == ["Whole one.", "Whole two."]


def test_endpoint_dropping_mid_stream_speaks_the_complete_part_then_fails_plainly(
    monkeypatch, endpoint
):
    _server, url = endpoint("break")
    spoken_through_bridge(monkeypatch, url)
    assert Tts.spoken[:2] == ["First one.", "Second one."]
    assert len(Tts.spoken) == 3 and "could not reach the model" in Tts.spoken[2]
    assert "Third" not in Tts.spoken
