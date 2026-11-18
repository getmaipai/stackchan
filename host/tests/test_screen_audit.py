# ruff: noqa: E501
"""The physical screen standard (docs/design/screen-style.md, scripts/virtual-unit/screen_standard.py): every touch screen is audited with the unit's own geometry (click areas, line heights).
The failures held in docs/design/screen-audit-baseline.json are today's debt: they may only shrink; a screen that is not in the baseline (a new screen) must have none. Needs the screens renderer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VU = ROOT / "scripts" / "virtual-unit"
sys.path.insert(0, str(VU))
pytestmark = pytest.mark.skipif(not (ROOT / ".runs" / "vu-screens" / "render").exists(), reason="screens renderer not built")


def test_no_screen_is_worse_than_its_baseline_and_a_new_screen_has_no_failure():
    import screen_audit as sa

    baseline = json.loads((ROOT / "docs" / "design" / "screen-audit-baseline.json").read_text())
    worse, new = [], []
    for name in sa.screens():
        res, _ = sa.audit(name)
        n = len(res["fails"])
        if name not in baseline:
            if n:
                new.append((name, n, res["fails"][:2]))
        elif n > baseline[name]["fails"]:
            worse.append((name, baseline[name]["fails"], n, res["fails"][:2]))
    assert not new, f"new screens must meet the standard (targets 48 px or more, 8 px gaps, text 16 px or more, nothing clipped): {new}"
    assert not worse, f"a screen got worse than its baseline (lower docs/design/screen-audit-baseline.json only when a screen got better): {worse}"


def test_the_standard_comes_from_one_panel_size():
    import screen_standard as std

    assert 7.7 < std.PX_PER_MM < 8.0 and std.PRIMARY_PX == 56 and std.SECONDARY_PX == 48 and std.GAP_PX == 8
    assert abs(std.px(7.0) - 55) <= 1 and abs(std.mm(56) - 7.1) < 0.1


def test_the_audit_sees_a_known_bad_screen_and_a_known_good_one():
    import screen_audit as sa

    bad = sa.judge([{"x1": 4, "y1": 32, "x2": 79, "y2": 75, "scroll": 0, "own": [0, 0, 0, 0]}, {"x1": 4, "y1": 80, "x2": 79, "y2": 123, "scroll": 0, "own": [0, 0, 0, 0]}], [])
    assert len(bad["fails"]) >= 2   # two 44 px tabs: under 48 each, and 4 px apart
    good = sa.judge([{"x1": 16, "y1": 40, "x2": 100, "y2": 96, "scroll": 0, "own": [0, 0, 0, 0]}, {"x1": 112, "y1": 40, "x2": 196, "y2": 96, "scroll": 0, "own": [0, 0, 0, 0]}], [{"x1": 0, "y1": 0, "x2": 50, "y2": 23, "line": 23, "scroll": 0, "text": "Hello"}])
    assert not good["fails"] and not good["warnings"]
