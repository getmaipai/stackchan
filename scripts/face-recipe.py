#!/usr/bin/env python3
"""Face recipes: the style assets (kind style, docs/plan/face-parts.md). firmware/styles/NAME.json holds the numbers of one face style; this writes NAME.rcp, the 44 bytes the unit reads
(maipai_look_core.h: ml_recipe_parse), and checks the same ranges, so a bad recipe stops here with a plain sentence.
Usage: python3 scripts/face-recipe.py build [NAME ...]   writes the .rcp files
       python3 scripts/face-recipe.py check              fails when a .rcp is missing or differs from its JSON (check.sh runs it)
Placement: host-side development tool; the recipes are installable assets, nothing is in the firmware image. Upstream: none."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "firmware" / "styles"
LOOKS = {"std": 0, "pie": 1, "neon": 2, "slit": 3, "heart": 4}
EXTRAS = {"none": 0, "cat": 1, "robot": 2, "blush": 3, "hose": 4, "neon": 5}
MOUTHS = {"none": 0, "cute": 1, "bar": 2}


def encode(spec: dict) -> bytes:
    name = spec["name"]
    if not (1 <= len(name) <= 12 and name.isascii() and all(c.isalnum() or c == "_" for c in name)):
        raise SystemExit(f"{name}: a style name is 1 to 12 letters, digits or underscores. Rename it.")
    look, extras, mouth = LOOKS[spec.get("look", "std")], EXTRAS[spec.get("extras", "none")], MOUTHS[spec["mouth"]]
    n = {k: int(spec[k]) for k in ("eye_d", "eye_x", "eye_y", "mouth_y", "mouth_w", "mouth_t", "ew", "eh")}
    r_pct, pupil, brows, drift, blw, lid_min = (int(spec.get(k, d)) for k, d in (("r_pct", 100), ("pupil", 0), ("brows", 0), ("drift", 5), ("blw", 5), ("lid_min", 0)))
    problems = []
    if not (10 <= n["ew"] <= 120 and 10 <= n["eh"] <= 110 and 10 <= n["eye_d"] <= 120 and 30 <= n["eye_x"] <= 110 and -60 <= n["eye_y"] <= 40):
        problems.append("the eyes are too small, too big or too far out (sizes 10 to 120, spacing 30 to 110, height -60 to 40)")
    if not (20 <= n["mouth_y"] <= 70 and 0 <= n["mouth_w"] <= 90 and 0 <= n["mouth_t"] <= 14) or n["eye_y"] - n["eh"] * 0.64 < -76:
        problems.append("the mouth or the top of the eyes would leave the face zone (mouth place 20 to 70, eye top above -76 when surprised)")
    if not (0 <= r_pct <= 100 and pupil in (0, 1) and brows in (0, 1) and 0 <= lid_min <= 70 and 0 <= drift <= 12 and 0 <= blw <= 12):
        problems.append("a choice is out of range (roundness 0 to 100, pupil and brows 0 or 1, lid floor 0 to 70, drift and brow thickness 0 to 12)")
    if problems:
        raise SystemExit(f"{name}: " + "; ".join(problems) + ". Fix the JSON and run this again.")
    head = b"MPS1" + bytes([1, look, extras, lid_min, mouth, r_pct, pupil, brows, drift, blw, 0, 0])
    return head + name.encode().ljust(12, b"\0") + struct.pack("<8h", n["eye_d"], n["eye_x"], n["eye_y"], n["mouth_y"], n["mouth_w"], n["mouth_t"], n["ew"], n["eh"])


def specs(names: list[str]) -> list[Path]:
    return [DIR / f"{n}.json" for n in names] if names else sorted(DIR.glob("*.json"))


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode not in ("build", "check"):
        print(__doc__)
        return 2
    bad = []
    for path in specs(sys.argv[2:]):
        data = encode(json.loads(path.read_text()))
        out = path.with_suffix(".rcp")
        if mode == "check":
            if not out.exists() or out.read_bytes() != data:
                bad.append(out.name)
        else:
            out.write_bytes(data)
            print(f"wrote {out.relative_to(ROOT)} ({len(data)} bytes)")
    if bad:
        print("face recipes out of date: " + ", ".join(bad) + ". Run python3 scripts/face-recipe.py build and commit the result.")
        return 1
    if mode == "check":
        print(f"face-recipes: ok ({len(specs([]))} styles)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
