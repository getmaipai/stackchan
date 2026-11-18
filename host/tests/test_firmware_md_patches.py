# ruff: noqa: E501
"""Firmware patches ML01 (movement limiter) and MD01 to MD03 (the music dance ladder): on ORDER after NX09, ML01 first, with their header lines."""

from __future__ import annotations

from pathlib import Path

PATCHES = Path(__file__).resolve().parents[2] / "firmware" / "patches"
NAMES = [
    "ML01-movement-limiter-at-the-servo-layer.patch",
    "MD01-music-dance-ladder-and-beat-dance.patch",
    "MD02-dance-faces-wink-silly-grin-serene-excited.patch",
    "MD03-music-notes-and-eye-gaze-tools.patch",
]


def test_the_limiter_comes_first_then_the_dance_patches_in_order_with_header_lines_and_no_em_dash() -> None:
    order = (PATCHES / "ORDER").read_text().split()
    positions = [order.index(n) for n in NAMES]
    assert positions == sorted(positions) and positions[0] == order.index("NX09-timers-preset-column-and-tall-rows-no-word-timer.patch") + 1
    for name in NAMES:
        text = (PATCHES / name).read_text()
        head = text.split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash", "# Kconfig:"):
            assert key in head, (name, key)
        assert chr(8212) not in text, name


def test_every_servo_target_passes_the_one_chokepoint() -> None:
    text = (PATCHES / NAMES[0]).read_text()
    assert "maipai_motion_hold()" in text and "update_angle_anim_target" in text
    added = "\n".join(line for line in text.splitlines() if line.startswith("+"))
    # the three public setters and the continuous rotate all reach the limiter
    for needle in ("maipai_motion_speed(speed)", "maipai_motion_stiffness(stiffness)", "maipai_motion_angle(angle)", "maipai_motion_speed(-velocity)"):
        assert needle in added, needle
