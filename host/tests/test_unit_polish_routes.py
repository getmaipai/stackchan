# ruff: noqa: E501
"""The newer settings routes (preferences, overlays, packs, fillers) against the simulated units."""

from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path

import pytest

from maipai_body import i18n, packs, settings_ui
from maipai_body.settings_page import render_page
from maipai_body.settings_sim import DEN, KITCHEN, build

GET = "/api/stackchan/unit/{}/{}"


@pytest.fixture
def old(tmp_path: Path):  # a unit without the next update's tools
    return build(tmp_path)


@pytest.fixture
def new(tmp_path: Path):  # a unit with them
    return build(tmp_path, next_unit=True)


def get(backend, unit, what, lang="en"):
    status, _, body = backend.route_get(GET.format(unit, what), lang, True)
    return status, json.loads(body)


def post(backend, unit, what, body, lang="en"):
    return backend.route_post(GET.format(unit, what), {"lang": lang, **body}, True)


def pack_b64(kind="look", name="Pixel", size=800, **kw):
    return base64.b64encode(packs.encode(packs.make_pack(kind, name, os.urandom(size), **kw))).decode()


# ---- preferences ---------------------------------------------------------------------------------------


def test_prefs_start_at_their_defaults_and_say_the_unit_lacks_the_tool(old):
    backend, _ = old
    status, view = get(backend, KITCHEN, "prefs")
    assert status == 200 and view["unit_ready"] is False and view["reachable"] is True
    v = view["values"]
    assert (v["emotion_faces"], v["filler_mode"], v["filler_wait_s"], v["listen_sound"], v["listen_face"], v["speech_bubble"]) == (True, "tone", 0.4, "chime", True, False)
    assert view["features"] == {"overlay": False, "pack": False, "filler": False, "prefs": False}


def test_host_only_prefs_save_with_no_message_and_unit_prefs_say_they_wait(old):
    backend, units = old
    status, out = post(backend, KITCHEN, "prefs", {"emotion_faces": False, "filler_wait_s": 1.2})
    assert status == 200 and out["pushed"] is None and out["message"] == ""
    status, out = post(backend, KITCHEN, "prefs", {"listen_light": "dim"}, "es")
    assert status == 200 and out["pushed"] is False and out["pending"] is True and "próxima actualización" in out["message"]
    saved = get(backend, KITCHEN, "prefs")[1]["values"]
    assert saved["emotion_faces"] is False and saved["filler_wait_s"] == 1.2 and saved["listen_light"] == "dim"
    assert backend.store.get(KITCHEN)["emotion_faces"] is False
    assert not [c for c in units[KITCHEN].calls if c[0] == "self.prefs.set"]


def test_a_ready_unit_gets_only_its_own_keys_in_one_call_and_again_on_connect(new):
    backend, units = new
    status, out = post(backend, KITCHEN, "prefs", {"listen_sound": "mm", "fx_crt": True, "emotion_faces": False})
    assert status == 200 and out["pushed"] is True
    sent = dict(units[KITCHEN].prefs)
    assert sent["listen_sound"] == "mm" and sent["fx_crt"] is True
    assert "emotion_faces" not in sent and "filler_mode" not in sent  # host-only keys never go to the unit
    units[KITCHEN].prefs.clear()
    backend.polish.on_connect(KITCHEN)
    assert units[KITCHEN].prefs["listen_sound"] == "mm"


@pytest.mark.parametrize(
    ("body", "word"),
    [
        ({"filler_wait_s": 0.1}, "0.2 to 1.5"), ({"filler_wait_s": 9}, "0.2 to 1.5"), ({"filler_mode": "song"}, "none, tone, phrase"),
        ({"listen_light_colour": "blue"}, "#40c0ff"), ({"emotion_faces": "yes"}, "on or off"), ({"listen_sound": "bell"}, "off, chime, mm"),
    ],
)  # fmt: skip
def test_bad_prefs_are_refused_in_plain_words_and_change_nothing(old, body, word):
    backend, _ = old
    status, out = post(backend, KITCHEN, "prefs", body)
    assert status == 400 and word in out["error"]
    assert get(backend, KITCHEN, "prefs")[1]["values"]["filler_mode"] == "tone"


def test_the_notice_appears_when_all_three_listening_cues_are_off(old):
    backend, _ = old
    post(backend, KITCHEN, "prefs", {"listen_sound": "off", "listen_light": "off", "listen_face": False})
    assert "will not see or hear" in get(backend, KITCHEN, "prefs")[1]["notice"]
    post(backend, KITCHEN, "prefs", {"listen_face": True})
    assert get(backend, KITCHEN, "prefs")[1]["notice"] == ""


def test_the_listening_test_button_waits_on_old_units_and_plays_on_new_ones(old, new):
    assert post(old[0], KITCHEN, "listen-test", {})[1]["pending"] is True
    assert post(new[0], KITCHEN, "listen-test", {})[1]["ok"] is True
    assert post(old[0], DEN, "listen-test", {})[1]["ok"] is False  # offline unit


# ---- the remote overlay button -------------------------------------------------------------------------


def test_the_remote_overlay_button_draws_on_a_new_unit_and_waits_on_an_old_one(old, new):
    status, out = post(new[0], KITCHEN, "remote", {"do": "overlay", "name": "lluvia", "intensity": "heavy", "seconds": 5})
    assert status == 200 and out["ok"] is True and out["name"] == "rain"
    assert new[1][KITCHEN].overlay == {"name": "rain", "intensity": "heavy", "seconds": 5}
    assert post(new[0], KITCHEN, "remote", {"do": "overlay_clear"})[1]["ok"] is True and new[1][KITCHEN].overlay == {}
    status, out = post(old[0], KITCHEN, "remote", {"do": "overlay", "name": "rain"}, "es")
    assert status == 200 and out["pending"] is True and "próxima actualización" in out["message"]
    assert [c for c in old[1][KITCHEN].calls if c[0].startswith("self.overlay.")] == [("self.overlay.status", {})]


def test_the_remote_overlay_button_refuses_bad_input_plainly(new):
    status, out = post(new[0], KITCHEN, "remote", {"do": "overlay", "name": "tornado"})
    assert status == 400 and "not known" in out["error"]
    status, out = post(new[0], KITCHEN, "remote", {"do": "overlay", "name": "rain", "seconds": 5000})
    assert status == 400 and "1 to" in out["error"]
    status, out = post(new[0], DEN, "remote", {"do": "overlay", "name": "rain"})
    assert status == 400 and "not connected" in out["error"]


# ---- packs ---------------------------------------------------------------------------------------------


def test_the_library_routes_import_list_export_delete_and_gate_by_size(new):
    backend, _ = new
    status, out = backend.route_post("/api/stackchan/packs/import", {"b64": pack_b64("look", "Rubber Hose")}, True)
    assert status == 200 and out["pack"]["id"] == "look/rubber-hose"
    status, _, body = backend.route_get("/api/stackchan/packs", "en", True)
    assert [p["name"] for p in json.loads(body)["packs"]] == ["Rubber Hose"]
    status, out = backend.route_post("/api/stackchan/packs/export", {"pack_id": "look/rubber-hose"}, True)
    assert status == 200 and packs.decode(base64.b64decode(out["b64"])).name == "Rubber Hose"
    big = pack_b64("dance", "Huge", packs.MAX_BYTES["dance"] + 10)
    status, out = backend.route_post("/api/stackchan/packs/import", {"b64": big, "lang": "es"}, True)
    assert status == 400 and "máximo" in out["error"]
    status, out = backend.route_post("/api/stackchan/packs/import", {"b64": "###"}, True)
    assert status == 400 and "not a pack" in out["error"]
    assert backend.route_post("/api/stackchan/packs/delete", {"pack_id": "look/rubber-hose"}, True)[0] == 200
    assert json.loads(backend.route_get("/api/stackchan/packs", "en", True)[2])["packs"] == []


def test_a_look_pack_is_chosen_per_unit_and_only_it_reaches_that_unit(new):
    backend, units = new
    for name in ("Pixel", "Dots"):
        backend.route_post("/api/stackchan/packs/import", {"b64": pack_b64("look", name)}, True)
    status, out = post(backend, KITCHEN, "packs/activate", {"type": "look", "pack_id": "look/pixel"})
    assert status == 200 and out["pushed"] is True
    assert units[KITCHEN].pack_held["look"]["name"] == "Pixel"
    view = get(backend, KITCHEN, "packs")[1]
    assert view["active"] == {"look": "look/pixel"} and view["unit_ready"] is True
    assert units[DEN].calls == []  # the other unit was not touched
    assert post(backend, KITCHEN, "packs/activate", {"type": "look", "pack_id": ""})[1]["active"] == {}
    assert "look" not in units[KITCHEN].pack_held


def test_a_unit_without_pack_tools_is_flagged_and_keeps_the_choice(old):
    backend, units = old
    backend.route_post("/api/stackchan/packs/import", {"b64": pack_b64("language", "Deutsch", lang="de")}, True)
    status, out = post(backend, KITCHEN, "packs/activate", {"type": "language", "pack_id": "language/deutsch"})
    assert status == 200 and out["pending"] is True and out["pushed"] is False
    view = get(backend, KITCHEN, "packs")[1]
    assert view["unit_ready"] is False and view["active"] == {"language": "language/deutsch"}
    assert not [c for c in units[KITCHEN].calls if c[0] in {"self.pack.begin", "self.pack.data"}]


# ---- fillers -------------------------------------------------------------------------------------------


def test_the_filler_pack_is_made_in_the_background_and_listed(new):
    backend, _ = new
    status, out = post(backend, KITCHEN, "fillers/generate", {"voice": "sage", "lang": "en"})
    assert status == 200 and out["ok"] is True
    for _ in range(100):
        view = get(backend, KITCHEN, "fillers")[1]
        if not view["status"]["running"]:
            break
        time.sleep(0.1)
    assert view["status"]["error"] == "" and view["can_make"] is True
    assert [p["voice"] for p in view["packs"]] == ["sage"] and view["packs"][0]["size"] <= packs.MAX_BYTES["filler"]


def test_without_a_local_voice_engine_the_page_says_so(tmp_path):
    from maipai_body.settings_page import SettingsBackend

    backend = SettingsBackend(devices=lambda: {KITCHEN: {}}, language="en")
    backend.polish.library.root = tmp_path / "p"
    assert get(backend, KITCHEN, "fillers")[1]["can_make"] is False
    status, out = post(backend, KITCHEN, "fillers/generate", {})
    assert status == 400 and "local speech server" in out["error"]


# ---- the words -----------------------------------------------------------------------------------------


def test_every_new_word_exists_in_all_six_languages_and_none_has_a_dash_or_blank():
    from maipai_body.i18n_polish import CATALOGS

    keys = set(CATALOGS["en"])
    assert len(keys) > 100
    for code in i18n.SUPPORTED:
        assert set(CATALOGS[code]) == keys
        for key, text in CATALOGS[code].items():
            assert text.strip() and chr(0x2014) not in text, (code, key)
            assert i18n.CATALOG[code][key] == text
    es = CATALOGS["es"]
    assert es["settings.ui.pol.listen.title"] != CATALOGS["en"]["settings.ui.pol.listen.title"]


def test_the_script_asks_only_for_words_that_exist():
    js = settings_ui.JS
    asked = set(re.findall(r"T\('(pol\.[a-z0-9_.]+)'\)", js))
    asked |= {f"pol.ov.{n}" for n in ("rain", "snow", "sun", "clouds", "wind", "thunder", "fog", "stars", "disco", "confetti", "fireworks", "hearts", "steam", "balloons", "leaves", "zzz")}
    asked |= {f"pol.type.{t}{s}" for t in ("look", "sound", "dance", "game") for s in ("", "_help")}
    asked |= {f"pol.{k}.{o}" for k, opts in {"filler_mode": ("none", "tone", "phrase"), "listen_sound": ("off", "chime", "mm"), "listen_light": ("off", "dim", "normal"), "fx_colour_mode": ("normal", "mono", "warm", "cool")}.items() for o in opts}
    page = render_page("es").decode()
    assert asked and "settings.ui.pol.listen.title" in page
    for code in i18n.SUPPORTED:
        for key in asked:
            assert f"settings.ui.{key}" in i18n.CATALOG[code], (code, key)
    assert "BUILDERS.packs" in js and "g.packs" in js
