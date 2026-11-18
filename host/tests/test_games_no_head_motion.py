"""Owner rule (2026-11-18): a game never moves the head. No line a patch adds to the game player, the game engine or the grid engine may call the head's motion, a servo or the
torque. Reads every patch of firmware/patches/ORDER, so a later patch cannot add one quietly."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / "firmware" / "patches"
FILES = re.compile(r"^diff --git a/firmware/main/hal/(maipai_games\w*|maipai_grid\w*)\.(cc|h)\b")
FORBIDDEN = re.compile(r"motion\(\)|moveWithSpeed|moveWithSpringParams|GetStackChan|yawServo|pitchServo|setTorque|EnableTorque|op_head|maipai_dance_play|stackchan/motion")


def _violations() -> list[str]:
    bad: list[str] = []
    for name in (PATCHES / "ORDER").read_text().split():
        path = PATCHES / name
        if not path.exists() or not name.endswith(".patch"):
            continue
        current = None
        for line in path.read_text(errors="replace").splitlines():
            if line.startswith("diff --git"):
                m = FILES.match(line)
                current = m.group(1) if m else None
            elif current and line.startswith("+") and not line.startswith("+++"):
                text = line[1:].split("//")[0]
                if FORBIDDEN.search(text):
                    bad.append(f"{name}: {current}: {line[1:].strip()}")
    return bad


def test_no_game_or_grid_patch_moves_the_head():
    assert _violations() == [], "a game file calls the head's motion; games never move the head (owner rule, 2026-11-18)"


def test_the_lint_sees_a_violation():
    # the pattern itself: a line that must be caught
    assert FORBIDDEN.search("GetStackChan().motion().yawServo().moveWithSpeed(0, 100);")
    assert not FORBIDDEN.search("maipai_games_post_input(MAIPAI_GAME_EV_PET);")
