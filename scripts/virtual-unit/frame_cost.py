#!/usr/bin/env python3
"""Frame cost per screen type from the host renderer (lane P baseline). Usage: frame_cost.py [--write]   prints a table; --write puts it in docs/dev.
For each scenario the renderer runs 3 s of animation in dirty-area mode (PERF=1: LVGL draws and flushes only the changed areas, as on the unit) and
reports pixels flushed per frame and host milliseconds per frame. The unit's flush cost is estimated from the one measured number in
docs/design/picture-faces-2026-11-16.md: a full-screen flush (153,600 bytes) takes 26 to 35 ms, taken here as 30 ms, so 0.195 ms per 1,000 bytes.
Host milliseconds are a relative check between screens on this Mac, not unit milliseconds. Placement: host-side development tool. Upstream: none."""
import importlib.util
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.environ["PERF"] = "1"
spec = importlib.util.spec_from_file_location("scenarios", HERE / "scenarios.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)
vunit = sc.vunit

PICKS = ["face-neutral", "face-happy", "speak-90", "face-thinking", "face-sleeping", "screen-status-normal", "screen-page-clock", "screen-page-timers",
         "screen-control-sheet", "screen-apps-wall", "screen-games-wall", "screen-settings-general", "screen-eyes-only-muted", "first-run-1"]
MS_PER_BYTE = 30.0 / 153600  # the measured full-screen flush on the unit
LINE = re.compile(r"perf (\S+) frames (\d+) flushed_px_per_frame (\d+) host_ms_per_frame ([\d.]+)")


def measure(name):
    steps = sc.SCREENS.get(name) or sc.SCENARIOS[name]
    profile = "screens" if name in sc.SCREENS else "face"
    with vunit.VirtualUnit(profile=profile) as u:
        sc.run(u, steps)
        u.advance(500)
        u.raw("perfbegin")
        u.advance(3000)
        u.raw(f"perfend {name}")
        u._sync()
        for line in u.output:
            m = LINE.match(line)
            if m and m.group(1) == name:
                return int(m.group(2)), int(m.group(3)), float(m.group(4))
    return None


def main():
    rows = []
    for name in PICKS:
        r = measure(name)
        if r is None:
            print(f"no reading for {name}")
            continue
        frames, px, host_ms = r
        rows.append((name, frames, px, host_ms, px * 2 * MS_PER_BYTE))
    lines = ["| Scenario | Frames in 3 s | Pixels flushed per frame | Host ms per frame | Estimated unit flush ms per frame |", "|---|---|---|---|---|"]
    lines += [f"| {n} | {f} | {px} | {h:.2f} | {e:.1f} |" for n, f, px, h, e in rows]
    table = "\n".join(lines)
    print(table)
    if "--write" in sys.argv:
        text = f"""# Frame cost baseline from the virtual unit (2026-11-18)

Lane P baseline. Measured with `python3 scripts/virtual-unit/frame_cost.py --write` on the host renderer in dirty-area mode (only changed areas drawn and flushed, as on the unit), 3 s of each screen after it settled.

{table}

## How to read it

- Pixels flushed per frame is exact for the unit's own drawing code: it does not depend on the Mac. A static screen flushes 0 pixels.
- Host ms per frame is the time of the same drawing on this Mac: use it to compare screens with each other, not as unit time.
- The estimated unit flush time uses the one measured number we have (a full-screen flush of 153,600 bytes takes 26 to 35 ms on the unit, `docs/design/picture-faces-2026-11-16.md`), taken as 30 ms. It covers the flush only, not the drawing, so the real frame is longer.
- Finding (fixed by patch UX06): before it, full-screen screens flushed 2,600 to 2,700 pixels per frame, as much as the face, because the face behind a cover kept its gaze drift and blink going. With UX06 the face update rests while a full-screen screen is up: pages, the Apps and Games walls and Settings flush 0 pixels per frame (the clock page 9, its seconds). The half-height control sheet keeps the face live, so it still flushes about 2,700. The first-run screens are not registered as screens yet and still flush about 2,400 per frame during first run only. A sleeping face flushes 0.
- Lane P target: when a change raises pixels flushed per frame of a screen, say so here.
"""
        (ROOT / "docs" / "dev" / "frame-cost-baseline-2026-11-18.md").write_text(text)
        print("wrote docs/dev/frame-cost-baseline-2026-11-18.md")


if __name__ == "__main__":
    main()
