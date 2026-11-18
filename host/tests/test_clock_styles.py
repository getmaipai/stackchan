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
