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


def test_the_page_has_the_seven_groups_and_no_outside_address() -> None:
    page = render_page("en").decode()
    for group in ("home", "look", "voice", "network", "behaviour", "play", "system"):
        assert f"BUILDERS.{group}" in page
    assert "prefers-color-scheme" in page and "var(--accent)" in page
    assert not re.search(r"(src|href)=['\"]https?://", page)
    assert "fetch('http" not in page


def test_the_unit_list_carries_each_units_colour(sim) -> None:
    backend, _ = sim
    backend.faces.update(KITCHEN, {"colour": "mint"})
    colours = {u["device_id"]: u["colour"] for u in backend.state()["units"]}
    assert colours == {KITCHEN: "mint", DEN: "none"}


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
    assert saved == {"volume": 35, "brightness": 60, "idle_motion": False, "led": "#40c0ff"}


def test_bad_values_are_refused_in_plain_words_and_change_nothing(sim) -> None:
    backend, units = sim
    for body in ({"volume": 101}, {"brightness": 5}, {"led": "red"}, {"idle_motion": "yes"}, {"volume": 1, "led": "off"}, {"colour": 1}):
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
    assert units[KITCHEN].travel["has_key"] is True
    status, view = _get(backend, KITCHEN, "travel")
    assert view["available"] is True and view["has_key"] is True and key not in json.dumps(view)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert key not in path.read_text(errors="ignore"), path
    assert _post(backend, KITCHEN, "travel", {"key": "short key"})[0] == 400
    assert _post(backend, KITCHEN, "travel", {})[0] == 400
    assert _post(backend, KITCHEN, "travel", {"enabled": False})[0] == 200
    assert units[KITCHEN].travel["enabled"] is False
    assert _post(backend, KITCHEN, "travel", {"forget": True})[0] == 200
    assert units[KITCHEN].travel["has_key"] is False
    assert _get(backend, DEN, "travel")[1]["available"] is None  # offline: not asked successfully


def test_every_other_section_reads_and_writes_through_the_stand_in(sim) -> None:
    backend, units = sim
    status, payload = backend.route_post(
        f"/api/stackchan/faces/{KITCHEN}", {"style": "cat", "colour": "sky", "captions": True, "caption_size": "large"}, True
    )
    assert status == 200 and units[KITCHEN].face["style"] == "cat"
    assert _get(backend, KITCHEN, "reactions")[1]["builtin"] is True
    rows = [{"say": "good morning", "face": "happy", "sound": "none", "decor": "sparkles", "dance": "none"}]
    assert _post(backend, KITCHEN, "reactions", {"rows": rows})[0] == 200
    assert units[KITCHEN].table[0]["say"] == "good morning"
    assert _get(backend, KITCHEN, "reactions")[1]["rows"][0]["say"] == "good morning"
    assert _post(backend, KITCHEN, "clock", {"zone": "america_chicago"})[0] == 200
    assert _get(backend, KITCHEN, "clock")[1]["zone"] == "america_chicago"
    assert _post(backend, KITCHEN, "network-test", {})[1]["steps"]
    assert _get(backend, KITCHEN, "games")[1]["lines"][0].startswith("Colour Memory")
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
