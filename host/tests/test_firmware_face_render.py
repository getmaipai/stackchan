"""The eyes are drawn as designed (patches X01 and V10), checked on real pixels: the unit's own face classes drawn by LVGL on this machine.

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
STYLES = {"stock": 20}  # the circle styles: only Stock is a circle with a tilted lid now
# the approved design (patch V10) inside the face zone (patch N04: Big eyes at 0.82, eyes only at 0.9; every eye is above y 150 and every
# mouth below it): the eye box (width, height) of each of the other styles
BOXES = {"big_eyes": (79, 85, 150), "eyes_only": (76, 80, 150), "classic": (56, 72, 150), "minimal": (28, 40, 150)}  # width, height, a row above the mouth

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
    diameter = STYLES["stock"]
    area = math.pi * (diameter / 2) ** 2
    for lid in (80, 60, 40):
        d = 1 - lid / 50
        expected = area * (math.acos(d) - d * math.sqrt(1 - d * d)) / math.pi  # the visible part of a circle cut by a straight lid
        for deg in (0, 45, 100, 160, 250):
            left, right = _counts(render, "stock", deg, lid)
            for count, *_ in (left, right):
                assert abs(count - expected) / area < 0.08, (lid, deg, count, expected)
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


@pytest.mark.parametrize("style", sorted([*STYLES, *BOXES]))
def test_both_eyes_blink_and_close_together_at_every_frame(render: Path, style: str) -> None:
    # 14 seconds of an awake face (about four blinks), a sleepy spell, the closing, the sleeping and the waking
    for lead in ("emotion neutral\nadvance 300\n", "emotion sleepy\nadvance 300\n", "emotion neutral\nadvance 600\nemotion closing\n"):
        frames = _frames(render, style, lead, 430 if "closing" not in lead else 120)
        for i, (left, right) in enumerate(frames):
            assert abs(left - right) <= max(10, 0.1 * max(left, right)), (style, lead.split()[1], i, left, right)  # anti-aliasing of a mirrored tilt  # one lid for both, every step
    awake = _frames(render, style, "emotion neutral\nadvance 300\n", 430)
    assert min(c for pair in awake for c in pair) < 0.6 * max(c for pair in awake for c in pair)  # a blink did happen


def _boxes(render: Path, style: str, lead: str, frames: int) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
    """The lit pixels of the left and the right eye (count and bounding box) at each 33 ms frame; the box stops above the mouth."""
    ylim = BOXES[style][2]
    script = f"style {style}\n{lead}" + f"eyebox {ylim}\n" * frames  # both eyes read from the same frame
    ran = subprocess.run([str(render)], input=script, capture_output=True, text=True, timeout=120)
    rows = [tuple(int(v) for v in row) for row in re.findall(r"eyebox (\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+)", ran.stdout)]
    assert len(rows) == 2 * frames, ran.stdout + ran.stderr
    return [(rows[i], rows[i + 1]) for i in range(0, len(rows), 2)]


EYE_X = {"big_eyes": 70, "eyes_only": 70, "classic": 70, "minimal": 62}


@pytest.mark.parametrize("style", sorted(BOXES))
def test_at_rest_the_eyes_are_the_designed_box_and_level_with_each_other(render: Path, style: str) -> None:
    """The owner saw the left eye higher than the right on the glass: at rest both are the same box on the same line, every frame."""
    ew, eh, _ = BOXES[style]
    frames = _boxes(render, style, "emotion content\nadvance 1500\n", 240)  # eight seconds of drift and blinks
    open_frames = 0
    for (_lc, lx0, ly0, lx1, ly1), (_rc, rx0, ry0, rx1, ry1) in frames:
        if ly1 - ly0 + 1 < eh - 4 or ry1 - ry0 + 1 < eh - 4:
            continue  # a blink is under way (both eyes at once, checked elsewhere)
        open_frames += 1
        assert abs((ly0 + ly1) - (ry0 + ry1)) <= 1, (style, "left and right eye not level", (ly0, ly1), (ry0, ry1))
        assert abs((lx1 - lx0) - (rx1 - rx0)) <= 2 and abs((ly1 - ly0) - (ry1 - ry0)) <= 1, (style, "different size")
        assert abs((lx1 - lx0 + 1) - ew) <= 3 and abs((ly1 - ly0 + 1) - eh) <= 3, (style, (lx0, ly0, lx1, ly1))
        assert abs(((rx0 + rx1) - (lx0 + lx1)) / 2 - 2 * EYE_X[style]) <= 2, (style, "wrong distance between the eyes")  # the drift moves both together
    assert open_frames > 100


@pytest.mark.parametrize("style", sorted(BOXES))
def test_the_lid_cuts_cleanly_at_every_step_and_both_eyes_agree(render: Path, style: str) -> None:
    ew, eh, _ = BOXES[style]
    previous = None
    for lid in (100, 90, 80, 70, 60, 50, 40, 30):  # below this the eye gives way to its closed arc
        left, right = _boxes(render, style, f"emotion neutral\neyepose 0 {lid}\nadvance 700\n", 1)[0]
        assert abs(left[0] - right[0]) <= max(10, 0.03 * left[0]), (style, lid, left[0], right[0])  # one lid for both eyes
        for _count, x0, y0, x1, y1 in (left, right):
            assert x1 - x0 + 1 <= ew + 3 and y1 - y0 + 1 <= eh + 3, (style, lid, (x0, y0, x1, y1))  # nothing beyond the eye box
        if previous is not None:
            assert left[0] <= previous + 3, (style, lid, left[0], previous)  # a lower lid never shows more of the eye
        previous = left[0]
    assert previous < 0.6 * ew * eh  # a low lid hides much of the eye


@pytest.mark.parametrize("style", sorted(BOXES))
def test_the_gaze_moves_the_eye_and_never_cuts_it(render: Path, style: str) -> None:
    ew, eh, _ = BOXES[style]
    seen = set()
    for (_lc, lx0, ly0, lx1, ly1), _right in _boxes(render, style, "emotion neutral\nadvance 300\n", 300):
        if ly1 - ly0 + 1 < eh - 4:
            continue  # a blink
        assert abs((lx1 - lx0 + 1) - ew) <= 3 and abs((ly1 - ly0 + 1) - eh) <= 3, (style, (lx0, ly0, lx1, ly1))
        seen.add((lx0 + lx1) // 2)
    assert len(seen) >= 3  # the gaze did drift across several places
