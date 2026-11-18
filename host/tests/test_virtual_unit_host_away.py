# ruff: noqa: E501
"""What the unit does while its host is away (scripts/virtual-unit/host_away.py; patches 143 and SF49): the Offline label after 45 s, the plain-words notice after 10 minutes and every 30
minutes, and the reconnect wait (doubling with jitter, capped at 30 s then 120 s), all from the unit's own reconnect core. Needs the screens renderer."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VU = ROOT / "scripts" / "virtual-unit"
sys.path.insert(0, str(VU))
needs_render = pytest.mark.skipif(not (ROOT / ".runs" / "vu-screens" / "render").exists(), reason="screens renderer not built")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, VU / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ha = _load("host_away")
vunit = _load("vunit")


def test_the_backoff_rules_are_the_patchs_own_core():
    L = ha.lib()
    assert (L.rc_cap(0), L.rc_cap(599_999), L.rc_cap(600_000)) == (30_000, 30_000, 120_000)
    assert [L.rc_grow(d, 30_000) for d in (1000, 2000, 4000, 8000, 16000, 30000)] == [2000, 4000, 8000, 16000, 30000, 30000]
    assert 4000 <= L.rc_wait(4000, 30_000, 123456) <= 5000   # the delay plus up to a quarter of it
    assert L.rc_wait(30_000, 30_000, 99999) == 30_000        # never above the cap
    assert L.rc_notice_due(599_000, 0) == 0 and L.rc_notice_due(600_000, 0) == 1
    assert L.rc_notice_due(1_000_000, 600_000) == 0 and L.rc_notice_due(2_400_000, 600_000) == 1   # once, then every 30 minutes


@needs_render
def test_the_label_after_45_seconds_the_notice_after_ten_minutes_then_every_half_hour_and_the_waits_never_pass_the_cap():
    with vunit.VirtualUnit(profile="screens") as u:
        away = u.host_away
        away.link_lost()
        u.jump(44_000)
        away.tick(u.now_ms)
        assert not away.label                                   # a hub restart under 45 s shows nothing
        u.jump(2_000)
        away.tick(u.now_ms)
        assert away.label
        for minute in range(1, 130):                            # two hours, a minute at a time
            u.jump(60_000)
            away.tick(u.now_ms)
        times = [t // 60_000 for t, _ in away.notices]
        assert times[0] == 10 and len(times) == 4 and all(b - a >= 30 for a, b in zip(times, times[1:]))   # at 10 minutes, then every 30
        assert all(text == ha.NOTICE["en"] for _, text in away.notices)
        first = [w for t, w in away.attempts if t < 600_000]
        assert first and max(first) <= 30_000 and all(w <= 120_000 for _, w in away.attempts)
        away.link_up()
        assert away.since is None and not away.label


def test_every_language_has_the_notice_and_it_names_home_and_the_wifi():
    assert set(ha.NOTICE) == {"en", "es", "fr", "de", "pt", "it"}
    for lang, text in ha.NOTICE.items():
        assert "Home" in text and len(text) < 100, lang
