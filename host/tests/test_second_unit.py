"""A second connected unit must not break every call that names no unit."""

import pytest

from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer
from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore


def _server(tmp_path, sessions):
    server = XiaozhiServer(PairingStore(tmp_path / "p.json"), robot=None)
    server._sessions = dict(sessions)
    return server


def test_no_unit_named_with_two_connected_uses_the_longest_connected(tmp_path):
    server = _server(tmp_path, {"aa:bb:cc:dd:ee:01": "ws1", "aa:bb:cc:dd:ee:02": "ws2"})
    assert server._resolve_unit(None) == ("aa:bb:cc:dd:ee:01", "ws1")


def test_a_named_unit_is_used_even_when_it_is_the_second(tmp_path):
    server = _server(tmp_path, {"aa:bb:cc:dd:ee:01": "ws1", "aa:bb:cc:dd:ee:02": "ws2"})
    assert server._resolve_unit("aa:bb:cc:dd:ee:02") == ("aa:bb:cc:dd:ee:02", "ws2")


def test_no_unit_connected_and_unknown_unit_say_what_to_do(tmp_path):
    server = _server(tmp_path, {})
    with pytest.raises(ConnectionError, match="No StackChan is connected"):
        server._resolve_unit(None)
    server = _server(tmp_path, {"aa:bb:cc:dd:ee:01": "ws1"})
    with pytest.raises(ConnectionError, match="not connected"):
        server._resolve_unit("aa:bb:cc:dd:ee:09")


def test_a_call_made_during_a_unit_turn_goes_to_that_unit(tmp_path):
    from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

    server = _server(tmp_path, {"aa:bb:cc:dd:ee:01": "ws1", "aa:bb:cc:dd:ee:02": "ws2"})
    token = ACTIVE_UNIT.set("aa:bb:cc:dd:ee:02")  # the second unit is the one that is talking
    try:
        assert server._resolve_unit(None) == ("aa:bb:cc:dd:ee:02", "ws2")
        ACTIVE_UNIT.set("aa:bb:cc:dd:ee:99")  # a unit that is gone: back to the longest-connected
        assert server._resolve_unit(None)[0] == "aa:bb:cc:dd:ee:01"
    finally:
        ACTIVE_UNIT.reset(token)
    assert server._resolve_unit(None)[0] == "aa:bb:cc:dd:ee:01"


def test_the_turn_bridge_marks_the_talking_unit_for_the_whole_turn():
    import asyncio

    from maipai_body.bodies.stackchan.turn import StackChanTurnBridge
    from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

    seen = []
    bridge = StackChanTurnBridge.__new__(StackChanTurnBridge)

    async def inner(session_id, device_id, capture):
        seen.append(ACTIVE_UNIT.get())
        await asyncio.to_thread(lambda: seen.append(ACTIVE_UNIT.get()))  # worker threads see it too

    bridge._run_inner = inner
    asyncio.run(bridge._run("s", "aa:bb:cc:dd:ee:02", None))
    assert seen == ["aa:bb:cc:dd:ee:02", "aa:bb:cc:dd:ee:02"] and ACTIVE_UNIT.get() is None
