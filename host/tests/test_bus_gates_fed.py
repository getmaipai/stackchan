"""The command-bus gates for a child present, a remote cue and a sleeping unit are fed from real state."""

from types import SimpleNamespace

from maipai_body import remote_activity as ra
from maipai_body.bodies.stackchan.turn import StackChanTurnBridge

UNIT = "aa:bb:cc:dd:ee:01"


def test_remote_activity_knows_when_a_unit_has_an_open_remote_session(tmp_path):
    activity = ra.RemoteActivity(
        lambda *a, **k: {"ok": True},
        lambda *a, **k: True,
        ra.RemoteStore(tmp_path / "r.json"),
        ra.RemoteLog(tmp_path / "l.jsonl"),
    )
    assert not activity.session_active(UNIT)
    activity._sessions[(UNIT, "Phone")] = 0.0
    assert activity.session_active(UNIT) and not activity.session_active("aa:bb:cc:dd:ee:02")


def test_a_child_present_note_expires():
    now = [100.0]
    bridge = StackChanTurnBridge.__new__(StackChanTurnBridge)
    bridge._child_until = {}
    bridge._clock = lambda: now[0]
    bridge.note_child_present(UNIT, True, seconds=60)
    assert bridge.child_present_for(UNIT)
    now[0] = 161.0
    assert not bridge.child_present_for(UNIT)
    bridge.note_child_present(UNIT, True, seconds=60)
    bridge.note_child_present(UNIT, False)
    assert not bridge.child_present_for(UNIT)


def test_the_hub_command_feeds_the_child_gate():
    from maipai_body import app

    bridge = StackChanTurnBridge.__new__(StackChanTurnBridge)
    bridge._child_until, bridge._clock = {}, lambda: 10.0
    voice = SimpleNamespace(gate_bridge=bridge, connected_devices=lambda: [UNIT])
    assert app._note_child(voice, {"present": True, "seconds": 30}) == {"ok": True}
    assert bridge.child_present_for(UNIT)
    assert app._note_child(SimpleNamespace(), {"present": True}) == {"ok": False}
