#!/usr/bin/env python3
"""Writes a renderer script: every style times every state. Usage: scene.py OUTDIR [style ...]"""
import sys
out = sys.argv[1]
styles = sys.argv[2:] or ["big_eyes", "eyes_only", "stock", "classic", "minimal"]
L = []
for st in styles:
    L.append(f"style {st}"); L.append("emotion neutral"); L.append("advance 1500")
    for e in ["neutral", "happy", "sad", "angry", "doubt", "surprised", "sleepy"]:
        L += [f"emotion {e}", "advance 1200", "tile"]
    # closing: frames at 0, 0.5, 1.0, 1.5 s, then sleeping
    L += ["emotion neutral", "advance 800", "emotion closing", "advance 500", "tile", "advance 500", "tile", "advance 800", "tile"]
    L += ["emotion sleeping", "advance 600", "tile"]
    L += ["emotion neutral", "advance 900"]
    for lv in (25, 55, 90):
        L += [f"speak {lv}", "advance 300", "tile"]
    L += ["speak 0", "advance 600"]
    L += ["emotion doubt", "think on", "advance 500", "tile", "advance 300", "tile", "think off", "emotion neutral", "advance 600"]
    L += ["emotion tired", "advance 3400", "tile", "advance 1000", "tile", "emotion neutral", "advance 1500"]
    L += [f"sheet {out}/{st}.png 8 2"]
open(f"{out}/scene.txt", "w").write("\n".join(L) + "\n")
