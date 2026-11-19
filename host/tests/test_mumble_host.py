"""Host half of the mumble voice (decision 24): a text-only line with "mumble": true, sent only to a unit whose hello announced it."""

from __future__ import annotations

import asyncio

from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer


class _Rig:
    def __init__(self, features):
        self.sent: list[tuple[str, dict]] = []
        self.server = XiaozhiServer.__new__(XiaozhiServer)
        self.server._sessions = {"u1": object()}
        self.server._session_ids = {"u1": "s1"}
        self.server._session_features = {"u1": features}
        self.server._session_authorized = lambda device_id: True

        async def fake_json(ws, session, kind, payload):
            self.sent.append((kind, payload))

        self.server._json = fake_json


def test_a_unit_that_announced_mumble_gets_one_text_only_line():
    rig = _Rig({"mumble": True})
    assert asyncio.run(rig.server.send_mumble("u1", " Hello there ")) is True
    assert rig.sent == [("tts", {"state": "start"}), ("tts", {"state": "sentence_start", "text": "Hello there", "mumble": True}), ("tts", {"state": "stop"})]


def test_a_unit_that_did_not_announce_it_is_sent_nothing():
    rig = _Rig({"notify": True})
    assert asyncio.run(rig.server.send_mumble("u1", "Hello")) is False
    assert rig.sent == []


def test_empty_text_an_unknown_unit_or_an_unpaired_session_send_nothing():
    rig = _Rig({"mumble": True})
    assert asyncio.run(rig.server.send_mumble("u1", "  ")) is False
    assert asyncio.run(rig.server.send_mumble("zz", "Hello")) is False
    rig.server._session_authorized = lambda device_id: False
    assert asyncio.run(rig.server.send_mumble("u1", "Hello")) is False
    assert rig.sent == []


def test_a_line_that_cannot_be_spoken_falls_back_to_the_mumble_for_that_unit():
    import threading
    from types import SimpleNamespace

    from maipai_body.bodies.stackchan.turn import StackChanTurnBridge
    from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    sent: list[tuple[str, str]] = []

    async def send_mumble(device_id, text):
        sent.append((device_id, text))
        return True

    bridge = StackChanTurnBridge.__new__(StackChanTurnBridge)
    bridge.server = SimpleNamespace(_loop=loop, _sessions={"u1": 1, "u2": 2}, send_mumble=send_mumble)
    token = ACTIVE_UNIT.set("u2")
    try:
        assert bridge._mumble("I am here") is True
    finally:
        ACTIVE_UNIT.reset(token)
        loop.call_soon_threadsafe(loop.stop)
    assert sent == [("u2", "I am here")]
