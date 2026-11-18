#!/usr/bin/env python3
"""Opens every screen in turn on the virtual unit, uses overlays, notes, the music dance and the first run, returns to the face each time, and checks the memory model (decision 15):
the budget holds at every step and, back at the face, the loaded set is the baseline again (the leak canary). Prints one line; exit 1 on a break.
Usage: python3 scripts/virtual-unit/memory_walk.py [--json]. Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memory_model as mm  # noqa: E402
import vunit  # noqa: E402

BAR = [("raw", "style big_eyes"), ("raw", "bbar always"), ("raw", "bstatus 80 0 1 1 1")]


def walk(u) -> dict:
    """The walk on a running screens unit. Returns the peaks and what was opened, raises MemoryBudgetError on a break or a leak."""
    mem = u.memory
    for kind, arg in [("raw", "style big_eyes"), ("raw", "bbar always"), ("raw", "bstatus 80 0 1 1 1")]:
        u.raw(arg)
    u.advance(500)
    baseline = mem.snapshot()
    opened = []

    def back_to_face(what):
        u.raw("pshow face")
        u.advance(300)
        mem.assert_back_to(baseline, f"after {what} closed")

    for page in mm.PAGES:   # the six pages
        u.raw(f"pshow {page}")
        u.advance(400)
        opened.append(f"screen.page.{page}")
        assert f"screen.page.{page}" in mem.loaded, page
        back_to_face(f"the {page} page")
    for name in ("sheet", "settings"):   # the control sheet and the settings screen
        u.raw(f"pshow {name}")
        u.advance(400)
        opened.append(mm.SCREEN_IDS[name])
        back_to_face(name)
    for wall in ("screen.apps_wall", "screen.games_wall"):   # reached by a touch inside the unit: declared here, the renderer has no event for it
        u.raw("pshow sheet")
        u.advance(300)
        mem.open(wall)
        opened.append(wall)
        u.advance(300)
        mem.close(wall)
        back_to_face(wall)
    u.raw("overlay disco 2 3")   # an overlay that ends by itself, then one that is cleared
    u.raw("overlay confetti 2 0")
    u.raw("notes 3")
    opened += ["overlay.layer.back", "overlay.layer.event", "decor.notes"]
    u.advance(3500)
    assert "overlay.layer.back" not in mem.loaded   # the timed one ended by itself
    u.raw("ovclear")
    u.raw("notes 0")
    mem.assert_back_to(baseline, "after the overlays and notes were cleared")
    u.call("sim.music", {"action": "start", "song": "loud_peak", "mode": "home"})   # the music dance: step, overlays, notes
    u.advance(14000)
    opened.append("feature.music_dance")
    u.call("sim.music", {"action": "stop"})
    u.advance(300)
    mem.assert_back_to(baseline, "after the music dance stopped")
    u.raw("frun start")   # the first-run flow, to its end
    u.advance(500)
    opened.append("screen.first_run")
    mem.close("screen.first_run")
    u.raw("pshow face")
    u.advance(300)
    mem.assert_back_to(baseline, "after the first run finished")
    return {"opened": opened, "peak": dict(mem.peak), "numbers": mem.numbers(), "violations": list(mem.violations)}


def main() -> int:
    try:
        with vunit.VirtualUnit(profile="screens") as u:
            out = walk(u)
    except (mm.MemoryBudgetError, vunit.RendererMissing) as e:
        print(f"memory-walk: FAIL: {e}", file=sys.stderr)
        return 1
    if "--json" in sys.argv:
        print(json.dumps(out, indent=1))
    else:
        n = out["numbers"]
        print(f"memory-walk: ok: {len(out['opened'])} screens and features opened and closed, back at the baseline; peak internal {out['peak']['internal']:,} B (lowest free {n['internal_free_lowest']:,}, gate 24,000)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
