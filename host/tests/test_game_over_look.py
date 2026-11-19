"""Patch UX15d, the new look of the shared game-over screen (docs/design/game-over-look.md): the pure core's host test runs here against the patch text (the series UX15, SF82, UX15c, UX15d applied in order);
the patch carries its header lines, makes two objects, keeps the callers' calls; the renderer checks (words fit, two objects, no pixel outside the dirty rectangles, today's look unchanged) need the screens
renderer built from a tree that has UX15d and skip otherwise. The patch waits on the branch ux/unproven-games for the bench."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATCHES = ROOT / "firmware" / "patches"
NAME = "UX15d-game-over-look.patch"
SERIES = ["UX15-shared-game-over-screen.patch", "SF82-grid-games-end-on-the-shared-game-over-screen.patch", "UX15c-game-over-neutral-end-after-sf82.patch", NAME]
GRID = ROOT / ".runs" / "vu-screens" / "grid" / "grid_render"
if not (PATCHES / NAME).exists():
    pytest.skip("the game-over look patch is not in firmware/patches yet", allow_module_level=True)


def _added_new_file(name: str, path: str) -> str:
    text = (PATCHES / name).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    out = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            out.append(line[1:])
    return "\n".join(out) + "\n"


def _added() -> str:
    return "\n".join(l[1:] for l in (PATCHES / NAME).read_text().splitlines() if l.startswith("+") and not l.startswith("+++"))


def _tree(tmp_path: Path) -> Path:
    tree = tmp_path / "tree"
    hal = tree / "firmware" / "main" / "hal"
    hal.mkdir(parents=True)
    for f in ("maipai_game_over_core.h", "maipai_game_over.h"):
        (hal / f).write_text(_added_new_file(SERIES[0], f"firmware/main/hal/{f}"))
    for name in SERIES[1:]:
        text = (PATCHES / name).read_text()
        keep = [b for b in text.split("diff --git ")[1:] if b.split(" ", 1)[0] in ("a/firmware/main/hal/maipai_game_over_core.h", "a/firmware/main/hal/maipai_game_over.h")]
        done = subprocess.run(["patch", "-p1", "-s", "-f", "-N"], input="".join("diff --git " + b for b in keep), cwd=tree, capture_output=True, text=True)
        assert done.returncode == 0, name + done.stdout + done.stderr
    return hal


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_the_core_test_passes_against_the_series(tmp_path):
    hal = _tree(tmp_path)
    shutil.copy(hal / "maipai_game_over_core.h", tmp_path / "maipai_game_over_core.h")
    binary = tmp_path / "t"
    build = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", f"-I{tmp_path}", str(HERE / "firmware" / "game_over_look_core_test.c"), "-o", str(binary)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr


def test_the_patch_is_last_in_order_after_the_game_over_patches_with_its_header_lines():
    order = (PATCHES / "ORDER").read_text().split()
    assert all(order.index(a) < order.index(b) for a, b in zip(SERIES, SERIES[1:]))
    head = (PATCHES / NAME).read_text().split("diff --git", 1)[0]
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:"):
        assert key in head, key


def test_the_new_look_is_one_canvas_and_the_callers_do_not_change():
    added = _added()
    assert added.count("lv_obj_create(") == 2                       # the root and the canvas (the old look's own objects stay as the dead branch at look 0)
    assert "LV_EVENT_DRAW_MAIN" in added and "LV_EVENT_DELETE" in added and "lv_obj_invalidate_area(" in added
    assert not re.search(r"(?<!lv_)(malloc|free)\(", added) and not re.search(r"esp_|nvs_|hal_bridge|Application|Board::", re.sub(r"esp_timer_get_time|esp_heap", "", added.split("self.game.bench_over")[0]))
    files = re.findall(r"^diff --git a/(\S+) b/", (PATCHES / NAME).read_text(), re.M)
    assert files == ["firmware/main/hal/maipai_game_over_core.h", "firmware/main/hal/maipai_game_over.h", "firmware/main/hal/maipai_grid.cc"]   # games.cc, grid.cc's game code and qa_game.cc are untouched
    assert "MGO_LOOK_DEFAULT 0" in added                            # a normal image keeps today's screen until the bench decides
    assert "self.game.bench_over" in added                          # the bench tool


def _built():
    return GRID.exists() and "word title" in subprocess.run([str(GRID)], input="game c4 3\noverwidths\n", capture_output=True, text=True, cwd=ROOT).stdout


@pytest.mark.skipif(not _built(), reason="the grid renderer is not built from a tree with UX15d")
def test_every_word_fits_in_every_language():
    out = subprocess.run([str(GRID)], input="game c4 3\noverwidths\n", capture_output=True, text=True, cwd=ROOT).stdout
    rows = [l.split() for l in out.splitlines() if l.startswith("word ")]
    assert len(rows) == 6 * 8
    limits = {"title": 296, "button": 148 - 24, "newbest": 200}   # a title across the glass with a margin, a label inside a 148 px button with 12 px each side, a chip label
    for _, kind, lang, width in rows:
        assert int(width) <= limits[kind], f"{kind} in {lang} is {width} px wide (limit {limits[kind]}): shorten the word"


@pytest.mark.skipif(not _built(), reason="the grid renderer is not built from a tree with UX15d")
def test_the_new_look_is_two_objects_and_the_old_look_is_unchanged_in_count():
    def objs(look):
        out = subprocess.run([str(GRID)], input=f"game c4 3\nover won|Score 66|Best 70|0|en|{look}\nobjcount\n", capture_output=True, text=True, cwd=ROOT).stdout
        return int([l.split()[1] for l in out.splitlines() if l.startswith("objects")][0])
    base = objs(0) - 0
    # objcount counts the game board too: the screens differ only by what the game-over screen adds
    out = subprocess.run([str(GRID)], input="game c4 3\nobjcount\n", capture_output=True, text=True, cwd=ROOT).stdout
    game = int([l.split()[1] for l in out.splitlines() if l.startswith("objects")][0])
    assert objs(1) - game == 2 and objs(2) - game == 2 and base - game >= 9


@pytest.mark.skipif(not _built(), reason="the grid renderer is not built from a tree with UX15d")
def test_no_pixel_changes_outside_the_rectangles_the_screen_invalidates():
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "virtual-unit" / "games_cost.py"), "--json"], capture_output=True, text=True, timeout=300).stdout
    import json
    rows = json.loads(out)
    names = [n for n in rows if n.startswith("Game over, new look")]
    assert len(names) == 5
    for n in names:
        assert rows[n]["outside_dirty"] == 0, f"{n}: {rows[n]['outside_dirty']} changed pixels lay outside the rectangles the screen invalidates"
        assert rows[n]["dirty_px"] <= 6500 and rows[n]["dirty_px_max"] <= 16000, n   # the motion rule: mean and worst dirty area of a frame (docs/plan/games-visual-budget.md, section 4)
