# ruff: noqa: E501
"""Pickup events (firmware patch TB04) through the host's real handlers: the companion that reads the unit's event queue, the
behavior's touch poll and the reactions. The unit sends lifted, carried, set_down and shaken (each with the axis); nothing
here is a Python stand-in for those three pieces. The owner has not yet lifted a unit for a hardware check (merge note), so
this is the evidence the host side takes them in and does the right small things."""

from __future__ import annotations

import json
import random

import pytest

from maipai_body.app import StackChanBehavior
from maipai_body.bodies.stackchan.adapter import StackChanRobotAdapter
from maipai_body.bodies.stackchan.companion import StackChanCompanion
from maipai_body.bodies.stackchan.fake import FakeStackChanDeviceClient
from maipai_body.bodies.stackchan.reactions import Reactions


def _queue(*batches):
    """What self.robot.get_events answers on each poll: the unit's own JSON, one list per look."""
    pending = [json.dumps(list(batch)) for batch in batches]
    return lambda name, args: pending.pop(0) if pending else "[]"


def _unit_event(kind, at_ms, **extra):
    return {"kind": kind, "at_ms": at_ms, **extra}


class _Rig:
    def __init__(self, *batches):
        self.faces: list[str] = []
        self.said: list[str] = []
        self.now = [100.0]
        self.behavior = StackChanBehavior(StackChanRobotAdapter(FakeStackChanDeviceClient()).robot)
        companion = StackChanCompanion(_queue(*batches))
        self.behavior.event_poll = companion.poll_events
        self.reactions = Reactions(
            face=self.faces.append,
            say=lambda text: self.said.append(text) or True,
            clock=lambda: self.now[0],
            rng=random.Random(2),
        )
        self.behavior.reaction = self.reactions.on_events

    def look(self, at: float) -> bool:
        return self.behavior.wake_on_touch(at)

    def close(self) -> None:
        self.behavior.close()


@pytest.fixture
def make():
    rigs = []

    def build(*batches):
        rig = _Rig(*batches)
        rigs.append(rig)
        return rig

    yield build
    for rig in rigs:
        rig.close()


def test_the_companion_keeps_each_pickup_event_and_its_axis_name_as_the_unit_sent_them() -> None:
    companion = StackChanCompanion(
        _queue(
            [
                _unit_event("lifted", 10, axis="z"),
                _unit_event("carried", 1600, axis="z"),
                _unit_event("set_down", 3200, axis="z"),
                _unit_event("shaken", 4800, axis="x"),
            ]
        )
    )
    events = companion.poll_events()
    assert [e.kind for e in events] == ["lifted", "carried", "set_down", "shaken"]
    assert [e.at_ms for e in events] == [10, 1600, 3200, 4800]


@pytest.mark.parametrize("kind", ["lifted", "carried", "set_down", "shaken"])
def test_a_pickup_event_reaches_the_reactions_and_makes_no_touch_reaction(make, kind) -> None:
    rig = make([], [_unit_event(kind, 5, axis="z")])
    rig.look(0.0)  # the first look after a pause only empties the unit's queue
    rig.look(5.0)
    assert (
        rig.faces == [] and rig.said == []
    )  # the unit shows its own surprise or smile; the host adds no pet heart or line


def test_a_sleeping_unit_that_is_lifted_wakes_once_and_a_carry_does_not_wake_it_again_at_once(
    make,
) -> None:
    rig = make(
        [],
        [_unit_event("lifted", 5, axis="z")],
        [_unit_event("carried", 1700, axis="z")],
        [_unit_event("carried", 3300, axis="z")],
    )
    rig.behavior._rest._stage = "asleep"
    rig.look(0.0)
    assert rig.look(1.0) is True  # the lift wakes it
    assert rig.look(2.0) is False  # the carry events that follow are inside the wake cooldown
    assert rig.look(3.0) is False


def test_an_awake_unit_just_takes_the_event_in(make) -> None:
    rig = make([], [_unit_event("lifted", 5, axis="z")], [_unit_event("set_down", 2000, axis="z")])
    rig.look(0.0)
    assert rig.look(5.0) is False
    assert rig.look(10.0) is False


def test_a_pickup_never_cancels_a_look_around_as_a_touch_would(make) -> None:
    rig = make([], [_unit_event("lifted", 5, axis="z")])
    rig.look(0.0)
    started = rig.behavior._search.start("person", 4.0)
    assert started and rig.behavior._search.active
    rig.look(5.0)
    assert rig.behavior._search.active  # a head touch ends it; being lifted is not a head touch
    rig.behavior._search.stop(9.0)


def test_a_shake_in_the_hand_is_not_a_table_shake_so_no_dizzy_line_is_spoken(make) -> None:
    """The unit's own shaken event is not the older sensor event shake the host answers with a spoken line."""
    rig = make(
        [],
        [_unit_event("shaken", 5, axis="x")],
        [_unit_event("shaken", 900, axis="x")],
        [_unit_event("shaken", 2600, axis="x")],
    )
    for at in (0.0, 5.0, 6.0, 7.0):
        rig.look(at)
    assert rig.said == [] and rig.faces == []
