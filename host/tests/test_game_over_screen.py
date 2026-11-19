"""Patch UX15, the shared game-over screen: its pure core is plain C and its host test runs here against the patch text; the patch is on ORDER
and carries its header lines; the screen is two header-only files the host renderer compiles too (no ESP call in either)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
NAME = "UX15-shared-game-over-screen.patch"
NAME_B = "UX15c-game-over-neutral-end-after-sf82.patch"
NAME_MID = "SF82-grid-games-end-on-the-shared-game-over-screen.patch"   # changes the header between UX15 and UX15c


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
    tree = tmp_path / "tree"
    (tree / "firmware" / "main" / "hal").mkdir(parents=True)
    core = tree / "firmware" / "main" / "hal" / "maipai_game_over_core.h"
    core.write_text(_added("firmware/main/hal/maipai_game_over_core.h"))
    (tree / "firmware" / "main" / "hal" / "maipai_game_over.h").write_text(_added("firmware/main/hal/maipai_game_over.h"))
    # SF82 changes the header after UX15 and UX15c changes both files after SF82: apply them in series order, the same patches the unit gets, before testing
    for name in (NAME_MID, NAME_B):
        text = (PATCHES / name).read_text()
        keep = [b for b in text.split("diff --git ")[1:] if b.split(" ", 1)[0] in ("a/firmware/main/hal/maipai_game_over_core.h", "a/firmware/main/hal/maipai_game_over.h")]
        done = subprocess.run(["patch", "-p1", "-s", "-f", "-N"], input="".join("diff --git " + b for b in keep), cwd=tree, capture_output=True, text=True)
        assert done.returncode == 0, name + done.stdout + done.stderr
    shutil.copy(core, tmp_path / "maipai_game_over_core.h")
    binary = tmp_path / "t"
    build = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{tmp_path}", str(HERE / "firmware" / "game_over_core_test.c"), "-o", str(binary)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr


def test_the_patch_is_on_order_with_its_header_lines():
    order = (PATCHES / "ORDER").read_text().split()
    assert NAME in order and order.index(NAME_B) > order.index(NAME_MID) > order.index(NAME)
    head = (PATCHES / NAME).read_text().split("diff --git", 1)[0]
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:"):
        assert key in head, f"{key} missing from the header of {NAME}"


def test_neither_file_calls_the_esp_or_the_hardware():
    for f in ("firmware/main/hal/maipai_game_over_core.h", "firmware/main/hal/maipai_game_over.h"):
        text = _added(f)
        assert not re.search(r"esp_|nvs_|hal_bridge|Application|Board::", text), f"{f} must stay free of hardware calls so the host renderer compiles it"
