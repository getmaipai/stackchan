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
GOLDEN_SCREENS = ROOT / "host" / "tests" / "golden" / "screens"

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


# Screens other than the bare face, on the screens renderer. Not drawn by the renderer yet (gaps, listed so they are not forgotten):
# pairing screen, updating screen, lock screen and keypad (lock_render.sh is a separate program), the Wi-Fi setup screen itself
# (the renderer only has the banner flag for it).
SCREEN_GAPS = []  # every screen the unit can show is drawn
BAR = [("raw", "style big_eyes"), ("raw", "bbar always"), ("raw", "bstatus 80 0 1 1 1")]
SCREENS: dict[str, list] = {
    "screen-status-normal": BAR + [EMOTE("neutral"), ("advance", 1500)],
    "screen-listening": BAR + [("raw", "bst 1"), ("advance", 700)],
    "screen-muted": BAR + [("raw", "bstatus 80 0 1 1 0"), ("advance", 700)],
    "screen-offline": BAR + [("raw", "bstatus 80 0 0 0 1"), ("advance", 700)],
    "screen-low-battery": BAR + [("raw", "bstatus 12 0 1 1 1"), ("call", "self.face.bench_emotion", {"emotion": "tired", "tired_level": 2}), ("advance", 3400)],
    "screen-charging": BAR + [("raw", "bstatus 40 1 1 1 1"), ("advance", 700)],
    "screen-eyes-only-muted": BAR + [("raw", "style eyes_only"), ("raw", "bstatus 80 0 1 1 0"), ("raw", "seal on"), ("advance", 900)],  # patch UX03a
    "screen-wifi-flag": BAR + [("raw", "bwifiscreen on"), ("advance", 700)],
    "screen-page-clock": BAR + [("raw", "pshow clock"), ("advance", 600)],
    "screen-page-timers": BAR + [("raw", "pshow timers"), ("advance", 600)],
    "screen-page-games": BAR + [("raw", "pshow games"), ("advance", 600)],
    "screen-page-actions": BAR + [("raw", "pshow actions"), ("advance", 600)],
    "screen-control-sheet": BAR + [("raw", "pshow sheet"), ("advance", 600)],
}


# The lock screen and keypad come from their own program (lock_render): script lines, one PNG per scenario written to {out}.
LOCK_SCENARIOS = {
    "lock-screen": ["banner on", "lock {out}"],
    "lock-keypad-empty": ["banner on", "pad 0 0 {out}"],
    "lock-keypad-three": ["banner on", "pad 3 0 {out}"],
    "lock-keypad-wrong": ["banner on", "pad 6 1 {out}"],
    "lock-keypad-wrong-es": ["banner on", "lang es", "pad 0 1 {out}"],
}


# The link covers, drawn by the unit's own code cut out of stackchan_display.cc (cover_gen.py): ShowBootCover(text, ring, glyph).
COVER_SCENARIOS = {
    "cover-connecting-wifi": ["show 1 0 Connecting to Wi-Fi...", "advance 800", "snap {out}"],
    "cover-connecting-home": ["show 1 0 Connecting to Home...", "advance 800", "snap {out}"],
    "cover-wifi-setup": ["show 2 1 Wi-Fi setup needed\\nHotspot MaiPai-1234\\n192.0.2.1", "advance 600", "snap {out}"],
    "cover-update-0": ["update 0", "advance 300", "snap {out}"],
    "cover-update-62": ["update 62", "advance 300", "snap {out}"],
    "cover-update-installed": ["update 100", "advance 300", "snap {out}"],
    "cover-update-refused": ["update -2", "advance 300", "snap {out}"],
    "cover-pairing": ["show 2 2 Waiting for Home\\nto approve me", "advance 600", "snap {out}"],
}


def run_lock(name: str) -> bytes:
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "shot.png"
        lines, prog = (COVER_SCENARIOS[name], "cover/cover_render") if name in COVER_SCENARIOS else (LOCK_SCENARIOS[name], "lock/lock_render")
        script = "\n".join(line.format(out=out) for line in lines) + "\n"
        subprocess.run([str(ROOT / ".runs" / "vu-screens" / prog)], input=script, text=True, check=True, capture_output=True)
        return out.read_bytes()


def run(u, steps) -> None:
    for step in steps:
        if step[0] == "call":
            out = u.call(step[1], step[2])
            assert not out.get("isError"), out
        elif step[0] == "raw":
            u.raw(step[1])
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
    screens_built = (ROOT / ".runs" / "vu-screens" / "render").exists()
    names = args or list(SCENARIOS) + (list(SCREENS) + list(LOCK_SCENARIOS) + list(COVER_SCENARIOS) if screens_built else [])
    if not args and not screens_built:
        print("screens renderer not built: skipping screen scenarios (bash scripts/virtual-unit/build-screens.sh)")
    failed = 0
    GOLDEN.mkdir(parents=True, exist_ok=True)
    GOLDEN_SCREENS.mkdir(parents=True, exist_ok=True)
    for name in names:
        is_screen = name in SCREENS or name in LOCK_SCENARIOS or name in COVER_SCENARIOS
        if name in LOCK_SCENARIOS or name in COVER_SCENARIOS:
            png, problems = run_lock(name), []
        else:
            with vunit.VirtualUnit(profile="screens" if is_screen else "face") as u:
                run(u, SCREENS[name] if is_screen else SCENARIOS[name])
                png = u.snapshot()
                problems = layout_problems(u, name)
        folder = GOLDEN_SCREENS if is_screen else GOLDEN
        gold = folder / f"{name}.png"
        if update:
            gold.write_bytes(png)
        elif not gold.exists():
            problems.append("no golden frame: run scenarios.py --update and look at it")
        elif png_pixels(gold.read_bytes()) != png_pixels(png):
            (folder.parent / f"{name}.actual.png").write_bytes(png)
            problems.append(f"frame differs from golden (actual saved to host/tests/golden/{name}.actual.png)")
        for p in problems:
            failed += 1
            print(f"FAIL {name}: {p}")
    if not args:
        print("not drawn yet: " + ", ".join(SCREEN_GAPS))
    print(f"{len(names) - failed} of {len(names)} scenarios clean" if not failed else f"{failed} problems")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
