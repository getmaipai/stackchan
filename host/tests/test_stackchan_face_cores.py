"""The face cores (firmware patches F01 to F06) are plain C: build and run their test here."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parent.parent / "firmware" / "patches"
C_TEST = HERE / "firmware" / "face_cores_test.c"

# patch file -> the header it adds
CORES = {
    "F01-face-config.patch": "maipai_face_core.h",
    "F03-face-time-of-day.patch": "maipai_face_tod_core.h",
    "F04-face-clock.patch": "maipai_face_clock_core.h",
    "F05-face-thinking-cue.patch": "maipai_face_think_core.h",
    "F06-face-timer-countdowns.patch": "maipai_face_timers_core.h",
}
FACE_PATCHES = [
    "F01-face-config.patch",
    "F02-face-captions.patch",
    "F03-face-time-of-day.patch",
    "F04-face-clock.patch",
    "F05-face-thinking-cue.patch",
    "F06-face-timer-countdowns.patch",
]


def _header_from_patch(patch: str, name: str) -> str:
    text = (PATCHES / patch).read_text()
    block = text.split(f"+++ b/firmware/main/hal/{name}\n", 1)[1]
    body = block.split("\n", 1)[1]  # drop the @@ line
    lines = []
    for line in body.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_face_core_c_tests_pass(tmp_path):
    for patch, name in CORES.items():
        (tmp_path / name).write_text(_header_from_patch(patch, name))
    binary = tmp_path / "face_cores_test"
    build = subprocess.run(
        [
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{tmp_path}",
            str(C_TEST),
            "-o",
            str(binary),
        ],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all passed" in run.stdout


def test_face_patches_are_on_order_in_sequence_with_their_header_lines():
    order = (PATCHES / "ORDER").read_text().split()
    positions = [order.index(name) for name in FACE_PATCHES]
    assert positions == sorted(positions), "the face patches must replay in number order"
    for name in FACE_PATCHES:
        text = (PATCHES / name).read_text()
        head = text.split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:"):
            assert key in head, f"{name} has no '{key}' line"
        assert chr(8212) not in text, f"{name} has an em dash"


def test_every_optional_face_feature_has_a_kconfig_switch():
    text = "".join((PATCHES / name).read_text() for name in FACE_PATCHES)
    for symbol in (
        "MAIPAI_FACE_CONFIG",
        "MAIPAI_FACE_CAPTIONS",
        "MAIPAI_FACE_TOD",
        "MAIPAI_FACE_CLOCK",
        "MAIPAI_FACE_THINKING",
        "MAIPAI_FACE_TIMERS",
    ):
        assert f"+config {symbol}\n" in text, f"{symbol} is not defined by the face patches"
        assert "default y" in text
