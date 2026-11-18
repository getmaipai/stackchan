#!/usr/bin/env python3
"""Renders the sounds the robot really plays for the games, with the unit's own tone core (maipai_games_sfx_core.h: the tone-segment table and mgs_render), to WAV files in
docs/dev/game-sounds/on-the-robot/ with a manifest (clip, ms, bytes as a 16 kHz 16 bit WAV, peak) so a person can hear them next to the sketches of make-game-sounds.py.
The header is the one in the replayed firmware tree (the overlay tree .runs/fixtree, made by scripts/virtual-unit/build-face.sh), optionally with more patches applied to it with --patch
FILE (for a patch that is not in the series yet, for example SF72 from the branch fw/unproven: `git show origin/fw/unproven:firmware/patches/SF72-....patch > /tmp/sf72.patch`).
Usage: python3 scripts/render-unit-sounds.py [--patch FILE ...] [--out DIR] [clip ...]. Placement: docs tooling. Upstream: none."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = "maipai_games_sfx_core.h"
DEFAULT_CLIPS = ["good", "fanfare", "bad", "thud", "rattle", "ting", "grid_tick_lo", "grid_tick_mid", "grid_tick_hi", "grid_clack_lo", "grid_clack_mid", "grid_clack_hi", "grid_drop", "grid_lose", "grid_draw"]


def main(argv: list[str]) -> int:
    patches, clips, out = [], [], ROOT / "docs" / "dev" / "game-sounds" / "on-the-robot"
    i = 0
    while i < len(argv):
        if argv[i] == "--patch":
            patches.append(Path(argv[i + 1]))
            i += 2
        elif argv[i] == "--out":
            out = Path(argv[i + 1])
            i += 2
        else:
            clips.append(argv[i])
            i += 1
    src = ROOT / ".runs" / "fixtree" / "firmware" / "main" / "hal" / HEADER
    if not src.exists():
        print("no overlay tree: run bash scripts/virtual-unit/build-face.sh first", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix="sfx-") as work:
        w = Path(work)
        shutil.copy(src, w / HEADER)
        for p in patches:
            text = p.read_text()
            m = re.search(r"^(diff --git a/firmware/main/hal/" + re.escape(HEADER) + r" b/.*?)(?=^diff --git |\Z)", text, re.S | re.M)
            if m:
                diff = m.group(1).replace(f"firmware/main/hal/{HEADER}", HEADER)
                done = subprocess.run(["patch", "-p1", "-s", "-f", "-d", str(w)], input=diff.encode(), capture_output=True)
                if done.returncode != 0:
                    print(f"{p.name} does not apply to {HEADER}: {done.stdout.decode()[-200:]}", file=sys.stderr)
                    return 1
        exe = w / "sfx_render"
        subprocess.run(["cc", "-O1", "-std=c99", "-Wall", "-I", str(w), str(ROOT / "scripts" / "virtual-unit" / "dance" / "sfx_render.c"), "-o", str(exe), "-lm"], check=True)
        out.mkdir(parents=True, exist_ok=True)
        names = clips or DEFAULT_CLIPS
        proc = subprocess.run([str(exe), str(out), *names], capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            return 1
    manifest = []
    names = [n for n in names if (out / f"{n}.wav").exists()]   # a clip the tree does not hold (SF72's grid clips without --patch) is skipped
    for n in names:
        with wave.open(str(out / f"{n}.wav")) as wv:
            frames = wv.readframes(wv.getnframes())
        samples = [int.from_bytes(frames[i : i + 2], "little", signed=True) for i in range(0, len(frames), 2)]
        manifest.append({"clip": n, "ms": round(len(samples) * 1000 / 16000), "wav_bytes": 44 + len(frames), "peak": max(abs(s) for s in samples), "peak_of_32767": round(max(abs(s) for s in samples) / 32767, 3), "source": "the unit's own tone table (maipai_games_sfx_core.h) rendered by mgs_render"})
    (out / "manifest.json").write_text(json.dumps({"version": 1, "what": "the sounds the robot really plays for the games, rendered from its own tone table", "patches": [p.name for p in patches], "clips": manifest}, indent=1) + "\n")
    print(f"on the robot: {len(manifest)} clips in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
