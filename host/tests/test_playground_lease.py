"""The playground lease and scope: one session per robot, expiry, clean release, per-robot isolation, forbidden tools."""

import pytest

from maipai_body.playground_lease import FORBIDDEN_PREFIXES, LeaseManager, tool_allowed


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


def test_a_second_session_gets_a_plain_refusal_and_the_first_keeps_control():
    clock = Clock()
    leases = LeaseManager(clock=clock)
    assert leases.acquire("u1", "s1", "Ana's laptop") == (True, "")
    ok, why = leases.acquire("u1", "s2", "Ben's laptop")
    assert not ok and "Ana's laptop" in why and leases.holder("u1") == "Ana's laptop"
    assert leases.acquire("u1", "s1", "Ana's laptop")[0]  # the same session renews


def test_the_lease_expires_when_heartbeats_stop_and_the_next_session_gets_it():
    clock = Clock()
    leases = LeaseManager(clock=clock, ttl=15)
    leases.acquire("u1", "s1", "Ana")
    clock.t = 10
    assert leases.heartbeat("u1", "s1")
    clock.t = 24
    assert leases.holder("u1") == "Ana"  # beat at 10, ttl 15
    clock.t = 30
    assert leases.holder("u1") is None and leases.acquire("u1", "s2", "Ben")[0]
    assert leases.log.rows[0]["why"] == "no heartbeat" and leases.log.rows[0]["who"] == "Ana"


def test_a_clean_release_frees_the_robot_and_logs_a_row():
    leases = LeaseManager(clock=Clock())
    leases.acquire("u1", "s1", "Ana")
    assert not leases.release("u1", "s2") and leases.release("u1", "s1")
    assert leases.acquire("u1", "s2", "Ben")[0] and leases.log.rows[0]["why"] == "released"


def test_each_robot_has_its_own_lease():
    leases = LeaseManager(clock=Clock())
    assert leases.acquire("u1", "s1", "Ana")[0] and leases.acquire("u2", "s2", "Ben")[0] and leases.acquire("u3", "s1", "Ana")[0]
    assert leases.holder("u1") == "Ana" and leases.holder("u2") == "Ben"


@pytest.mark.parametrize("tool", ["self.lock.set", "self.firmware.update", "self.pair_start", "self.link.key", "self.settings.set", "self.pack.begin", "self.assets.install"])
def test_the_playground_scope_never_reaches_lock_update_pairing_settings_or_packs(tool):
    ok, why = tool_allowed(tool)
    assert not ok and "playground cannot" in why


def test_camera_tools_need_live_view_and_ordinary_tools_pass():
    assert not tool_allowed("self.camera.frame")[0] and tool_allowed("self.camera.frame", live_view_allowed=True)[0]
    assert tool_allowed("self.robot.set_head_angles") == (True, "")
    assert FORBIDDEN_PREFIXES


def test_a_call_needs_the_lease_and_then_the_scope():
    leases = LeaseManager(clock=Clock())
    assert not leases.check("u1", "s1", "self.robot.set_head_angles")[0]
    leases.acquire("u1", "s1", "Ana")
    assert leases.check("u1", "s1", "self.robot.set_head_angles")[0]
    assert not leases.check("u1", "s1", "self.lock.set")[0] and not leases.check("u1", "s2", "self.robot.set_head_angles")[0]
