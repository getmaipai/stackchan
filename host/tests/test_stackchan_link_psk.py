"""Encrypted robot link: TLS 1.2 with a pre-shared key on the voice, avatar and HTTP listeners."""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import ssl
import time
import unittest

from aiohttp import ClientSession, TCPConnector
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidMessage

from maipai_body.bodies.stackchan.avatar.server import AvatarServer
from maipai_body.bodies.stackchan.xiaozhi import link_security as ls
from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer
from maipai_body.settings_page import SettingsBackend

DEVICE = "02:00:00:00:00:01"
CLIENT = "00000000-0000-4000-8000-000000000001"
FAKE_TOKEN = "test-token-not-a-secret-0123456789abcdefghijklmnopq"


def psk_client_context(identity: str, psk: bytes) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers(ls.PSK_CIPHERS)
    context.set_psk_client_callback(lambda hint: (identity, psk))
    return context


def lan_address() -> str | None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))
        address = probe.getsockname()[0]
    except OSError:
        return None
    finally:
        probe.close()
    return None if address.startswith("127.") else address


class VectorTests(unittest.TestCase):
    def test_hkdf_matches_rfc5869_case_1(self) -> None:
        okm = ls.hkdf_sha256(
            bytes.fromhex("0b" * 22),
            bytes(range(13)),
            bytes(range(0xF0, 0xFA)),
            42,
        )
        self.assertEqual(
            okm.hex(),
            "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf"
            "34007208d5b887185865",
        )

    def test_psk_vectors_are_fixed(self) -> None:
        digest = ls.token_digest(FAKE_TOKEN)
        self.assertEqual(
            digest, "0a58fbd7c218e7b6e0c0cb253a90dd6fed0bc0d56486681c0417ba46f58422d1"
        )
        self.assertEqual(
            ls.derive_psk(digest, "02:00:5e:00:53:01").hex(),
            "1d45f16f0548601ad8c4d97eca15889af3732d4660128bac45ebb00c46214926",
        )
        # The identity is lower-cased first; a different unit gets a different key.
        self.assertEqual(
            ls.derive_psk(digest, "AA:BB:CC:DD:EE:FF").hex(),
            "9f8bb521a3077108311d155761ff66cf7ca3b45b209aa706c64b8fa660a6b373",
        )
        self.assertEqual(
            ls.derive_psk(digest, "AA:BB:CC:DD:EE:FF"), ls.derive_psk(digest, "aa:bb:cc:dd:ee:ff")
        )
        self.assertNotEqual(bytes.fromhex(digest), ls.derive_psk(digest, DEVICE))

    def test_reference_script_agrees_with_the_host(self) -> None:
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parents[2] / "scripts" / "link-psk-vector.py"
        spec = importlib.util.spec_from_file_location("link_psk_vector", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        digest = ls.token_digest(FAKE_TOKEN)
        self.assertEqual(module.derive(digest, DEVICE), ls.derive_psk(digest, DEVICE))


class StoreTests(unittest.TestCase):
    def test_link_fields_persist_in_the_pairing_file(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pairing.json"
            store = PairingStore(path)
            store.request(DEVICE, CLIENT)
            store.approve(DEVICE, CLIENT)
            self.assertTrue(store.link_record(DEVICE)["link_new"])
            store.mark_seen_encrypted(DEVICE)
            store.set_link_mode(DEVICE, "required")
            again = PairingStore(path)
            self.assertEqual(
                (again.link_mode(DEVICE), again.link_record(DEVICE)["seen_encrypted"]), ("required", True)
            )
            self.assertEqual(oct(path.stat().st_mode & 0o777), "0o600")
            self.assertIsNone(again.link_material("02:00:00:00:00:55"))


class LinkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.pairing = PairingStore()
        self.pairing.request(DEVICE, CLIENT)
        self.token = self.pairing.approve(DEVICE, CLIENT)
        self.link = ls.LinkSecurity(self.pairing)
        self.voice = XiaozhiServer(self.pairing, None, vision_host="127.0.0.1", vision_port=0)
        self.voice.link = self.link
        self.avatar = AvatarServer(self.pairing)
        self.avatar.link = self.link
        await self.voice.start("127.0.0.1", 0)
        await self.voice.start_encrypted("0.0.0.0", 0, 0)
        await self.avatar.start("127.0.0.1", 0)
        await self.avatar.start_encrypted("0.0.0.0", 0)
        self.plain_port = self.voice._server.sockets[0].getsockname()[1]
        self.psk = ls.derive_psk(ls.token_digest(self.token), DEVICE)
        self.headers = {
            "Device-Id": DEVICE,
            "Client-Id": CLIENT,
            "Protocol-Version": "1",
            "Authorization": f"Bearer {self.token}",
        }
        self.records: list[str] = []
        handler = logging.Handler()
        handler.emit = lambda record: self.records.append(record.getMessage())  # type: ignore[method-assign]
        self.handler = handler
        logging.getLogger().addHandler(handler)
        handler.setLevel(logging.INFO)
        self._old_level = logging.getLogger().level
        logging.getLogger().setLevel(logging.INFO)

    async def asyncTearDown(self) -> None:
        logging.getLogger().removeHandler(self.handler)
        logging.getLogger().setLevel(self._old_level)
        await self.voice.close()
        await self.avatar.close()

    def encrypted(self, host: str = "127.0.0.1", identity: str = DEVICE, psk: bytes | None = None):
        return connect(
            f"wss://{host}:{self.voice.tls_port}",
            additional_headers=self.headers,
            ssl=psk_client_context(identity, psk if psk is not None else self.psk),
        )

    def plain(self):
        return connect(f"ws://127.0.0.1:{self.plain_port}", additional_headers=self.headers)

    @staticmethod
    async def hello(ws, features: dict | None = None) -> dict:
        await ws.send(json.dumps({"type": "hello", "version": 1, "features": features or {}}))
        return json.loads(await asyncio.wait_for(ws.recv(), 5))

    async def test_voice_exchanges_frames_over_psk(self) -> None:
        async with self.encrypted() as ws:
            reply = await self.hello(ws)
            self.assertEqual(reply["type"], "hello")
            await ws.send(json.dumps({"type": "listen", "state": "stop", "session_id": reply["session_id"]}))
            answer = json.loads(await asyncio.wait_for(ws.recv(), 5))
            self.assertEqual((answer["type"], answer["state"]), ("tts", "stop"))
            self.assertIn("ECDHE-PSK", ws.transport.get_extra_info("ssl_object").cipher()[0])
        self.assertTrue(self.pairing.link_record(DEVICE)["seen_encrypted"])

    async def test_avatar_exchanges_frames_over_psk(self) -> None:
        async with connect(
            f"wss://127.0.0.1:{self.avatar.tls_port}/stackChan/ws?deviceType=StackChan",
            additional_headers=self.headers,
            ssl=psk_client_context(DEVICE, self.psk),
        ) as ws:
            await ws.send(json.dumps({"type": "hello"}))
            reply = json.loads(await asyncio.wait_for(ws.recv(), 5))
            self.assertEqual(reply["type"], "hello")
            self.assertTrue(reply["session_id"])

    async def test_http_route_serves_over_psk(self) -> None:
        connector = TCPConnector(ssl=psk_client_context(DEVICE, self.psk))
        async with ClientSession(connector=connector) as session:
            async with session.get(f"https://127.0.0.1:{self.voice.tls_http_port}/selftest/checks") as r:
                self.assertLess(r.status, 600)
        wrong = TCPConnector(ssl=psk_client_context(DEVICE, b"\x01" * 32))
        async with ClientSession(connector=wrong) as session:
            with self.assertRaises(Exception):
                async with session.get(f"https://127.0.0.1:{self.voice.tls_http_port}/selftest/checks"):
                    pass

    async def test_wrong_psk_or_identity_is_refused_at_the_handshake(self) -> None:
        for kwargs in ({"psk": b"\x02" * 32}, {"identity": "02:00:00:00:00:99"}):
            with self.assertRaises((ssl.SSLError, ConnectionError, InvalidMessage, OSError)):
                async with self.encrypted(**kwargs):
                    self.fail("the handshake must fail")

    async def test_wrong_psk_refused_on_avatar(self) -> None:
        with self.assertRaises((ssl.SSLError, ConnectionError, InvalidMessage, OSError)):
            async with connect(
                f"wss://127.0.0.1:{self.avatar.tls_port}/stackChan/ws?deviceType=StackChan",
                additional_headers=self.headers,
                ssl=psk_client_context(DEVICE, b"\x03" * 32),
            ):
                self.fail("the handshake must fail")

    async def test_plain_client_is_refused_by_the_encrypted_port(self) -> None:
        with self.assertRaises(Exception):
            async with connect(
                f"ws://127.0.0.1:{self.voice.tls_port}", additional_headers=self.headers, open_timeout=3
            ):
                self.fail("a plain client must not get a WebSocket on the encrypted port")

    async def test_required_refuses_plain_and_allowed_serves_both(self) -> None:
        self.link.set_mode(DEVICE, "allowed")
        async with self.plain() as ws:
            self.assertEqual((await self.hello(ws))["type"], "hello")
        async with self.encrypted() as ws:
            self.assertEqual((await self.hello(ws))["type"], "hello")
        self.link.set_mode(DEVICE, "required")
        async with self.plain() as ws:
            with self.assertRaises(ConnectionClosed) as ctx:
                await asyncio.wait_for(ws.recv(), 5)
            self.assertEqual(ctx.exception.rcvd.code, 1008)
            self.assertIn("encrypted", ctx.exception.rcvd.reason)
        async with self.encrypted() as ws:
            self.assertEqual((await self.hello(ws))["type"], "hello")

    async def test_required_refuses_plain_avatar_socket(self) -> None:
        self.link.set_mode(DEVICE, "required")
        port = self.avatar._server.sockets[0].getsockname()[1]
        async with connect(
            f"ws://127.0.0.1:{port}/stackChan/ws?deviceType=StackChan", additional_headers=self.headers
        ) as ws:
            with self.assertRaises(ConnectionClosed):
                await asyncio.wait_for(ws.recv(), 5)

    async def test_off_is_plain_only(self) -> None:
        self.link.set_mode(DEVICE, "off")
        self.assertEqual(self.link.state(DEVICE), "plain")
        async with self.plain() as ws:
            self.assertEqual((await self.hello(ws))["type"], "hello")
        async with self.encrypted() as ws:
            with self.assertRaises(ConnectionClosed):
                await asyncio.wait_for(ws.recv(), 5)

    async def test_no_downgrade_after_seen_encrypted(self) -> None:
        # A new pairing, a unit that says it can encrypt: required from then on.
        self.assertEqual(self.link.mode(DEVICE), "allowed")
        async with self.plain() as ws:
            await self.hello(ws, {ls.FEATURE_TLS_PSK: True})
        self.assertEqual(self.link.mode(DEVICE), "required")
        async with self.plain() as ws:
            with self.assertRaises(ConnectionClosed):
                await asyncio.wait_for(ws.recv(), 5)
        # A hello without the flag changes nothing (older firmware tolerated).
        other = "02:00:00:00:00:02"
        self.pairing.request(other, CLIENT)
        token = self.pairing.approve(other, CLIENT)
        self.headers.update({"Device-Id": other, "Authorization": f"Bearer {token}"})
        async with self.plain() as ws:
            await self.hello(ws, {})
        self.assertEqual(self.link.mode(other), "allowed")

    async def test_explicit_choice_is_not_overridden_by_the_flag(self) -> None:
        self.link.set_mode(DEVICE, "allowed")
        async with self.plain() as ws:
            await self.hello(ws, {ls.FEATURE_TLS_PSK: True})
        self.assertEqual(self.link.mode(DEVICE), "allowed")

    async def test_state_values(self) -> None:
        self.assertEqual(self.link.state(DEVICE), "never_seen")
        async with self.encrypted() as ws:
            await self.hello(ws)
            self.assertEqual(self.link.state(DEVICE), "encrypted")
        await asyncio.sleep(0.3)
        self.assertEqual(self.link.state(DEVICE), "plain_allowed")
        self.link.set_mode(DEVICE, "required")
        self.assertEqual(self.link.state(DEVICE), "encrypted")

    async def test_stale_or_foreign_session_id_is_refused(self) -> None:
        async with self.encrypted() as ws:
            old = (await self.hello(ws))["session_id"]
        async with self.encrypted() as ws:
            await self.hello(ws)
            await ws.send(json.dumps({"type": "listen", "state": "stop", "session_id": old}))
            with self.assertRaises(ConnectionClosed) as ctx:
                await asyncio.wait_for(ws.recv(), 5)
            self.assertEqual(ctx.exception.rcvd.code, 1008)
        async with self.encrypted() as ws:
            await self.hello(ws)
            await ws.send(json.dumps({"type": "listen", "state": "stop", "session_id": "made-up"}))
            with self.assertRaises(ConnectionClosed):
                await asyncio.wait_for(ws.recv(), 5)
        self.assertTrue(any("stale or unknown session id" in r for r in self.records))

    async def test_avatar_hello_carrying_a_session_id_is_refused(self) -> None:
        async with connect(
            f"wss://127.0.0.1:{self.avatar.tls_port}/stackChan/ws?deviceType=StackChan",
            additional_headers=self.headers,
            ssl=psk_client_context(DEVICE, self.psk),
        ) as ws:
            await ws.send(json.dumps({"type": "hello", "session_id": "0123"}))
            with self.assertRaises(ConnectionClosed):
                await asyncio.wait_for(ws.recv(), 5)

    async def test_same_behavior_on_loopback_and_a_lan_address(self) -> None:
        address = lan_address()
        if address is None:
            self.skipTest("this machine has no non-loopback address")
        results = []
        for host in ("127.0.0.1", address):
            async with self.encrypted(host=host) as ws:
                reply = await self.hello(ws)
                results.append(reply["type"])
            with self.assertRaises((ssl.SSLError, ConnectionError, InvalidMessage, OSError)):
                async with self.encrypted(host=host, psk=b"\x04" * 32):
                    self.fail("the handshake must fail")
        self.assertEqual(results, ["hello", "hello"])

    async def test_the_psk_never_appears_in_logs_or_settings(self) -> None:
        async with self.encrypted() as ws:
            await self.hello(ws)
        with self.assertRaises(Exception):
            async with self.encrypted(psk=b"\x05" * 32):
                pass
        backend = SettingsBackend(devices=self.pairing.paired_devices, link=self.link)
        dumps = [
            json.dumps(backend.state()),
            json.dumps(self.link.view(DEVICE)),
            repr(backend._unit_get(f"{DEVICE}/link", "en")),
            "\n".join(self.records),
        ]
        secrets = [self.psk.hex(), self.psk.hex().upper(), ls.token_digest(self.token), self.token]
        for text in dumps:
            for secret in secrets:
                self.assertNotIn(secret, text)
        self.assertNotIn(repr(self.psk), "\n".join(dumps))

    async def test_settings_route_changes_the_choice(self) -> None:
        backend = SettingsBackend(devices=self.pairing.paired_devices, link=self.link)
        status, body = backend._unit_post(f"{DEVICE}/link", {"mode": "required"}, "en")
        self.assertEqual((status, body["mode"]), (200, "required"))
        status, body = backend._unit_post(f"{DEVICE}/link", {"mode": "banana"}, "en")
        self.assertEqual(status, 400)
        self.assertEqual(self.link.mode(DEVICE), "required")

    async def test_home_handed_digest_is_honored(self) -> None:
        other = "02:00:00:00:00:07"
        digest = ls.token_digest(FAKE_TOKEN)
        self.pairing.adopt_device(other, CLIENT, digest)
        psk = ls.derive_psk(digest, other)
        self.headers.update({"Device-Id": other, "Authorization": f"Bearer {FAKE_TOKEN}"})
        async with self.encrypted(identity=other, psk=psk) as ws:
            self.assertEqual((await self.hello(ws))["type"], "hello")

    async def test_performance_note(self) -> None:
        async def rounds(ws, n: int) -> float:
            reply = await self.hello(ws)
            frame = json.dumps({"type": "listen", "state": "stop", "session_id": reply["session_id"]})
            start = time.perf_counter()
            for _ in range(n):
                await ws.send(frame)
                await ws.recv()
            return n / (time.perf_counter() - start)

        n = 300
        t0 = time.perf_counter()
        async with self.plain() as ws:
            plain_connect = time.perf_counter() - t0
            plain_fps = await rounds(ws, n)
        self.link.set_mode(DEVICE, "allowed")
        t0 = time.perf_counter()
        async with self.encrypted() as ws:
            tls_connect = time.perf_counter() - t0
            tls_fps = await rounds(ws, n)
        print(
            f"\nlink perf: connect plain {plain_connect * 1000:.1f} ms, tls-psk {tls_connect * 1000:.1f} ms; "
            f"round trips per second plain {plain_fps:.0f}, tls-psk {tls_fps:.0f}"
        )
        self.assertGreater(tls_fps, 50)


if __name__ == "__main__":
    unittest.main()
