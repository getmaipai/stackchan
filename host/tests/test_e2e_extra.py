# ruff: noqa: E501
"""The pieces of the extra end to end scenarios (scripts/virtual-unit/e2e_extra.py) that need no host process: the leak verdict, the unit's own cores as command line
programs (gesture, key schedule, remote session) and the long idle jump on the virtual unit. The scenarios themselves run in test_e2e_virtual_unit.py."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VU = ROOT / "scripts" / "virtual-unit"
sys.path.insert(0, str(VU))
spec = importlib.util.spec_from_file_location("e2e_extra", VU / "e2e_extra.py")
extra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extra)

needs_cc = pytest.mark.skipif(shutil.which("cc") is None or shutil.which("git") is None, reason="needs cc and git to build the unit's cores")
needs_render = pytest.mark.skipif(not (ROOT / ".runs" / "vu-screens" / "render").exists(), reason="the screens renderer is not built")

BASE = {"rss_mb": 200.0, "threads": 24, "fds": 28, "sockets": 8}


def test_no_growth_is_not_a_leak():
    assert extra.leak_verdict(BASE, {"rss_mb": 205.0, "threads": 25, "fds": 30, "sockets": 9}) == []


@pytest.mark.parametrize(
    ("after", "word"),
    [
        ({"rss_mb": 260.0, "threads": 24, "fds": 28, "sockets": 8}, "memory"),
        ({"rss_mb": 200.0, "threads": 40, "fds": 28, "sockets": 8}, "threads"),
        ({"rss_mb": 200.0, "threads": 24, "fds": 120, "sockets": 8}, "fds"),
        ({"rss_mb": 200.0, "threads": 24, "fds": 28, "sockets": 30}, "sockets"),
    ],
)
def test_each_kind_of_growth_is_named(after, word):
    verdict = extra.leak_verdict(BASE, after)
    assert len(verdict) == 1 and word in verdict[0]


def test_a_small_unit_does_not_fail_on_a_few_megabytes():  # 20 MB more is under the 25 MB floor
    assert extra.leak_verdict({**BASE, "rss_mb": 20.0}, {**BASE, "rss_mb": 40.0}) == []


@pytest.fixture(scope="module")
def cores():
    if shutil.which("cc") is None:
        pytest.skip("needs cc")
    return extra.shims()


@needs_cc
def test_the_touch_core_taps_on_and_holds_off(cores):
    touch = extra.Program(cores["touch_shim"])
    try:
        assert extra.gesture(touch, 150, 170, 120, (0, 0, 0))["result"] == "toggle:mute"
        assert extra.gesture(touch, 150, 170, 120, (1, 0, 0))["result"].startswith("ignored")
        assert extra.gesture(touch, 150, 170, 700, (1, 0, 0))["result"] == "toggle:mute"
        assert extra.gesture(touch, 150, 170, 700, (0, 0, 0))["result"].startswith("ignored")
    finally:
        touch.close()


@needs_cc
def test_the_key_schedule_core_agrees_with_the_hosts_own_digits(cores):
    from maipai_body.bodies.stackchan.xiaozhi.link_exchange import commit, sas

    pk_u, pk_h, n_u, n_h = bytes([1]) * 32, bytes([2]) * 32, bytes([3]) * 16, bytes([4]) * 16
    link = extra.Program(cores["link_shim"])
    try:
        assert link.ask(f"sas {pk_u.hex()} {pk_h.hex()} {n_u.hex()} {n_h.hex()}") == sas(pk_u, pk_h, n_u, n_h)
        assert link.ask(f"commit {pk_h.hex()} {pk_u.hex()} {n_h.hex()}") == commit(pk_h, pk_u, n_h).hex()
    finally:
        link.close()


@needs_cc
def test_the_first_host_id_of_a_remote_session_wins(cores):
    remote = extra.Program(cores["remote_shim"])
    try:
        remote.ask("session 1 111 1000")
        assert remote.ask("session 1 222 2000") == "active=1 host=111"
        assert remote.ask("call dance 222 3000") == "not_host"
        assert remote.ask("call dance 111 3000") == "ok"
        remote.ask("session 0 0 4000")
        assert remote.ask("host") == "0"
    finally:
        remote.close()


@needs_render
def test_a_unit_left_on_for_fifty_days_still_draws_and_fires_its_timer():
    spec_v = importlib.util.spec_from_file_location("vunit_idle", VU / "vunit.py")
    vunit = importlib.util.module_from_spec(spec_v)
    sys.modules["vunit_idle"] = vunit
    spec_v.loader.exec_module(vunit)
    day = 86_400_000
    with vunit.VirtualUnit(profile="screens") as unit:
        for days in (3, 22, 25):  # 3, 25 and 50 days in all: past 2^31 ms and past 2^32 ms
            unit.call("self.timer.set", {"seconds": 5, "label": "wait"})
            unit.jump(days * day)
            unit.advance(6000)
            assert unit.call("self.timer.list", {})["ringing"]
            unit.call("self.timer.stop", {})
            assert unit.count(0, 30, 320, 150)["lit"] > 1500
        assert unit.now_ms > 2**32
