from maipai_body.brain.fake import FakeBrain
from maipai_body.brain.interface import Brain, BrainFeature, TurnRequest, VisionRequest
from maipai_body.brain.home import HomeBrain


def test_interface_contract_for_fake_and_home():
    class Turn:
        def stream(self, text, **kwargs):
            return iter(())

        def cancel(self, turn_id):
            return True

    class Client:
        def stream(self, *args, **kwargs):
            return None

        def speak(self, *args, **kwargs):
            return None

    class Poster:
        def post(self, *args, **kwargs):
            return {"ok": True}

    brains = [FakeBrain(), HomeBrain(turn_client=Turn(), stt_client=Client(),
                                     tts_client=Client(), vision_poster=Poster(),
                                     people_provider=list, settings_provider=dict,
                                     reminder_handler=lambda *_: [])]
    for brain in brains:
        assert isinstance(brain, Brain)
        assert brain.capabilities()
        list(brain.stream_turn(TurnRequest("hello")))
        brain.cancel_turn("turn-1")
        brain.transcribe_stream()
        brain.speak("hello")
        brain.describe(VisionRequest(b"jpeg", "scene"))
        brain.people()
        brain.settings()
        brain.reminders("get")


def test_missing_capability_hides_feature():
    brain = FakeBrain(features={BrainFeature.LLM})
    assert brain.capabilities() == {BrainFeature.LLM}
    assert BrainFeature.VISION_DESCRIBE not in brain.capabilities()
