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


def _photo(server, bearer=None, query_token=None):
    headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
    request = SimpleNamespace(
        match_info={"device_id": UNIT}, headers=headers, query={"token": query_token} if query_token else {},
        content_length=1, content_type="multipart/form-data",
    )
    return asyncio.run(server._receive_photo(request))


def test_the_long_lived_pairing_token_is_refused_on_every_web_route(tmp_path):
    server, token = _server(tmp_path)
    with pytest.raises(web.HTTPForbidden):
        _notify(server, token)
    with pytest.raises(web.HTTPForbidden):
        _photo(server, bearer=token)
    with pytest.raises(web.HTTPForbidden):
        _photo(server, query_token=token)


def test_a_ticket_is_the_only_credential_the_web_routes_take(tmp_path):
    server, _ = _server(tmp_path)
    ticket = server.issue_ticket(UNIT)
    assert _notify(server, ticket).body == b"ogg"
    for wrong in (None, "nope", ticket + "x"):
        with pytest.raises(web.HTTPForbidden):
            _photo(server, bearer=wrong)
    with pytest.raises(web.HTTPUnsupportedMediaType):  # past the credential check: the next rule (a multipart body) applies
        SimpleNamespace  # noqa: B018
        asyncio.run(server._receive_photo(SimpleNamespace(
            match_info={"device_id": UNIT}, headers={"Authorization": f"Bearer {ticket}"}, query={},
            content_length=1, content_type="text/plain",
        )))
