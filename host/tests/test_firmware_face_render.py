"""The eyes are full circles (patch X01), checked on real pixels: the unit's own face classes drawn by LVGL on this machine.

Needs a built firmware tree (set MAIPAI_FW_TREE to its firmware folder; the repo does not carry LVGL) and a C++ compiler;
otherwise it is skipped. The pure geometry of the same rule runs everywhere in look_core_test.c.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TREE = os.environ.get("MAIPAI_FW_TREE", "")
RENDER = Path(__file__).resolve().parents[2] / "scripts" / "fw-face-render"
STYLES = {"big_eyes": 48, "eyes_only": 50, "classic": 34, "stock": 20, "minimal": 16}

pytestmark = pytest.mark.skipif(
    not TREE or not Path(TREE, "managed_components").is_dir() or shutil.which("clang++") is None,
    reason="needs MAIPAI_FW_TREE (a built firmware folder) and clang++",
)


@pytest.fixture(scope="module")
def render(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("render")
    built = subprocess.run(
        ["bash", str(RENDER / "build.sh"), str(out)],
        env={**os.environ, "MAIPAI_FW_TREE": TREE},
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stderr[-2000:]
    return out / "render"


def _counts(render: Path, style: str, deg: int, lid: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    script = f"style {style}\nemotion neutral\neyepose {deg} {lid}\nadvance 450\ncount 12 30 140 142\ncount 180 30 308 142\n"
    ran = subprocess.run([str(render)], input=script, capture_output=True, text=True, timeout=60)
    rows = re.findall(r"count (\d+) bbox (-?\d+) (-?\d+) (-?\d+) (-?\d+)", ran.stdout)
    assert len(rows) == 2, ran.stdout + ran.stderr
    left, right = (tuple(int(v) for v in row) for row in rows)
    return left, right


@pytest.mark.parametrize("style", sorted(STYLES))
def test_an_open_eye_is_a_full_circle_at_every_tilt_and_the_two_eyes_agree(render: Path, style: str) -> None:
    diameter = STYLES[style]
    area = math.pi * (diameter / 2) ** 2
    for deg in range(0, 360, 20):
        left, right = _counts(render, style, deg, 100)
        for count, x0, y0, x1, y1 in (left, right):
            assert abs(count - area) / area < 0.05, (style, deg, count, area)  # a full disc, nothing clipped off it
            assert abs((x1 - x0 + 1) - diameter) <= 2 and abs((y1 - y0 + 1) - diameter) <= 2, (style, deg, (x0, y0, x1, y1))
        assert abs(left[0] - right[0]) <= max(3, 0.03 * area), (style, deg, left[0], right[0])  # the old clamp cut them differently


def test_a_lid_hides_the_part_of_the_circle_it_should_at_any_tilt(render: Path) -> None:
    diameter = STYLES["big_eyes"]
    area = math.pi * (diameter / 2) ** 2
    for lid in (80, 60, 40):
        d = 1 - lid / 50
        expected = area * (math.acos(d) - d * math.sqrt(1 - d * d)) / math.pi  # the visible part of a circle cut by a straight lid
        for deg in (0, 45, 100, 160, 250):
            left, right = _counts(render, "big_eyes", deg, lid)
            for count, *_ in (left, right):
                assert abs(count - expected) / area < 0.06, (lid, deg, count, expected)
            # the right eye is the mirror of the left: the same width and height of what shows (the old clamp left the
            # right eye untilted, so its cut had a different size and angle)
            assert abs((left[3] - left[1]) - (right[3] - right[1])) <= 2, (lid, deg, left, right)
            assert abs((left[4] - left[2]) - (right[4] - right[2])) <= 2, (lid, deg, left, right)


def _frames(render: Path, style: str, lead: str, frames: int) -> list[tuple[int, int]]:
    """Both eyes' lit pixel counts at each 33 ms frame."""
    script = f"style {style}\n{lead}" + "eyes\n" * frames
    ran = subprocess.run([str(render)], input=script, capture_output=True, text=True, timeout=120)
    pairs = [(int(a), int(b)) for a, b in re.findall(r"eyes (\d+) (\d+)", ran.stdout)]
    assert len(pairs) == frames, ran.stdout + ran.stderr
    return pairs


@pytest.mark.parametrize("style", sorted(STYLES))
def test_both_eyes_blink_and_close_together_at_every_frame(render: Path, style: str) -> None:
    # 14 seconds of an awake face (about four blinks), a sleepy spell, the closing, the sleeping and the waking
    for lead in ("emotion neutral\nadvance 300\n", "emotion sleepy\nadvance 300\n", "emotion neutral\nadvance 600\nemotion closing\n"):
        frames = _frames(render, style, lead, 430 if "closing" not in lead else 120)
        for i, (left, right) in enumerate(frames):
            assert abs(left - right) <= 8, (style, lead.split()[1], i, left, right)  # anti-aliasing of a mirrored tilt  # one lid for both, every step
    awake = _frames(render, style, "emotion neutral\nadvance 300\n", 430)
    assert min(c for pair in awake for c in pair) < 0.5 * max(c for pair in awake for c in pair)  # a blink did happen
