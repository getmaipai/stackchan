"""A fake unit pairs over the plain pairing socket with the key exchange; the owner's six digits finish it (docs/plan/link-key-exchange.md)."""

from __future__ import annotations

import asyncio
import base64
import json
import unittest

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from maipai_body.bodies.stackchan.xiaozhi import link_exchange as lx
from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer

DEVICE, CLIENT = "02:00:5E:00:53:11", "00000000-0000-4000-8000-000000000011"
SK_U, N_U = bytes(range(1, 33)), bytes(range(16))
b64 = lambda raw: base64.b64encode(raw).decode()  # noqa: E731


class PairExchangeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pairing = PairingStore()
        self.service = XiaozhiServer(self.pairing, None, None)
        self.server = await serve(self.service.handle, "127.0.0.1", 0)
        self.url = f"ws://127.0.0.1:{self.server.sockets[0].getsockname()[1]}"

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()

    async def unit_pairs(self, ws, owner_types):
        pk_u = lx.x25519(SK_U, lx.BASE)
        await ws.send(json.dumps({"type": "pair_start", "pk_u": b64(pk_u)}))
        host = json.loads(await ws.recv())
        pk_h, c = base64.b64decode(host["pk_h"]), base64.b64decode(host["c"])
        await ws.send(json.dumps({"type": "pair_nonce", "n_u": b64(N_U)}))
        n_h = base64.b64decode(json.loads(await ws.recv())["n_h"])
        assert lx.commit(pk_h, pk_u, n_h) == c  # the unit checks the host's commitment
        shown = lx.sas(pk_u, pk_h, N_U, n_h)  # the six digits on the unit's screen
        owner = asyncio.create_task(asyncio.to_thread(owner_types, shown))
        message = json.loads(await asyncio.wait_for(ws.recv(), 5))
        await owner
        return message, lx.link_key(lx.x25519(SK_U, pk_h), pk_u, pk_h, N_U, n_h, DEVICE)

    async def wait_waiting(self):
        for _ in range(100):
            if self.service.waiting_exchanges():
                return
            await asyncio.sleep(0.02)
        self.fail("the exchange never reached the waiting-for-code step")

    async def test_the_right_six_digits_pair_the_unit_and_both_sides_hold_the_same_key(self):
        async with connect(self.url, additional_headers={"Device-Id": DEVICE, "Client-Id": CLIENT, "Pair-Exchange": "1"}) as ws:
            async def owner(code):
                await self.wait_waiting()
                self.service.approve_exchange(DEVICE, code)

            message, unit_key = await self.unit_pairs(ws, lambda code: asyncio.run(owner(code)))
        self.assertEqual(message["type"], "paired")
        self.assertEqual(self.pairing.link_key(DEVICE), unit_key)
        self.assertEqual(self.pairing.link_mode(DEVICE), "required")
        self.assertTrue(self.pairing.authorize_link(DEVICE, CLIENT))

    async def test_a_wrong_code_pairs_nothing(self):
        async with connect(self.url, additional_headers={"Device-Id": DEVICE, "Client-Id": CLIENT, "Pair-Exchange": "1"}) as ws:
            async def owner(code):
                await self.wait_waiting()
                wrong = "000000" if code != "000000" else "111111"
                with self.assertRaises(lx.ExchangeError):
                    self.service.approve_exchange(DEVICE, wrong)

            message, _ = await self.unit_pairs(ws, lambda code: asyncio.run(owner(code)))
        self.assertEqual(message["type"], "pair_failed")
        self.assertIsNone(self.pairing.link_key(DEVICE))

    async def test_a_socket_without_the_exchange_header_is_still_refused_as_before(self):
        async with connect(self.url, additional_headers={"Device-Id": DEVICE, "Client-Id": CLIENT}) as ws:
            with self.assertRaises(Exception):
                await asyncio.wait_for(ws.recv(), 3)
        self.assertIsNone(self.pairing.link_key(DEVICE))

    async def test_messages_in_the_wrong_order_end_the_exchange(self):
        async with connect(self.url, additional_headers={"Device-Id": DEVICE, "Client-Id": CLIENT, "Pair-Exchange": "1"}) as ws:
            await ws.send(json.dumps({"type": "pair_nonce", "n_u": b64(N_U)}))
            self.assertEqual(json.loads(await ws.recv())["type"], "pair_failed")


if __name__ == "__main__":
    unittest.main()
