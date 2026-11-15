from maipai_body.brain.home import HomeBrain
from maipai_body.brain.interface import TurnRequest


def test_home_turn_preserves_recorded_request_fields():
    class Response:
        status_code = 200
        text = ""

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def raise_for_status(self):
            return None

        def iter_lines(self, decode_unicode=True):
            return ['{"type":"done","reply":"ok","turn_id":"turn-1"}']

    class Session:
        calls = []

        def post(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return Response()

    from maipai_body.speech.turn_client import TurnClient

    session = Session()
    client = TurnClient("http://home", "cookie", session=session)
    brain = HomeBrain(turn_client=client)
    list(brain.stream_turn(TurnRequest("hello", {"person": "p1"}, [], "conv-1")))
    args, kwargs = session.calls[0]
    assert args[0] == "http://home/api/turn/stream"
    assert kwargs["json"] == {
        "surface": "robot", "text": "hello", "spoken": True,
        "speaker_evidence": {"person": "p1"}, "present": [], "conversation_id": "conv-1"
    }
    assert kwargs["headers"] == {"Cookie": "session=cookie"}
    assert kwargs["stream"] is True
    assert kwargs["timeout"] == (10, 120)
