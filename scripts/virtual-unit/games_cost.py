#!/usr/bin/env python3
"""Frame cost of every game from the host renderer (docs/plan/games-visual-budget.md): for a run of each game, how much of the glass changes from one frame to the next, as pixels changed and as the
area of the bounding box of the change (what a flush of only the changed rectangle costs). The unit's cost is taken from the box times the bench measured on the unit (2026-11-19, self.game.bench_box,
a 100 by 100 pixel box drawn and flushed): a flat box takes 7,329 microseconds on the b85 bench (8,490 on the b80 bench), so 0.733 ms per 1,000 pixels, draw and flush together (a full 320 by 240 screen is about 56 ms). The first figure used
here, 0.39 ms per 1,000 pixels, came from a 30 ms full-screen flush that the bench did not confirm. Each technique costs its own multiple of the flat box (UNIT_BOX_US).
Two models of the flush: only the 16 by 16 pixel tiles that changed (several small dirty rectangles, what SF78 does for the grid games), or one rectangle round everything that changed. The renderer's host
milliseconds do not carry over to the chip. Usage: games_cost.py [--json]. Placement: host-side development tool. Upstream: none."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRID = ROOT / ".runs" / "vu-screens" / "grid" / "grid_render"
# Measured on the unit, microseconds to draw and flush one 100 by 100 pixel box (bench b85, 2026-11-19): the K of every estimate in the budget.
UNIT_BOX_US = {"flat": 7329, "radius": 7400, "circle": 9300, "gradient": 9000, "shadow-small": 14300, "shadow": 21800, "alpha": 9700, "outline": 10500}   # b85 bench (the b80 bench was 8490, 9075, 9879, 9317, 13182, 20875, 9798, 10133)
MS_PER_PIXEL = UNIT_BOX_US["flat"] / 1000.0 / 10000.0   # 0.000733 ms a pixel: 56 ms for a full screen

RUNS = {
    "Four in a Row (a disc falls)": ["game c4 3", "diffbegin", "drop 3 1", "advance 700", "drop 4 2", "advance 700", "diffend c4"],
    "Match (two cards flip)": ["game match 2", "diffbegin", "tap 0", "advance 400", "tap 5", "advance 1300", "diffend match"],
    "Hangman (a letter)": ["game hangman 4", "diffbegin", "tap 4", "advance 300", "tap 17", "advance 300", "diffend hangman"],
    "Mine Finder (a reveal)": ["game mines 3", "diffbegin", "tap 20", "advance 300", "tap 40", "advance 300", "diffend mines"],
    "Snake (it moves)": ["game snake 9", "advance 100", "diffbegin", "advance 3000", "diffend snake"],
    "2048 (two swipes)": ["game slide 5", "advance 100", "diffbegin", "swipe 250 120 60 125 180", "advance 400", "swipe 160 210 165 40 180", "advance 400", "diffend slide"],
    "Dice Poker (a roll)": [],   # static screens: measured from two states below
    "Higher or Lower (a turn)": ["game c4 3", "diffbegin", "play hilo 5 12", "diffend hilo"],
    "Reversi (a game)": ["game c4 3", "diffbegin", "play reversi 3", "diffend reversi"],
    "Battleship-lite (shots)": ["game c4 3", "diffbegin", "play battleship 3 12", "diffend battleship"],
    "Pong (a rally)": ["game c4 3", "diffbegin", "play pong 400 18", "diffend pong"],
    "Balance (a lean)": ["game c4 3", "diffbegin", "play balance 4 900", "diffend balance"],
    "Maze (a roll)": ["game c4 3", "diffbegin", "play maze 4 700", "diffend maze"],
    "Game over, today's (won)": ["game c4 3", "diffbegin", "play over won 0 0 1800", "diffend gover0"],
    "Game over, new look (won, confetti)": ["game c4 3", "diffbegin", "play over won 0 2 1800", "diffend gover_won"],
    "Game over, new look (lost, rain)": ["game c4 3", "diffbegin", "play over lost 0 2 1800", "diffend gover_lost"],
    "Game over, new look (draw)": ["game c4 3", "diffbegin", "play over draw 0 2 1800", "diffend gover_draw"],
    "Game over, new look (new best)": ["game c4 3", "diffbegin", "play over won 1 2 1800", "diffend gover_nb"],
    "Game over, new look (time's up)": ["game c4 3", "diffbegin", "play over timeup 0 2 1800", "diffend gover_time"],
    "Flappy-style flyer (flying)": ["game c4 3", "diffbegin", "play flyer 4 600", "diffend flyer"],
}
LINE = re.compile(r"cost (\S+) frames (\d+) changed_px (\d+) bbox_px (\d+) bbox_px_max (\d+) tile_px (\d+) tile_px_max (\d+)(?: outside_dirty (\d+) dirty_px (\d+) dirty_px_max (\d+))?")


def run(commands):
    cmds = [c for c in commands if c != "play_start"]
    out = subprocess.run([str(GRID)], input="\n".join(cmds) + "\n", capture_output=True, text=True, timeout=300).stdout
    for line in out.splitlines():
        m = LINE.match(line)
        if m:
            return {"frames": int(m.group(2)), "changed_px": int(m.group(3)), "bbox_px": int(m.group(4)), "bbox_px_max": int(m.group(5)), "tile_px": int(m.group(6)), "tile_px_max": int(m.group(7)), "outside_dirty": int(m.group(8) or 0), "dirty_px": int(m.group(9) or 0), "dirty_px_max": int(m.group(10) or 0)}
    return None


def main() -> int:
    rows = {}
    for name, cmds in RUNS.items():
        if not cmds:
            continue
        r = run(cmds)
        if r is None:
            print(f"no reading for {name} (this firmware tree has not got the game)")
            continue
        r["flush_ms_mean"] = round(r["tile_px"] * MS_PER_PIXEL, 1)        # only the 16 by 16 tiles that changed are flushed (several small dirty rectangles)
        r["flush_ms_worst"] = round(r["tile_px_max"] * MS_PER_PIXEL, 1)
        r["flush_ms_one_rect"] = round(r["bbox_px"] * MS_PER_PIXEL, 1)    # one rectangle round everything that changed
        r["flush_ms_dirty"] = round(r["dirty_px"] * MS_PER_PIXEL, 1)      # the rectangles the game itself invalidates (Pong and the flyer: pg_dirty and fl_dirty), 0 where the game has none yet
        r["flush_ms_dirty_worst"] = round(r["dirty_px_max"] * MS_PER_PIXEL, 1)
        rows[name] = r
    if "--json" in sys.argv:
        print(json.dumps(rows, indent=1))
        return 0
    print("| Game | Frames | Pixels changed per frame | Tiles flushed per frame (px) | Flush ms (mean) | Flush ms (worst frame) | One rectangle, ms (mean) | The game's own dirty rectangles, ms (mean / worst) | Pixels changed outside them |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for n, r in rows.items():
        print(f"| {n} | {r['frames']} | {r['changed_px']:,} | {r['tile_px']:,} | {r['flush_ms_mean']} | {r['flush_ms_worst']} | {r['flush_ms_one_rect']} | {(str(r['flush_ms_dirty']) + ' / ' + str(r['flush_ms_dirty_worst'])) if r['dirty_px'] else 'none yet'} | {r['outside_dirty'] if r['dirty_px'] else '-'} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
