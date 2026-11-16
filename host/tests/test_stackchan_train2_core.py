"""The Train 2 cores (firmware patches T01 to T05) are plain C: compile and run their test on the host, and check
the rules the patches must keep (the camera cue has no off switch, the ladder never powers the simulated unit off)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware/patches"
C_TEST = HERE / "firmware" / "train2_core_test.c"

CORES = {
    "maipai_battery_core.h": "T01-low-battery-ladder.patch",
    "maipai_hourly_core.h": "T02-hourly-chime-quiet-hours.patch",
    "maipai_wake_core.h": "T03-wake-cue-and-selftest.patch",
    "maipai_link_quiet_core.h": "T04-quiet-reconnect-offline-tone.patch",
    "maipai_cue_core.h": "T05-camera-on-cue.patch",
    "maipai_sounds_core.h": "115-sounds-core.patch",
}


def added_file(patch: str, path: str) -> str:
    text = (PATCHES / patch).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1]
    body = block.split("\n", 1)[1]
    lines = []
    for line in body.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_train2_core_c_tests_pass(tmp_path):
    for header, patch in CORES.items():
        (tmp_path / header).write_text(added_file(patch, f"firmware/main/hal/{header}"))
    binary = tmp_path / "train2_test"
    build = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{tmp_path}", str(C_TEST), "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all passed" in run.stdout


def test_patches_carry_the_required_header_lines_and_are_on_order():
    order = (PATCHES / "ORDER").read_text().split()
    for name in [p for p in CORES.values() if p.startswith("T")]:
        text = (PATCHES / name).read_text()
        for tag in ("# Intent:", "# Placement: unit (", "# Upstream:"):
            assert tag in text, (name, tag)
        assert name in order


def test_the_camera_cue_has_no_off_switch():
    text = (PATCHES / "T05-camera-on-cue.patch").read_text()
    assert "CONFIG_MAIPAI" not in added_file("T05-camera-on-cue.patch", "firmware/main/hal/maipai_cue_core.h")
    assert "config MAIPAI_CAMERA" not in text  # no Kconfig switch
    assert text.count("monitor_cue_begin(") >= 4  # declared, defined, photo, stream, and the test tool


def test_the_simulated_battery_step_never_powers_off():
    code = added_file("T01-low-battery-ladder.patch", "firmware/main/hal/maipai_daily.cc")
    sim = code.index("if (sim >= 0) {\n                ESP_LOGW(TAG, \"simulated 5 percent")
    real = code.index("hal_bridge::battery_power_off();")
    assert sim < real and "else {" in code[sim:real]
    assert code.count("battery_power_off()") == 1


def test_the_offline_tone_waits_three_minutes_and_skips_refused():
    core = added_file("T04-quiet-reconnect-offline-tone.patch", "firmware/main/hal/maipai_link_quiet_core.h")
    assert "180000u" in core and "!refused" in core
