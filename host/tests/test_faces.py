"""Face settings per unit: validation, saving and the push to the unit (patches F01 to F06)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from maipai_body.faces import (
    DEFAULT_HOURS,
    FaceConfig,
    FaceError,
    FaceService,
    FaceStore,
    apply_settings,
    band_for_hour,
    clean,
    from_stored,
    settings_view,
    valid_color,
)
from maipai_body.hal.errors import BodyLost

UNIT = "AA:BB:CC:00:00:01"
OTHER = "AA:BB:CC:00:00:02"


class FakeFirmware:
    """Stands in for the unit: same rules as self.face.set_config, and a switchable lost link."""

    def __init__(
        self,
        features: tuple[str, ...] = ("config", "captions", "tod", "clock", "thinking", "timers"),
    ) -> None:
        self.link = True
        self.features = list(features)
        self.state = FaceConfig().to_wire()
        self.calls: list[tuple[str, dict, str]] = []
        self.refuse: str | None = None
        self.has_tools = True

    def __call__(self, name: str, arguments: dict, *, device_id: str, timeout: float) -> object:
        self.calls.append((name, arguments, device_id))
        if not self.link:
            raise BodyLost("the unit is not connected")
        if not self.has_tools:
            return json.dumps({"ok": False, "error": "unknown tool"})
        if self.refuse:
            return {"ok": False, "error": self.refuse}
        if name == "self.face.set_config":
            self.state.update(json.loads(arguments["config"]))
            return json.dumps({"ok": True, **self.state, "features": self.features})
        if name == "self.face.get_config":
            return {"ok": True, **self.state, "features": self.features}
        return {"ok": True}

    def names(self) -> list[str]:
        return [c[0] for c in self.calls]


@pytest.fixture
def firmware() -> FakeFirmware:
    return FakeFirmware()


@pytest.fixture
def service(tmp_path: Path, firmware: FakeFirmware) -> FaceService:
    return FaceService(firmware, FaceStore(tmp_path / "faces.json"))


# ---- the defaults and the rules ----


def test_default_face_is_neutral_and_plain() -> None:
    config = FaceConfig()
    assert (config.style, config.color, config.captions, config.tod) == (
        "big_eyes",
        "none",
        False,
        False,
    )
    assert config.clock_idle_s == 0
    assert config.thinking_tone is True
    assert config.tod_hours == DEFAULT_HOURS


def test_clean_applies_a_partial_change_and_keeps_the_rest() -> None:
    config = clean(FaceConfig(), {"style": "big_eyes", "color": "MINT".lower()})
    assert config.style == "big_eyes" and config.color == "mint" and config.captions is False


@pytest.mark.parametrize(
    ("values", "words"),
    [
        ({"style": "huge"}, "big_eyes, stock or minimal"),
        ({"color": "purple"}, "not one I know"),
        ({"color": "#101010"}, "too dark"),
        ({"color": "#12"}, "not one I know"),
        ({"captions": "yes"}, "on or off"),
        ({"background": "#f0f0f0"}, "too bright for white eyes"),
        ({"background": "pink"}, "is not one I know"),
        ({"tod_hours": [9, 6, 18, 21]}, "must be four hours"),
        ({"tod_hours": [6, 9, 18, 24]}, "must be four hours"),
        ({"tod_hours": [6, 9, 18]}, "must be four hours"),
        ({"lang": "ja"}, "en, es, fr, de, pt or it"),
        ({"clock_style": "sundial"}, "digits or ring"),
        ({"clock_idle_s": 4000}, "0 (never) to 3600"),
        ({"clock_idle_s": -1}, "0 (never) to 3600"),
        ({"clock_idle_s": True}, "0 (never) to 3600"),
        ({"sparkles": True}, "not a face setting"),
    ],
)
def test_bad_values_say_what_went_wrong_and_what_to_do(values: dict, words: str) -> None:
    with pytest.raises(FaceError) as caught:
        clean(FaceConfig(), values)
    assert words in str(caught.value)


def test_nothing_changes_unless_every_field_is_valid() -> None:
    base = FaceConfig()
    with pytest.raises(FaceError):
        clean(base, {"style": "minimal", "color": "#000000"})
    assert base == FaceConfig()


def test_error_messages_follow_the_page_language() -> None:
    with pytest.raises(FaceError) as caught:
        clean(FaceConfig(), {"color": "#101010"}, lang="es")
    assert "demasiado oscuro" in str(caught.value)
    assert chr(8212) not in str(caught.value)


def test_dark_color_rule_matches_the_firmware() -> None:
    assert valid_color("#ff8800") is None
    assert valid_color("#FF8800") is None
    assert valid_color("#101010") == "dark"
    assert valid_color("ff8800") == "color"
    # the same threshold the unit uses: luma 60 of 255 is the lowest allowed
    assert valid_color("#3c3c3c") is None
    assert valid_color("#3b3b3b") == "dark"


def test_time_of_day_bands_match_the_firmware() -> None:
    config = clean(FaceConfig(), {"tod": True})
    assert band_for_hour(config, 6) == "morning"
    assert band_for_hour(config, 9) == "day"
    assert band_for_hour(config, 18) == "evening"
    assert band_for_hour(config, 21) == "night"
    assert band_for_hour(config, 0) == "night"
    assert band_for_hour(config, 5, 59) == "night"
    assert band_for_hour(FaceConfig(), 23) == "day"  # off: always the day look


# ---- saving, per unit ----


def test_settings_are_kept_per_unit_and_survive_a_restart(tmp_path: Path) -> None:
    path = tmp_path / "faces.json"
    store = FaceStore(path)
    store.set(UNIT, clean(FaceConfig(), {"color": "amber", "captions": True}))
    store.set(OTHER, clean(FaceConfig(), {"style": "minimal"}))
    again = FaceStore(path)
    assert again.get(UNIT).color == "amber" and again.get(UNIT).captions is True
    assert again.get(OTHER).style == "minimal" and again.get(OTHER).color == "none"
    assert again.get("never-seen") == FaceConfig()
    assert again.known() == [UNIT, OTHER]


def test_a_damaged_file_gives_the_plain_face_and_a_plain_line(tmp_path: Path) -> None:
    path = tmp_path / "faces.json"
    path.write_text("{ not json")
    store = FaceStore(path)
    assert store.get(UNIT) == FaceConfig()
    assert (
        store.problem is not None
        and str(path) in store.problem
        and "Fix or remove" in store.problem
    )


def test_stored_values_that_are_no_longer_valid_fall_back_to_plain() -> None:
    assert from_stored({"style": "gone", "color": "mint"}) == FaceConfig()
    assert from_stored("nonsense") == FaceConfig()
    assert from_stored({"color": "mint", "unknown_future_key": 1}).color == "mint"


# ---- sending to the unit ----


def test_update_saves_then_sends_one_json_object_through_the_tool(service, firmware) -> None:
    result = service.update(UNIT, {"color": "sky", "style": "big_eyes"})
    assert result["pushed"] is True and result["config"]["color"] == "sky"
    name, arguments, device = firmware.calls[0]
    assert (name, device) == ("self.face.set_config", UNIT)
    sent = json.loads(arguments["config"])
    assert sent["colour"] == "sky" and sent["style"] == "big_eyes" and sent["captions"] is False
    assert sent["tod_hours"] == [6, 9, 18, 21]
    assert service.config(UNIT).color == "sky"


def test_a_bad_value_is_refused_before_anything_is_sent_or_saved(service, firmware) -> None:
    with pytest.raises(FaceError):
        service.update(UNIT, {"color": "#050505"})
    assert firmware.calls == []
    assert service.config(UNIT).color == "none"


def test_a_unit_that_is_not_connected_keeps_the_setting_and_gets_it_later(
    service, firmware
) -> None:
    firmware.link = False
    result = service.update(UNIT, {"captions": True})
    assert result["pushed"] is False and "reconnects" in result["message"]
    assert service.pending(UNIT)
    firmware.link = True
    firmware.state = FaceConfig().to_wire()  # the unit still has the plain face
    out = service.sync(UNIT)
    assert out["pushed"] is True and firmware.state["captions"] is True
    assert not service.pending(UNIT)


def test_sync_leaves_a_unit_alone_when_it_already_matches(service, firmware) -> None:
    service.update(UNIT, {"color": "rose"})
    firmware.calls.clear()
    out = service.sync(UNIT)
    assert out["pushed"] is False
    assert firmware.names() == ["self.face.get_config"]


def test_sync_restores_a_unit_that_was_reset(service, firmware) -> None:
    service.update(UNIT, {"color": "rose", "tod": True})
    firmware.state = FaceConfig().to_wire()  # reset on the unit
    service.sync(UNIT)
    assert firmware.state["colour"] == "rose" and firmware.state["tod"] is True


def test_the_unit_refusing_a_setting_is_told_in_plain_words(service, firmware) -> None:
    firmware.refuse = "color: color too dark to see on the black screen: pick a lighter color"
    with pytest.raises(FaceError) as caught:
        service.update(UNIT, {"color": "mint"})
    assert "refused" in str(caught.value) and "pick a lighter color" in str(caught.value)


def test_old_firmware_without_face_tools_is_named_and_not_an_error(service, firmware) -> None:
    firmware.has_tools = False
    assert service.sync(UNIT)["pushed"] is False
    assert service.features(UNIT) == set()
    with pytest.raises(FaceError) as caught:
        service.show_clock(UNIT, 10)
    assert "does not have a clock face" in str(
        caught.value
    ) and "Update the unit's firmware" in str(caught.value)


def test_features_the_firmware_lacks_are_listed_for_the_page(tmp_path: Path) -> None:
    firmware = FakeFirmware(features=("config", "timers"))
    service = FaceService(firmware, FaceStore(tmp_path / "faces.json"))
    result = service.update(UNIT, {"captions": True, "tod": True, "color": "mint"})
    assert len(result["unsupported"]) == 2
    assert any("captions" in line for line in result["unsupported"])
    view = settings_view(service, UNIT)
    assert view["features"] == ["config", "timers"]
    assert "a clock face" in view["unavailable"] and "captions" in view["unavailable"]
    spanish = settings_view(service, UNIT, "es")
    assert "cara de reloj" in spanish["unavailable"]


def test_reset_returns_the_plain_face(service, firmware) -> None:
    service.update(UNIT, {"color": "lime", "captions": True})
    result = service.reset(UNIT)
    assert result["config"] == FaceConfig().to_json()
    assert firmware.state["colour"] == "none" and firmware.state["captions"] is False


def test_units_do_not_share_settings(service, firmware) -> None:
    service.update(UNIT, {"color": "lime"})
    service.update(OTHER, {"color": "coral"})
    assert service.config(UNIT).color == "lime" and service.config(OTHER).color == "coral"
    assert {c[2] for c in firmware.calls} == {UNIT, OTHER}


# ---- the cues the host starts ----


def test_show_clock_and_thinking_go_through_the_unit_tools(service, firmware) -> None:
    service.update(UNIT, {"clock_idle_s": 60})
    firmware.calls.clear()
    assert service.show_clock(UNIT, 45) == {"ok": True}
    assert service.thinking(UNIT, True) == {"ok": True}
    assert service.thinking(UNIT, False) == {"ok": True}
    assert firmware.calls[0][:2] == ("self.face.show_clock", {"seconds": 45})
    assert firmware.calls[1][:2] == ("self.face.thinking", {"on": True})
    assert firmware.calls[2][:2] == ("self.face.thinking", {"on": False})


@pytest.mark.parametrize("seconds", [-1, 3601, True, 1.5, "30"])
def test_show_clock_refuses_a_bad_number_with_the_range(service, seconds) -> None:
    with pytest.raises(FaceError) as caught:
        service.show_clock(UNIT, seconds)  # type: ignore[arg-type]
    assert "1 to 3600" in str(caught.value)


def test_the_unit_saying_no_to_the_clock_is_passed_on_in_plain_words(service, firmware) -> None:
    service.update(UNIT, {"color": "mint"})
    firmware.refuse = "the clock does not cover a mute or a ringing timer: end that first"
    with pytest.raises(FaceError) as caught:
        service.show_clock(UNIT, 20)
    assert "end that first" in str(caught.value)


def test_a_lost_link_on_a_cue_is_not_swallowed(service, firmware) -> None:
    service.update(UNIT, {"color": "mint"})
    firmware.link = False
    with pytest.raises(BodyLost):
        service.thinking(UNIT, True)


# ---- for the settings page ----


def test_the_page_can_apply_and_draw_a_unit(service, firmware) -> None:
    out = apply_settings(service, UNIT, {"clock_style": "ring", "clock24": True, "lang": "es"})
    assert out["config"]["clock_style"] == "ring" and out["config"]["lang"] == "es"
    view = settings_view(service, UNIT)
    assert view["values"]["lang"] == "es" and view["choices"]["color"][0] == "none"
    assert view["limits"]["clock_idle_s"] == [0, 3600]
    assert view["pending"] is False and view["problem"] is None


def test_no_unit_is_a_plain_error(service) -> None:
    with pytest.raises(FaceError) as caught:
        service.config("")
    assert "Choose a unit" in str(caught.value)


# ---- patch X02 and SF58: the three styles, the dropped ones, the screen color and the emotion tint ----


def test_the_three_styles_and_big_eyes_is_the_default() -> None:
    from maipai_body.faces import DEFAULT_STYLE, DROPPED_STYLES, STYLES

    assert STYLES == ("big_eyes", "stock", "minimal")
    assert DEFAULT_STYLE == "big_eyes" == FaceConfig().style
    assert not set(DROPPED_STYLES) & set(STYLES)
    assert set(DROPPED_STYLES) == {"round", "cat", "robot", "sleepy", "retro_pixel", "heart_eyes", "classic", "eyes_only"}


@pytest.mark.parametrize("old", ["round", "cat", "robot", "sleepy", "retro_pixel", "heart_eyes", "classic", "eyes_only"])
def test_a_dropped_style_falls_back_to_big_eyes_when_sent_or_read_back(old: str) -> None:
    from maipai_body.faces import from_stored

    assert clean(FaceConfig(style="minimal"), {"style": old}).style == "big_eyes"
    assert from_stored({"style": old, "color": "sky"}).style == "big_eyes"
    assert from_stored({"style": old, "color": "sky"}).color == "sky"  # the rest of the saved face survives


def test_decorators_no_longer_include_sweat_or_shy() -> None:
    from maipai_body.faces import DECORATOR_FOR_FACE, DECORATORS

    assert "sweat" not in DECORATORS and "shy" not in DECORATORS
    assert "sweat" not in DECORATOR_FOR_FACE.values() and "shy" not in DECORATOR_FOR_FACE.values()
    assert {"dizzy", "heart", "anger", "tears", "sparkles", "stars", "zzz", "notes"} == set(DECORATORS)  # notes: the music dance (MD03)


def test_background_and_emotion_tint_are_checked_like_the_firmware_does() -> None:
    config = clean(FaceConfig(), {"background": "mint", "emotion_tint": False})
    assert config.background == "mint" and config.emotion_tint is False
    assert config.to_wire()["background"] == "mint" and config.to_wire()["emotion_tint"] is False
    assert clean(FaceConfig(), {"background": "#102030"}).background == "#102030"
    assert clean(FaceConfig(background="mint"), {"background": "none"}).background == "none"
    assert FaceConfig().emotion_tint is True and FaceConfig().background == "none"  # tint on, black screen
    with pytest.raises(FaceError):
        clean(FaceConfig(), {"background": "#eeeeee"})  # white eyes would vanish on it
    with pytest.raises(FaceError):
        clean(FaceConfig(), {"emotion_tint": "yes"})


def test_a_unit_with_older_firmware_still_counts_as_in_sync() -> None:
    from maipai_body.faces import _wire_equal

    reply = {k: v for k, v in FaceConfig().to_wire().items() if k not in ("background", "emotion_tint", "caption_size")}
    assert _wire_equal(FaceConfig(), reply)  # it does not report them and the saved values are the plain ones
    assert not _wire_equal(FaceConfig(background="mint"), reply)


def test_the_new_styles_need_the_looks_feature(tmp_path) -> None:
    from maipai_body.faces import FaceService

    service = FaceService.__new__(FaceService)
    service.config = lambda unit_id: FaceConfig()  # type: ignore[method-assign]
    service.features = lambda unit_id: {"config", "packs"}  # type: ignore[method-assign]
    lines = FaceService.unsupported(service, "u", {"style": "stock", "background": "sky", "emotion_tint": False}, "en")
    assert any("eyes-only and stock" in line for line in lines)
    assert any("screen color" in line for line in lines)
    assert any("emotion colors" in line for line in lines)
    assert FaceService.unsupported(service, "u", {"style": "classic"}, "en") == []
