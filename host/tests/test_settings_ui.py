# ruff: noqa: E501
"""The redesigned settings page: its words, its script, and every everyday control through the simulated units."""

from __future__ import annotations

import http.client
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from maipai_body import i18n, settings_ui
from maipai_body.settings_page import render_page
from maipai_body.settings_server import SettingsServer
from maipai_body.settings_sim import DEN, KITCHEN, build

EM = chr(0x2014)  # written this way so the hygiene check never sees the character here
GET = "/api/stackchan/unit/{}/{}"


@pytest.fixture
def sim(tmp_path: Path):
    return build(tmp_path)


def _get(backend, unit, what, lang="en"):
    status, _, body = backend.route_get(GET.format(unit, what), lang, True)
    return status, json.loads(body)


def _post(backend, unit, what, body, lang="en"):
    return backend.route_post(GET.format(unit, what), {"lang": lang, **body}, True)


def test_every_page_word_exists_in_all_six_languages() -> None:
    from maipai_body.i18n_design import CATALOGS

    keys = set(CATALOGS["en"])
    assert len(keys) > 150
    for code in i18n.SUPPORTED:
        assert set(CATALOGS[code]) == keys, code
        for key, text in CATALOGS[code].items():
            assert text.strip() and EM not in text, (code, key)
            assert i18n.CATALOG[code][key] == text
    assert CATALOGS["es"]["settings.ui.nav.face"] != CATALOGS["en"]["settings.ui.nav.face"]


@pytest.mark.parametrize("code", list(i18n.SUPPORTED))
def test_every_word_the_script_asks_for_exists(code: str) -> None:
    page = render_page(code).decode()
    asked = set(re.findall(r"\bT\('([a-z0-9_.]+)'\)", settings_ui.JS))
    asked |= set(re.findall(r"settings\.ui\.([a-z0-9_.]+)", settings_ui.JS))
    for key in asked:
        assert f"settings.ui.{key}" in i18n.CATALOG[code], key
    assert f"<html lang='{code}'>" in page and f"lang:'{code}'" in page


def test_the_script_parses_in_every_language() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    for code in i18n.SUPPORTED:
        page = render_page(code).decode()
        script = re.search(r"<script>([\s\S]*)</script>", page)
        assert script is not None
        result = subprocess.run(
            [node, "--check", "/dev/stdin"], input=script.group(1), capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr


def test_the_page_has_the_eight_groups_and_no_outside_address() -> None:
    page = render_page("en").decode()
    for group in ("home", "remote", "look", "voice", "network", "behavior", "play", "system"):
        assert f"BUILDERS.{group}" in page
    assert "prefers-color-scheme" in page and "var(--accent)" in page
    assert not re.search(r"(src|href)=['\"]https?://", page)
    assert "fetch('http" not in page


def test_the_unit_list_carries_each_units_color(sim) -> None:
    backend, _ = sim
    backend.faces.update(KITCHEN, {"color": "mint"})
    colors = {u["device_id"]: u["color"] for u in backend.state()["units"]}
    assert colors == {KITCHEN: "mint", DEN: "none"}


def test_volume_brightness_led_idle_motion_save_send_and_read_back(sim) -> None:
    backend, units = sim
    for what, value, tool in (
        ("volume", 35, "self.audio_speaker.set_volume"),
        ("brightness", 60, "self.screen.set_brightness"),
        ("idle_motion", False, "self.robot.set_idle_motion"),
        ("led", "#40c0ff", "self.robot.set_led_color"),
    ):
        status, payload = _post(backend, KITCHEN, "device", {what: value})
        assert status == 200 and payload["pushed"] is True, what
        assert tool in units[KITCHEN].device
    assert units[KITCHEN].device["self.audio_speaker.set_volume"] == {"volume": 35}
    assert units[KITCHEN].device["self.robot.set_led_color"] == {"red": 42, "green": 126, "blue": 168}
    saved = _get(backend, KITCHEN, "overview")[1]["saved"]
    assert saved == {"volume": 35, "brightness": 60, "idle_motion": False, "idle_movement": "off", "look_speaker": False, "look_faces": False, "led": "#40c0ff"}


def test_bad_values_are_refused_in_plain_words_and_change_nothing(sim) -> None:
    backend, units = sim
    for body in ({"volume": 101}, {"brightness": 5}, {"led": "red"}, {"idle_motion": "yes"}, {"volume": 1, "led": "off"}, {"color": 1}):
        status, payload = _post(backend, KITCHEN, "device", body)
        assert status == 400 and "try again" in payload["error"].lower() or "range" in payload["error"], body
    assert units[KITCHEN].device == {}
    assert _get(backend, KITCHEN, "overview")[1]["saved"]["volume"] == 70


def test_an_offline_unit_saves_the_choice_and_says_it_will_be_sent(sim) -> None:
    backend, _ = sim
    status, payload = _post(backend, DEN, "device", {"volume": 20})
    assert status == 200 and payload["pushed"] is False and "reconnects" in payload["message"]
    assert _get(backend, DEN, "overview")[1]["saved"]["volume"] == 20
    assert _get(backend, DEN, "overview")[1]["reachable"] is False


def test_mute_vision_and_quiet_go_through_the_privacy_tool(sim) -> None:
    backend, units = sim
    _post(backend, KITCHEN, "device", {"mute": True})
    _post(backend, KITCHEN, "device", {"vision_off": True})
    assert units[KITCHEN].privacy == {"muted": True, "vision_off": True, "quiet": False}
    view = _get(backend, KITCHEN, "overview")[1]
    assert view["privacy"] == {"mute": True, "vision_off": True, "quiet": False}
    assert view["battery"] == {"percent": 78, "charging": True} and view["light"] == 180
    assert backend.state()["units"][0]["muted"] is True


def test_reset_needs_the_typed_word_and_says_when_the_firmware_lacks_it(sim) -> None:
    backend, units = sim
    status, payload = _post(backend, KITCHEN, "reset", {"confirm_word": "reset"})
    assert status == 400 and "RESET" in payload["error"]
    assert not any(name == "self.system.reset" for name, _ in units[KITCHEN].calls)
    status, payload = _post(backend, KITCHEN, "reset", {"confirm_word": "RESET"})
    assert status == 400 and "no reset command yet" in payload["error"]


def test_travel_key_reaches_the_unit_and_is_never_stored_or_shown(sim, tmp_path: Path) -> None:
    backend, units = sim
    key = "tskey-auth-abcdefghijklmnop12345"
    status, payload = _post(backend, KITCHEN, "travel", {"key": key})
    assert status == 200 and key not in json.dumps(payload)
    assert units[KITCHEN].travel["key_saved"] is True
    status, view = _get(backend, KITCHEN, "travel")
    assert view["available"] is True and view["phase"] == "waiting" and key not in json.dumps(view)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert key not in path.read_text(errors="ignore"), path
    assert _post(backend, KITCHEN, "travel", {"key": "short key"})[0] == 400
    assert _post(backend, KITCHEN, "travel", {})[0] == 400
    assert _post(backend, KITCHEN, "travel", {"enabled": False})[0] == 200
    assert units[KITCHEN].travel["enabled"] is False
    assert _post(backend, KITCHEN, "travel", {"forget": True})[0] == 200
    assert units[KITCHEN].travel["key_saved"] is False
    assert _get(backend, DEN, "travel")[1]["available"] is None  # offline: not asked successfully


def test_tailscale_steps_status_and_plain_errors(sim) -> None:
    backend, units = sim
    assert _get(backend, KITCHEN, "travel")[1]["phase"] == "off"
    status, payload = _post(backend, KITCHEN, "travel", {"peer": "192.0.2.5"})
    assert status == 400 and "100.x.x.x" in payload["error"]
    assert _post(backend, KITCHEN, "travel", {"peer": "100.64.0.7"})[0] == 200
    key = "tskey-auth-zzzzzzzzzzzzzzzz1234"
    status, payload = _post(backend, KITCHEN, "travel", {"key": key})
    assert status == 200 and "Tailscale" in payload["message"] and key not in json.dumps(payload)
    view = _get(backend, KITCHEN, "travel")[1]
    assert view["phase"] == "connected" and view["route"] == "private" and view["ip"].startswith("100.")
    assert view["ready_to_use"] is True and "key" not in view
    units[KITCHEN].handle = lambda name, args: {"ok": False, "error": "bad_key"}  # the unit refuses the key
    status, payload = _post(backend, KITCHEN, "travel", {"key": key})
    assert status == 400 and "one-time key" in payload["error"] and key not in payload["error"]


def test_the_page_names_tailscale_and_has_about_and_remote() -> None:
    for code in i18n.SUPPORTED:
        words = i18n.CATALOG[code]
        assert "Tailscale" in words["settings.ui.units.travel"]
        assert "tskey-" in words["settings.ui.units.travel_key"]
        assert "100.x.x.x" in words["settings.ui.net.hub_addr"]
        for text in words.values():
            assert not re.search(r"\b(PSRAM|NVS|MCP|RAM)\b", text), text
    page = render_page("en").decode()
    assert "login.tailscale.com/admin/settings/keys" in page and "docs/user/use-it-anywhere.md" in page
    assert "github.com/getmaipai/stackchan" in page and "BUILDERS.remote" in page


def test_remote_buttons_act_on_the_unit(tmp_path: Path) -> None:
    backend, units = build(tmp_path, next_unit=True)  # a unit with the remote cue: say and photo are allowed on it
    kitchen = units[KITCHEN]
    view = _get(backend, KITCHEN, "remote")[1]
    assert view["reachable"] and view["photo"] and "groove" in [d["name"] for d in view["dances"]]
    assert view["limits"] == {"yaw": 128, "pitch": [5, 85]}
    for body, tool in (
        ({"do": "beep"}, "self.audio.play_sound"),
        ({"do": "say", "text": "Hello there"}, "self.audio.speak"),
        ({"do": "head", "yaw": 30, "pitch": 40}, "self.robot.set_head_angles"),
        ({"do": "nod"}, "self.robot.set_head_angles"),
        ({"do": "dance", "name": "groove"}, "self.robot.dance"),
        ({"do": "stop_dance"}, "self.robot.stop_dance"),
        ({"do": "game", "name": "memory"}, "self.game.start"),
    ):
        status, payload = _post(backend, KITCHEN, "remote", body)
        assert status == 200 and payload["ok"] is True, body
        assert tool in [name for name, _ in kitchen.actions], tool
    assert ("self.audio.speak", {"text": "Hello there"}) in kitchen.actions
    assert ("self.robot.set_head_angles", {"yaw": 30, "pitch": 40, "speed": 150, "source": "user"}) in kitchen.actions
    assert all(a["speed"] >= 100 for n, a in kitchen.actions if n == "self.robot.set_head_angles")  # the unit's minimum
    assert _post(backend, KITCHEN, "remote", {"do": "center"})[0] == 200
    before = len(kitchen.actions)
    assert _post(backend, KITCHEN, "remote", {"do": "flash"})[0] == 200
    assert _post(backend, KITCHEN, "remote", {"do": "look"})[0] == 200
    assert _post(backend, KITCHEN, "remote", {"do": "shake"})[0] == 200
    heads = [a for n, a in kitchen.actions[before:] if n == "self.robot.set_head_angles"]
    assert heads[-1]["yaw"] == 0 and heads[-1]["pitch"] == 5 and heads[-1]["source"] == "user"  # ends where it started
    assert all(a["speed"] >= 100 for a in heads)
    assert kitchen.device["self.robot.set_led_color"] == {"red": 0, "green": 0, "blue": 0}  # lights end off
    photo = _post(backend, KITCHEN, "remote", {"do": "photo"})[1]
    assert photo["image"].startswith("data:image/png;base64,")


def test_remote_refuses_bad_input_and_offline_units_in_plain_words(sim) -> None:
    backend, units = sim
    for body in ({"do": "head", "yaw": 200, "pitch": 40}, {"do": "head", "yaw": 0, "pitch": 3}, {"do": "head", "yaw": "a", "pitch": 9}, {"do": "say", "text": "   "}, {"do": "say", "text": "x" * 201}, {"do": "dance", "name": "moonwalk"}, {"do": "beep", "sound": "boom"}, {"do": "fly"}):
        status, payload = _post(backend, KITCHEN, "remote", body)
        assert status == 400 and payload["error"], body
    assert units[KITCHEN].actions == []
    for body in ({"do": "beep"}, {"do": "say", "text": "hi"}, {"do": "head", "yaw": 0, "pitch": 9}, {"do": "dance", "name": "happy"}):
        status, payload = _post(backend, DEN, "remote", body)
        assert status == 400 and "not connected" in payload["error"], body
    assert _get(backend, DEN, "remote")[1]["reachable"] is False


def test_find_my_robot_runs_until_stopped_and_leaves_the_unit_centered(sim) -> None:
    import time

    backend, units = sim
    kitchen = units[KITCHEN]
    assert _post(backend, KITCHEN, "remote", {"do": "find", "on": True})[1]["finding"] is True
    assert _get(backend, KITCHEN, "remote")[1]["finding"] is True
    time.sleep(0.1)
    assert _post(backend, KITCHEN, "remote", {"do": "find", "on": False})[1]["finding"] is False
    deadline = time.time() + 3
    while time.time() < deadline and _get(backend, KITCHEN, "remote")[1]["finding"]:
        time.sleep(0.05)
    assert _get(backend, KITCHEN, "remote")[1]["finding"] is False
    assert kitchen.device["self.robot.set_led_color"] == {"red": 0, "green": 0, "blue": 0}
    heads = [a for n, a in kitchen.actions if n == "self.robot.set_head_angles"]
    assert heads and heads[-1]["yaw"] == 0


def test_without_a_camera_the_photo_button_says_so(tmp_path: Path) -> None:
    from maipai_body.unit_remote import UnitRemote

    backend, _ = build(tmp_path)
    backend.activity.store.update({"allow_without_cue": True})  # the camera message, not the cue refusal, is under test
    backend._remote = UnitRemote(lambda *a, **k: {"ok": True})  # no photo source
    assert _get(backend, KITCHEN, "remote")[1]["photo"] is False
    status, payload = _post(backend, KITCHEN, "remote", {"do": "photo"})
    assert status == 400 and "camera build" in payload["error"]


def test_the_about_card_has_version_license_and_links(sim) -> None:
    backend, _ = sim
    assert "host_version" in backend.state()
    assert "GNU AGPL-3.0" in settings_ui.JS and "github.com/getmaipai/stackchan" in settings_ui.JS


def test_every_other_section_reads_and_writes_through_the_stand_in(sim) -> None:
    backend, units = sim
    status, payload = backend.route_post(
        f"/api/stackchan/faces/{KITCHEN}", {"style": "stock", "color": "sky", "captions": True, "caption_size": "large"}, True
    )
    assert status == 200 and units[KITCHEN].face["style"] == "stock"
    assert _get(backend, KITCHEN, "reactions")[1]["builtin"] is True
    rows = [{"say": "good morning", "face": "happy", "sound": "none", "decor": "sparkles", "dance": "none"}]
    assert _post(backend, KITCHEN, "reactions", {"rows": rows})[0] == 200
    assert units[KITCHEN].table[0]["say"] == "good morning"
    assert _get(backend, KITCHEN, "reactions")[1]["rows"][0]["say"] == "good morning"
    assert _post(backend, KITCHEN, "clock", {"zone": "america_chicago"})[0] == 200
    assert _get(backend, KITCHEN, "clock")[1]["zone"] == "america_chicago"
    assert _post(backend, KITCHEN, "network-test", {})[1]["steps"]
    assert _get(backend, KITCHEN, "games")[1]["lines"][0].startswith("Color Memory")
    backend.save(KITCHEN, {"speech_speed": 1.2, "speech_pitch": -2, "volume_cap": 40, "name": "Kitchen A"})
    unit = backend.state()["units"][0]
    assert (unit["speech_speed"], unit["speech_pitch"], unit["volume_cap"], unit["name"]) == (1.2, -2, 40, "Kitchen A")


def test_the_page_is_served_and_saves_over_http(sim) -> None:
    backend, _ = sim
    server = SettingsServer(backend, "127.0.0.1", 0)
    server.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
        conn.request("GET", "/settings?lang=es")
        reply = conn.getresponse()
        page = reply.read().decode()
        assert reply.status == 200 and "lang='es'" in page and "Voz y sonido" in page
        body = json.dumps({"volume": 44})
        conn.request("POST", GET.format(KITCHEN, "device"), body, {"Content-Type": "application/json"})
        reply = conn.getresponse()
        assert reply.status == 200 and json.loads(reply.read())["pushed"] is True
        conn.request("GET", GET.format(KITCHEN, "overview"))
        assert json.loads(conn.getresponse().read())["saved"]["volume"] == 44
    finally:
        server.stop()


def test_remote_reads_the_effect_back_and_never_says_done_for_nothing(sim) -> None:
    backend, units = sim
    kitchen = units[KITCHEN]
    kitchen.accept_head = False  # the unit answers ok but ignores the move
    for body in ({"do": "head", "yaw": 40, "pitch": 30}, {"do": "look"}, {"do": "nod"}, {"do": "shake"}):
        status, payload = _post(backend, KITCHEN, "remote", body)
        assert status == 400 and "head did not move" in payload["error"], body
    kitchen.accept_head = True
    assert _post(backend, KITCHEN, "remote", {"do": "head", "yaw": 40, "pitch": 30})[0] == 200
    assert kitchen.head == {"yaw": 40, "pitch": 30}


def test_remote_mute_reports_the_unit_state_and_beep_needs_real_sound(sim) -> None:
    backend, units = sim
    kitchen = units[KITCHEN]
    status, payload = _post(backend, KITCHEN, "remote", {"do": "mute", "on": True})
    assert status == 200 and payload["muted"] is True and kitchen.privacy["muted"] is True
    assert _get(backend, KITCHEN, "remote")[1]["muted"] is True
    status, payload = _post(backend, KITCHEN, "remote", {"do": "beep"})
    assert status == 400 and "muted" in payload["error"]
    # find is a user-asked locate: it sounds even while muted, and it never touches the microphone
    assert _post(backend, KITCHEN, "remote", {"do": "find", "on": True})[1]["finding"] is True
    _post(backend, KITCHEN, "remote", {"do": "find", "on": False})
    finds = [a for n, a in kitchen.actions if n == "self.audio.play_sound" and a.get("find") == 1]
    assert finds and kitchen.privacy["muted"] is True
    assert not any("mic" in n or "microphone" in n for n, _ in kitchen.calls)
    assert _post(backend, KITCHEN, "remote", {"do": "mute", "on": False})[1]["muted"] is False
    assert _post(backend, KITCHEN, "remote", {"do": "beep"})[0] == 200
    assert _post(backend, KITCHEN, "remote", {"do": "mute", "on": "x"})[0] == 400


def test_a_unit_that_rejects_a_tool_gives_a_plain_json_error_not_a_dropped_connection(tmp_path: Path) -> None:
    import threading
    import urllib.request

    from maipai_body.settings_server import SettingsServer

    backend, _ = build(tmp_path)

    def boom(*_a, **_k):
        raise RuntimeError("Unknown tool: self.robot.nod")

    backend._remote = None
    backend.route_post = boom  # type: ignore[method-assign]
    server = SettingsServer(backend, port=0)
    server.start()
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.port}/api/stackchan/unit/x/remote", data=b"{}", headers={"Content-Type": "application/json"}
        )
        try:
            urllib.request.urlopen(request, timeout=5)
            raise AssertionError("expected an error status")
        except urllib.error.HTTPError as error:
            assert error.code == 500 and b"nothing was changed" in error.read()
    finally:
        server.stop()
        threading.Event()
