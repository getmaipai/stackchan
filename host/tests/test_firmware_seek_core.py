"""Turning toward a person (firmware patch S10): the core is plain C; compile and run its host test, and check the patch rules
(on ORDER after the last earlier entry, header lines, no em dashes, no sound direction, no camera or ESP call in the core)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
NAME = "S10-face-seek-core.patch"
HEADER = "firmware/main/hal/maipai_seek_core.h"


def _added_file(path: str) -> str:
    text = (PATCHES / NAME).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    lines = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_seek_core_c_tests_pass(tmp_path, tmp_path_factory):
    # The core as the whole of ORDER leaves it: patch NX06 added the lock, carry and night gates to what S10 wrote.
    from firmware_order_cores import cores_dir

    hal = cores_dir(tmp_path_factory)
    binary = tmp_path / "t"
    build = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{hal}", str(HERE / "firmware" / "seek_core_test.c"), "-o", str(binary), "-lm"],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=300)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr


def test_the_patch_is_on_order_and_carries_its_header_lines():
    order = (PATCHES / "ORDER").read_text().split()
    assert NAME in order
    assert order.index(NAME) > order.index("FI03-bench-snapshot-includes-top-layer.patch")
    text = (PATCHES / NAME).read_text()
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:"):
        assert key in text.split("diff --git", 1)[0], key
    assert chr(8212) not in text


def test_the_core_has_no_hardware_call_and_no_sound_direction():
    core = _added_file(HEADER)
    assert not re.search(r"\b(esp_|heap_caps|xTask|vTask|gpio_|i2s_)", core)
    code = re.sub(r"/\*.*?\*/", "", core, flags=re.S)
    assert not re.search(r"(?i)doa|direction_of|sound_dir|mic_array", code)


def test_the_flash_key_for_the_setting_fits_fifteen_characters():
    assert len("turn_to_faces") <= 15
