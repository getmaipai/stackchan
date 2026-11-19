"""The data-pack games drawn by ONE draw callback (patch UX29, docs/plan/games-pack-engine.md): three LVGL objects a screen on every pack instead of 15 to 87, and the same pixels as the
drawing before it. The renderer checks need games_render built from a tree that holds UX29 (scripts/virtual-unit/build-screens.sh); they skip otherwise. The patch waits on the branch
ux/unproven-games for the bench."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / "firmware" / "patches"
UX29 = "UX29-pack-engine-one-draw-callback.patch"
RENDER = ROOT / ".runs" / "vu-screens" / "games" / "games_render"
PROOF = ROOT / "scripts" / "virtual-unit" / "packs_pixel_proof.py"
PACKS = ["tictactoe", "whack", "bopit", "eightball", "dice", "memory", "rps"]
if not (PATCHES / UX29).exists():
    pytest.skip("the pack engine patch is not in firmware/patches yet", allow_module_level=True)


def _added():
    return "\n".join(l[1:] for l in (PATCHES / UX29).read_text().splitlines() if l.startswith("+") and not l.startswith("+++"))


def _built_with_ux29():
    if not RENDER.exists():
        return False
    out = subprocess.run([str(RENDER)], input="load firmware/games/memory.mpk\nstate 0\ndraw\nobjcount\n", capture_output=True, text=True, cwd=ROOT).stdout
    return " nodes " in out


def test_patch_follows_the_draw_patches_and_has_its_header():
    order = (PATCHES / "ORDER").read_text().split()
    assert order.index(UX29) > order.index("GM05-games-draw-icons-pop-and-bump.patch")
    head = (PATCHES / UX29).read_text().split("diff --git", 1)[0]
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:"):
        assert key in head, key


def test_patch_makes_one_canvas_object_and_no_object_per_shape():
    added = _added()
    assert added.count("lv_obj_create(") == 1                         # the canvas; the drag bar (already there) is the other
    assert "lv_label_create(" not in added and "lv_line_create(" not in added
    assert "LV_EVENT_DRAW_MAIN" in added and "LV_EVENT_DELETE" in added   # it draws, and frees the block with the object
    assert "lv_obj_invalidate_area(" in added and "lv_obj_invalidate(" not in added.replace("lv_obj_invalidate_area(", "")   # only what changed, never the whole canvas
    assert "malloc(" in added and "lv_free(" in added                  # one block, freed with the canvas
    assert not re.search(r"(?<!lv_)(malloc|free)\(", added)           # LVGL's allocator only (host/tests/test_more_games_cores.py holds the games to it)


@pytest.mark.skipif(not _built_with_ux29(), reason="games_render is not built from a tree with UX29")
def test_every_pack_screen_is_three_objects():
    shapes = {"tictactoe": 46, "whack": 64, "bopit": 44, "eightball": 47, "dice": 49, "memory": 15, "rps": 87}   # what the drawing before UX29 made
    for pack in PACKS:
        n_states = len(json.loads((ROOT / "firmware" / "games" / f"{pack}.json").read_text())["states"])
        cmds = [f"load firmware/games/{pack}.mpk", "lang en"] + [c for s in range(n_states) for c in (f"state {s}", "draw", "objcount")]
        out = subprocess.run([str(RENDER)], input="\n".join(cmds) + "\n", capture_output=True, text=True, cwd=ROOT).stdout
        counts = [int(l.split()[1]) for l in out.splitlines() if l.startswith("objects")]
        assert counts and max(counts) == 3, f"{pack}: {max(counts)} objects, expected 3 (it was {shapes[pack]})"


@pytest.mark.skipif(not _built_with_ux29(), reason="games_render is not built from a tree with UX29")
def test_pixels_are_the_pixels_of_the_drawing_before_the_patch():
    done = subprocess.run([sys.executable, str(PROOF), "--check-digests", str(ROOT / "host" / "tests" / "golden" / "pack_games_digests.json"), str(RENDER)],
                          capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.skipif(not _built_with_ux29(), reason="games_render is not built from a tree with UX29")
def test_a_partial_refresh_shows_every_change():
    done = subprocess.run([sys.executable, str(PROOF), str(RENDER), str(RENDER), "--partial", "--scenes", "25"], capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stdout[-1500:] + done.stderr[-500:]
