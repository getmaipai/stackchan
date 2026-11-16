"""The faces-core patches (X01, X02, 2026-11-16): listed in ORDER, documented, and carrying what the brief decided."""

from __future__ import annotations

from pathlib import Path

PATCHES = Path(__file__).resolve().parents[2] / "firmware" / "patches"
NAMES = ["X01-look-core-and-skin.patch", "X02-face-styles-colours-and-battery.patch"]


def _text(name: str) -> str:
    return (PATCHES / name).read_text()


def _added(name: str, path: str) -> str:
    """The lines a patch adds to one file, joined."""
    block = _text(name).split(f"diff --git a/firmware/main/{path} ", 1)[1].split("\ndiff --git ", 1)[0]
    return "\n".join(line[1:] for line in block.splitlines() if line.startswith("+") and not line.startswith("+++"))


def test_the_patches_are_last_on_order_in_sequence_and_have_their_header_lines() -> None:
    order = (PATCHES / "ORDER").read_text().split()
    first = order.index(NAMES[0])
    assert order[first : first + 2] == NAMES and first > order.index("L09-stop-word-not-probed.patch")  # in a row; later patches may follow
    for name in NAMES:
        head = _text(name).split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:"):
            assert key in head, f"{name} has no '{key}' line"
        assert chr(8212) not in _text(name), "no em dashes"


def test_the_right_eye_tilt_is_not_clamped_any_more() -> None:
    eyes = _added(NAMES[0], "stackchan/avatar/skins/default/eyes.cpp")
    assert "_rotation = rotation;" in eyes  # signed, stored as given
    assert "Element::setRotation(rotation)" not in eyes  # the base setter clamps every negative tilt to none
    core = _added(NAMES[0], "hal/maipai_look_core.h")
    assert "ml_eye_rotation_deci" in core and "left == -right" not in core  # the test, not the header, checks the mirror


def test_there_are_five_styles_and_the_old_ones_fall_back_to_big_eyes() -> None:
    core = _added(NAMES[1], "hal/maipai_face_core.h")
    for name in ("big_eyes", "eyes_only", "stock", "classic", "minimal"):
        assert f'"{name}"' in core
    for gone in ("round", "cat", "robot", "retro_pixel", "heart_eyes"):
        assert f'"{gone}"' in core  # still accepted by name, and they mean big eyes
    assert "MF_STYLE_DROPPED_FIRST 3" in core and "MF_STYLE_EYES_ONLY 9" in core and "MF_STYLE_STOCK 10" in core
    assert "t.style = MF_STYLE_BIG_EYES; /* a style that was dropped" in core


def test_low_battery_is_tired_not_sad() -> None:
    daily = _added(NAMES[1], "hal/maipai_daily.cc")
    assert "maipai_face_set_tired(" in daily and "mb_step_for(level)" in daily
    display = _added(NAMES[1], "hal/board/stackchan_display.cc")
    assert "switch (maipai_face_tired())" in display and "return Emotion::Tired;" in display
    assert "return Emotion::Sleepy;" in display and "return Emotion::Content;" in display
    tired_block = display.split("switch (maipai_face_tired())", 1)[1].split("default:", 1)[0]
    assert "Emotion::Sad" not in tired_block  # the ladder never shows sad


def test_the_thinking_dots_are_the_skins_and_sit_at_the_mouth() -> None:
    skin = _added(NAMES[0], "stackchan/avatar/skins/default/default.cpp")
    assert "setThinking" in skin and "ml_dot(" in skin
    face = _added(NAMES[1], "hal/maipai_face.cc")
    assert "face->setThinking(true)" in face and "LV_ALIGN_TOP_MID" not in face
