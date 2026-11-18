"""Turning toward a person on the unit (firmware patches S12, S13, S14): the wiring core is plain C; build it from the patches (S10 plus S12 on
the seek core, S13 for the wire core) and run its host test, and check the patch rules (on ORDER after S10 and S11 and in the right order,
header lines, no em dashes, no ESP call in the pure parts, the seek task is a low priority PSRAM-stack task that reads no flash)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
S10 = "S10-face-seek-core.patch"
S12 = "S12-seek-core-measured-geometry.patch"
S13 = "S13-seek-wire-core-and-camera-grab.patch"
S14 = "S14-seek-task-tools-and-setting.patch"
CORE = "firmware/main/hal/maipai_seek_core.h"
WIRE = "firmware/main/hal/maipai_seek_wire_core.h"


def _added_file(patch: str, path: str) -> str:
    text = (PATCHES / patch).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    lines = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


def _build_headers(tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    hal = root / "firmware" / "main" / "hal"
    hal.mkdir(parents=True)
    (hal / "maipai_seek_core.h").write_text(_added_file(S10, CORE))
    text = (PATCHES / S12).read_text()
    (tmp_path / "s12.diff").write_text(text[text.index("diff --git") :])
    applied = subprocess.run(["git", "apply", "--whitespace=nowarn", str(tmp_path / "s12.diff")], cwd=root, capture_output=True, text=True)
    assert applied.returncode == 0, applied.stderr
    (hal / "maipai_seek_wire_core.h").write_text(_added_file(S13, WIRE))
    return hal


@pytest.mark.skipif(shutil.which("cc") is None or shutil.which("git") is None, reason="no C compiler or git on this machine")
def test_seek_wire_c_tests_pass(tmp_path, tmp_path_factory):
    # The cores as the whole of ORDER leaves them (patch NX06 adds the lock, carry and night gates to both).
    from firmware_order_cores import cores_dir

    hal = cores_dir(tmp_path_factory)
    for name in ("seek_wire_test.c", "seek_core_test.c"):
        binary = tmp_path / name.replace(".c", "")
        build = subprocess.run(
            ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{hal}", str(HERE / "firmware" / name), "-o", str(binary), "-lm"],
            capture_output=True,
            text=True,
        )
        assert build.returncode == 0, build.stderr
        run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=300)
        assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr


def test_the_patches_are_on_order_in_sequence_and_carry_their_header_lines():
    order = (PATCHES / "ORDER").read_text().split()
    names = [S10, "S11-turn-to-faces-setting.patch", S12, S13, S14]
    assert all(n in order for n in names)
    assert [order.index(n) for n in names] == sorted(order.index(n) for n in names)
    assert order.index(S12) > order.index("FI06-snapshot-includes-overlays-and-effects.patch")
    for name in (S12, S13, S14):
        text = (PATCHES / name).read_text()
        head = text.split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:"):
            assert key in head, (name, key)
        assert chr(8212) not in text
    assert "+" + "MAIPAI_FACE_DETECT" not in (PATCHES / S13).read_text()


def test_the_pure_parts_have_no_hardware_call():
    wire = _added_file(S13, WIRE)
    assert not re.search(r"\b(esp_|heap_caps|xTask|vTask|gpio_|i2s_|xSemaphore|malloc|calloc)\b", wire)
    assert not re.search(r"(?i)doa|direction_of|sound_dir|mic_array", re.sub(r"/\*.*?\*/", "", wire, flags=re.S))


def test_the_seek_task_is_low_priority_with_a_psram_stack_and_reads_no_flash_itself():
    text = _added_file(S14, "firmware/main/hal/maipai_seek.cc")
    create = re.search(r"xTaskCreatePinnedToCoreWithCaps\(seek_task, \"seek\", (\d+), nullptr, (\d+), &s_task, (\d+), MALLOC_CAP_SPIRAM\)", text)
    assert create is not None
    stack, priority, core = (int(g) for g in create.groups())
    assert stack <= 8192 and priority == 1 and core == 0  # below the face loop and the servo task (3, core 1) and the audio tasks
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    assert not re.search(r"\b(nvs_|Settings\b|esp_flash_|spi_flash_|esp_partition_|esp_ota_)", code)
    assert "maipai_tb_prefs()" in code  # the setting arrives through the cached reader
    assert "monitor_cue_begin" in code and 'maipai_remote_gate(far ? "move" : "move_near", "user", 0)' in code
    for tool in ("self.look.claim", "self.look.release", "self.look.status", "self.look.calibrate"):
        assert tool in code
    assert "#error" in text and "MAIPAI_FACE_DETECT" in text  # the detector switch is reserved, not built
