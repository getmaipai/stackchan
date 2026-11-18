"""Signed, ranged, cacheable asset delivery: the manifest is signed and checks out, ranges answer correctly, a unit gets only what the host chose."""

import asyncio
import base64
import hashlib
import json
import subprocess
from types import SimpleNamespace

import pytest

from maipai_body.assets import CHUNK, IMMUTABLE, Asset, AssetService, SigningKey
from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

PAYLOAD = bytes(range(256)) * 40 + b"tail"  # 10,244 bytes: three chunks
ASSET = Asset(hashlib.sha256(PAYLOAD).hexdigest(), "language", "french", 3, PAYLOAD)


def _service(tmp_path, wanted=("unit-a",)):
    key = SigningKey(tmp_path / "asset-signing.pem")
    return AssetService(key, lambda device, asset_id: ASSET if device in wanted and asset_id == ASSET.asset_id else None), key


def _verify(key, body, signature_b64, tmp_path):
    pub = tmp_path / "pub.pem"
    pub.write_bytes(subprocess.run([openssl_cli(), "pkey", "-in", str(key.path), "-pubout"], check=True, capture_output=True).stdout)
    sig = tmp_path / "sig"
    sig.write_bytes(base64.b64decode(signature_b64))
    msg = tmp_path / "msg"
    msg.write_bytes(body)
    done = subprocess.run([openssl_cli(), "pkeyutl", "-verify", "-pubin", "-inkey", str(pub), "-rawin", "-in", str(msg), "-sigfile", str(sig)], capture_output=True)
    return done.returncode == 0


def test_the_manifest_lists_every_chunk_hash_and_its_signature_verifies(tmp_path):
    service, key = _service(tmp_path)
    body, signature = service.manifest("unit-a", ASSET.asset_id)
    manifest = json.loads(body)
    assert manifest["size"] == len(PAYLOAD) and manifest["sha256"] == ASSET.asset_id and manifest["chunk"] == CHUNK and len(manifest["chunks"]) == 3
    assert manifest["chunks"][2] == hashlib.sha256(PAYLOAD[2 * CHUNK :]).hexdigest()
    assert _verify(key, body, signature, tmp_path)
    assert not _verify(key, body.replace(b'"version":3', b'"version":4'), signature, tmp_path)  # a changed manifest fails
    assert oct((tmp_path / "asset-signing.pem").stat().st_mode & 0o777) == "0o600"


def test_a_unit_gets_only_what_the_host_chose_for_it(tmp_path):
    service, _ = _service(tmp_path)
    assert service.manifest("unit-b", ASSET.asset_id) is None and service.data("unit-b", ASSET.asset_id, None) is None
    assert service.manifest("unit-a", "0" * 64) is None


def test_ranges_answer_with_the_right_bytes_and_headers(tmp_path):
    service, _ = _service(tmp_path)
    status, body, headers = service.data("unit-a", ASSET.asset_id, None)
    assert status == 200 and body == PAYLOAD and headers["Cache-Control"] == IMMUTABLE and headers["ETag"] == f'"{ASSET.asset_id}"'
    status, body, headers = service.data("unit-a", ASSET.asset_id, f"bytes={CHUNK}-{2 * CHUNK - 1}")
    assert status == 206 and body == PAYLOAD[CHUNK : 2 * CHUNK] and headers["Content-Range"] == f"bytes {CHUNK}-{2 * CHUNK - 1}/{len(PAYLOAD)}"
    assert service.data("unit-a", ASSET.asset_id, "bytes=10000-")[1] == PAYLOAD[10000:]
    assert service.data("unit-a", ASSET.asset_id, "bytes=-4")[1] == b"tail"
    assert service.data("unit-a", ASSET.asset_id, "bytes=99999-")[0] == 416
    assert service.data("unit-a", ASSET.asset_id, "bytes=garbage")[0] == 416


def test_the_routes_need_the_units_session_ticket_and_serve_ranges(tmp_path):
    from aiohttp.test_utils import TestClient, TestServer

    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
    from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer

    pairing = PairingStore()
    device, client = "02:00:00:00:00:41", "00000000-0000-4000-8000-000000000041"
    pairing.request(device, client)
    token = pairing.approve(device, client)
    voice = XiaozhiServer(pairing, robot=None)
    voice._session_credentials[device] = (client, token)
    ticket = voice.issue_ticket(device)
    service, _ = _service(tmp_path, wanted=(device,))
    voice.assets = service

    async def run():
        from aiohttp import web

        app = web.Application()
        app.router.add_get("/assets/{device_id}/{asset_id}/manifest", voice._serve_asset_manifest)
        app.router.add_get("/assets/{device_id}/{asset_id}/data", voice._serve_asset_data)
        async with TestClient(TestServer(app)) as http:
            base = f"/assets/{device}/{ASSET.asset_id}"
            assert (await http.get(base + "/data")).status == 401 or (await http.get(base + "/data")).status == 403
            auth = {"Authorization": f"Bearer {ticket}"}
            manifest = await http.get(base + "/manifest", headers=auth)
            assert manifest.status == 200 and manifest.headers["X-Asset-Signature"] and "immutable" in manifest.headers["Cache-Control"]
            part = await http.get(base + "/data", headers={**auth, "Range": "bytes=0-9"})
            assert part.status == 206 and await part.read() == PAYLOAD[:10]
            assert (await http.get(f"/assets/{device}/{'0' * 64}/data", headers=auth)).status == 404
            assert (await http.get(base + "/data", headers={"Authorization": f"Bearer {token}"})).status == 403  # the pairing token is never the key

    asyncio.run(run())
