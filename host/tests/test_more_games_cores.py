"""Patches UX21 (Higher or Lower) and UX22 (Reversi): each pure core's host test runs here against the patch text; both patches are on ORDER with their header lines and neither file calls the
hardware. They wait on the branch ux/unproven-games for their bench proof (plain boot first); the tests skip while a patch is not in firmware/patches."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
GAMES = [
    ("UX21-higher-or-lower.patch", "hilo", ["maipai_hilo_core.h", "maipai_hilo.h"]),
    ("UX22-reversi.patch", "reversi", ["maipai_reversi_core.h", "maipai_reversi.h"]),
]


def _added(name: str, path: str) -> str:
    text = (PATCHES / name).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    out = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            out.append(line[1:])
    return "\n".join(out) + "\n"


@pytest.mark.parametrize("name,short,files", GAMES)
def test_the_core_test_passes_against_the_patch_text(name, short, files, tmp_path):
    if not (PATCHES / name).exists():
        pytest.skip(f"{name} is not in firmware/patches yet")
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    (tmp_path / files[0]).write_text(_added(name, f"firmware/main/hal/{files[0]}"))
    binary = tmp_path / "t"
    build = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", f"-I{tmp_path}", str(HERE / "firmware" / f"{short}_core_test.c"), "-o", str(binary)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr


@pytest.mark.parametrize("name,short,files", GAMES)
def test_the_patch_is_on_order_with_its_header_lines(name, short, files):
    if not (PATCHES / name).exists():
        pytest.skip(f"{name} is not in firmware/patches yet")
    assert name in (PATCHES / "ORDER").read_text().split()
    head = (PATCHES / name).read_text().split("diff --git", 1)[0]
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:"):
        assert key in head, f"{key} missing from the header of {name}"


@pytest.mark.parametrize("name,short,files", GAMES)
def test_neither_file_calls_the_esp_or_the_hardware(name, short, files):
    if not (PATCHES / name).exists():
        pytest.skip(f"{name} is not in firmware/patches yet")
    for f in files:
        assert not re.search(r"esp_|nvs_|hal_bridge|Application|Board::|malloc|calloc", _added(name, f"firmware/main/hal/{f}")), f"{f} must stay free of hardware calls so the host renderer compiles it"
