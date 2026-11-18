# ruff: noqa: E501
"""The settings page's "Dance to music" toggle: why music features were off, and the wiring that turns them on.

Before this toggle nothing on the local settings page could set ``robot.dance.auto``; only a Home settings push did, and Home's page has
no such control yet. So the unit stayed at "music features off" (its boot default) and the controller ignored every ``music_feat``.
A simulated feature stream drives the whole chain here. Nothing in this file ran on a unit.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from maipai_body import i18n, settings_ui
from maipai_body.bodies.stackchan.dance import DanceSettings
from maipai_body.bodies.stackchan.music_dance_wiring import MusicFeatureSwitch, music_status_code
from maipai_body.settings_sim import KITCHEN, build
from maipai_body.unit_settings import SettingsError, UnitSettingsStore
from maipai_body.unit_settings import _clean as validate
from tests.test_stackchan_music_dance import (  # type: ignore[import-not-found]
    _music_event,
    _real_behavior,
    _Unit,
    _wire,
)

EM = chr(0x2014)  # written this way so the hygiene check never sees the character here
GET = "/api/stackchan/unit/{}/{}"


# ---------------------------------------------------------------- the setting itself


def test_the_setting_is_a_boolean_that_defaults_off() -> None:
    assert validate({"dance_to_music": True}) == {"dance_to_music": True}
    assert validate({"dance_to_music": False}) == {"dance_to_music": False}
    for bad in ("yes", 1, None, "true"):
        with pytest.raises(SettingsError):
            validate({"dance_to_music": bad})


def test_the_page_saves_it_tells_the_host_and_reads_it_back(tmp_path) -> None:
    backend, _units = build(tmp_path)
    told: list = []
    backend.on_saved = lambda device_id, values: told.append((device_id, values))
    saved = json.loads(backend.route_get(GET.format(KITCHEN, "overview"), "en", True)[2])["saved"]
    assert saved["dance_to_music"] is False and saved["dance_status"] == "off"
    status, payload = backend.route_post(GET.format(KITCHEN, "device"), {"lang": "en", "dance_to_music": True}, True)
    assert status == 200 and payload["ok"] is True and payload["dance_to_music"] is True
    assert told == [(KITCHEN, {"dance_to_music": True})]
    assert payload["status"] == "waiting"  # no host wiring in this fixture: on, not yet told to the unit
    saved = json.loads(backend.route_get(GET.format(KITCHEN, "overview"), "en", True)[2])["saved"]
    assert saved["dance_to_music"] is True
    status, payload = backend.route_post(GET.format(KITCHEN, "device"), {"lang": "en", "dance_to_music": "yes"}, True)
    assert status == 400 and "on or off" in payload["error"]
    assert backend.store.get(KITCHEN)["dance_to_music"] is True  # a bad value changed nothing


def test_the_page_script_and_words_exist_in_every_language() -> None:
    assert "musicCard" in settings_ui.JS and "dance_to_music" in settings_ui.JS
    keys = ["title", "toggle", "help", "privacy", *(f"status.{s}" for s in ("off", "waiting", "listening", "dancing", "paused", "unsupported"))]
    for code in i18n.SUPPORTED:
        for key in keys:
            text = i18n.CATALOG[code][f"settings.ui.pol.dance.{key}"]
            assert text.strip() and EM not in text, (code, key)
    assert i18n.CATALOG["es"]["settings.ui.pol.dance.toggle"] != i18n.CATALOG["en"]["settings.ui.pol.dance.toggle"]
    privacy = i18n.CATALOG["en"]["settings.ui.pol.dance.privacy"]
    assert privacy == "The unit measures sound levels and tempo only. No audio is kept or sent."


# ---------------------------------------------------------------- the status line


def _switch(unit, state):
    return MusicFeatureSwitch(unit, auto=lambda: state["auto"], silenced=lambda: state["silenced"], clock=lambda: 0.0)


def test_the_status_line_follows_the_switch_and_the_controller() -> None:
    unit, state = _Unit(), {"auto": False, "silenced": False}
    switch = _switch(unit, state)

    def code(saved, controller="idle"):
        return music_status_code(saved=saved, auto=state["auto"], switch=switch, state=controller)

    assert code(False) == "off"
    state["auto"] = True
    assert code(True) == "waiting"  # on, but the unit has not been told
    switch.sync()
    assert code(True) == "listening" and code(True, "watch") == "dancing"
    state["silenced"] = True
    assert code(True) == "paused"
    state["silenced"] = False
    state["auto"] = False
    assert code(False) == "off"


def test_a_unit_without_music_analysis_says_so() -> None:
    from maipai_body.hal.errors import NotSupported

    def old_unit(name, arguments):
        raise NotSupported(name)

    state = {"auto": True, "silenced": False}
    switch = MusicFeatureSwitch(old_unit, auto=lambda: state["auto"], silenced=lambda: False, clock=lambda: 0.0)
    switch.sync()
    assert switch.unsupported and music_status_code(saved=True, auto=True, switch=switch, state="idle") == "unsupported"


# ---------------------------------------------------------------- the host side: toggle to the unit's switch


def _page_and_behavior(tmp_path):
    """The settings page's saved hook as app.py wires it, with a real behavior and a recording unit."""
    from maipai_body.app import _wire_idle_setting

    behavior = _real_behavior()
    unit, state = _Unit(), {"silenced": False}
    switch = MusicFeatureSwitch(unit, auto=lambda: behavior.dance_settings.auto, silenced=lambda: state["silenced"], clock=lambda: 0.0)
    behavior.music_sync = switch.sync
    backend = SimpleNamespace()
    voice = SimpleNamespace(session_listeners=[])
    store = UnitSettingsStore(tmp_path / "units.json")
    units = SimpleNamespace(store=store)
    _wire_idle_setting(backend, units, behavior, voice)
    return behavior, backend, voice, store, unit, switch


def test_turning_the_toggle_on_and_off_flips_the_controller_switch_and_the_unit(tmp_path) -> None:
    behavior, backend, _voice, _store, unit, switch = _page_and_behavior(tmp_path)
    try:
        assert behavior.dance_settings.auto is False  # off by default
        backend.on_saved(KITCHEN, {"dance_to_music": True})
        assert behavior.dance_settings.auto is True
        assert unit.calls[-1] == ("self.music.set", {"enabled": True}) and switch.sent is True
        backend.on_saved(KITCHEN, {"dance_to_music": False})
        assert behavior.dance_settings.auto is False
        assert unit.calls[-1] == ("self.music.set", {"enabled": False})
        backend.on_saved(KITCHEN, {"look_faces": True})  # an unrelated save leaves it alone
        assert behavior.dance_settings.auto is False and len(unit.calls) == 2
    finally:
        behavior.close()


def test_a_saved_choice_is_applied_again_when_the_unit_connects(tmp_path) -> None:
    behavior, _backend, voice, store, unit, _switch_ = _page_and_behavior(tmp_path)
    try:
        store.update(KITCHEN, {"dance_to_music": True})
        for listener in voice.session_listeners:
            listener(KITCHEN)
        assert behavior.dance_settings.auto is True
        assert unit.calls[-1] == ("self.music.set", {"enabled": True})
    finally:
        behavior.close()


def test_the_default_for_a_unit_with_nothing_saved_is_off(tmp_path) -> None:
    behavior, _backend, voice, _store, unit, _switch_ = _page_and_behavior(tmp_path)
    try:
        for listener in voice.session_listeners:
            listener(KITCHEN)
        assert behavior.dance_settings.auto is False
        assert unit.calls == [("self.music.set", {"enabled": False})]  # the unit is told off, once, on connect
    finally:
        behavior.close()


# ---------------------------------------------------------------- a simulated music_feat stream


def _stream(behavior, w, seconds: int) -> None:
    for _ in range(seconds):
        w.clock["t"] += 1.0
        behavior.music_feat(_music_event().extra, w.clock["t"])
        w.controller.tick(w.clock["t"])


def test_with_the_toggle_off_a_music_stream_does_nothing() -> None:
    behavior = _real_behavior()
    try:
        w = _wire(behavior)
        w.controller._timing = __import__("tests.test_stackchan_music_dance", fromlist=["LEGACY_TIMING"]).LEGACY_TIMING
        assert behavior.dance_settings.auto is False
        _stream(behavior, w, 30)
        assert w.controller.state == "idle" and w.calls == [] and w.moves == []
    finally:
        behavior.close()


def test_with_the_toggle_on_the_same_stream_nods_then_dances_with_faces_and_the_voice_dance_still_works() -> None:
    from tests.test_stackchan_music_dance import LEGACY_TIMING  # type: ignore[import-not-found]

    behavior = _real_behavior()
    try:
        w = _wire(behavior)
        w.controller._timing = LEGACY_TIMING
        behavior.dance_settings.apply({"robot.dance.auto": True})  # what the page's toggle does
        _stream(behavior, w, 26)
        assert w.faces and w.faces[0] == "happy"  # the nod's face
        dances = [c for c in w.calls if c[0] == "dance"]
        assert dances[:2] == [("dance", "happy"), ("dance", "happy")]  # the firmware's happy sway, twice
        assert any(c[0] == "dance" and c[1] == "robot" for c in w.calls)  # then the stiff robot turns
        # the voice command is the same runner and is unaffected by the music setting
        w.runner.stop("test")
        w.clock["t"] += 120.0  # past the little dance's one-a-minute spacing
        reply = w.runner.request("voice")
        assert reply.started is True  # asked by voice with the toggle on: the same little dance
        behavior.dance_settings.apply({"robot.dance.auto": False})
        before = len(w.calls)
        _stream(behavior, w, 30)
        assert not [c for c in w.calls[before:] if c[0] == "dance" and c[1] == "robot"]  # off again: no new dance rounds
    finally:
        behavior.close()


def test_the_voice_dance_works_with_the_toggle_off() -> None:
    behavior = _real_behavior()
    try:
        w = _wire(behavior)
        assert behavior.dance_settings.auto is False
        reply = w.runner.request("voice")
        assert reply.started is True
        assert ("dance", "happy") in w.calls
    finally:
        behavior.close()


def test_dance_settings_stay_in_step_with_homes_key() -> None:
    settings = DanceSettings()
    settings.apply({"robot.dance.auto": True})
    assert settings.auto is True  # Home's push and the page share one switch


def test_a_clear_steady_beat_that_is_a_little_flat_still_counts_on_the_host() -> None:
    from dataclasses import replace

    from maipai_body.bodies.stackchan.music_dance import judge, judge_host
    from test_stackchan_music_dance import MUSIC

    real_song = replace(MUSIC, tc=53, fl=89, bpm=103, mo=6, ps=28)  # measured 2026-11-17: refused as too flat by the shared rule
    assert judge(real_song).why == "too_flat"
    assert judge_host(real_song).music is True
    assert judge_host(replace(real_song, tc=30)).why == "too_flat"  # a weak beat gets no allowance
    assert judge_host(replace(real_song, fl=96)).why == "too_flat"  # noise stays refused
    assert judge_host(replace(real_song, mo=70)).music is False  # extreme speech-like modulation still refuses it


def test_music_playing_keeps_the_robot_from_falling_asleep() -> None:
    from maipai_body.expression.rest import RestPolicy

    from test_stackchan_music_dance import MUSIC  # a feature window judged as music
    from maipai_body.bodies.stackchan.music_dance import judge_host

    assert judge_host(MUSIC).music is True
    policy = RestPolicy(0.0, drowsy_after_s=120.0, asleep_after_s=300.0)
    policy.update(0.0, person_present=False, turn_active=False)
    # no one around for 400 seconds: it falls asleep
    assert policy.update(400.0, person_present=False, turn_active=False).stage == "asleep"
    # music heard (the app passes turn_active while music was heard in the last 20 s): it wakes and stays awake
    assert policy.update(401.0, person_present=False, turn_active=True).stage == "awake"
    assert policy.update(402.0, person_present=False, turn_active=True).stage == "awake"


def test_a_song_with_vocals_and_a_steady_beat_counts_but_fast_speech_does_not() -> None:
    from dataclasses import replace

    from maipai_body.bodies.stackchan.music_dance import judge, judge_host
    from test_stackchan_music_dance import MUSIC

    song = replace(MUSIC, tc=51, fl=90, mo=50, ps=20)  # measured 2026-11-17: refused as speech by the shared rule
    assert judge(song).why in {"speech_like_modulation", "too_flat"}
    assert judge_host(song).music is True
    assert judge_host(replace(song, tc=20)).music is False  # no steady tempo: speech
    assert judge_host(replace(song, mo=70)).music is False  # extreme modulation: speech
