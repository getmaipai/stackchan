"""Travel with the private network, host side: a unit that reaches the hub over a private-network address connects
and is recognized, several units keyed by Device-Id keep working side by side (one at home, one traveling), and the
link path reads "away" for the traveling one. The unit's route choice is plain C (test_stackchan_tailnet_travel.py)."""

from __future__ import annotations

import asyncio
import time
import unittest

from stackchan_sim import StackChanFirmware
from websockets.asyncio.server import serve

from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer
from maipai_body.link.checkin import link_path, tailnet_channel


class _FromAddress:
    """The socket the server sees, with the source address of the connection set by the test."""

    def __init__(self, websocket, address: str) -> None:
        self._ws = websocket
        self.remote_address = (address, 51515)

    def __getattr__(self, name: str):
        return getattr(self._ws, name)


class TravelHostTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.pairing = PairingStore()

        async def on_audio(session: str, frame: bytes) -> None:
            return None

        self.service = XiaozhiServer(self.pairing, None, on_audio)
        self.sources: list[str] = []  # the source address of each next connection, in order

        async def handler(websocket) -> None:
            address = self.sources.pop(0) if self.sources else "127.0.0.1"
            await self.service.handle(_FromAddress(websocket, address))

        self.server = await serve(handler, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{self.port}"
        self.firmware: list[StackChanFirmware] = []

    async def asyncTearDown(self) -> None:
        for device in self.firmware:
            device.resume_close_response()
            await device.stop()
        self.server.close()
        await self.server.wait_closed()

    def pair(self, device_id: str, client_id: str) -> str:
        self.pairing.request(device_id, client_id)
        return self.pairing.approve(device_id, client_id)

    async def wait_until(self, predicate, timeout: float = 2.0) -> None:
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            await asyncio.sleep(0.005)
        self.assertTrue(predicate(), "condition did not become true before the deadline")

    async def connect(self, device_id: str, client_id: str, source: str) -> StackChanFirmware:
        token = self.pair(device_id, client_id)
        self.sources.append(source)  # the next connection looks like it came from this address
        device = StackChanFirmware(self.url, token, device_id=device_id, client_id=client_id)
        self.firmware.append(device)
        await device.start()
        await device.wait_connected()
        return device

    async def test_a_unit_over_a_private_network_address_connects_and_reads_as_away(self) -> None:
        device = await self.connect("02:00:00:00:00:61", "00000000-0000-4000-8000-000000000061", "100.64.0.9")
        self.assertEqual(device.server_hello["type"], "hello")
        self.assertIn("02:00:00:00:00:61", self.service.connected_devices())
        self.assertEqual(self.service._session_info["02:00:00:00:00:61"][0], "100.64.0.9")
        # The classification the host uses for the address a session came from.
        self.assertEqual(link_path("100.64.0.9"), "away")
        self.assertEqual(link_path("100.127.255.254"), "away")
        self.assertEqual(link_path("192.0.2.40"), "home")

    async def test_two_units_keyed_by_device_id_work_at_once(self) -> None:
        a = await self.connect("02:00:00:00:00:62", "00000000-0000-4000-8000-000000000062", "192.0.2.41")
        b = await self.connect("02:00:00:00:00:63", "00000000-0000-4000-8000-000000000063", "100.64.0.10")
        await self.wait_until(lambda: len(self.service.connected_devices()) == 2)
        self.assertEqual(set(self.service.connected_devices()), {"02:00:00:00:00:62", "02:00:00:00:00:63"})
        self.assertEqual(a.server_hello["type"], "hello")
        self.assertEqual(b.server_hello["type"], "hello")
        self.assertEqual(link_path(self.service._session_info["02:00:00:00:00:62"][0]), "home")
        self.assertEqual(link_path(self.service._session_info["02:00:00:00:00:63"][0]), "away")

    async def test_the_unit_is_the_tailnet_channel_only_when_its_own_address_matches(self) -> None:
        facts = {"tailnet_state": "connected", "tailnet_ip": "100.64.0.9"}
        self.assertTrue(tailnet_channel("100.64.0.9", facts))
        self.assertFalse(tailnet_channel("100.64.0.10", facts))  # another private-network device (a relay)
        self.assertFalse(tailnet_channel("192.0.2.41", facts))
        self.assertFalse(tailnet_channel("100.64.0.9", {"tailnet_state": "registering", "tailnet_ip": "100.64.0.9"}))


if __name__ == "__main__":
    unittest.main()
