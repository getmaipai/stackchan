"""The reset core (firmware patch R01) is plain C: compile and run its test on the host, and check the patch
keeps the rules that make the reset safe."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCH = HERE.parents[1] / "firmware/patches/R01-reset-on-device.patch"
C_TEST = HERE / "firmware" / "reset_core_test.c"


def _added_file(path: str) -> str:
    text = PATCH.read_text()
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
def test_reset_core_c_tests_pass(tmp_path):
    (tmp_path / "maipai_reset_core.h").write_text(_added_file("firmware/main/hal/maipai_reset_core.h"))
    binary = tmp_path / "reset_test"
    build = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{tmp_path}", str(C_TEST), "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all passed" in run.stdout


def test_the_clear_is_marked_first_and_finished_on_the_next_boot():
    code = _added_file("firmware/main/hal/maipai_reset.cc")
    code = code[code.index("void reset_task"):]
    assert code.index("set_mark(true)") < code.index("erase_settings()") < code.index("set_mark(false)")
    assert "maipai_reset_resume" in _added_file("firmware/main/hal/maipai_reset.h")
    assert "maipai_reset_resume();" in PATCH.read_text()


def test_only_the_screen_starts_it():
    text = PATCH.read_text()
    assert text.count("maipai_reset_start()") == 3  # the header, the definition, the screen's one call
    assert "mcp" not in _added_file("firmware/main/hal/maipai_reset.cc").lower()
