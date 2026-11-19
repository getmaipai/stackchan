#!/usr/bin/env python3
# Intent: the screenshots for the user docs come from the virtual unit's golden frames (real LVGL drawing of the unit's own screen code, made by scripts/virtual-unit/scenarios.py and checked by the tests), never drawn by hand. This script copies the chosen frames to docs/images/vu-NAME.png, so a screen change that updates a golden frame updates the docs picture on the next run.
# Usage: python3 scripts/make-vu-screenshots.py          write the pictures
#        python3 scripts/make-vu-screenshots.py --check   exit 1 when a picture differs from its frame (run by scripts/check.sh)
# The page, the caption and the target doc of each picture are in docs/plan/doc-screenshots.md.
# Placement: docs tooling. Upstream: none.
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "host" / "tests" / "golden" / "screens"
OUT = ROOT / "docs" / "images"
PICTURES = {
    "control-sheet": "screen-control-sheet.png",
    "first-run-language": "first-run-1-en.png",
    "first-run-name": "first-run-2-en.png",
    "first-run-mode": "first-run-4-en.png",
    "first-run-done": "first-run-6-en.png",
    "pairing": "cover-pairing.png",
    "lock-screen": "lock-screen.png",
    "lock-keypad": "lock-keypad-three.png",
    "lock-wrong": "lock-keypad-wrong.png",
    "clock": "screen-page-clock.png",
    "timers": "screen-page-timers.png",
    "games": "screen-games-wall.png",
    "settings-general": "screen-settings-general.png",
    "update": "cover-update-62.png",
    "offline-line": "offline-line-cannot-reach-home-en.png",
    "four-in-a-row": "game-c4-playing.png",
    "game-over": "game-over-c4-win.png",
    "question-game": "game-trivia-ask.png",
    "mumble": "mumble-mouth-sync.png",
}


def main() -> int:
    check = "--check" in sys.argv
    wrong = []
    for name, frame in PICTURES.items():
        src, dst = GOLDEN / frame, OUT / f"vu-{name}.png"
        if not src.is_file():
            wrong.append(f"{frame}: the golden frame does not exist. Run scripts/virtual-unit/scenarios.py --update.")
        elif check:
            if not dst.is_file() or dst.read_bytes() != src.read_bytes():
                wrong.append(f"docs/images/vu-{name}.png is out of date with {frame}. Run python3 scripts/make-vu-screenshots.py.")
        else:
            shutil.copyfile(src, dst)
    for line in wrong:
        print(line)
    if check:
        print("vu-screenshots: ok" if not wrong else f"vu-screenshots: {len(wrong)} problem(s)")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
