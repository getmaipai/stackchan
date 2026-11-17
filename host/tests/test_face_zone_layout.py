# ruff: noqa: E501
"""The fixed zones of the screen (patches N01, N04): the banner zone, the face zone and the subtitle zone never overlap, and no shape of
the face (every style, emotion, lid, blink, voice level and gaze extreme) reaches the zones around it.

The check needs the face core with the zone layout (patch N04), so it runs against a firmware tree: set ``MAIPAI_FW_TREE`` to a
firmware folder whose ``main/hal`` has ``maipai_look_core.h`` with ``ML_ZONE_Y0``; without one it is skipped (the host renderer's
zone check in ``scripts/fw-face-render/scene_banner.py`` says the same from the pictures)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TREE = os.environ.get("MAIPAI_FW_TREE", "")


def test_no_face_shape_reaches_the_banner_or_subtitle_zone(tmp_path: Path) -> None:
    hal = Path(TREE, "main", "hal") if TREE else None
    if hal is None or "ML_ZONE_Y0" not in (hal / "maipai_look_core.h").read_text():
        pytest.skip("set MAIPAI_FW_TREE to a firmware folder that has the face zone (patch N04)")
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    binary = tmp_path / "t"
    build = subprocess.run(
        [
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{hal}",
            str(HERE / "firmware" / "face_zone_core_test.c"),
            "-o",
            str(binary),
            "-lm",
        ],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all passed" in run.stdout
