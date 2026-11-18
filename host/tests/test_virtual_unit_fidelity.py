"""Handlers the virtual unit shares with the unit's own cores, checked against the core's rules (docs/dev/virtual-unit-fidelity.md)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

VU = Path(__file__).resolve().parents[2] / "scripts" / "virtual-unit"


def _registry():
    spec = importlib.util.spec_from_file_location("vunit_fid", VU / "vunit.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("vunit_fid", mod)
    spec.loader.exec_module(mod)
    return mod._tools.REGISTRY


def _locked_unit(code="4821"):
    u = SimpleNamespace(state={}, now_ms=1000)
    reg = _registry()
    a = reg["self.lock.status"](u, {})  # creates the app state
    u.state["apps"].update(code=code, locked=True, ui_on=True)
    return u, reg, a


def _press(u, reg, digits):
    out = None
    for d in digits:
        out = reg["self.lock.bench_key"](u, {"key": d})
    return out


def test_keypad_checks_from_the_fourth_digit_and_clears_after_six_wrong_ones():
    u, reg, _ = _locked_unit("4821")
    reg["self.lock.bench_touch"](u, {})
    assert _press(u, reg, "482")["unlocked"] is False  # three digits: never checked
    assert _press(u, reg, "1")["unlocked"] is True  # the fourth matches: no enter key
    u, reg, _ = _locked_unit("4821")
    reg["self.lock.bench_touch"](u, {})
    assert _press(u, reg, "111111")["unlocked"] is False
    assert u.state["apps"]["entered"] == ""  # six wrong digits clear the entry
    assert _press(u, reg, "4821")["unlocked"] is True


def test_keypad_ignores_keys_when_it_is_not_up_and_goes_back_after_fifteen_seconds():
    u, reg, _ = _locked_unit("4821")
    assert _press(u, reg, "4821")["unlocked"] is False and u.state["apps"]["locked"]  # no touch yet: keys ignored
    reg["self.lock.bench_touch"](u, {})
    u.now_ms += 14000
    assert _press(u, reg, "48")["keypad"] is True
    u.now_ms += 15000
    assert _press(u, reg, "2")["keypad"] is False and u.state["apps"]["entered"] == ""  # timed out: back to the lock screen
    assert _press(u, reg, "1")["unlocked"] is False
