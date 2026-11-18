"""Own-model mode works with only a model address, and /v1 is never doubled."""

from types import SimpleNamespace

import numpy as np
import pytest

from maipai_body.bodies.stackchan.turn import StackChanTurnBridge
from maipai_body.brain.own_llm import _endpoint
from maipai_body.config import LlmConfig
from maipai_body.speech.local_speech import (
    LocalSttClient,
    builtin_stt_factory,
    builtin_tts_factory,
)


def _units(**llm):
    return SimpleNamespace(base=SimpleNamespace(brain="llm", llm=LlmConfig(**llm)))


def test_model_address_alone_selects_local_speech():
    chosen = StackChanTurnBridge._local_speech_from(_units(url="http://192.0.2.5:8080/v1"))
    assert chosen is not None
    stt_url, tts_url, _timeout, _llm = chosen
    assert stt_url is None and tts_url is None


def test_speech_addresses_are_passed_through():
    chosen = StackChanTurnBridge._local_speech_from(
        _units(url="http://192.0.2.5:8080", stt_url="http://192.0.2.5:8001")
    )
    assert chosen[0] == "http://192.0.2.5:8001" and chosen[1] is None


def test_no_model_address_or_home_brain_means_no_local_speech():
    assert StackChanTurnBridge._local_speech_from(_units(url="")) is None
    home = SimpleNamespace(base=SimpleNamespace(brain="home", llm=LlmConfig(url="http://x")))
    assert StackChanTurnBridge._local_speech_from(home) is None


def test_built_in_stt_client_uses_the_engine_when_no_address():
    class Engine:
        def transcribe(self, samples, rate):
            return " hello robot "

    client = LocalSttClient(None, engine=lambda: Engine())
    assert client._transcribe(np.zeros(1600, dtype=np.float32)) == "hello robot"


def test_missing_built_in_models_say_what_to_set():
    with pytest.raises(RuntimeError, match="stt_url"):
        builtin_stt_factory(LlmConfig(url="http://x"))()
    with pytest.raises(RuntimeError, match="tts_url"):
        builtin_tts_factory(LlmConfig(url="http://x"))()


@pytest.mark.parametrize(
    "base",
    [
        "http://192.0.2.5:8080",
        "http://192.0.2.5:8080/",
        "http://192.0.2.5:8080/v1",
        "http://192.0.2.5:8080/v1/",
        "http://192.0.2.5:8080/v1/chat/completions",
    ],
)
def test_chat_address_never_doubles_v1(base):
    assert _endpoint(base, "/v1/chat/completions") == "http://192.0.2.5:8080/v1/chat/completions"
