"""The first-run step rules (maipai_firstrun_core.h, patches UX05a and UX11) run by their C test on the replayed patch series: the name step offers seven names, StackChan is the default and
is saved as index 6 exactly as picked, the six older names keep their indexes, and back keeps an answer."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir

HERE = Path(__file__).resolve().parent
needs_cc = pytest.mark.skipif(shutil.which("cc") is None or shutil.which("git") is None, reason="needs cc and git")


@needs_cc
def test_the_first_run_core_test_passes_on_the_patch_series(tmp_path, tmp_path_factory):
    binary = tmp_path / "firstrun"
    built = subprocess.run(["cc", "-std=gnu99", "-Wall", "-Wextra", "-Werror", f"-I{cores_dir(tmp_path_factory)}", str(HERE / "firmware" / "firstrun_core_test.c"), "-o", str(binary)], capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr
