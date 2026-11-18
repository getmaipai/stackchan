"""Per-unit touch handling (docs/plan/per-unit-behavior.md, step 2): a tap on the second unit reaches only the second unit."""

from __future__ import annotations

from types import SimpleNamespace

from maipai_body.unit_behaviors import UnitBehaviors


class FakeBehavior:
    def __init__(self, name: str, fail: bool = False) -> None:
        self.name, self.fail = name, fail
        self.event_poll = None
        self.touched: list = []
        self.ticked = 0
        self.reaction_tick = self._reaction_tick
        self.orientation_ticks = 0
        self.orientation_tick = lambda: setattr(self, 'orientation_ticks', self.orientation_ticks + 1)
        self.orientation = SimpleNamespace(reassert=lambda: self.warnings.append('reasserted'))
        self.warnings: list[str] = []

    def wake_on_touch(self, now: float) -> bool:
        if self.fail:
            raise RuntimeError("boom")
        self.touched.extend(self.event_poll())
        return False

    def _reaction_tick(self) -> None:
        self.ticked += 1

    def _warn_limited(self, key: str, message: str) -> None:
        self.warnings.append(message)


def _rig(connected, primary="a1"):
    made: dict[str, FakeBehavior] = {}

    def make(device_id: str) -> FakeBehavior:
        made[device_id] = FakeBehavior(device_id, fail=device_id.startswith("bad"))
        return made[device_id]

    units = UnitBehaviors(primary_id=lambda: primary, connected=lambda: list(connected), make_behavior=make)
    units.scopes = []
    real = units._scope
    units._scope = lambda d: (units.scopes.append(d), real(d))[1]
    return units, made


def tap(kind="head_touch"):
    return SimpleNamespace(kind=kind, extra={"tap": 1})


def test_a_tap_on_the_second_unit_reaches_only_that_unit():
    units, made = _rig(["a1", "b2", "c3"])
    units.feed("b2", [tap()])
    units.feed("c3", [tap("shake")])
    units.tick()
    assert [e.kind for e in made["b2"].touched] == ["head_touch"]
    assert [e.kind for e in made["c3"].touched] == ["shake"]
    assert "a1" not in made, "the first unit keeps the main behavior and gets no second one"


def test_events_of_the_first_unit_are_ignored_here():
    units, made = _rig(["a1", "b2"])
    units.feed("a1", [tap()])
    units.tick()
    assert made == {} and units.units() == []


def test_one_unit_failing_never_stops_another():
    units, made = _rig(["a1", "bad2", "c3"])
    units.feed("bad2", [tap()])
    units.feed("c3", [tap()])
    units.tick()
    assert made["bad2"].warnings and len(made["c3"].touched) == 1 and made["c3"].ticked == 1


def test_events_are_read_once_and_a_unit_that_left_is_dropped():
    connected = ["a1", "b2"]
    units, made = _rig(connected)
    units.feed("b2", [tap(), tap()])
    units.tick()
    units.tick()
    assert len(made["b2"].touched) == 2, "the second tick finds nothing left to read"
    connected.remove("b2")
    units.tick()
    assert units.units() == []


def test_a_flood_of_events_is_capped():
    units, made = _rig(["a1", "b2"])
    units.feed("b2", [tap() for _ in range(1000)])
    units.tick()
    assert len(made["b2"].touched) == 200


def test_the_unit_runs_inside_its_own_scope_so_its_faces_go_to_it(tmp_path):
    from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

    units, made = _rig(["a1", "b2"])
    seen: list = []
    units.feed("b2", [tap()])
    made["b2"].reaction_tick = lambda: seen.append(ACTIVE_UNIT.get())
    units.tick()
    assert seen == ["b2"] and ACTIVE_UNIT.get() is None, "the scope is set while the unit's behavior runs and removed after"


def test_the_orientation_timer_runs_per_unit_and_a_connect_reasserts_the_pose():
    units, made = _rig(["a1", "b2"])
    units.feed("b2", [])
    units.tick()
    units.tick()
    assert made["b2"].orientation_ticks == 2
    units.on_connect("b2")
    units.on_connect("a1")   # the first unit's own wiring does this
    assert made["b2"].warnings == ["reasserted"] and "a1" not in made
