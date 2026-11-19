#!/usr/bin/env python3
"""A sheet of the seven data-pack games as the unit draws them today, and each pack's LVGL object count (docs/plan/games-packs-look.md). Draws one typical state of each pack with games_render and joins the
frames (needs ffmpeg). Usage: games_pack_sheet.py [OUT.png] [--counts]. Placement: host-side development tool. Upstream: none."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RENDER = ROOT / ".runs" / "vu-screens" / "games" / "games_render"
PACKS = [("tictactoe", 1, ["board 0 1", "board 4 2", "board 8 1", "board 2 2"]), ("whack", 1, ["ctr 0 7", "ctr 1 3"]), ("bopit", 2, []), ("eightball", 2, []), ("dice", 7, ["ctr 1 4", "ctr 2 6", "ctr 5 10"]),
         ("memory", 3, []), ("rps", 6, ["ctr 1 1", "ctr 2 2"])]


def counts():
    out = {}
    for name, _, _ in PACKS:
        states = list(json.loads((ROOT / "firmware" / "games" / f"{name}.json").read_text())["states"])
        cmds = [f"load firmware/games/{name}.mpk", "lang en"] + [c for i in range(len(states)) for c in (f"state {i}", "draw", "objcount")]
        lines = subprocess.run([str(RENDER)], input="\n".join(cmds) + "\n", capture_output=True, text=True, cwd=ROOT).stdout.splitlines()
        rows = [l.split() for l in lines if l.startswith("objects")]
        out[name] = {"objects": max(int(r[1]) for r in rows), "labels": max(int(r[3]) for r in rows)}
    return out


def sheet(path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cmds = []
        for name, state, setup in PACKS:
            cmds += [f"load firmware/games/{name}.mpk", "lang en"] + setup + [f"state {state}", f"snap {tmp}/{name}.png"]
        subprocess.run([str(RENDER)], input="\n".join(cmds) + "\n", capture_output=True, text=True, cwd=ROOT, check=True)
        imgs = [f"{tmp}/{n}.png" for n, _, _ in PACKS] + [f"{tmp}/{PACKS[0][0]}.png"]
        row1, row2 = f"{tmp}/r1.png", f"{tmp}/r2.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y"] + sum([["-i", i] for i in imgs[:4]], []) + ["-filter_complex", "hstack=inputs=4", row1], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y"] + sum([["-i", i] for i in imgs[4:7]], []) + ["-filter_complex", "hstack=inputs=3", row2], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", row1, "-i", row2, "-filter_complex", "[0]pad=iw:ih*2[a];[a][1]overlay=0:H/2", str(path)], check=True)


def main() -> int:
    if "--counts" in sys.argv:
        for n, c in counts().items():
            print(f"{n}: {c['objects']} objects, {c['labels']} labels, about {(c['objects'] - c['labels']) * 110 + c['labels'] * 200} bytes of internal RAM")
        return 0
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sheet(Path(args[0]) if args else ROOT / "docs" / "images" / "games-packs-today.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
