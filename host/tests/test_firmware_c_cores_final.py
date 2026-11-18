"""The unit's C core tests, compiled against the headers exactly as the whole of ``firmware/patches/ORDER`` leaves them.

These replace the wrappers that read the old base's patch folder: a test here fails when the header the unit runs is wrong."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir

HERE = Path(__file__).resolve().parent
needs_cc = pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")

# Tests that take no arguments and print their own verdict through the exit code.
# Legacy sounds_core_test.c and tailnet_core_test.c call functions the final headers no longer have.
# These final-header tests cover their current interfaces.
PLAIN = [
    "touch_core_test.c",
    "timers_core_test.c",
    "tailnet_travel_test.c",
    "music_core_test.c",
    "music_mood_test.c",
    "beat_test.c",
    "mouthcue_core_test.c",
    "sounds_core_final_test.c",
    "tailnet_core_final_test.c",
]


@needs_cc
@pytest.mark.parametrize("name", PLAIN)
def test_core_test_passes_on_the_final_headers(name, tmp_path, tmp_path_factory):
    source = HERE / "firmware" / name
    if not source.exists():
        pytest.skip(f"{name} is not in host/tests/firmware")
    binary = tmp_path / name.replace(".c", "")
    build = subprocess.run(
        ["cc", "-std=gnu99", "-Wall", "-Wextra", "-Werror", f"-I{cores_dir(tmp_path_factory)}", str(source), "-o", str(binary), "-lm"],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr[-2000:]
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, (run.stdout + run.stderr)[-2000:]
