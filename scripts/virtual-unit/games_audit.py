#!/usr/bin/env python3
"""The screen audit for the data-pack games (Color Memory, Whack-a-Mole, Tic-Tac-Toe, Do It, Rock Paper Scissors, Magic 8 Ball, Dice and Coin): the touch regions of every pack, listed by the
games renderer (`targets`), judged against the physical standard (scripts/virtual-unit/screen_standard.py). A board (cells that touch each other, six or more) is judged by the board rule of
docs/design/screen-style.md: each cell at least 24 px, the board as a whole 8 px from any other target; every other region follows the ordinary rules (48 px fails, 56 px warns, 8 px gaps).
Usage: games_audit.py [--write]   --write writes docs/dev/games-audit.json and docs/dev/games-audit.md. Needs the games renderer (bash scripts/virtual-unit/build-screens.sh).
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import screen_audit as sa  # noqa: E402
import screen_standard as std  # noqa: E402

RENDER = ROOT / ".runs" / "vu-screens" / "games" / "games_render"
PACKS = ROOT / "firmware" / "games"
BOARD_MIN_CELL = 24


def regions(pack: Path) -> list[dict]:
    out = subprocess.run([str(RENDER)], input=f"load {pack}\ntargets\n", capture_output=True, text=True, check=True).stdout
    targets, _ = sa.parse(out.splitlines())
    return targets


def touching(a: dict, b: dict) -> bool:
    gx = max(a["x1"], b["x1"]) - min(a["x2"], b["x2"]) - 1
    gy = max(a["y1"], b["y1"]) - min(a["y2"], b["y2"]) - 1
    return (gx <= 2 and gy < 0) or (gy <= 2 and gx < 0)


def split_board(ts: list[dict]) -> tuple[list[dict], list[dict]]:
    """Cells that touch another cell of the same size are a board when there are six or more."""
    cell = [t for t in ts if any(touching(t, o) for o in ts if o is not t)]
    return (cell, [t for t in ts if t not in cell]) if len(cell) >= 6 else ([], ts)


def audit_pack(pack: Path) -> dict:
    ts = regions(pack)
    board, rest = split_board(ts)
    fails, warns = [], []
    if board:
        x1, y1, x2, y2 = min(c["x1"] for c in board), min(c["y1"] for c in board), max(c["x2"] for c in board), max(c["y2"] for c in board)
        small = [c for c in board if min(c["x2"] - c["x1"] + 1, c["y2"] - c["y1"] + 1) < BOARD_MIN_CELL]
        fails += [f"board cell {c['x2'] - c['x1'] + 1}x{c['y2'] - c['y1'] + 1} at {c['x1']},{c['y1']}: under {BOARD_MIN_CELL} px" for c in small]
        box = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "own": [x1, y1, x2, y2], "scroll": 0}
        for o in rest:
            gx = max(box["x1"], o["x1"]) - min(box["x2"], o["x2"]) - 1
            gy = max(box["y1"], o["y1"]) - min(box["y2"], o["y2"]) - 1
            if (gx < std.GAP_PX and gy < std.GAP_PX) and not (gx >= std.GAP_PX or gy >= std.GAP_PX):
                fails.append(f"a target at {o['x1']},{o['y1']} is {max(gx, gy)} px from the board (under {std.GAP_PX})")
    verdict = sa.judge(rest, []) if rest else {"fails": [], "warnings": []}
    fails += verdict["failures"] if "failures" in verdict else verdict.get("fails", [])
    warns += verdict["warnings"] if "warnings" in verdict else verdict.get("warns", [])
    cell_w = (board[0]["x2"] - board[0]["x1"] + 1, board[0]["y2"] - board[0]["y1"] + 1) if board else None
    return {"regions": len(ts), "board_cells": len(board), "board_cell_px": cell_w, "targets": len(rest), "fails": len(fails), "warnings": len(warns), "failures": fails, "warns": warns}


def main() -> int:
    if not RENDER.exists():
        print("the games renderer is not built: run bash scripts/virtual-unit/build-screens.sh first", file=sys.stderr)
        return 2
    report = {p.stem: audit_pack(p) for p in sorted(PACKS.glob("*.mpk"))}
    total = sum(r["fails"] for r in report.values())
    print(f"games audit: {len(report)} packs, {total} failures, {sum(r['warnings'] for r in report.values())} warnings")
    for name, r in report.items():
        print(f"  {name}: {r['regions']} regions" + (f", a board of {r['board_cells']} cells of {r['board_cell_px'][0]}x{r['board_cell_px'][1]}" if r["board_cells"] else "") + f", {r['fails']} failures, {r['warnings']} warnings")
        for f in r["failures"][:4]:
            print("     " + f)
    if "--write" in sys.argv:
        (ROOT / "docs" / "dev" / "games-audit.json").write_text(json.dumps(report, indent=1) + "\n")
        lines = ["# Screen audit of the data-pack games", "", "Made by `scripts/virtual-unit/games_audit.py --write` from the touch regions of each pack (the games renderer's `targets` command). A board (six or more cells that touch) follows the board rule of `docs/design/screen-style.md`: every cell at least 24 px, the board as a whole 8 px from any other target. Other regions follow the ordinary rules.", "", "| Pack | Regions | Board | Failures | Warnings |", "|---|---:|---|---:|---:|"]
        for name, r in report.items():
            lines.append(f"| {name} | {r['regions']} | " + (f"{r['board_cells']} cells of {r['board_cell_px'][0]} x {r['board_cell_px'][1]} px" if r["board_cells"] else "none") + f" | {r['fails']} | {r['warnings']} |")
        (ROOT / "docs" / "dev" / "games-audit.md").write_text("\n".join(lines) + "\n")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
