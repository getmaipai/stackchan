"""Patch UX17, the question and answer game screens: the pure core is plain C and its host test runs here against the patch text; the patch is on ORDER with its header lines;
neither file calls the ESP or the hardware."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
NAME = "UX17-question-and-answer-game-screens.patch"


def _added(path: str) -> str:
    text = (PATCHES / NAME).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    out = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            out.append(line[1:])
    return "\n".join(out) + "\n"


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_the_core_test_passes_against_the_patch_text(tmp_path):
    (tmp_path / "maipai_qa_core.h").write_text(_added("firmware/main/hal/maipai_qa_core.h"))
    binary = tmp_path / "t"
    build = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{tmp_path}", str(HERE / "firmware" / "qa_core_test.c"), "-o", str(binary)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr


def test_the_patch_is_on_order_with_its_header_lines():
    assert NAME in (PATCHES / "ORDER").read_text().split()
    head = (PATCHES / NAME).read_text().split("diff --git", 1)[0]
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:"):
        assert key in head, f"{key} missing from the header of {NAME}"


def test_neither_file_calls_the_esp_or_the_hardware():
    for f in ("firmware/main/hal/maipai_qa_core.h", "firmware/main/hal/maipai_qa.h"):
        assert not re.search(r"esp_|nvs_|hal_bridge|Application|Board::", _added(f)), f"{f} must stay free of hardware calls so the host renderer compiles it"
