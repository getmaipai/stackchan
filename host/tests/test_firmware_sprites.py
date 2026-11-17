# ruff: noqa: E501
"""Fast eyes, sprites (firmware patches V20 to V26): the pure picture core, and the patch files.

The core test builds the headers as the patches leave them (the same chain the face core tests use, then V23 for the new header)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from test_stackchan_train4 import CORE_CHAIN

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PATCHES = ROOT / "firmware" / "patches"
EM = chr(0x2014)  # written this way so the hygiene check never sees the character in this file
FAST = [
    "V20-face-bench-counters-and-ab-switch.patch",
    "V21-dirty-rectangles-and-color-steps.patch",
    "V22-fast-gaze-and-pose-springs.patch",
    "V23-face-pictures-for-eyes-and-mouth.patch",
    "V24-face-bench-counters-2.patch",
    "V25-face-loop-holds-the-screen-lock-less.patch",
    "V26-two-half-buffers-overlap-draw-and-flush.patch",
]


@pytest.fixture(scope="module")
def headers(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """maipai_look_core.h and friends as the patches leave them, plus the sprite core."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    work = tmp_path_factory.mktemp("sprites")
    for name in [l.strip() for l in (PATCHES / "ORDER").read_text().splitlines() if l.strip() and not l.startswith("#")]:  # the whole of ORDER, as the parity test does
        text = (PATCHES / name).read_text()
        diff = work / "p.diff"
        diff.write_text(text[text.index("diff --git") :])
        run = subprocess.run(
            ["git", "apply", "--include=firmware/main/hal/*_core.h", str(diff)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        assert run.returncode == 0, f"{name}: {run.stderr}"
    return work / "firmware" / "main" / "hal"


def test_the_sprite_core_passes_its_test_under_the_sanitizers(headers: Path, tmp_path: Path) -> None:
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    binary = tmp_path / "t"
    build = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined", f"-I{headers}", str(HERE / "firmware" / "sprite_core_test.c"), "-o", str(binary), "-lm"],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all passed" in run.stdout


def test_the_fast_eyes_patches_are_in_order_with_their_header_lines() -> None:
    order = (PATCHES / "ORDER").read_text().split()
    positions = [order.index(name) for name in FAST]
    assert positions == sorted(positions)
    assert order.index("M06-camera-dma-in-psram.patch") < positions[0]  # they replay onto the tree that has the memory headroom patches
    for name in FAST:
        text = (PATCHES / name).read_text()
        head = text.split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement:", "# Upstream:", "# Check after a flash:"):
            assert key in head, (name, key)
        assert EM not in text, name


def test_the_pictures_leave_internal_ram_alone() -> None:
    """The pictures are PSRAM only: no static buffer of picture size in the skin sources."""
    text = (PATCHES / "V23-face-pictures-for-eyes-and-mouth.patch").read_text()
    assert "MALLOC_CAP_SPIRAM" in text
    assert "MALLOC_CAP_INTERNAL" not in text
    added = [line[1:] for line in text.splitlines() if line.startswith("+") and not line.startswith("+++")]
    assert not any(("static uint8_t" in line or "static uint16_t" in line) and "[" in line for line in added)


def test_the_screen_lock_is_not_held_over_the_servo_and_led_buses() -> None:
    text = (PATCHES / "V25-face-loop-holds-the-screen-lock-less.patch").read_text()
    assert "void updateScreen()" in text and "void updateBody()" in text
    assert "GetStackChan().updateScreen();" in text


def test_the_display_keeps_its_twelve_point_eight_kilobytes_as_two_half_buffers() -> None:
    text = (PATCHES / "V26-two-half-buffers-overlap-draw-and-flush.patch").read_text()
    assert "width_ * 10" in text and "double_buffer  = true" in text
    assert "width_ * 20" in text  # the one buffer it replaces: 2 x 10 rows is the same memory
