"""The old British keys still work on the host side (owner rule 2026-11-16; docs/design/spelling-aliases.md)."""

from __future__ import annotations

import json

from maipai_body import faces, spelling_aliases, unit_extras, unit_prefs
from maipai_body.speech.offline_clips import load_manifest
from maipai_body.unit_settings import UnitSettingsStore


def test_upgrade_renames_old_keys_and_the_new_key_wins():
    assert spelling_aliases.upgrade_keys({"colour": "mint", "style": "x"}) == {"color": "mint", "style": "x"}
    assert spelling_aliases.upgrade_keys({"colour": "old", "color": "new"}) == {"color": "new"}


def test_unit_keys_go_out_in_the_spelling_the_flashed_unit_knows():
    assert spelling_aliases.to_unit_keys({"color": "mint", "style": "x"}) == {"colour": "mint", "style": "x"}
    assert spelling_aliases.to_unit_keys({"listen_light_color": "#000000", "fx_color_mode": "mono"}) == {
        "listen_light_colour": "#000000",
        "fx_colour_mode": "mono",
    }
    assert spelling_aliases.from_unit_keys({"colour": "rose"}) == {"color": "rose"}


def test_a_face_config_saves_color_and_sends_colour():
    config = faces.clean(faces.FaceConfig(), {"colour": "Mint"})  # the old key is accepted
    assert config.color == "mint"
    assert "color" in config.to_json() and "colour" not in config.to_json()
    assert config.to_wire()["colour"] == "mint" and "color" not in config.to_wire()
    assert faces.clean(faces.FaceConfig(), {"color": "sky"}).color == "sky"


def test_an_old_saved_face_file_still_loads():
    assert faces.from_stored({"style": "classic", "colour": "amber"}).color == "amber"


def test_prefs_accept_and_translate_old_keys():
    out = unit_prefs.clean({"listen_light_colour": "#ABCDEF", "fx_colour_mode": "cool"}, ValueError)
    assert out == {"listen_light_color": "#abcdef", "fx_color_mode": "cool"}
    assert unit_prefs.prefs_of({"listen_light_colour": "#010203"})["listen_light_color"] == "#010203"


def test_an_old_unit_settings_file_reads_with_the_new_names(tmp_path):
    path = tmp_path / "units.json"
    path.write_text(json.dumps({"AA:BB:CC:DD:EE:FF": {"listen_light_colour": "#101010"}}))
    store = UnitSettingsStore(path)
    assert store.get("AA:BB:CC:DD:EE:FF") == {"listen_light_color": "#101010"}
    store.update("AA:BB:CC:DD:EE:FF", {"fx_color_mode": "warm"})
    saved = json.loads(path.read_text())["AA:BB:CC:DD:EE:FF"]
    assert saved == {"listen_light_color": "#101010", "fx_color_mode": "warm"}


def test_an_old_people_file_keeps_its_color():
    person = unit_extras.clean_person({"name": "Sage", "colour": "#40C0FF"})
    assert person.color == "#40c0ff" and "color" in person.to_json()


def test_an_old_offline_voice_manifest_still_loads(tmp_path):
    raw = {
        "voice": {"engine": "e", "name": "n", "licence": "CC-BY-4.0", "licence_checked": True},
        "sample_rate": 24000,
        "clips": [],
    }
    path = tmp_path / "m.json"
    path.write_text(json.dumps(raw))
    voice = load_manifest(path).voice
    assert voice.license == "CC-BY-4.0" and voice.license_checked is True
