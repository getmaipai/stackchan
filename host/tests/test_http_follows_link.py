"""On an encrypted link the unit is told encrypted web addresses; a required unit is refused on the plain port."""

import asyncio
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from maipai_body.bodies.stackchan.xiaozhi.link_security import LinkSecurity
from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer

UNIT = "aa:bb:cc:dd:ee:01"


def _server(tmp_path, encrypted):
    pairing = PairingStore(tmp_path / "p.json")
    server = XiaozhiServer(pairing, robot=None, vision_host="192.0.2.10", vision_port=8767)
    server.link = LinkSecurity(pairing)
    server.tls_http_port = 8777
    server.link.note_connected(UNIT, encrypted)
    return server


def test_plain_unit_gets_plain_addresses(tmp_path):
    server = _server(tmp_path, False)
    assert server._vision_url(UNIT).startswith("http://192.0.2.10:8767/vision/")
    assert server._notify_audio_url(UNIT, "abc").startswith("http://192.0.2.10:8767/notify/")


def test_encrypted_unit_gets_encrypted_addresses(tmp_path):
    server = _server(tmp_path, True)
    assert server._vision_url(UNIT) == f"https://192.0.2.10:8777/vision/{UNIT}"
    assert server._notify_audio_url(UNIT, "abc").startswith("https://192.0.2.10:8777/notify/")


def test_required_unit_is_refused_on_the_plain_port(tmp_path):
    server = _server(tmp_path, True)
    server.pairing.set_link_mode(UNIT, "required")
    # no such record yet: adopt one so the mode can be set
    server.pairing.adopt_device(UNIT, "11111111-2222-3333-4444-555555555555", "0" * 64)
    server.pairing.set_link_mode(UNIT, "required")
    request = make_mocked_request("POST", f"/vision/{UNIT}", match_info={"device_id": UNIT})

    async def handler(_request):
        return web.Response(text="ok")

    response = asyncio.run(server._link_middleware(request, handler))
    assert response.status == 403
