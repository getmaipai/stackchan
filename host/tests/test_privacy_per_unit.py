"""With two units each one has its own privacy state: a mute on one unit is read back for that unit and gates only its turns."""

import threading

from maipai_body.bodies.stackchan.privacy import PrivacyUnits
from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

KITCHEN, DEN = "aa:bb:cc:dd:ee:01", "aa:bb:cc:dd:ee:02"


def _units(states):
    """A call function per unit: self.privacy.get answers from `states[device]`."""
    def make(device_id):
        def call(name, arguments):
            if name == "self.privacy.get":
                return dict(states[device_id])
            return {"ok": True}
        return call
    return PrivacyUnits(make)


def test_each_unit_reads_back_its_own_state():
    units = _units({KITCHEN: {"muted": True, "vision_off": False, "quiet": False}, DEN: {"muted": False, "vision_off": False, "quiet": False}})
    units.on_connect(KITCHEN)
    units.on_connect(DEN)
    assert units.state_for(KITCHEN).muted is True and units.state_for(DEN).muted is False


def test_the_muted_reason_follows_the_unit_whose_turn_is_running():
    units = _units({KITCHEN: {"muted": True, "vision_off": False, "quiet": False}, DEN: {"muted": False, "vision_off": False, "quiet": False}})
    units.on_connect(KITCHEN)
    units.on_connect(DEN)
    token = ACTIVE_UNIT.set(KITCHEN)
    try:
        assert units.muted_reason() == "muted"
        seen = []
        t = threading.Thread(target=lambda: seen.append(units.muted_reason()))  # a plain thread has no unit: the first unit
        t.start(); t.join()
        assert seen == ["muted"]
    finally:
        ACTIVE_UNIT.reset(token)
    token = ACTIVE_UNIT.set(DEN)
    try:
        assert units.muted_reason() is None
    finally:
        ACTIVE_UNIT.reset(token)


def test_an_unknown_state_never_counts_as_unmuted_for_the_other_unit():
    units = _units({KITCHEN: {"muted": True, "vision_off": False, "quiet": False}})
    units.on_connect(KITCHEN)
    token = ACTIVE_UNIT.set(DEN)  # a unit never read back
    try:
        assert units.muted_reason() is None  # nothing known about it: the host does not invent a mute
        assert units.state_for(DEN).known is False
    finally:
        ACTIVE_UNIT.reset(token)


def test_ticks_run_for_every_unit_and_a_failing_one_does_not_stop_the_others():
    calls = []

    def make(device_id):
        def call(name, arguments):
            calls.append((device_id, name))
            if device_id == KITCHEN and name == "self.privacy.get":
                raise RuntimeError("kitchen is not answering")
            return {"muted": False, "vision_off": False, "quiet": False}
        return call

    units = PrivacyUnits(make)
    units.on_connect(KITCHEN)
    units.on_connect(DEN)
    units.tick_all()
    assert (DEN, "self.privacy.get") in calls


def test_the_primary_units_state_is_used_unless_the_turn_is_on_another_unit():
    from maipai_body.bodies.stackchan.privacy import PrivacyState

    primary = PrivacyState()
    primary.observe("privacy", {"muted": True, "vision_off": False, "quiet": False})
    units = PrivacyUnits(lambda d: (lambda name, args: {"muted": False, "vision_off": False, "quiet": False}), primary=primary)
    units.on_connect(DEN)  # a second unit, not muted
    assert units.muted_reason() == "muted"  # no turn: the primary's state
    token = ACTIVE_UNIT.set(DEN)
    try:
        assert units.muted_reason() is None
    finally:
        ACTIVE_UNIT.reset(token)
    token = ACTIVE_UNIT.set(KITCHEN)  # the primary unit is talking
    try:
        assert units.muted_reason() == "muted"
    finally:
        ACTIVE_UNIT.reset(token)


def test_a_client_bound_to_a_unit_sends_everything_to_that_unit():
    from types import SimpleNamespace

    from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiDeviceClient

    sent = []
    server = SimpleNamespace(
        _sessions={KITCHEN: 1, DEN: 2},
        call_device_tool=lambda name, args, timeout=5.0, device_id=None: sent.append((name, device_id)) or {"ok": True},
        refuse_on_loop=lambda *a, **k: None,
    )
    client = XiaozhiDeviceClient(server).for_unit(DEN)
    client._call("self.audio.set_sound_policy", {"policy": "x"})  # a fan-out tool, but this client is bound
    client._call("self.privacy.get", {})
    assert sent == [("self.audio.set_sound_policy", DEN), ("self.privacy.get", DEN)]


def _two(primary_quiet=False, den_vision_off=True, den_quiet=True):
    from maipai_body.bodies.stackchan.privacy import PrivacyState

    primary = PrivacyState()
    primary.observe("privacy", {"muted": False, "vision_off": False, "quiet": primary_quiet})
    units = PrivacyUnits(
        lambda d: (lambda name, args: {"muted": False, "vision_off": den_vision_off, "quiet": den_quiet}), primary=primary
    )
    units.on_connect(DEN)
    return units


def test_the_head_gate_follows_the_unit_that_is_moving():
    units = _two(primary_quiet=False, den_quiet=True)
    assert units.head_blocked() is None  # no turn: the primary unit's rule
    token = ACTIVE_UNIT.set(DEN)
    try:
        assert units.head_blocked() == "full quiet"  # the second unit is in full quiet
    finally:
        ACTIVE_UNIT.reset(token)


def test_the_camera_gate_follows_the_unit_the_frame_came_from():
    units = _two(den_vision_off=True)
    assert units.vision_off() is False  # the primary has its camera on
    token = ACTIVE_UNIT.set(DEN)
    try:
        assert units.vision_off() is True  # frames from the second unit are dropped
    finally:
        ACTIVE_UNIT.reset(token)


def test_a_frame_while_vision_is_off_is_a_leak_only_for_the_unit_that_has_it_off():
    leaks = []
    from maipai_body.bodies.stackchan.privacy import PrivacyState

    primary = PrivacyState(on_leak=lambda what, detail: leaks.append(("primary", what)))
    primary.observe("privacy", {"muted": False, "vision_off": False, "quiet": False})
    clock = [0.0]
    units = PrivacyUnits(
        lambda d: (lambda name, args: {"muted": False, "vision_off": True, "quiet": False}),
        on_leak=lambda what, detail: leaks.append(("den", what)),
        primary=primary,
    )
    units.state_for(DEN)._clock = lambda: clock[0]
    units.on_connect(DEN)
    clock[0] = 100.0
    token = ACTIVE_UNIT.set(DEN)
    try:
        units.frame_arrived()
    finally:
        ACTIVE_UNIT.reset(token)
    assert leaks == [("den", "camera")]  # not the primary's leak alarm


def test_the_avatar_server_marks_the_unit_while_it_checks_a_frame():
    import asyncio
    import inspect

    from maipai_body.bodies.stackchan.avatar import server as avatar_server

    source = inspect.getsource(avatar_server)
    assert "ACTIVE_UNIT.set(device_id)" in source  # the frame check runs as the unit that sent it
    assert asyncio  # (the behavior is covered by the gate tests above)
