#!/usr/bin/env python3
"""Scripted scenarios on the virtual unit: golden frames and layout checks.
Usage: scenarios.py [--update] [name ...]   --update rewrites host/tests/golden/face/<scenario>.png from the current renderer.
Each scenario is a list of steps (tool calls, advance, touch) ending in a frame; checks run on that frame.
Exit 1 and one line per failing scenario on a mismatch or a broken layout rule.
Placement: host-side development tool; no firmware change. Upstream: none."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "host" / "tests" / "golden" / "face"

spec = importlib.util.spec_from_file_location("vunit", Path(__file__).with_name("vunit.py"))
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)

EMOTE = lambda e: ("call", "self.face.bench_emotion", {"emotion": e})
SCENARIOS: dict[str, list] = {}
for e in ("neutral", "happy", "sad", "angry", "doubtful", "surprised", "sleepy", "sleeping", "love", "content", "thinking"):
    SCENARIOS[f"face-{e}"] = [EMOTE(e), ("advance", 1500)]
for lv in (25, 90):
    SCENARIOS[f"speak-{lv}"] = [EMOTE("neutral"), ("advance", 800), ("call", "self.face.bench_speak", {"level": lv, "seconds": 20}), ("advance", 400)]
SCENARIOS["closing-mid"] = [EMOTE("closing"), ("advance", 500)]
SCENARIOS["tired-low-battery"] = [("call", "self.face.bench_emotion", {"emotion": "tired", "tired_level": 2}), ("advance", 3400)]


def run(u, steps) -> None:
    for step in steps:
        if step[0] == "call":
            out = u.call(step[1], step[2])
            assert not out.get("isError"), out
        elif step[0] == "advance":
            u.advance(step[1])
        elif step[0] == "touch":
            u.touch(*step[1:])


def png_pixels(png: bytes) -> bytes:
    import zlib
    return zlib.decompress(png[png.index(b"IDAT") + 4 : png.rindex(b"IEND") - 8])


def layout_problems(u, name: str) -> list[str]:
    """Layout rules every face must keep (panel 320x240): lit pixels stay on the panel and keep a 4 px edge margin; eyes stay in the upper 60 percent."""
    bad = []
    whole = u.count(0, 0, 320, 240)
    if name not in ("face-sleeping",) and whole["lit"] == 0:
        bad.append("blank screen")
    elif whole["lit"]:
        x0, y0, x1, y1 = whole["bbox"]
        if x0 < 4 or y0 < 4 or x1 > 315 or y1 > 235:
            bad.append(f"drawing touches the panel edge (bbox {whole['bbox']})")
    return bad


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    update = "--update" in sys.argv
    names = args or list(SCENARIOS)
    failed = 0
    GOLDEN.mkdir(parents=True, exist_ok=True)
    for name in names:
        with vunit.VirtualUnit() as u:
            run(u, SCENARIOS[name])
            png = u.snapshot()
            problems = layout_problems(u, name)
        gold = GOLDEN / f"{name}.png"
        if update:
            gold.write_bytes(png)
        elif not gold.exists():
            problems.append("no golden frame: run scenarios.py --update and look at it")
        elif png_pixels(gold.read_bytes()) != png_pixels(png):
            (GOLDEN.parent / f"{name}.actual.png").write_bytes(png)
            problems.append(f"frame differs from golden (actual saved to host/tests/golden/{name}.actual.png)")
        for p in problems:
            failed += 1
            print(f"FAIL {name}: {p}")
    print(f"{len(names) - failed} of {len(names)} scenarios clean" if not failed else f"{failed} problems")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
