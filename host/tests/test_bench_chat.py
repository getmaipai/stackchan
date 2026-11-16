import json
import threading
import urllib.error
import urllib.request

from maipai_body.bench import BenchServer
from maipai_body.brain.fake import FakeBrain


def _post(url, path, data):
    request = urllib.request.Request(
        url + path, json.dumps(data).encode(), {"Content-Type": "application/json"}
    )
    return urllib.request.urlopen(request, timeout=2)


def test_sim_chat_stream_order_persona_and_reset():
    brain = FakeBrain(reply="Hello there. Ready?")
    server = BenchServer(port=0, sim=True, brain=brain)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.address[1]}"
    try:
        response = _post(url, "/api/chat", {"text": "hi", "persona": "Speak softly."})
        events = [json.loads(line) for line in response.read().decode().splitlines()]
        assert [event["type"] for event in events] == [
            "first_token",
            "text",
            "first_sentence",
            "done",
        ]
        assert "Speak softly." in brain.turns[0].text
        assert "Speak softly." not in json.dumps(events[-1]["history"])
        reset = _post(url, "/api/chat/reset", {}).read()
        assert json.loads(reset)["history"] == []
    finally:
        server.httpd.shutdown()
        server.httpd.server_close()


def test_unreachable_brain_message_is_returned():
    class OfflineBrain:
        def stream_turn(self, request):
            raise RuntimeError("The model could not be reached. Check its URL and try again.")
            yield

    server = BenchServer(port=0, sim=True, brain=OfflineBrain())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.address[1]}"
    try:
        try:
            _post(url, "/api/chat", {"text": "hi"})
        except urllib.error.HTTPError as error:
            assert (
                json.loads(error.read())["error"]
                == "The model could not be reached. Check its URL and try again."
            )
        else:
            raise AssertionError("offline brain request succeeded")
    finally:
        server.httpd.shutdown()
        server.httpd.server_close()
