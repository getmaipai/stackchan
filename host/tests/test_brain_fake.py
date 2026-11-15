from maipai_body.brain.fake import FakeBrain
from maipai_body.brain.interface import TurnRequest


def test_fake_brain_is_deterministic():
    brain = FakeBrain(reply="Ready")
    assert [event.reply_text for event in brain.stream_turn(TurnRequest("hi"))] == ["Ready"]
    assert brain.turns == [TurnRequest("hi")]
