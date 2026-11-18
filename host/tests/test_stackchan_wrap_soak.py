# ruff: noqa: E501
"""Soak test for the 24.9 day (2^31 ms) and 49.7 day (2^32 ms) clock wrap class across every core that uses the stamp helper (lane P, report 4)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir

HERE = Path(__file__).resolve().parent
needs_cc = pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")


@needs_cc
def test_every_stamp_core_behaves_the_same_across_the_wrap_points(tmp_path, tmp_path_factory):
    binary = tmp_path / "wrap_soak_test"
    build = subprocess.run(
        ["cc", "-std=gnu99", "-Wall", "-Wextra", "-Werror", f"-I{cores_dir(tmp_path_factory)}", str(HERE / "firmware" / "wrap_soak_test.c"), "-o", str(binary), "-lm"],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "wrap soak ok" in run.stdout
