"""The unit gets a session ticket for the web port, never its long-lived pairing token."""

import asyncio
from types import SimpleNamespace

import pytest
from aiohttp import web

from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer

UNIT, CLIENT = "aa:bb:cc:dd:ee:01", "11111111-2222-3333-4444-555555555555"


def _server(tmp_path):
    pairing = PairingStore(tmp_path / "p.json")
    token = pairing.redeem_pair_code(UNIT, CLIENT, pairing.create_pair_code())
    server = XiaozhiServer(pairing, robot=None)
    server._session_credentials[UNIT] = (CLIENT, token)
    server._notification_audio[(UNIT, "a1")] = b"ogg"
    return server, token


def _notify(server, bearer):
    request = SimpleNamespace(
        match_info={"device_id": UNIT, "audio_id": "a1"}, headers={"Authorization": f"Bearer {bearer}"}
    )
    return asyncio.run(server._serve_notify_audio(request))


def test_the_ticket_is_not_the_pairing_token_and_works_on_the_web_port(tmp_path):
    server, token = _server(tmp_path)
    ticket = server.issue_ticket(UNIT)
    assert ticket != token and token not in ticket
    assert _notify(server, ticket).body == b"ogg"


def test_a_ticket_belongs_to_one_unit_and_ends_with_its_session(tmp_path):
    server, _ = _server(tmp_path)
    ticket = server.issue_ticket(UNIT)
    assert not server.ticket_ok("aa:bb:cc:dd:ee:02", ticket)
    server.end_tickets(UNIT)
    server._notification_audio[(UNIT, "a1")] = b"ogg"
    with pytest.raises(web.HTTPForbidden):
        _notify(server, ticket)


def test_an_expired_ticket_is_refused(tmp_path):
    server, _ = _server(tmp_path)
    ticket = server.issue_ticket(UNIT)
    server._tickets[ticket] = (UNIT, 0.0)
    assert not server.ticket_ok(UNIT, ticket)
