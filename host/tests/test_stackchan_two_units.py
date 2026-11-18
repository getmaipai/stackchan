"""Two fake units connected to one XiaozhiServer: a tool call goes to the unit it names, a call that names none goes to the
unit connected the longest, and when the first unit drops the second keeps working (the scripted two-unit scenario of
docs/plan/friend-test-path-2026-11-18.md)."""

from __future__ import annotations

import asyncio
import time
import unittest

from stackchan_sim import StackChanFirmware
from websockets.asyncio.server import serve

from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer

KITCHEN = "02:00:00:00:00:61"
DEN = "02:00:00:00:00:62"


class TwoUnitsOneHostTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.pairing = PairingStore()

        async def on_audio(session: str, frame: bytes) -> None:
            return None

        self.service = XiaozhiServer(self.pairing, None, on_audio)
        self.server = await serve(self.service.handle, "127.0.0.1", 0)
        self.url = f"ws://127.0.0.1:{self.server.sockets[0].getsockname()[1]}"
        self.units: dict[str, StackChanFirmware] = {}

    async def asyncTearDown(self) -> None:
        for unit in self.units.values():
            await unit.stop()
        self.server.close()
        await self.server.wait_closed()

    async def connect(self, device_id: str, client_id: str) -> StackChanFirmware:
        self.pairing.request(device_id, client_id)
        token = self.pairing.approve(device_id, client_id)
        unit = StackChanFirmware(self.url, token, device_id=device_id, client_id=client_id)
        self.units[device_id] = unit
        await unit.start()
        await unit.wait_connected()
        return unit

    async def call(self, name: str, arguments: dict, unit: str | None = None):
        # the host's call is blocking and runs on the server's loop: call it from another thread, as the host's own loops do
        return await asyncio.to_thread(
            self.service.call_device_tool, name, arguments, device_id=unit, timeout=3.0
        )

    async def wait_until(self, predicate, timeout: float = 2.0) -> None:
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            await asyncio.sleep(0.01)
        self.assertTrue(predicate(), "condition did not become true before the deadline")

    async def test_each_call_reaches_only_the_unit_it_names(self) -> None:
        kitchen = await self.connect(KITCHEN, "00000000-0000-4000-8000-000000000061")
        den = await self.connect(DEN, "00000000-0000-4000-8000-000000000062")
        self.assertEqual(set(self.service._sessions), {KITCHEN, DEN})

        await self.call("self.audio_speaker.set_volume", {"volume": 30}, unit=DEN)
        await self.call("self.audio_speaker.set_volume", {"volume": 70}, unit=KITCHEN)

        self.assertEqual(
            [c for c in den.tool_calls if c[0] == "self.audio_speaker.set_volume"],
            [("self.audio_speaker.set_volume", {"volume": 30})],
        )
        self.assertEqual(
            [c for c in kitchen.tool_calls if c[0] == "self.audio_speaker.set_volume"],
            [("self.audio_speaker.set_volume", {"volume": 70})],
        )
        self.assertEqual((kitchen.volume, den.volume), (70, 30))

    async def test_a_call_that_names_no_unit_goes_to_the_longest_connected_one(self) -> None:
        kitchen = await self.connect(KITCHEN, "00000000-0000-4000-8000-000000000061")
        den = await self.connect(DEN, "00000000-0000-4000-8000-000000000062")
        await self.call("self.audio_speaker.set_volume", {"volume": 55})
        self.assertEqual(kitchen.volume, 55)
        self.assertNotEqual(den.volume, 55)

    async def test_the_second_unit_keeps_working_when_the_first_drops(self) -> None:
        kitchen = await self.connect(KITCHEN, "00000000-0000-4000-8000-000000000061")
        den = await self.connect(DEN, "00000000-0000-4000-8000-000000000062")
        await kitchen.stop()
        await self.wait_until(lambda: KITCHEN not in self.service._sessions)
        self.assertIn(DEN, self.service._sessions)

        await self.call(
            "self.audio_speaker.set_volume", {"volume": 41}
        )  # no unit named: the one that is left
        self.assertEqual(den.volume, 41)
        with self.assertRaises(ConnectionError) as refused:
            await self.call("self.audio_speaker.set_volume", {"volume": 10}, unit=KITCHEN)
        self.assertIn("not connected", str(refused.exception))
        self.assertEqual(den.volume, 41)  # the refused call did not leak to the other unit


if __name__ == "__main__":
    unittest.main()
