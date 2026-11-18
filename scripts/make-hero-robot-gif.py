#!/usr/bin/env python3
"""Make docs/images/hero-robot.gif from the virtual unit: the unit's own screen renderer, scripted and reproducible.
Usage: python3 scripts/make-hero-robot-gif.py [--keep-frames DIR]
Cycles four scenes of about 2.5 s each at 10 frames a second (talking, dancing, weather, the games page then a win with confetti; the games themselves are not drawn by the renderer yet), then loops. Needs the screens renderer
(bash scripts/virtual-unit/build-screens.sh) and ffmpeg. Placement: host-side development tool; no firmware change. Upstream: none."""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "virtual-unit"))
spec = importlib.util.spec_from_file_location("vunit", ROOT / "scripts" / "virtual-unit" / "vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)

OUT = ROOT / "docs" / "images" / "hero-robot.gif"
FPS, SCENE_MS = 10, 2500
BAR = [("raw", "style big_eyes"), ("raw", "bbar always"), ("raw", "bstatus 80 0 1 1 1")]
SYLLABLES = [15, 70, 40, 90, 10, 60, 85, 30, 0, 55]   # speech levels, one per frame: the mouth opens and closes like talking
SCENES = [
    # name, set-up steps, steps run before each frame (i = frame number inside the scene)
    ("talking", BAR + [("call", "self.face.bench_emotion", {"emotion": "happy"}), ("advance", 400)], lambda i: [("raw", "speak %d" % SYLLABLES[i % 10])]),
    ("dancing", [("call", "self.robot.dance", {"name": "happy"}), ("advance", 5600)], lambda i: []),
    ("weather", BAR + [("call", "self.face.bench_emotion", {"emotion": "neutral"}), ("raw", "overlay rain 3 0"), ("advance", 800)], lambda i: []),
    ("a game", BAR + [("raw", "pshow games")], lambda i: [("raw", "pshow face"), ("raw", "overlay confetti 3 0")] if i == 12 else []),
]


def step(u, s):
    if s[0] == "call":
        out = u.call(s[1], s[2])
        assert not out.get("isError"), out
    elif s[0] == "raw":
        u.raw(s[1])
    else:
        u.advance(s[1])


def main():
    keep = Path(sys.argv[sys.argv.index("--keep-frames") + 1]) if "--keep-frames" in sys.argv else None
    tmp = Path(tempfile.mkdtemp(prefix="hero-robot-"))
    n = 0
    try:
        for name, steps, per_frame in SCENES:
            with vunit.VirtualUnit(profile="screens") as u:
                for s in steps:
                    step(u, s)
                for i in range(SCENE_MS // (1000 // FPS)):
                    for s in per_frame(i):
                        step(u, s)
                    u.advance(1000 // FPS)
                    (tmp / f"f{n:04d}.png").write_bytes(u.snapshot())
                    n += 1
        if keep:
            shutil.copytree(tmp, keep, dirs_exist_ok=True)
        vf = "split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.png"), "-vf", vf, "-loop", "0", str(OUT)], check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("wrote %s (%d frames, %.2f MB)" % (OUT.relative_to(ROOT), n, OUT.stat().st_size / 1e6))


if __name__ == "__main__":
    main()
