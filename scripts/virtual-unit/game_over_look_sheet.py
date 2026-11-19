#!/usr/bin/env python3
"""The two pictures of docs/design/game-over-look.md, made from the goldens (needs ffmpeg): before and after (today's screen, look 0, above the new look), and the rest of the new look (a new best, Game over,
Time's up, and the words in French, German and Portuguese). Usage: game_over_look_sheet.py. Placement: host-side development tool. Upstream: none."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
G = ROOT / "host" / "tests" / "golden" / "screens"
IMAGES = ROOT / "docs" / "images"


def grid(names, cols, out):
    inputs = []
    for n in names:
        inputs += ["-i", str(G / f"{n}.png")]
    rows = [names[i:i + cols] for i in range(0, len(names), cols)]
    parts, labels = [], []
    k = 0
    for r, row in enumerate(rows):
        ids = "".join(f"[{k + j}]" for j in range(len(row)))
        parts.append(f"{ids}hstack=inputs={len(row)}[r{r}]")
        labels.append(f"[r{r}]")
        k += len(row)
    parts.append("".join(labels) + f"vstack=inputs={len(rows)}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(parts), str(out)], check=True)


def main() -> int:
    grid(["game-over-look-today-won", "game-over-look-today-lost", "game-over-look-today-draw", "game-over-look-won-c4", "game-over-look-lost-c4", "game-over-look-draw-rps"], 3, IMAGES / "game-over-look-before-after.png")
    grid(["game-over-look-newbest-c4", "game-over-look-over-doit", "game-over-look-timeup-whack", "game-over-look-won-lang-fr", "game-over-look-lost-lang-de", "game-over-look-won-lang-pt"], 3, IMAGES / "game-over-look-more.png")
    print("wrote docs/images/game-over-look-before-after.png and game-over-look-more.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
