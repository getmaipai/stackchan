"""No-terminal pairing and the phone path, end to end through the real settings server.

The owner opens the page on the host computer, presses a button for a pairing code, and shows a QR
code that logs a phone in; the phone then opens the page with the token and saves a setting."""

import http.client
import json

import pytest

from maipai_body import local_guard
from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
from maipai_body.settings_server import SettingsServer
from maipai_body.settings_sim import KITCHEN, build

UNIT_ID, CLIENT = "aa:bb:cc:dd:ee:09", "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def world(tmp_path):
    backend, _ = build(tmp_path)
    pairing = PairingStore(tmp_path / "pairing.json")
    auth = local_guard.SettingsAuth(tmp_path / "settings-token")
    backend.pair_code = pairing.create_pair_code
    backend.phone_link = lambda: {"lan": True, "base": "http://192.0.2.10:8051", "token": auth.token}
    server = SettingsServer(backend, "127.0.0.1", 0, auth=auth)
    server.start()
    yield server, pairing, auth
    server.stop()


def _call(server, method, path, headers=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
    h = {"Host": f"127.0.0.1:{server.port}", **(headers or {})}
    if body is not None:
        h["Content-Type"] = "application/json"
        body = json.dumps(body).encode()
    conn.request(method, path, body=body, headers=h)
    r = conn.getresponse()
    data = r.read()
    conn.close()
    return r.status, data


def test_the_page_mints_a_code_the_robot_can_redeem(world):
    server, pairing, _ = world
    status, data = _call(server, "POST", "/api/stackchan/pairings/code", body={})
    code = json.loads(data)["code"]
    assert status == 200 and len(code) == 6
    assert pairing.redeem_pair_code(UNIT_ID, CLIENT, code)  # the robot types it on its setup page


def test_a_phone_cannot_mint_a_code(world):
    server, _, auth = world
    status, _ = _call(server, "POST", "/api/stackchan/pairings/code", {"X-Forwarded-For": "192.0.2.50", "Authorization": f"Bearer {auth.token}"}, {})
    assert status == 403


def test_the_phone_link_has_a_qr_and_the_token_only_for_the_host_computer(world):
    server, _, auth = world
    status, data = _call(server, "GET", "/api/stackchan/phone-link")
    link = json.loads(data)
    assert status == 200 and link["url"] == f"http://192.0.2.10:8051/settings?token={auth.token}"
    assert link["svg"].startswith("<svg") and "</svg>" in link["svg"]
    phone, _ = _call(server, "GET", "/api/stackchan/phone-link", {"X-Forwarded-For": "192.0.2.50", "Authorization": f"Bearer {auth.token}"})
    assert phone == 403


def test_scanning_the_qr_logs_the_phone_in_and_it_can_save_a_setting(world):
    server, _, auth = world
    link = json.loads(_call(server, "GET", "/api/stackchan/phone-link")[1])
    path = link["url"].split("8051", 1)[1]  # what the phone opens after scanning
    phone = {"X-Forwarded-For": "192.0.2.50"}
    assert _call(server, "GET", path, phone)[0] == 200
    cookie = {"Cookie": f"maipai_settings={auth.token}", **phone}
    status, _ = _call(server, "POST", f"/api/stackchan/unit/{KITCHEN}/clock", {**cookie, "Origin": "http://192.0.2.10:8051", "Host": "192.0.2.10:8051"}, {"zone": "america_chicago"})
    assert status == 200


def test_when_the_phone_page_is_off_the_link_says_how_to_turn_it_on(world):
    server, _, _ = world
    server.backend.phone_link = lambda: {"lan": False}
    status, data = _call(server, "GET", "/api/stackchan/phone-link")
    assert status == 200 and "lan = true" in json.loads(data)["note"]
