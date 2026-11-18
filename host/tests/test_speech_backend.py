"""The turn bridge gets its three clients from one backend (seam refactor P3)."""

from types import SimpleNamespace

from maipai_body.bodies.stackchan.speech_backend import HubBackend, LocalBackend
from maipai_body.bodies.stackchan.turn import StackChanTurnBridge


def test_the_hub_backend_builds_each_client_from_its_factory():
    seen = []
    backend = HubBackend(lambda b, c: seen.append(("stt", b, c)) or "S", lambda b, c: seen.append(("turn", b, c)) or "T", lambda b, c, p: seen.append(("tts", b, c, p)) or "V")
    assert (backend.stt("base", "ck"), backend.turn("base", "ck"), backend.tts("base", "ck", "pb")) == ("S", "T", "V")
    assert seen == [("stt", "base", "ck"), ("turn", "base", "ck"), ("tts", "base", "ck", "pb")] and backend.local is False


def test_the_local_backend_is_marked_local():
    assert LocalBackend(None, None, None).local is True


def test_a_bridge_without_a_model_uses_the_hub_backend_and_with_one_the_local_backend(tmp_path):
    from maipai_body.config import LlmConfig

    hub = StackChanTurnBridge.__new__(StackChanTurnBridge)
    hub.backend = HubBackend("s", "t", "v")
    assert hub.stt_factory == "s" and hub.turn_factory == "t" and hub.tts_factory == "v"
    hub.stt_factory = "replaced"  # the older names still work
    assert hub.backend.stt_factory == "replaced"
    units = SimpleNamespace(base=SimpleNamespace(brain="llm", llm=LlmConfig(url="http://192.0.2.5:8080")))
    assert StackChanTurnBridge._local_speech_from(units) is not None
