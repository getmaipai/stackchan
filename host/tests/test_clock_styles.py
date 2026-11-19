"""Patch UX14 on the virtual unit: a tap on the clock page cycles classic, ring, date and time and back; a tap on a sleeping unit changes nothing.
Needs the screens renderer (bash scripts/virtual-unit/build-screens.sh). Placement: host-side test."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vunit", ROOT / "scripts" / "virtual-unit" / "vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)

pytestmark = pytest.mark.skipif(not (ROOT / ".runs" / "vu-screens" / "render").exists(), reason="screens renderer not built")
SETUP = ["style big_eyes", "bbar always", "bstatus 80 0 1 1 1", "pset hh 9", "pset mm 41"]


def shot(u, ms=600):
    u.advance(ms)
    return u.snapshot()


def open_clock(u, extra=()):
    for line in SETUP + list(extra):
        u.raw(line)
    u.raw("pshow clock")


def test_tap_cycles_three_styles_and_back():
    with vunit.VirtualUnit(profile="screens") as u:
        open_clock(u)
        frames = [shot(u)]
        for _ in range(3):
            u.raw("pclick 20 60")
            frames.append(shot(u))
        assert len({frames[0], frames[1], frames[2]}) == 3, "each of the first two taps must show a different style"
        assert frames[3] != frames[2] and frames[3] != frames[1], "the third tap leaves date and time for the classic style"


def test_tap_on_a_sleeping_unit_changes_nothing():
    with vunit.VirtualUnit(profile="screens") as u:
        open_clock(u, ["pset asleep 1"])
        before = shot(u)
        u.raw("pclick 20 60")
        after = shot(u)
        assert before == after, "a tap on a sleeping unit must leave the style alone"


def _bbox(png):
    import thumbnails as tn
    w, h, rows = tn._rows(png)
    cols = [x // 3 for r in rows[40:140] for x in range(0, len(r), 3) if r[x] > 200]
    return (min(cols), max(cols), len(cols)) if cols else None


def test_the_flip_closes_to_a_line_and_opens_on_the_new_style():
    import sys
    sys.path.insert(0, str(ROOT / "scripts" / "virtual-unit"))
    with vunit.VirtualUnit(profile="screens") as u:
        open_clock(u)
        u.advance(700)
        before = _bbox(u.snapshot_now())
        u.raw("pclick 20 60")
        widths = []
        for _ in range(8):
            u.raw("advance 33")
            b = _bbox(u.snapshot_now())
            widths.append(0 if b is None else b[1] - b[0])
        assert min(widths) < 60, "the page must close to near a line in the middle of the flip"
        assert widths[0] < before[1] - before[0], "the first frames narrow"
        assert widths[-1] > 60 and widths[-1] > min(widths), "the new style opens again"


def test_a_tap_during_the_flip_is_ignored():
    with vunit.VirtualUnit(profile="screens") as u:
        open_clock(u)
        u.advance(700)
        u.raw("pclick 20 60")
        u.advance(100)
        u.raw("pclick 20 60")   # mid-flip: ignored, so the page ends in the ring style, not in date and time
        u.advance(600)
        two = _bbox(u.snapshot_now())
    with vunit.VirtualUnit(profile="screens") as u:
        open_clock(u)
        u.advance(700)
        u.raw("pclick 20 60")
        u.advance(700)
        one = _bbox(u.snapshot_now())
    assert two[:2] == one[:2], "a second tap during the flip must not change the style again"
