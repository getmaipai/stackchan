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
