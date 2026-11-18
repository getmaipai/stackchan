"""Host check on reads, proxy headers mean not local, request bodies are capped."""

import http.client
import json

import pytest

from maipai_body import local_guard
from maipai_body.settings_server import SettingsServer


@pytest.mark.parametrize(
    "peer,headers,expected",
    [
        ("127.0.0.1", {"Host": "127.0.0.1:8051"}, True),
        ("127.0.0.1", {"Host": "localhost:8051"}, True),
        ("::1", {"Host": "[::1]:8051"}, True),
        ("127.0.0.1", {"Host": "evil.example:8051"}, False),
        ("127.0.0.1", {"Host": "127.0.0.1", "X-Forwarded-For": "198.51.100.9"}, False),
        ("127.0.0.1", {"Host": "127.0.0.1", "Via": "1.1 proxy"}, False),
        ("192.0.2.7", {"Host": "127.0.0.1"}, False),
        ("127.0.0.1", {"Host": "[::1]evil.com"}, False),
        ("127.0.0.1", {"Host": "[::1]:8051"}, True),
        ("127.0.0.1", {"Host": "localhost.evil.com"}, False),
        ("127.0.0.1", {"Host": "127.0.0.1:80:90"}, False),
    ],
)
def test_request_is_local(peer, headers, expected):
    assert local_guard.request_is_local(peer, headers) is expected


@pytest.fixture
def sim(tmp_path):
    from maipai_body.settings_sim import build

    backend, _ = build(tmp_path)
    return backend


def _start(backend):
    server = SettingsServer(backend, "127.0.0.1", 0)
    server.start()
    return server


def _request(server, method, path, headers=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    data = response.read()
    conn.close()
    return response.status, data


def test_get_with_a_foreign_host_name_is_refused(sim):
    server = _start(sim)
    try:
        status, _ = _request(server, "GET", "/api/stackchan/settings", {"Host": "evil.example"})
        assert status == 403
        status, _ = _request(server, "GET", "/settings", {"Host": f"127.0.0.1:{server.port}"})
        assert status == 200
    finally:
        server.stop()


def test_oversized_post_is_refused_before_it_is_read(sim):
    server = _start(sim)
    try:
        status, data = _request(
            server,
            "POST",
            "/api/stackchan/settings",
            {
                "Host": f"127.0.0.1:{server.port}",
                "Content-Type": "application/json",
                "Content-Length": str(local_guard.MAX_JSON_BODY + 1),
            },
            body=b"{}",
        )
        assert status == 413
        assert "too large" in json.loads(data)["error"]
    finally:
        server.stop()


def test_dashboard_refuses_an_oversized_non_picture_post_and_pair_code_needs_post(tmp_path):
    from maipai_body.bodies.reachy_mini.fake import FakeReachyMiniClient
    from maipai_body.bodies.reachy_mini.profile import REACHY_MINI_PROFILE
    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
    from maipai_body.dashboard.server import DashboardServer

    store = PairingStore(tmp_path / "p.json")
    dash = DashboardServer(
        FakeReachyMiniClient(), REACHY_MINI_PROFILE, host="127.0.0.1", port=0, pairing_store=store
    )
    dash.start()
    try:
        port = dash.port
        host = {"Host": f"127.0.0.1:{port}"}
        status, _ = _request(dash, "GET", "/api/stackchan/pairings/code", host)
        assert status == 405  # a GET never mints a code
        status, data = _request(
            dash,
            "POST",
            "/api/stackchan/pairings/code",
            {**host, "Content-Type": "application/json", "Content-Length": "2"},
            body=b"{}",
        )
        assert status == 200 and len(json.loads(data)["code"]) == 6
        status, _ = _request(
            dash,
            "POST",
            "/api/stackchan/other",
            {
                **host,
                "Content-Type": "application/json",
                "Content-Length": str(local_guard.MAX_JSON_BODY + 1),
            },
            body=b"{}",
        )
        assert status == 413
    finally:
        dash.stop()


def test_the_size_cap_follows_the_path_not_the_query(sim):
    server = _start(sim)
    try:
        status, _ = _request(
            server,
            "POST",
            "/api/stackchan/settings?x=picture",
            {
                "Host": f"127.0.0.1:{server.port}",
                "Content-Type": "application/json",
                "Content-Length": str(local_guard.MAX_JSON_BODY + 1),
            },
            body=b"{}",
        )
        assert status == 413
    finally:
        server.stop()


def test_the_settings_server_refuses_to_listen_beyond_this_computer_without_a_token(tmp_path):
    import pytest

    from maipai_body.local_guard import SettingsAuth
    from maipai_body.settings_server import SettingsServer

    with pytest.raises(ValueError, match="settings token"):
        SettingsServer(object(), "0.0.0.0", 0, auth=None)
    server = SettingsServer(object(), "0.0.0.0", 0, auth=SettingsAuth(tmp_path / "token"))
    server.server_close()
    SettingsServer(object(), "127.0.0.1", 0, auth=None).server_close()
