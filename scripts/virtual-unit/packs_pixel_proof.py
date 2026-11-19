#!/usr/bin/env python3
"""Pixel proof for the data-pack games' drawing (patch UX29): runs two builds of the pack renderer (games_render) through the same many scenes
(every pack, every state, both languages, random counters and board cells, several moments of the motion) and counts the pixels that differ.
Usage: packs_pixel_proof.py OLD_RENDER NEW_RENDER [--scenes N] [--seed S] [--partial]. With --partial the second build runs in partial-refresh mode
(PARTIAL=1: only what its code invalidated is redrawn, the frame builds up as the unit's panel keeps it) against the first in full-refresh mode: pass the
same build twice to prove the invalidation covers every change. Exit 0 only when no pixel differs.
Also: packs_pixel_proof.py --write-digests FILE RENDER writes a short hash of every frame of a fixed set of scenes (made with the build whose
drawing is the reference), and packs_pixel_proof.py --check-digests FILE RENDER draws the same scenes and fails on any frame whose hash differs:
host/tests/golden/pack_games_digests.json holds the hashes of the drawing as it was before patch UX29. Placement: host-side development
tool. Upstream: none."""
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKS = ["tictactoe", "whack", "bopit", "eightball", "dice", "memory", "rps"]
TIMES = [1000, 1050, 1120, 1200, 1300, 1500, 1750, 2100, 2600, 4000]


def read_png(path):
    data = Path(path).read_bytes()
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(data):
        n = int.from_bytes(data[pos:pos + 4], "big")
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h = int.from_bytes(body[:4], "big"), int.from_bytes(body[4:8], "big")
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    raw = zlib.decompress(idat)
    stride = w * 3 + 1
    return w, h, [raw[y * stride + 1:(y + 1) * stride] for y in range(h)]


def scenes(pack, count, rng):
    j = json.loads((ROOT / "firmware" / "games" / f"{pack}.json").read_text())
    n_states, n_ctr = len(j["states"]), len(j["counters"])
    out = []
    for s in range(n_states):   # every state, plain, both languages, the motion at three moments
        for lang in ("en", "es"):
            for t in (1000, 1120, 1300):
                out.append({"lang": lang, "state": s, "ctr": [], "board": [], "t": t})
    for _ in range(count):
        out.append({"lang": rng.choice(["en", "es"]), "state": rng.randrange(n_states),
                    "ctr": [(i, rng.choice([0, 1, 2, 3, 4, 5, 6, 7, 9])) for i in range(n_ctr) if rng.random() < 0.6],
                    "board": [(c, rng.choice([0, 1, 2])) for c in range(9) if rng.random() < 0.5] if pack == "tictactoe" else [],
                    "t": rng.choice(TIMES)})
    return out


def run(render, pack, sc, outdir, partial=False):
    cmds = [f"load firmware/games/{pack}.mpk"]
    for k, s in enumerate(sc):
        cmds += [f"lang {s['lang']}", f"state {s['state']}"] + [f"ctr {i} {v}" for i, v in s["ctr"]] + [f"board {c} {v}" for c, v in s["board"]]
        cmds += [f"t {s['t']}", "draw", f"snap {outdir}/{pack}-{k}.png"]
    env = dict(os.environ, PARTIAL="1") if partial else {k: v for k, v in os.environ.items() if k != "PARTIAL"}
    done = subprocess.run([str(render)], input="\n".join(cmds) + "\n", capture_output=True, text=True, cwd=ROOT, env=env)
    return done.stdout


def digests(render):
    """A hash for every frame of the fixed scenes of every pack: {pack: [hash, ...]}."""
    out = {}
    rng = random.Random(1)
    with tempfile.TemporaryDirectory() as tmp:
        for pack in PACKS:
            sc = scenes(pack, 25, rng)
            run(render, pack, sc, tmp)
            out[pack] = [hashlib.sha1(b"".join(read_png(f"{tmp}/{pack}-{k}.png")[2])).hexdigest()[:12] for k in range(len(sc))]
    return out


def main():
    args = sys.argv[1:]
    if args[0] == "--write-digests":
        Path(args[1]).write_text(json.dumps(digests(args[2]), indent=0) + "\n")
        print(f"wrote {args[1]}")
        return 0
    if args[0] == "--check-digests":
        want, got = json.loads(Path(args[1]).read_text()), digests(args[2])
        bad = [(p, k) for p in want for k in range(len(want[p])) if k >= len(got[p]) or got[p][k] != want[p][k]]
        print(f"{sum(len(v) for v in want.values())} frames, {len(bad)} differ" + (f" (first: {bad[0]})" if bad else ""))
        return 1 if bad else 0
    old, new = args[0], args[1]
    count = int(args[args.index("--scenes") + 1]) if "--scenes" in args else 150
    rng = random.Random(int(args[args.index("--seed") + 1]) if "--seed" in args else 7)
    frames = bad_frames = bad_pixels = 0
    with tempfile.TemporaryDirectory() as tmp:
        for pack in PACKS:
            sc = scenes(pack, count, rng)
            for tag, render in (("a", old), ("b", new)):
                Path(f"{tmp}/{tag}").mkdir(exist_ok=True)
                run(render, pack, sc, f"{tmp}/{tag}", partial=("--partial" in args and tag == "b"))
            pack_bad = 0
            for k, s in enumerate(sc):
                wa, ha, ra = read_png(f"{tmp}/a/{pack}-{k}.png")
                wb, hb, rb = read_png(f"{tmp}/b/{pack}-{k}.png")
                frames += 1
                diff = 0
                box = [9999, 9999, -1, -1]
                for y in range(ha):
                    if ra[y] != rb[y]:
                        for x in range(wa):
                            if ra[y][x * 3:x * 3 + 3] != rb[y][x * 3:x * 3 + 3]:
                                diff += 1
                                box = [min(box[0], x), min(box[1], y), max(box[2], x), max(box[3], y)]
                if diff:
                    bad_frames += 1
                    bad_pixels += diff
                    pack_bad += 1
                    if pack_bad <= 3:
                        print(f"DIFF {pack} scene {k} {s['lang']} state {s['state']} t {s['t']} ctr {s['ctr']} board {s['board']}: {diff} pixels in {box}")
            print(f"{pack}: {len(sc)} frames, {pack_bad} differ")
    print(f"{frames} frames, {bad_frames} differ, {bad_pixels} differing pixels")
    return 0 if bad_pixels == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
