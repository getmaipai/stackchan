"""The screen audit of the data-pack games (scripts/virtual-unit/games_audit.py): the failures of each pack may only shrink (docs/design/games-audit-baseline.json) and a new pack must have none.
Needs the games renderer (bash scripts/virtual-unit/build-screens.sh)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "virtual-unit"))

pytestmark = pytest.mark.skipif(not (ROOT / ".runs" / "vu-screens" / "games" / "games_render").exists(), reason="games renderer not built")


def test_no_pack_gets_worse_and_a_new_pack_has_no_failures():
    import games_audit as ga
    base = json.loads((ROOT / "docs" / "design" / "games-audit-baseline.json").read_text())
    bad = []
    for pack in sorted(ga.PACKS.glob("*.mpk")):
        got = ga.audit_pack(pack)["fails"]
        if got > base.get(pack.stem, {"fails": 0})["fails"]:
            bad.append(f"{pack.stem}: {got} failures, baseline {base.get(pack.stem, {'fails': 0})['fails']}")
    assert not bad, "the games audit got worse: " + "; ".join(bad) + ". Fix the layout (docs/dev/games-audit.md lists the regions) or, for a board, follow the board rule."


def test_the_boards_follow_the_board_rule():
    import games_audit as ga
    for name in ("tictactoe", "whack"):
        r = ga.audit_pack(ga.PACKS / f"{name}.mpk")
        assert r["board_cells"] == 9 and min(r["board_cell_px"]) >= ga.BOARD_MIN_CELL and r["fails"] == 0, name
