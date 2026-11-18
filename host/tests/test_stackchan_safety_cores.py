"""Host tests for the firmware safety trains (patches SF01 and later): the C test compiles against the headers as ORDER leaves them."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir

HERE = Path(__file__).resolve().parent
needs_cc = pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")


@needs_cc
def test_safety_core(tmp_path, tmp_path_factory):
    binary = tmp_path / "safety_core_test"
    build = subprocess.run(
        ["cc", "-std=gnu99", "-Wall", "-Wextra", "-Werror", f"-I{cores_dir(tmp_path_factory)}", str(HERE / "firmware" / "safety_core_test.c"), "-o", str(binary), "-lm"],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "safety core ok" in run.stdout
