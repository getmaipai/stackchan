# ruff: noqa: E501
"""The scenes card on the settings page: the table it edits, the routes, the words in six languages, and the Test button."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from maipai_body import i18n, reply_tags, scenes, settings_ui
from maipai_body.command_bus import Gate
from maipai_body.settings_page import render_page
from maipai_body.settings_sim import KITCHEN, build

GET = "/api/stackchan/unit/{}/{}"


@pytest.fixture
def new(tmp_path: Path):
    return build(tmp_path, next_unit=True)


def get(backend, unit, what):
    status, _, body = backend.route_get(GET.format(unit, what), "en", True)
    return status, json.loads(body)


def post(backend, unit, what, body, lang="en"):
    return backend.route_post(GET.format(unit, what), {"lang": lang, **body}, True)


def test_the_page_gets_the_table_and_every_choice_from_the_host_so_it_cannot_drift(new):
    backend, _ = new
    status, view = get(backend, KITCHEN, "scenes")
    assert status == 200 and [s["name"] for s in view["scenes"]] == list(reply_tags.SCENE_NAMES)
    assert view["options"]["mood"] == ["", *reply_tags.MOODS] and view["options"]["fx"] == ["", *reply_tags.OVERLAYS]
    assert view["options"]["light"] == ["", *reply_tags.LIGHT_COLORS] and view["options"]["sound"] == ["", *reply_tags.MODEL_SOUNDS]
    assert view["defaults"]["rainy_day"] == scenes.DEFAULT_SCENES["rainy_day"] and view["hold"] == list(scenes.HOLD_RANGE)
    assert all(s["changed"] is False for s in view["scenes"])


def test_saving_a_scene_keeps_it_for_this_unit_and_reset_brings_the_shipped_one_back(new):
    backend, _ = new
    row = {"name": "cozy", "mood": "happy", "fx": "hearts", "level": "heavy", "light": "amber", "sound": "", "hold_s": 40}
    status, out = post(backend, KITCHEN, "scenes", row)
    assert status == 200 and out["ok"] is True
    assert backend.store.get(KITCHEN)["scenes"]["cozy"]["level"] == "heavy"
    assert next(s for s in get(backend, KITCHEN, "scenes")[1]["scenes"] if s["name"] == "cozy")["changed"] is True
    assert backend.polish.scenes.expand(KITCHEN, "cozy")[1][1]["intensity"] == "heavy"
    status, out = post(backend, KITCHEN, "scenes", {"name": "cozy", "reset": True})
    assert status == 200 and "cozy" not in backend.store.get(KITCHEN).get("scenes", {})


@pytest.mark.parametrize(
    ("body", "word"),
    [
        ({"name": "cozy", "photo": True}, "A scene can only set"),
        ({"name": "cozy", "mood": "joy"}, "mood cannot be"),
        ({"name": "cozy", "light": "red"}, "light cannot be"),
        ({"name": "cozy", "hold_s": 9999}, "hold time must be"),
        ({"name": "weather"}, "That scene is not known"),
    ],
)
def test_a_bad_scene_is_refused_with_what_to_do_and_nothing_is_saved(new, body, word):
    backend, _ = new
    status, out = post(backend, KITCHEN, "scenes", body)
    assert status == 400 and word in out["error"]
    assert "scenes" not in backend.store.get(KITCHEN)


def test_the_unit_store_itself_refuses_a_scene_that_could_carry_anything_else(new):
    from maipai_body.unit_settings import SettingsError

    backend, _ = new
    for bad in ({"cozy": {"mood": "happy", "head": "nod"}}, {"weather": {}}, ["cozy"]):
        with pytest.raises(SettingsError):
            backend.store.update(KITCHEN, {"scenes": bad})


def test_the_test_button_runs_the_saved_scene_as_the_owner_and_reports_what_it_could_not_do(new):
    backend, units = new
    status, out = post(backend, KITCHEN, "remote", {"do": "scene", "name": "rainy_day"})
    assert status == 200 and out["ok"] is True and out["mood"] == "neutral"
    assert "fx.set" in out["shown"] and "light.look" in out["skipped"]  # the ring has no scene row yet: said plainly, not hidden
    assert units[KITCHEN].overlay.get("name") == "rain"
    assert post(backend, KITCHEN, "remote", {"do": "scene", "name": "off"})[1]["ok"] is True and units[KITCHEN].overlay == {}
    status, out = post(backend, KITCHEN, "remote", {"do": "scene", "name": "tornado"})
    assert status == 400 and "not known" in out["error"]


def test_the_test_button_draws_the_scene_mood_and_the_ring_when_a_ring_is_wired(new):
    backend, _ = new
    polish = backend.polish
    seen: list = []
    polish.mood_sink = lambda device, mood: seen.append(("mood", mood))
    polish.ring = lambda device, color, seconds: seen.append(("ring", color, seconds)) or True
    out = post(backend, KITCHEN, "remote", {"do": "scene", "name": "sunny_day"})[1]
    assert ("mood", "happy") in seen and ("ring", "amber", 20) in seen and out["skipped"] == []


def test_a_hard_mute_holds_the_scene_s_sound_even_from_the_page(new):
    backend, _ = new
    backend.polish.gate_state = lambda _d: Gate(muted=True)
    out = post(backend, KITCHEN, "remote", {"do": "scene", "name": "birthday"})[1]
    assert "sound.play" in out["skipped"] and "fx.set" in out["shown"]


def test_every_new_word_exists_in_all_six_languages_and_the_script_asks_only_for_words_that_exist():
    from maipai_body.i18n_polish import CATALOGS

    asked = set(re.findall(r"T\('(pol\.scene\.[a-z0-9_.]+)'\)", settings_ui.JS))
    asked |= {f"pol.scene.n.{n}" for n in reply_tags.SCENE_NAMES} | {f"pol.scene.m.{m}" for m in reply_tags.MOODS}
    asked |= {f"pol.scene.l.{c}" for c in reply_tags.LIGHT_COLORS} | {f"pol.scene.s.{s}" for s in reply_tags.MODEL_SOUNDS}
    asked |= {f"pol.ov.{o}" for o in reply_tags.OVERLAYS} | {"pol.ov.light", "pol.ov.normal", "pol.ov.heavy", "pol.ov.level", "rem.done"}
    assert len(asked) > 40
    for code in i18n.SUPPORTED:
        for key in asked:
            assert f"settings.ui.{key}" in i18n.CATALOG[code], (code, key)
    for key, text in CATALOGS["es"].items():
        if ".scene." in key:
            assert text != CATALOGS["en"][key] or key.endswith(("s.popup", "l.magenta")), key
            assert chr(0x2014) not in text
    assert "settings.ui.pol.scene.title" in render_page("es").decode()


def test_the_look_page_shows_the_scenes_card():
    js = settings_ui.JS
    assert "sceneCard(id)" in js and "pol.cards[6]" in js
