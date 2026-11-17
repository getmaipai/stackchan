# ruff: noqa: E501
"""Swipe pages and the control sheet (firmware patches P10 to P13): the two cores are plain C and their host tests run here against the
patch text; the patches are on ORDER after the last earlier entry with their header lines; the cores call no hardware; the wiring keeps
the rules the owner set (the edge swipe and the stop swipe stay, the pages cost nothing at rest, flash keys fit 15 characters)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
NAMES = [
    "P10-gesture-state-machine-core.patch",
    "P11-pages-data-and-layout-core.patch",
    "P12-pages-and-control-sheet-drawing.patch",
    "P13-pages-wiring-tools-and-switch.patch",
]
TOUCH_CORE_PATCH = "105-touch-regions.patch"


def _added(name: str, path: str) -> str:
    text = (PATCHES / name).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    lines = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


def _touch_core() -> str | None:
    """maipai_touch_core.h is added by an earlier patch; the gesture test includes it to prove a swipe never also toggles."""
    for patch in sorted(PATCHES.glob("*.patch")):
        text = patch.read_text()
        if (
            "+++ b/firmware/main/hal/maipai_touch_core.h" in text
            and "new file mode"
            in text.split("+++ b/firmware/main/hal/maipai_touch_core.h")[0].rsplit("diff --git", 1)[
                -1
            ]
        ):
            return _added(patch.name, "firmware/main/hal/maipai_touch_core.h")
    return None


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
@pytest.mark.parametrize(
    ("test", "needs_touch"),
    [("gesture_core_test.c", True), ("pages_core_test.c", False)],
)
def test_the_core_tests_pass_against_the_patch_text(tmp_path, test, needs_touch):
    (tmp_path / "maipai_gesture_core.h").write_text(
        _added(NAMES[0], "firmware/main/hal/maipai_gesture_core.h")
    )
    (tmp_path / "maipai_pages_core.h").write_text(
        _added(NAMES[1], "firmware/main/hal/maipai_pages_core.h")
    )
    if needs_touch:
        touch = _touch_core()
        if touch is None:
            pytest.skip("the touch core is not in the patch list on this checkout")
        (tmp_path / "maipai_touch_core.h").write_text(touch)
    binary = tmp_path / "t"
    build = subprocess.run(
        [
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{tmp_path}",
            str(HERE / "firmware" / test),
            "-o",
            str(binary),
        ],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=300)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr


def test_the_patches_are_on_order_after_the_earlier_ones_with_their_header_lines():
    order = (PATCHES / "ORDER").read_text().split()
    last_before = (
        max(order.index(n) for n in order if n not in NAMES and not n.startswith("P1"))
        if False
        else order.index("FI06-snapshot-includes-overlays-and-effects.patch")
    )
    positions = [order.index(n) for n in NAMES]
    assert positions == sorted(positions) and positions[0] > last_before
    for name in NAMES:
        text = (PATCHES / name).read_text()
        head = text.split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash"):
            assert key in head, (name, key)
        assert chr(8212) not in text, name


def test_the_cores_call_no_hardware_and_hold_no_heap():
    for name, path in (
        (NAMES[0], "firmware/main/hal/maipai_gesture_core.h"),
        (NAMES[1], "firmware/main/hal/maipai_pages_core.h"),
    ):
        code = re.sub(r"/\*.*?\*/", "", _added(name, path), flags=re.S)
        assert not re.search(
            r"\b(esp_|heap_caps|xTask|vTask|gpio_|lv_|malloc|calloc|new )", code
        ), name


def test_the_edge_swipe_and_the_stop_swipe_stay():
    core = _added(NAMES[0], "firmware/main/hal/maipai_gesture_core.h")
    assert "MGS_ACT_VOLUME" in core and "MGS_ACT_STOP" in core and "mgs_is_edge_x(g->x0)" in core
    wiring = (PATCHES / NAMES[3]).read_text()
    assert (
        "maipai_display_stop_swipe" in wiring
        and "maipai_games_stop_locked" in wiring
        and "ChangeVolume(delta)" in wiring
    )


def test_nothing_is_resident_at_rest():
    drawing = (PATCHES / NAMES[2]).read_text()
    assert (
        "lv_timer_create" in drawing and "lv_timer_delete" in drawing
    )  # the timer is made when something opens and deleted when it closes
    assert (
        "frame_free" in drawing and "new (std::nothrow) Ui()" in drawing
    )  # widgets and the picture buffer are made on demand
    unit = (PATCHES / NAMES[3]).read_text()
    assert "MALLOC_CAP_SPIRAM" in unit  # the picture buffer is PSRAM


def test_the_flash_keys_and_the_tools_are_named_as_documented():
    unit = (PATCHES / NAMES[3]).read_text()
    for key in re.findall(r'constexpr const char\* kKey\w+\s*=\s*"([^"]+)"', unit):
        assert len(key) <= 15, key
    for tool in (
        "self.pages.status",
        "self.pages.get",
        "self.pages.set",
        "self.page.show",
        "self.page.tiles",
    ):
        assert f'"{tool}"' in unit, tool
    assert "pages_cfg" in unit and "page_tiles" in unit
    assert "CONFIG_MAIPAI_PAGES=y" in unit


def test_overlays_pause_under_a_page_and_the_face_toggles_ignore_a_swipe():
    unit = (PATCHES / NAMES[3]).read_text()
    assert "maipai_face_clock_visible() || maipai_pages_open()" in unit
    assert unit.count("maipai_pages_last_touch_was_gesture()") >= 3
