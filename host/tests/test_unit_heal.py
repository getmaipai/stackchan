"""Self-heal per unit (docs/plan/per-unit-behavior.md, step 5): each unit after the first has its own restart guard facts and wake self-test."""

from __future__ import annotations

from types import SimpleNamespace

from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer


def _server(primary="a1"):
    server = XiaozhiServer.__new__(XiaozhiServer)
    from maipai_body.bodies.stackchan.self_heal import SelfHealState, WakeSelfTest

    server.heal = SelfHealState()
    server._sessions = {"a1": 1, "b2": 2}
    server._speaking = set()
    server._turns_running = 0
    server.wake_tester = WakeSelfTest(server.heal)
    server.primary_unit = lambda: primary
    server.unit_hold_listeners = []
    server._unit_heals = {}
    return server


def test_the_first_unit_keeps_the_original_state_and_others_get_their_own():
    server = _server()
    assert server.heal_for("a1")[0] is server.heal and server.heal_for(None)[0] is server.heal
    state_b, tester_b = server.heal_for("b2")
    assert state_b is not server.heal and tester_b is not server.wake_tester
    assert server.heal_for("b2")[0] is state_b, "the same state each time"


def test_a_hold_on_the_second_unit_is_that_units_alone_and_lights_its_own_listener():
    server = _server()
    held: list[tuple[str, bool]] = []
    server.unit_hold_listeners.append(lambda device_id, hold: held.append((device_id, hold)))
    state_b, _ = server.heal_for("b2")
    state_b.observe("boot", {"heal_hold": 1, "heal_n": 3})
    assert state_b.hold is True and server.heal.hold is False
    assert held == [("b2", True)]


def test_before_the_app_names_a_first_unit_every_unit_is_the_first():
    server = _server(primary=None)
    assert server.heal_for("b2")[0] is server.heal
