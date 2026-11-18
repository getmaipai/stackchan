"""The Home Assistant package: spoken requests by trigger phrase, one listed camera picture, token from the environment only."""

import pytest

from maipai_packages.home_assistant import HomeAssistant, HomeAssistantError

JPEG = b"\xff\xd8\xff" + b"x" * 100


class Resp:
    def __init__(self, status=200, payload=None, content=b""):
        self.status_code, self._payload, self.content = status, payload, content

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError("bad")

    def json(self):
        return self._payload


class Session:
    def __init__(self, post=None, get=None):
        self.posts, self.gets, self._post, self._get = [], [], post, get

    def post(self, url, **kw):
        self.posts.append((url, kw))
        return self._post(url, kw)

    def get(self, url, **kw):
        self.gets.append((url, kw))
        return self._get(url, kw)


def _speech(text):
    return Resp(payload={"response": {"speech": {"plain": {"speech": text}}}})


@pytest.fixture(autouse=True)
def token(monkeypatch):
    monkeypatch.setenv("STACKCHAN_HA_TOKEN", "test-token-value")


def _ha(**kw):
    return HomeAssistant("http://192.0.2.20:8123", cameras={"front door": "camera.front_door"}, **kw)


def test_only_requests_with_the_trigger_phrase_go_to_home_assistant():
    session = Session(post=lambda u, k: _speech("Turned off the kitchen light."))
    ha = _ha(session=session)
    assert ha.handle("what is the capital of France") is None and not session.posts
    assert ha.handle("Home Assistant, turn off the kitchen light") == "Turned off the kitchen light."
    url, kw = session.posts[0]
    assert url == "http://192.0.2.20:8123/api/conversation/process"
    assert kw["json"]["text"] == "turn off the kitchen light"
    assert kw["headers"]["Authorization"] == "Bearer test-token-value"


def test_the_trigger_alone_asks_what_to_do():
    assert _ha(session=Session()).handle("home assistant") == "What should I ask Home Assistant?"


def test_a_missing_token_says_how_to_fix_it(monkeypatch):
    monkeypatch.delenv("STACKCHAN_HA_TOKEN")
    reply = _ha(session=Session(post=lambda u, k: _speech("x"))).handle("home assistant turn on the lamp")
    assert "STACKCHAN_HA_TOKEN" in reply


def test_an_unreachable_server_is_a_plain_message():
    import requests

    def boom(u, k):
        raise requests.ConnectionError("down")

    assert "could not reach Home Assistant" in _ha(session=Session(post=boom)).handle("home assistant lights off")


def test_a_listed_camera_picture_goes_to_the_model_once_and_stays_local():
    asked = []
    session = Session(get=lambda u, k: Resp(content=JPEG))
    ha = _ha(session=session, ask_model=lambda q, jpeg: asked.append((q, jpeg)) or "A package is on the step.")
    assert ha.handle("home assistant what do you see on the front door camera") == "A package is on the step."
    assert session.gets[0][0] == "http://192.0.2.20:8123/api/camera_proxy/camera.front_door"
    assert asked[0][1] == JPEG


def test_a_camera_that_is_not_listed_cannot_be_fetched():
    with pytest.raises(HomeAssistantError, match="not on the list"):
        _ha(session=Session()).snapshot("camera.bedroom")


def test_a_bad_picture_is_refused():
    ha = _ha(session=Session(get=lambda u, k: Resp(content=b"<html>")))
    with pytest.raises(HomeAssistantError, match="usable picture"):
        ha.snapshot("camera.front_door")


def test_the_address_must_be_http():
    with pytest.raises(HomeAssistantError, match="http://"):
        HomeAssistant("ftp://x")


def test_it_is_off_by_default_and_switches_on_from_robot_toml():
    from maipai_body.config import RobotConfig, build_brain

    assert RobotConfig().packages.home_assistant.enabled is False and build_brain(RobotConfig()).handlers == []
    cfg = RobotConfig.model_validate({"packages": {"home_assistant": {"enabled": True, "url": "http://192.0.2.20:8123"}}})
    assert len(build_brain(cfg).handlers) == 1
