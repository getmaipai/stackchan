#!/usr/bin/env python3
"""Builds firmware/patches/UXF02-extended-moods.patch: five more mood faces (joy, excited, shocked, curious, worried) from the owner-approved expressive set (firmware-v1-cut row 132-expressive-faces).
The base is the reference tree with UXF01 applied (the patch builds on it). Usage: python3 scripts/face-kit/make_patch_moods.py [--tree TREE]
Placement: host-side development tool; the patch it writes is a unit patch on branch ux/faces. Upstream: none."""
from __future__ import annotations

import argparse
import difflib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = ["firmware/main/hal/maipai_look_core.h", "firmware/main/stackchan/avatar/avatar/elements/emotion.h"]
HEADER = """# Intent: Five more mood faces for the owner-approved expressive set (firmware-v1-cut row 132-expressive-faces, preview judged 2026-11-14): joy, excited, shocked, curious and worried. Content and love already exist. Each is a look row and a pose spec in the look core, so every style draws it (eyes, lids, brows, mouth) with no new shape and no new memory; the avatar's Emotion enum gains the five names in the order the look core uses. Joy is a bigger happy (arched eyes, a wide open grin); excited has wide eyes, raised brows and a restless gaze; shocked is the widest eyes with raised brows and a tall round mouth; curious has one smaller eye lifted, a look to the side and a small crooked mouth; worried has tilted lids, brows drawn up in the middle and a wavering mouth. Nothing in the unit picks them yet: the host's face vocabulary (face_set.json, docs/dev/stackchan-faces-2026-11-14.md) names them and falls back to the old ones until a unit with this patch reports them.
# Placement: unit
# Upstream: firmware/main/hal/maipai_look_core.h and firmware/main/stackchan/avatar/avatar/elements/emotion.h (ours, patches X01, UXF01)
# Check after a flash: self.face.bench_emotion with joy, excited, shocked, curious and worried draws five different faces in every style; the old twelve draw as before; the memory row is unchanged.
# Kconfig: none
# Memory cost: none (five table rows, about 400 bytes of flash).

"""


def edit(t: str, old: str, new: str) -> str:
    if t.count(old) != 1:
        raise SystemExit(f"edit expected one match, found {t.count(old)}: {old[:60]!r}")
    return t.replace(old, new)


def look(t: str) -> str:
    t = edit(t, "    ML_CONTENT, /* the resting look of a well cared for unit: round eyes, a small smile */\n    ML_COUNT", "    ML_CONTENT, /* the resting look of a well cared for unit: round eyes, a small smile */\n    ML_JOY,     /* patch UXF02: the expressive set */\n    ML_EXCITED,\n    ML_SHOCKED,\n    ML_CURIOUS,\n    ML_WORRIED,\n    ML_COUNT")
    t = edit(t, "    /* content   */ {100, 0, 0, 1.00f, {24, 8, 8, 0, 0, 0}, ML_TINT_NONE},\n};", """    /* content   */ {100, 0, 0, 1.00f, {24, 8, 8, 0, 0, 0}, ML_TINT_NONE},
    /* joy       */ {62, 1, -10, 1.04f, {34, 14, 8, 0, 1, 0}, ML_TINT_NONE},
    /* excited   */ {100, 0, 0, 1.10f, {30, 12, 10, 0, 1, 0}, ML_TINT_NONE},
    /* shocked   */ {100, 0, 0, 1.18f, {3, 0, 26, 0, 0, 0}, ML_TINT_NONE},
    /* curious   */ {88, 0, 4, 1.00f, {20, 2, 7, 1.2f, 0, 6}, ML_TINT_NONE},
    /* worried   */ {80, 0, -14, 0.97f, {22, -5, 7, 1.4f, 0, -4}, ML_TINT_NONE},
};""")
    t = edit(t, "        case ML_LOVE: s.heart = 1; s.mcurve = 1; s.mopen = .3f; s.dr = 0; break;\n", """        case ML_LOVE: s.heart = 1; s.mcurve = 1; s.mopen = .3f; s.dr = 0; break;
        case ML_JOY: s.cheek = 1; s.mcurve = 1.2f; s.mopen = .55f; s.dy = -4; s.sw = 1.04f; break;
        case ML_EXCITED: s.sw = 1.08f; s.sh = 1.15f; s.mcurve = 1; s.mopen = .7f; s.brow = 1; s.blift = 8; s.dr = 1.5f; break;
        case ML_SHOCKED: s.sw = 1.16f; s.sh = 1.4f; s.mopen = 1; s.mcurve = 0; s.smw = .45f; s.brow = 1; s.blift = 14; s.dr = .3f; break;
        case ML_CURIOUS: s.rscale = .88f; s.rlift = -8; s.gx = 8; s.gy = -5; s.brow = 1; s.blift = 4; s.br = 8; s.mcurve = .1f; s.mtilt = -6; s.mx = 8; s.smw = .8f; break;
        case ML_WORRIED: s.slant = -.45f; s.lid = .12f; s.brow = 1; s.btilt = -1; s.blift = 3; s.sh = .96f; s.mcurve = -.5f; s.smw = .85f; s.gy = 3; s.dr = .6f; break;
""")
    return t


def emotion(t: str) -> str:
    return edit(t, "    Content,  // the resting look of a well cared for unit: round eyes, a small smile\n};", "    Content,  // the resting look of a well cared for unit: round eyes, a small smile\n    // Patch UXF02: the order matches ml_emotion_t.\n    Joy,\n    Excited,\n    Shocked,\n    Curious,\n    Worried,\n};")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", default=str(Path.home() / "esp" / "stackchan-rebuild" / "main-ref"))
    a = ap.parse_args()
    tree = Path(a.tree)
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        for rel in FILES:
            (base / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(tree / rel, base / rel)
        uxf01 = (ROOT / "firmware" / "patches" / "UXF01-face-style-recipes.patch").read_text()
        done = subprocess.run(["patch", "-p1", "-s", "-f"], input="diff --git " + uxf01.split("diff --git ", 1)[1].split("\ndiff --git ", 1)[0] + "\n", cwd=base, capture_output=True, text=True)
        if done.returncode != 0:
            raise SystemExit("UXF01 does not apply to the base: " + done.stdout + done.stderr)
        out = [HEADER]
        for rel, fn in zip(FILES, (look, emotion)):
            old = (base / rel).read_text()
            new = fn(old)
            out.append(f"diff --git a/{rel} b/{rel}\n" + "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), f"a/{rel}", f"b/{rel}", n=3)))
    dest = ROOT / "firmware" / "patches" / "UXF02-extended-moods.patch"
    dest.write_text("".join(out))
    print(f"wrote {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
