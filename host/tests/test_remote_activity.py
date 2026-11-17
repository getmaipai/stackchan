# ruff: noqa: E501
"""Remote cue: nobody acts on the robot without the robot showing it first."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from maipai_body import remote_activity as ra
from maipai_body.settings_sim import DEN, KITCHEN, build

PATH = "/api/stackchan/unit/{}/remote"
ACCESS = "/api/stackchan/remote-access"


def _act(backend, body, unit=KITCHEN):
    return backend.route_post(PATH.format(unit), {"lang": "en", **body}, True)


def _access(backend, rest, body=None, local=True):
    return backend.route_post(ACCESS + ("/" + rest if rest else ""), {"lang": "en", **(body or {})}, local)


def _names(unit) -> list[str]:
    return [name for name, _ in unit.calls]


@pytest.fixture
def cued(tmp_path: Path):
    backend, units = build(tmp_path, next_unit=True)
    return backend, units


@pytest.fixture
def plain(tmp_path: Path):
    backend, units = build(tmp_path)  # a unit that has no remote tools
    return backend, units


ALL = (
    {"do": "head", "yaw": 10, "pitch": 30}, {"do": "center"}, {"do": "nod"}, {"do": "shake"}, {"do": "look"},
    {"do": "find", "on": True}, {"do": "photo"}, {"do": "dance", "name": "groove"}, {"do": "game", "name": "memory"},
    {"do": "say", "text": "Hello"}, {"do": "beep"}, {"do": "flash"}, {"do": "mute", "on": True},
)  # fmt: skip


@pytest.mark.parametrize("body", ALL, ids=lambda b: b["do"])
def test_every_remote_action_is_preceded_by_its_cue(cued, body) -> None:
    backend, units = cued
    kitchen = units[KITCHEN]
    status, payload = _act(backend, body)
    assert status == 200, payload
    _act(backend, {"do": "find", "on": False})
    names = _names(kitchen)
    assert names.index("self.remote.session") < names.index("self.remote.action")
    first = names.index("self.remote.action")
    # the cue is the first thing the unit hears from this action besides the capability probe
    before = [n for n in names[:first] if n not in {"self.remote.session"}]
    assert before == [], before
    cue = next(a for n, a in kitchen.calls if n == "self.remote.action")
    assert cue["cue"] and cue["label"] == "Settings page" and cue["kind"]


def test_the_host_never_acts_when_the_unit_does_not_accept_the_cue(cued) -> None:
    backend, units = cued
    kitchen = units[KITCHEN]
    original = kitchen.handle
    kitchen.handle = lambda name, args: {"ok": False, "error": "busy"} if name == "self.remote.action" else original(name, args)
    for body in ({"do": "head", "yaw": 5, "pitch": 20}, {"do": "say", "text": "hi"}, {"do": "photo"}, {"do": "flash"}):
        status, payload = _act(backend, body)
        assert status == 400 and "did not accept the remote cue" in payload["error"], body
    acted = [n for n in _names(kitchen) if n.startswith(("self.robot.set_head", "self.audio.speak", "self.robot.set_led"))]
    assert acted == []


def test_say_is_limited_to_200_characters_and_3_a_minute(cued) -> None:
    backend, units = cued
    now = [1000.0]
    backend.activity._clock = lambda: now[0]
    assert _act(backend, {"do": "say", "text": "x" * 201})[0] == 400
    for n in range(3):
        assert _act(backend, {"do": "say", "text": f"hello {n}"})[0] == 200
    status, payload = _act(backend, {"do": "say", "text": "one more"})
    assert status == 400 and "4 remote messages in a minute" in payload["error"]
    says = [a for n, a in units[KITCHEN].calls if n == "self.remote.action" and a["kind"] == "say"]
    assert len(says) == 3  # the fourth never reached the unit
    now[0] += 61
    assert _act(backend, {"do": "say", "text": "later"})[0] == 200


def test_speaking_modes(cued) -> None:
    backend, units = cued
    assert backend.activity.store.settings() == {"enabled": False, "speaking": "ask", "allow_without_cue": False}
    units[KITCHEN].remote_allow = False  # nobody taps allow on the robot
    status, payload = _act(backend, {"do": "say", "text": "hi"})
    assert status == 400 and "did not allow" in payload["error"]
    assert not any(n == "self.audio.speak" for n in _names(units[KITCHEN]))
    cue = next(a for n, a in units[KITCHEN].calls if n == "self.remote.action")
    assert cue["confirm"] == "ask" and cue["text"] == "hi"
    units[KITCHEN].remote_allow = True
    assert _act(backend, {"do": "say", "text": "hi"})[0] == 200
    _access(backend, "", {"speaking": "off"})
    status, payload = _act(backend, {"do": "say", "text": "hi"})
    assert status == 400 and "Remote speaking is off" in payload["error"]
    assert _access(backend, "", {"speaking": "loud"})[0] == 400


def test_content_filter_hook_can_refuse_words(cued) -> None:
    backend, units = cued
    backend.activity.content_filter = lambda text: "that word is not allowed" if "bad" in text else None
    status, payload = _act(backend, {"do": "say", "text": "a bad word"})
    assert status == 400 and "that word is not allowed" in payload["error"]
    assert not any(n == "self.remote.action" for n in _names(units[KITCHEN]))
    assert _act(backend, {"do": "say", "text": "a kind word"})[0] == 200


def test_a_unit_without_the_cue_refuses_remote_say_and_photo(plain) -> None:
    backend, units = plain
    kitchen = units[KITCHEN]
    view = backend.route_get(PATH.format(KITCHEN), "en", True)
    body = json.loads(view[2])
    assert body["cue"] is False and "no remote cue yet" in body["cue_note"]
    for do in ({"do": "say", "text": "hi"}, {"do": "photo"}):
        status, payload = _act(backend, do)
        assert status == 400 and "shows no remote cue yet" in payload["error"], do
    assert not any(n in {"self.audio.speak", "self.camera.take_photo"} for n in _names(kitchen))
    # the owner's own page on this machine can still move, beep and flash (local control)
    assert _act(backend, {"do": "beep"})[0] == 200 and _act(backend, {"do": "flash"})[0] == 200
    # the setting that allows it
    _access(backend, "", {"allow_without_cue": True})
    assert _act(backend, {"do": "say", "text": "hi"})[0] == 200 and _act(backend, {"do": "photo"})[0] == 200
    rows = backend.activity.log.rows()
    assert [r["result"] for r in rows if r["action"] in {"say", "photo"}][:2] == ["done", "done"]
    assert sum(1 for r in rows if r["result"] == "refused") == 2


def test_a_controller_needs_access_on_pairing_and_a_cue(cued, plain) -> None:
    backend, units = cued
    act = {"do": "head", "yaw": 5, "pitch": 20, "unit": KITCHEN}
    assert _access(backend, "pair", {"label": "Phone"}, local=False)[0] == 400  # access is off
    assert _access(backend, "act", {"token": "nope", **act}, local=False)[0] == 400
    assert _access(backend, "", {"enabled": True})[1]["enabled"] is True
    assert _access(backend, "", {"enabled": True}, local=False)[0] == 403  # settings are local only
    pair = _access(backend, "pair", {"label": "Phone"}, local=False)[1]
    assert pair["status"] == "waiting" and pair["token"]
    status, payload = _access(backend, "act", {"token": pair["token"], **act}, local=False)
    assert status == 400 and "waiting to be allowed" in payload["error"]
    assert _access(backend, "allow", {"id": pair["id"]}, local=False)[0] == 403  # only this machine can allow
    assert _access(backend, "allow", {"id": pair["id"]})[0] == 200
    stored = json.loads((backend.activity.store._file.path).read_text())
    assert pair["token"] not in json.dumps(stored)  # only a hash is kept
    status, payload = _access(backend, "act", {"token": pair["token"], **act}, local=False)
    assert status == 200, payload
    cue = next(a for n, a in units[KITCHEN].calls if n == "self.remote.action")
    assert cue["label"] == "Phone" and cue["kind"] == "move"
    assert _access(backend, "revoke", {"id": pair["id"]})[0] == 200
    status, payload = _access(backend, "act", {"token": pair["token"], **act}, local=False)
    assert status == 400 and "not paired" in payload["error"]
    assert backend.activity.store.controllers() == []


def test_a_controller_is_refused_on_a_unit_without_the_cue(plain) -> None:
    backend, units = plain
    _access(backend, "", {"enabled": True})
    pair = _access(backend, "pair", {"label": "Phone"}, local=False)[1]
    _access(backend, "allow", {"id": pair["id"]})
    status, payload = _access(backend, "act", {"token": pair["token"], "unit": KITCHEN, "do": "beep"}, local=False)
    assert status == 400 and "no remote cue" in payload["error"]
    assert not any(n == "self.audio.play_sound" for n in _names(units[KITCHEN]))
    assert backend.activity.log.rows()[0]["controller"] == "Phone"


def test_the_log_keeps_time_who_what_and_words_and_is_never_cleared(cued, tmp_path: Path) -> None:
    backend, units = cued
    assert _act(backend, {"do": "say", "text": "Dinner is ready"})[0] == 200
    assert _act(backend, {"do": "flash"})[0] == 200
    rows = backend.activity.log.rows()
    assert [r["action"] for r in rows] == ["light", "say"]  # newest first
    say = rows[1]
    assert say["controller"] == "Settings page" and say["text"] == "Dinner is ready" and say["result"] == "done" and say["unit"] == KITCHEN
    assert say["time"][:4].isdigit() and "T" in say["time"]
    assert [r["action"] for r in backend.activity.log.rows(action="say")] == ["say"]
    assert backend.activity.log.rows(controller="nobody") == []
    # a new process reads the same file; nothing in the log class can delete or trim
    again = ra.RemoteLog(backend.activity.log.path)
    assert len(again.rows()) == 2
    assert not any(hasattr(again, name) for name in ("clear", "delete", "trim", "truncate", "remove"))
    state = json.loads(backend.route_get(ACCESS, "en", True)[2])
    assert len(state["activity"]) == 2 and state["limits"] == {"say_chars": 200, "say_per_minute": 3}
    assert backend.route_get(ACCESS, "en", False)[0] == 403
    raw = backend.activity.log.path.read_text().splitlines()
    assert len(raw) == 2 and all(json.loads(line) for line in raw)


def test_a_stop_button_needs_no_cue(cued) -> None:
    backend, units = cued
    assert _act(backend, {"do": "stop_dance"})[0] == 200
    assert _act(backend, {"do": "find", "on": False})[0] == 200
    assert not any(n == "self.remote.action" for n in _names(units[KITCHEN]))


def test_the_session_heartbeat_renews_and_ends(cued) -> None:
    backend, units = cued
    now = [0.0]
    activity = backend.activity
    activity._clock = lambda: now[0]
    activity._heartbeat = False
    assert _act(backend, {"do": "flash"})[0] == 200
    sessions = lambda: [a["active"] for n, a in units[KITCHEN].calls if n == "self.remote.session" and a["label"]]  # noqa: E731
    assert sessions() == [True]
    now[0] += ra.HEARTBEAT_S
    activity.tick()
    assert sessions() == [True, True]
    now[0] += ra.SESSION_IDLE_S + 1
    activity.tick()
    assert sessions() == [True, True, False]
    activity.tick()
    assert sessions() == [True, True, False]  # nothing left to renew
    assert _act(backend, {"do": "flash"})[0] == 200
    activity.close()
    assert sessions()[-1] is False


def test_the_page_script_and_words(cued) -> None:
    from maipai_body import i18n
    from maipai_body.settings_page import render_page

    for code in i18n.SUPPORTED:
        page = render_page(code).decode()
        assert "accessCards" in page and "remote-access" in page
        for key in ("ra.title", "ra.enabled", "ra.speaking", "ra.nocue", "ra.act", "ra.last10", "ra.revoke", "ra.cue_none"):
            assert i18n.CATALOG[code][f"settings.ui.{key}"].strip()
    assert i18n.CATALOG["en"]["settings.ui.ra.enabled"] == "Remote access enabled"
    assert i18n.CATALOG["en"]["settings.ui.ra.nocue"] == "Allow remote actions on units without a remote cue"
    assert chr(0x2014) not in json.dumps(i18n.CATALOG["en"], ensure_ascii=False) and DEN


def _paired(backend):
    _access(backend, "", {"enabled": True})
    pair = _access(backend, "pair", {"label": "Phone"}, local=False)[1]
    _access(backend, "allow", {"id": pair["id"]})
    return pair["token"]


def test_a_controllers_tool_calls_carry_source_remote_and_the_cue_token(cued) -> None:
    """Patch TC01: the unit ignores a remote-marked call without the token from self.remote.action."""
    backend, units = cued
    token = _paired(backend)
    kitchen = units[KITCHEN]
    for body, tool in (({"do": "head", "yaw": 5, "pitch": 20}, "self.robot.set_head_angles"), ({"do": "dance", "name": "groove"}, "self.robot.dance"), ({"do": "game", "name": "memory"}, "self.game.start")):
        kitchen.calls.clear()
        assert _access(backend, "act", {"token": token, "unit": KITCHEN, **body}, local=False)[0] == 200
        names = _names(kitchen)
        assert names.index("self.remote.action") < names.index(tool)
        call = next(a for n, a in kitchen.calls if n == tool)
        assert call["source"] == "remote" and call["token"] == 4242
    seconds = next(a for n, a in kitchen.calls if n == "self.remote.action")["seconds"]
    assert seconds == ra.CUE_SECONDS["game"]


def test_a_nod_uses_one_token_then_the_open_window(cued) -> None:
    backend, units = cued
    token = _paired(backend)
    kitchen = units[KITCHEN]
    assert _access(backend, "act", {"token": token, "unit": KITCHEN, "do": "nod"}, local=False)[0] == 200
    moves = [a for n, a in kitchen.calls if n == "self.robot.set_head_angles"]
    assert len(moves) > 1
    assert moves[0]["token"] == 4242 and all(m["source"] == "remote" for m in moves)
    assert all(m["token"] == 0 for m in moves[1:])  # a token is one use; later moves ride the window the unit opened


def test_the_local_page_and_a_unit_without_a_token_are_not_marked(cued) -> None:
    backend, units = cued
    kitchen = units[KITCHEN]
    assert _act(backend, {"do": "head", "yaw": 5, "pitch": 20})[0] == 200  # this machine's own page: local control
    call = next(a for n, a in kitchen.calls if n == "self.robot.set_head_angles")
    assert call["source"] == "user" and "token" not in call
    cue = ra.RemoteCue("move", None)  # an old unit answers no token
    assert cue.marker("self.robot.set_head_angles", {}) == {}
    assert ra.RemoteCue("move", 7).marker("self.robot.get_head_angles", {}) == {}  # reading is not an action
    assert ra.RemoteCue("move", 7).marker("self.audio.play_sound", {"find": 2}) == {}  # ending a find needs no cue


def test_a_find_loop_asks_for_a_fresh_cue_before_the_window_closes() -> None:
    now = [0.0]
    renewed: list[int] = []

    def renew() -> int:
        renewed.append(1)
        return 99

    cue = ra.RemoteCue("find", 7, renew, lambda: now[0])
    first = cue.marker("self.audio.play_sound", {"find": 1})
    assert first == {"source": "remote", "token": 7}
    assert cue.marker("self.robot.set_head_angles", {}) == {"source": "remote", "token": 0, "cue_kind": "find"}
    now[0] = ra.FIND_RENEW_S + 1
    assert cue.marker("self.audio.play_sound", {"find": 1})["token"] == 99 and renewed == [1]


def test_the_session_label_the_unit_shows_is_short_and_plain() -> None:
    """The unit draws "Remote connected: <label>" in one fixed row: the label is a short plain name and is cut at 20 letters."""
    sent: list[dict] = []

    class _Log:
        def add(self, **_kw):
            return None

    activity = ra.RemoteActivity.__new__(ra.RemoteActivity)
    activity._call = lambda tool, arguments, **_kw: sent.append({"tool": tool, **arguments})  # type: ignore[method-assign]
    activity._send_session("unit-1", True, "  A very long controller name that would not fit  ")
    activity._send_session("unit-1", True, "   ")
    activity._send_session("unit-1", True, ra.LOCAL_LABEL)
    assert sent[0]["label"] == "A very long controll"
    assert len(sent[0]["label"]) <= ra.SESSION_LABEL_MAX
    assert sent[1]["label"] == ra.LOCAL_LABEL  # an empty name becomes the plain default
    assert sent[2]["label"] == "Settings page"
    assert all(item["tool"] == ra.SESSION_TOOL and item["active"] is True for item in sent)
