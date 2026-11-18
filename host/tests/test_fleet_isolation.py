"""A turn's face goes only to the unit that asked; many turns at once are not starved by the default thread pool."""

import asyncio
import contextvars
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from maipai_body.bodies.stackchan.turn import StackChanTurnBridge
from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT


def test_the_expression_event_carries_the_talking_unit_into_the_side_worker():
    seen = []
    bridge = StackChanTurnBridge.__new__(StackChanTurnBridge)
    bridge._side = ThreadPoolExecutor(max_workers=2)
    bridge.expression_sink = lambda state, mood=None: seen.append((state, mood, ACTIVE_UNIT.get()))
    for unit in ("unit-a", "unit-b"):
        token = ACTIVE_UNIT.set(unit)
        try:
            bridge._emit_expression("reply_mood", mood="happy")
        finally:
            ACTIVE_UNIT.reset(token)
    bridge._side.shutdown(wait=True)
    assert sorted(seen) == [("reply_mood", "happy", "unit-a"), ("reply_mood", "happy", "unit-b")]


def test_a_face_goes_only_to_the_unit_of_the_turn_and_the_resting_face_to_all():
    from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer
    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore

    sent = []

    class Socket:
        def __init__(self, unit):
            self.unit = unit

        async def send(self, message):
            sent.append(self.unit)

    server = XiaozhiServer(PairingStore(), robot=None)
    server._sessions = {f"u{n}": Socket(f"u{n}") for n in range(10)}
    server._session_ids = {f"u{n}": f"s{n}" for n in range(10)}
    token = ACTIVE_UNIT.set("u4")
    try:
        asyncio.run(server.send_emotion("happy"))
    finally:
        ACTIVE_UNIT.reset(token)
    assert sent == ["u4"]
    sent.clear()
    asyncio.run(server.send_emotion("happy"))
    assert len(sent) == 10


def test_a_fleet_of_blocking_turns_all_progress_with_the_sized_pool():
    """Thirty turns that each block for a moment (like listening for an utterance) all finish together on the sized pool; the default pool could not."""
    async def run(workers):
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ThreadPoolExecutor(max_workers=workers))
        started = time.monotonic()
        await asyncio.gather(*[asyncio.to_thread(time.sleep, 0.3) for _ in range(30)])
        return time.monotonic() - started

    assert asyncio.run(run(256)) < 0.9
    assert asyncio.run(run(4)) > 1.5  # a small pool serializes them: what starving looks like


def test_turns_over_the_limit_are_told_to_wait_not_left_in_silence():
    said = []
    bridge = StackChanTurnBridge.__new__(StackChanTurnBridge)
    bridge._inflight, bridge.busy_at, bridge._playbacks = 70, 64, {"s1": SimpleNamespace(caption=lambda text: said.append(text))}
    bridge.on_error_line = lambda: said.append("tone")
    bridge._say_busy("s1")
    assert "tone" in said and any("busy" in t for t in said)
