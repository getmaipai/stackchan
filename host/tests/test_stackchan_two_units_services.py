"""The background services share one client. With two units connected, a household-wide setting the services push (sound policy,
music features, idle motion) reaches every unit; a read comes from the longest-connected unit; a named call stays on its unit;
and a call made during a unit's turn goes to the talking unit."""

from __future__ import annotations

import asyncio
import unittest

from stackchan_sim import StackChanFirmware
from websockets.asyncio.server import serve

from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT, XiaozhiDeviceClient, XiaozhiServer

KITCHEN = "02:00:00:00:00:71"
DEN = "02:00:00:00:00:72"


class TwoUnitServicesTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.pairing = PairingStore()

        async def on_audio(session: str, frame: bytes) -> None:
            return None

        self.service = XiaozhiServer(self.pairing, None, on_audio)
        self.client = XiaozhiDeviceClient(self.service, timeout=3.0)
        self.server = await serve(self.service.handle, "127.0.0.1", 0)
        self.url = f"ws://127.0.0.1:{self.server.sockets[0].getsockname()[1]}"
        self.units: dict[str, StackChanFirmware] = {}

    async def asyncTearDown(self) -> None:
        for unit in self.units.values():
            await unit.stop()
        self.server.close()
        await self.server.wait_closed()

    async def connect(self, device_id: str, number: int) -> StackChanFirmware:
        client_id = f"00000000-0000-4000-8000-0000000000{number}"
        self.pairing.request(device_id, client_id)
        token = self.pairing.approve(device_id, client_id)
        unit = StackChanFirmware(self.url, token, device_id=device_id, client_id=client_id)
        self.units[device_id] = unit
        await unit.start()
        await unit.wait_connected()
        return unit

    @staticmethod
    def names(unit: StackChanFirmware) -> list[str]:
        return [name for name, _ in unit.tool_calls]

    async def settle(self) -> None:
        await asyncio.sleep(0.1)

    async def test_a_household_setting_reaches_both_units_and_a_read_comes_from_the_first(self) -> None:
        kitchen = await self.connect(KITCHEN, 71)
        den = await self.connect(DEN, 72)
        await asyncio.to_thread(self.client._call, "self.audio.set_sound_policy", {"policy": "normal"})
        await self.settle()
        self.assertIn("self.audio.set_sound_policy", self.names(kitchen))
        self.assertIn("self.audio.set_sound_policy", self.names(den))
        await asyncio.to_thread(self.client._call, "self.battery.get_status", {})
        self.assertIn("self.battery.get_status", self.names(kitchen))
        self.assertNotIn("self.battery.get_status", self.names(den))

    async def test_one_unit_keeps_the_old_single_unit_behavior(self) -> None:
        kitchen = await self.connect(KITCHEN, 71)
        await asyncio.to_thread(self.client._call, "self.audio.set_sound_policy", {"policy": "normal"})
        self.assertEqual(self.names(kitchen).count("self.audio.set_sound_policy"), 1)

    async def test_a_setting_still_goes_only_to_the_talking_unit_during_its_turn(self) -> None:
        kitchen = await self.connect(KITCHEN, 71)
        den = await self.connect(DEN, 72)

        def during_den_turn() -> None:
            token = ACTIVE_UNIT.set(DEN)
            try:
                self.client._call("self.audio.set_sound_policy", {"policy": "quiet"})
            finally:
                ACTIVE_UNIT.reset(token)

        await asyncio.to_thread(during_den_turn)
        self.assertIn("self.audio.set_sound_policy", self.names(den))
        self.assertNotIn("self.audio.set_sound_policy", self.names(kitchen))

    async def test_if_one_unit_drops_the_setting_still_reaches_the_other(self) -> None:
        kitchen = await self.connect(KITCHEN, 71)
        den = await self.connect(DEN, 72)
        await kitchen.stop()
        for _ in range(100):
            if KITCHEN not in self.service._sessions:
                break
            await asyncio.sleep(0.02)
        await asyncio.to_thread(self.client._call, "self.audio.set_sound_policy", {"policy": "normal"})
        self.assertIn("self.audio.set_sound_policy", self.names(den))


if __name__ == "__main__":
    unittest.main()


class SelfHealTwoUnitsTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_system_command_still_reaches_a_unit_when_two_are_connected(self) -> None:
        sent = []
        service = XiaozhiServer(PairingStore(), None, None)
        service._sessions = {KITCHEN: "ws1", DEN: "ws2"}
        service._session_ids = {KITCHEN: "s1", DEN: "s2"}

        async def fake_json(ws, session_id, kind, payload):
            sent.append((ws, kind, payload["command"]))

        service._json = fake_json
        await service.send_system("reboot")  # no unit named: the longest-connected
        await service.send_system("reboot", device_id=DEN)
        token = ACTIVE_UNIT.set(DEN)
        try:
            await service.send_system("reboot")  # during the second unit's turn: that unit
        finally:
            ACTIVE_UNIT.reset(token)
        self.assertEqual([w for w, _, _ in sent], ["ws1", "ws2", "ws2"])

    async def test_with_no_unit_connected_it_still_says_so_in_plain_words(self) -> None:
        service = XiaozhiServer(PairingStore(), None, None)
        with self.assertRaisesRegex(ConnectionError, "No StackChan is connected"):
            await service.send_system("reboot")
