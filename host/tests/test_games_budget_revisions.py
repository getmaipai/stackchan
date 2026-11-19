"""The revisions the games budget asked for (docs/plan/games-visual-budget.md): Dice Poker drawn by one draw callback (patch UX18b) and Pong and the flyer invalidating only what moved (the dirty
rectangle functions in UX24 and UX25, checked in detail by their C core tests and, pixel by pixel, by the renderer's play runs). The patches wait on the branch ux/unproven-games for the bench."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / "firmware" / "patches"
UX18B = "UX18b-dice-poker-one-draw-callback.patch"
if not (PATCHES / UX18B).exists() or not (PATCHES / "UX24-pong.patch").exists():
    pytest.skip("the budget revisions are not in firmware/patches yet", allow_module_level=True)


def _added(name):
    return "\n".join(l[1:] for l in (PATCHES / name).read_text().splitlines() if l.startswith("+") and not l.startswith("+++"))


def test_dice_poker_follows_uX18_and_draws_everything_in_one_callback():
    order = (PATCHES / "ORDER").read_text().split()
    assert order.index(UX18B) > order.index("UX18-dice-poker.patch")
    head = (PATCHES / UX18B).read_text().split("diff --git", 1)[0]
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:"):
        assert key in head, key
    added = _added(UX18B)
    assert added.count("lv_obj_create(") == 2 and "lv_label_create" not in added   # the root and the one draw object
    assert "LV_EVENT_DRAW_MAIN" in added and "LV_EVENT_DELETE" in added            # it draws, and frees its copy of the state with the object


def test_pong_and_the_flyer_expose_their_dirty_rectangles_and_invalidate_only_them():
    pong, flyer = _added("UX24-pong.patch"), _added("UX25-flyer.patch")
    assert "pg_dirty(" in pong and "lv_obj_invalidate_area(" in pong and "invalidate_dirty" in pong
    assert "fl_dirty(" in flyer and "lv_obj_invalidate_area(" in flyer and "invalidate_dirty" in flyer
    assert "lv_obj_invalidate(court)" not in pong and "lv_obj_invalidate(sky)" not in flyer   # never the whole object


@pytest.mark.skipif(not (ROOT / ".runs" / "vu-screens" / "grid" / "grid_render").exists(), reason="the grid renderer is not built")
def test_the_games_own_dirty_rectangles_cover_every_changed_pixel():
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "virtual-unit" / "games_cost.py"), "--json"], capture_output=True, text=True, timeout=300).stdout
    rows = json.loads(out)
    for name in ("Pong (a rally)", "Flappy-style flyer (flying)"):
        if name not in rows or not rows[name]["dirty_px"]:
            pytest.skip(f"{name}: the renderer was built without the dirty rectangle functions")
        assert rows[name]["outside_dirty"] == 0, f"{name}: {rows[name]['outside_dirty']} changed pixels lay outside the rectangles the game invalidates"
    for name in ("Balance (a lean)", "Maze (a roll)"):
        if name in rows and rows[name]["dirty_px"]:
            assert rows[name]["outside_dirty"] == 0, f"{name}: {rows[name]['outside_dirty']} changed pixels lay outside the rectangles the game invalidates"
    # at the unit's measured 0.849 ms per 1,000 px (docs/plan/games-visual-budget.md): the motion rule allows a mean of 5.5 ms and a worst frame of 13.6 ms; Pong measures 0.8 and 1.1, the flyer 4.8 and 8.5
    assert rows["Pong (a rally)"]["flush_ms_dirty"] < 2.0 and rows["Flappy-style flyer (flying)"]["flush_ms_dirty"] < 5.5 and rows["Flappy-style flyer (flying)"]["flush_ms_dirty_worst"] < 13.6
