"""The playground's backends (scripts/virtual-unit/backends.py) against the fake host (scripts/virtual-unit/fake_host.py, which uses the host's own lease and scope code): the one-active-connection
rule, the plain refusal when another playground holds a robot, the lease that ends without heartbeats, the scope that keeps lock and settings out of reach, and the LIVE banner."""
import sys
from pathlib import Path

import pytest

VU = Path(__file__).resolve().parents[2] / "scripts" / "virtual-unit"
sys.path.insert(0, str(VU))
import backends as bk  # noqa: E402
import fake_host as fh  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class StubUnit:
    now_ms = 0

    def call(self, name, args):
        return {"ok": True, "name": name}

    def snapshot(self):
        return b"png"


@pytest.fixture()
def world():
    clock = Clock()
    host = fh.FakeHost(clock=clock)
    url = host.start()
    yield host, url, clock
    host.stop()


def manager(url, who="Ana's laptop", token=fh.TOKEN):
    return bk.BackendManager(bk.Simulation(StubUnit()), url, token, who)


def test_the_simulation_is_always_there_and_says_nothing_touches_a_robot(world):
    host, url, _ = world
    m = manager(url)
    assert m.status()["live"] is False and "Simulation" in m.status()["message"]
    ids = {b["id"]: b for b in m.list()}
    assert set(ids) == {"sim", "r1", "r2", "r3"} and ids["r3"]["online"] is False and ids["r1"]["busy_by"] is None
    assert m.active.call_tool("self.face.bench_emotion", {"emotion": "happy"})["ok"]


def test_connecting_shows_the_live_banner_and_tools_reach_the_robot(world):
    host, url, _ = world
    m = manager(url)
    st = m.connect("r1", 0)
    assert st["live"] is True and st["kind"] == "robot" and st["message"].startswith("LIVE") and "Kitchen robot" in st["message"]
    assert m.active.call_tool("self.robot.dance", {"name": "happy"})["ok"]
    assert host.robots["r1"].calls == [("self.robot.dance", {"name": "happy"})]
    assert m.active.snapshot().startswith(b"\x89PNG")
    m.disconnect()
    assert host.leases.holder("r1") is None and m.status()["live"] is False


def test_the_scope_keeps_lock_settings_and_updates_out_of_reach(world):
    host, url, _ = world
    m = manager(url)
    m.connect("r1", 0)
    for tool in ("self.lock.now", "self.settings.set", "self.update.start", "self.wifi.join"):
        with pytest.raises(bk.BackendError) as e:
            m.active.call_tool(tool, {})
        assert "cannot" in str(e.value) or "lock" in str(e.value) or "settings" in str(e.value)
    assert host.robots["r1"].calls == []


def test_a_robot_held_by_someone_else_is_refused_in_plain_words_and_the_simulation_stays(world):
    host, url, _ = world
    first, second = manager(url, "Ana's laptop"), manager(url, "Ben's phone")
    first.connect("r1", 0)
    st = second.connect("r1", 0)
    assert st["live"] is False and "Ana's laptop" in st["notice"] and "controlling this robot" in st["notice"]
    assert {b["id"]: b["busy_by"] for b in second.list()}["r1"] == "Ana's laptop"
    assert second.connect("r2", 0)["live"] is True   # another robot is free


def test_one_connection_at_a_time_the_old_one_is_released(world):
    host, url, _ = world
    m = manager(url)
    m.connect("r1", 0)
    m.connect("r2", 1)
    assert host.leases.holder("r1") is None and host.leases.holder("r2") == "Ana's laptop"
    assert m.active.id == "r2"


def test_the_lease_is_kept_by_heartbeats_and_lost_without_them(world):
    host, url, clock = world
    m = manager(url)
    m.connect("r1", 0)
    clock.t += 10
    m.tick(6)                      # a heartbeat is due after 5 s: the lease is renewed
    clock.t += 10
    m.tick(7)
    assert m.status()["live"] is True, "renewed leases survive"
    clock.t += 20                  # the page stopped answering: the host lets go
    m.tick(30)
    st = m.status()
    assert st["live"] is False and "no longer yours" in st["notice"] and host.leases.holder("r1") is None
    other = manager(url, "Ben's phone")
    assert other.connect("r1", 0)["live"] is True


def test_failures_say_what_went_wrong_and_what_to_do(world):
    host, url, _ = world
    assert "offline" in manager(url).connect("r3", 0)["notice"]
    assert "token" in manager(url, token="wrong").connect("r1", 0)["notice"]
    assert "No host is set" in bk.BackendManager(bk.Simulation(StubUnit())).connect("r1", 0)["notice"]
    down = manager("http://127.0.0.1:9")
    assert "cannot be reached" in down.connect("r1", 0)["notice"]
