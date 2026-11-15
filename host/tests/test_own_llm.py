from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import pytest

from maipai_body.brain.interface import BrainFeature, TurnRequest
from maipai_body.brain.own_llm import OwnLLMBrain
from maipai_body.config import LlmConfig


class ModelHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.endswith("chat/completions"):
            size = int(self.headers.get("Content-Length", "0"))
            self.server.payload = json.loads(self.rfile.read(size))
            self.server.auth = self.headers.get("Authorization")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for text in ("First sentence. ", "Second sentence."):
                item = json.dumps({"choices": [{"delta": {"content": text}}]})
                self.wfile.write(f"data: {item}\n\n".encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
        else:
            self.send_error(404)

    def log_message(self, *_args):
        pass


class SlowModelHandler(ModelHandler):
    def do_POST(self):
        time.sleep(0.2)
        super().do_POST()


@pytest.fixture
def model_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


@pytest.fixture
def slow_model_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowModelHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


def test_streaming_sentence_chunks_history_and_persona(model_server):
    server, url = model_server
    spoken = []
    brain = OwnLLMBrain(
        LlmConfig(url=url, model="tiny", persona="Be brief", history_messages=2),
        on_sentence=spoken.append,
    )
    events = list(brain.stream_turn(TurnRequest("hello", conversation_id="c1")))
    assert spoken == ["First sentence.", "Second sentence."]
    assert events[-1].reply_text == "First sentence. Second sentence."
    assert server.payload["messages"][0] == {"role": "system", "content": "Be brief"}
    assert brain._history["c1"][-1]["content"] == "First sentence. Second sentence."
    list(brain.stream_turn(TurnRequest("again", conversation_id="c1")))
    assert len(brain._history["c1"]) == 2


def test_failure_is_spoken_plainly_and_does_not_raise():
    brain = OwnLLMBrain(LlmConfig(url="http://127.0.0.1:1", model="m", timeout_seconds=0.1))
    result = list(brain.stream_turn(TurnRequest("hello")))
    assert "could not reach the model at 127.0.0.1" in result[-1].reply_text
    assert "check robot.toml" in result[-1].reply_text


def test_timeout_is_spoken_and_does_not_escape(slow_model_server):
    brain = OwnLLMBrain(LlmConfig(url=slow_model_server, model="m", timeout_seconds=0.03))
    result = list(brain.stream_turn(TurnRequest("hello")))
    assert "could not reach the model" in result[-1].reply_text


def test_api_key_is_read_from_environment(monkeypatch, model_server):
    server, url = model_server
    monkeypatch.setenv("TEST_MODEL_KEY", "secret-value")
    brain = OwnLLMBrain(LlmConfig(url=url, model="m", api_key_env="TEST_MODEL_KEY"))
    list(brain.stream_turn(TurnRequest("hello")))
    assert server.payload["messages"][-1] == {"role": "user", "content": "hello"}
    assert server.auth == "Bearer secret-value"


def test_speech_urls_and_local_fallback_errors():
    brain = OwnLLMBrain(LlmConfig())
    assert brain.capabilities() == frozenset({BrainFeature.LLM, BrainFeature.TIMERS})
    with pytest.raises(RuntimeError, match="set llm.stt_url or install a speech model"):
        brain.transcribe_stream(np.zeros(160, dtype=np.float32))
    with pytest.raises(RuntimeError, match="set llm.tts_url or install a voice model"):
        brain.speak("hello")
    remote = OwnLLMBrain(LlmConfig(stt_url="http://127.0.0.1:1", tts_url="http://127.0.0.1:2"))
    assert BrainFeature.STT in remote.capabilities()
    assert BrainFeature.TTS in remote.capabilities()


def test_capabilities_hide_home_features_and_safety_is_prompt_owned():
    brain = OwnLLMBrain(LlmConfig(persona="No content filter is installed."))
    capabilities = brain.capabilities()
    assert BrainFeature.TIMERS in capabilities
    assert BrainFeature.PEOPLE not in capabilities
    assert BrainFeature.REMINDERS not in capabilities
    assert BrainFeature.VISION_DESCRIBE not in capabilities
    assert not hasattr(brain, "content_filter")
