"""Patch UXF01 (docs/design/face-styles.md): face styles as 44-byte recipes. The JSON sources and the .rcp files agree, every recipe reads on the unit's own reader and fits the face zone, and the
patch carries its header lines. The C test runs against the look core with the patch applied (the reference tree's file plus the patch's hunk), and skips with no C compiler or no tree."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STYLES = ROOT / "firmware" / "styles"
PATCH = ROOT / "firmware" / "patches" / "UXF01-face-style-recipes.patch"
if not PATCH.exists():
    pytest.skip("the face style recipe patch is not in firmware/patches yet", allow_module_level=True)


def _tree_header(tmp_path: Path) -> tuple[Path, Path] | None:
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "ref-tree.py")], capture_output=True, text=True, env={**__import__("os").environ})
    import os

    root = os.environ.get("MAIPAI_FW_TREE_ROOT") or (done.stdout.strip() if done.returncode == 0 else "")
    if not root:
        root = str(Path.home() / "esp" / "stackchan-rebuild" / "main-ref")
    src = Path(root) / "firmware" / "main" / "hal" / "maipai_look_core.h"
    if not src.exists():
        return None
    work = tmp_path / "tree" / "firmware" / "main" / "hal"
    work.mkdir(parents=True)
    shutil.copy(src, work / "maipai_look_core.h")
    if "ML_STYLE_RECIPE" not in src.read_text():
        text = PATCH.read_text()
        hunk = "diff --git " + text.split("diff --git ")[1].split("\ndiff --git ", 1)[0] + "\n"
        done = subprocess.run(["patch", "-p1", "-s", "-f"], input=hunk, cwd=tmp_path / "tree", capture_output=True, text=True)
        assert done.returncode == 0, done.stdout + done.stderr
        for later in ("UXF02-extended-moods.patch", "UXF03-cartoon-eyes.patch"):   # the later look core hunks build on the recipes patch, in order
            moods = ROOT / "firmware" / "patches" / later
            if not moods.exists():
                continue
            text = moods.read_text()
            hunk = "diff --git " + text.split("diff --git ")[1].split("\ndiff --git ", 1)[0] + "\n"
            done = subprocess.run(["patch", "-p1", "-s", "-f"], input=hunk, cwd=tmp_path / "tree", capture_output=True, text=True)
            assert done.returncode == 0, done.stdout + done.stderr
    return work, src.parent


def test_every_recipe_file_matches_its_json():
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "face-recipe.py"), "check"], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr


def test_the_recipes_are_the_owners_list():
    names = {p.stem for p in STYLES.glob("*.json")}
    assert {"round", "cat", "robot", "sleepy", "retro_pixel", "heart_eyes", "classic", "eyes_only", "hose", "neon"} <= names
    for p in STYLES.glob("*.json"):
        spec = json.loads(p.read_text())
        assert spec["name"] == p.stem and spec["title"] and spec["about"]
        assert p.with_suffix(".rcp").stat().st_size == 44 <= 256   # the style asset kind holds 256 bytes


def test_cartoon_recipe_color_bytes_and_old_recipes_unchanged():
    pal = ["white", "ice", "cream", "brown", "hazel", "green", "teal", "blue", "violet", "pink", "red", "coral", "amber", "gray", "ink"]
    data = (STYLES / "cartoon.rcp").read_bytes()
    assert len(data) == 44 and data[5] == 5
    assert data[14] == 0   # iris absent: the style's default
    assert data[15] == ((pal.index("pink") + 1) << 4) | (pal.index("white") + 1) == 0xA1
    for p in STYLES.glob("*.rcp"):
        if p.stem != "cartoon":
            assert p.read_bytes()[14:16] == b"\0\0", p.name


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_the_core_test_passes_on_every_recipe(tmp_path):
    found = _tree_header(tmp_path)
    if found is None:
        pytest.skip("no reference firmware tree on this machine")
    hal, tree_hal = found
    binary = tmp_path / "t"
    build = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", f"-I{hal}", f"-I{tree_hal}", str(HERE / "firmware" / "face_recipe_core_test.c"), "-o", str(binary), "-lm"], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary), *map(str, sorted(STYLES.glob("*.rcp")))], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr
    look = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", f"-I{hal}", f"-I{tree_hal}", str(HERE / "firmware" / "look_core_test.c"), "-o", str(tmp_path / "look"), "-lm"], capture_output=True, text=True)
    assert look.returncode == 0, look.stderr
    base = subprocess.run([str(tmp_path / "look")], capture_output=True, text=True, timeout=60)
    assert base.returncode == 0, base.stdout + base.stderr   # the base styles draw as before


def test_the_patch_has_its_header_lines_and_no_dashes():
    text = PATCH.read_text()
    head = text.split("diff --git", 1)[0]
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:", "# Memory cost:"):
        assert key in head, key
    assert chr(8212) not in text


def test_the_moods_patch_has_its_header_lines_and_names_the_five():
    path = ROOT / "firmware" / "patches" / "UXF02-extended-moods.patch"
    if not path.exists():
        pytest.skip("the extended moods patch is not in firmware/patches yet")
    text = path.read_text()
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:", "# Memory cost:"):
        assert key in text.split("diff --git", 1)[0], key
    for name in ("ML_JOY", "ML_EXCITED", "ML_SHOCKED", "ML_CURIOUS", "ML_WORRIED"):
        assert name in text
    assert chr(8212) not in text


def test_the_color_table_of_the_cartoon_patch_matches_the_recipe_script():
    path = ROOT / "firmware" / "patches" / "UXF03-cartoon-eyes.patch"
    if not path.exists():
        pytest.skip("the cartoon eyes patch is not in firmware/patches yet")
    import importlib.util
    import re

    spec = importlib.util.spec_from_file_location("face_recipe", ROOT / "scripts" / "face-recipe.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    line = next(l for l in path.read_text().splitlines() if "ML_PAL_NAMES[ML_PAL_COUNT]" in l)
    names = re.findall(r'"([a-z]+)"', line)
    assert names[0] == "default" and names[1:] == list(mod.PAL)   # one list: the firmware table and the script agree
    head = path.read_text().split("diff --git", 1)[0]
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:", "# Memory cost:"):
        assert key in head, key
    assert chr(8212) not in path.read_text()
