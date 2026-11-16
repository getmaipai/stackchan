"""The Train 3 mood core (firmware patch M01) is plain C: compile and run its test on the host, and check the rules the
patches must keep (the serial tool path is off by default; the mood has a switch and a header)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware/patches"
C_TEST = HERE / "firmware" / "mood_core_test.c"


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
def test_mood_core_c_test_passes(tmp_path):
    (tmp_path / "maipai_mood_core.h").write_text(
        added_file("M01-mood-from-care.patch", "firmware/main/hal/maipai_mood_core.h")
    )
    binary = tmp_path / "mood_test"
    build = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{tmp_path}", str(C_TEST), "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all passed" in run.stdout


def test_train3_patches_have_their_header_lines_and_are_on_order_in_order():
    order = (PATCHES / "ORDER").read_text().split()
    names = ["M01-mood-from-care.patch", "V01-serial-tool-path.patch"]
    assert order.index(names[0]) < order.index(names[1])
    for name in names:
        text = (PATCHES / name).read_text()
        for tag in ("# Intent:", "# Placement: unit (", "# Upstream:", "# Kconfig:"):
            assert tag in text, (name, tag)
        assert chr(8212) not in text


def test_the_serial_tool_path_is_off_by_default_and_only_built_when_on():
    text = (PATCHES / "V01-serial-tool-path.patch").read_text()
    block = text.split("config MAIPAI_SERIAL_TOOLS", 1)[1].split("help", 1)[0]
    assert "default n" in block
    source = added_file("V01-serial-tool-path.patch", "firmware/main/hal/maipai_serial_tools.cc")
    assert source.count("#if CONFIG_MAIPAI_SERIAL_TOOLS") == 1 and "usb_serial_jtag" in source
    assert source.index("#if CONFIG_MAIPAI_SERIAL_TOOLS") < source.index("usb_serial_jtag")


def test_the_mood_is_behind_its_switch_and_saves_rarely():
    text = (PATCHES / "M01-mood-from-care.patch").read_text()
    assert "config MAIPAI_MOOD" in text and "#if CONFIG_MAIPAI_MOOD" in text
    assert "15 * 60 * 1000" in text  # a write at most every 15 minutes
