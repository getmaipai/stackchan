#!/usr/bin/env python3
"""Frame cost of every face style against the display budget (docs/dev/display-capabilities.md, docs/plan/face-styles-verdict.md).
The renderer runs in dirty-area mode (PERF=1: only the changed areas are drawn and flushed, as on the unit); each style is stepped one 33 ms frame at a time for 4 s in four states
and the pixels flushed in every frame are kept. A frame costs K = 0.733 ms per 1,000 pixels (the bench's flat box, UNIT_BOX_US in games_cost.py); the face rule is a mean of at most 6,500 pixels
and a worst frame of at most 30 ms (40,900 pixels). Host milliseconds are not the unit's.
Usage: host/.venv/bin/python scripts/virtual-unit/face_style_cost.py [--json FILE] [--md FILE]
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from face_styles import BASE_STYLES, STYLES  # noqa: E402

K_MS_PER_KPX = 0.733
MEAN_LIMIT = 6500                      # the motion rule's mean pixels a frame
WORST_MS = 30.0                        # a worst face frame must fit in one 33 ms step; the 16,000 pixel rule is for game loops, and the shipped default (big_eyes) is already 22,000 on a blink
WORST_LIMIT = int(WORST_MS / K_MS_PER_KPX * 1000)
STATES = {"neutral": ("neutral", 0), "happy": ("happy", 0), "surprised": ("surprised", 0), "speaking": ("neutral", 90)}
LINE = re.compile(r"perf \S+ frames (\d+) flushed_px_per_frame (\d+)")
RENDER = ROOT / ".runs" / "vu-build" / "render"


def run_state(style: str, mood: str, speak: int, frames: int = 120) -> list[int]:
    cmds = [f"style {style}" if style in BASE_STYLES else f"recipe {ROOT / 'firmware' / 'styles' / (style + '.rcp')}", f"emotion {mood}", "advance 900"]
    if speak:
        cmds.append(f"speak {speak}")
    cmds.append("advance 300")
    for i in range(frames):
        cmds += ["perfbegin", "advance 33", f"perfend f{i}"]
    done = subprocess.run([str(RENDER)], input="\n".join(cmds) + "\n", capture_output=True, text=True, timeout=180, env={**os.environ, "PERF": "1"})
    px = [int(m.group(2)) for m in (LINE.match(line) for line in done.stdout.splitlines()) if m and m.group(1) == "1"]
    if len(px) < frames // 2:
        raise SystemExit(f"the renderer gave no frame readings for {style}/{mood}. Build it with bash scripts/virtual-unit/build-face.sh.")
    return px


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    ap.add_argument("--md", type=Path)
    a = ap.parse_args()
    table: dict[str, dict[str, dict[str, float]]] = {}
    for style in STYLES:
        table[style] = {}
        for label, (mood, speak) in STATES.items():
            px = run_state(style, mood, speak)
            mean, worst = sum(px) / len(px), max(px)
            table[style][label] = {"mean_px": round(mean), "worst_px": worst, "mean_ms": round(mean / 1000 * K_MS_PER_KPX, 2), "worst_ms": round(worst / 1000 * K_MS_PER_KPX, 2)}
    verdicts = {}
    for style, states in table.items():
        mean = max(s["mean_px"] for s in states.values())
        worst = max(s["worst_px"] for s in states.values())
        verdicts[style] = {"mean_px": mean, "worst_px": worst, "fits": mean <= MEAN_LIMIT and worst <= WORST_LIMIT}
    out = {"k_ms_per_1000px": K_MS_PER_KPX, "limits": {"mean_px": MEAN_LIMIT, "worst_px": WORST_LIMIT}, "states": table, "verdict": verdicts}
    if a.json:
        a.json.write_text(json.dumps(out, indent=1) + "\n")
    lines = ["| Style | Neutral mean / worst px | Speaking mean / worst px | Surprised worst px | Worst frame ms (unit estimate) | Rule |", "|---|---|---|---|---|---|"]
    for style in STYLES:
        s = table[style]
        v = verdicts[style]
        lines.append(f"| {style} | {s['neutral']['mean_px']} / {s['neutral']['worst_px']} | {s['speaking']['mean_px']} / {s['speaking']['worst_px']} | {s['surprised']['worst_px']} | {v['worst_px'] / 1000 * K_MS_PER_KPX:.1f} | {'fits' if v['fits'] else 'over'} |")
    text = "\n".join(lines)
    print(text)
    if a.md:
        a.md.write_text(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
