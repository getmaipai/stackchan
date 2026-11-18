"""The settings page from a phone: a per-install token is the login for requests that are not local."""

import http.client
import json
import stat

import pytest

from maipai_body import local_guard
from maipai_body.settings_server import SettingsServer
from maipai_body.settings_sim import build


@pytest.fixture
def server(tmp_path):
    backend, _ = build(tmp_path)
    auth = local_guard.SettingsAuth(tmp_path / "settings-token")
    srv = SettingsServer(backend, "127.0.0.1", 0, auth=auth)
    srv.start()
    yield srv, auth
    srv.stop()


def _req(srv, method, path, headers=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=5)
    conn.request(method, path, body=body, headers=headers or {})
    r = conn.getresponse()
    data = r.read()
    out = (r.status, data, r.getheader("Set-Cookie"))
    conn.close()
    return out


def test_token_file_is_private_and_stable(tmp_path):
    a = local_guard.SettingsAuth(tmp_path / "t")
    assert (tmp_path / "t").stat().st_mode & 0o777 == 0o600
    assert local_guard.SettingsAuth(tmp_path / "t").token == a.token and len(a.token) >= 32


def test_a_proxied_request_without_the_token_is_refused_with_a_fix(server):
    srv, _ = server
    status, data, _ = _req(srv, "GET", "/api/stackchan/settings", {"X-Forwarded-For": "192.0.2.50"})
    assert status == 401 and "settings token" in json.loads(data)["error"]


def test_the_token_in_the_address_logs_in_and_sets_a_cookie(server):
    srv, auth = server
    status, _, cookie = _req(srv, "GET", f"/settings?token={auth.token}", {"X-Forwarded-For": "192.0.2.50"})
    assert status == 200 and "maipai_settings=" in cookie and "SameSite=Strict" in cookie and "HttpOnly" in cookie
    value = cookie.split(";")[0]
    status, _, _ = _req(srv, "GET", "/api/stackchan/settings", {"X-Forwarded-For": "192.0.2.50", "Cookie": value})
    assert status == 200


def test_bearer_header_works_and_a_wrong_token_does_not(server):
    srv, auth = server
    ok = _req(srv, "GET", "/api/stackchan/settings", {"X-Forwarded-For": "1.2.3.4", "Authorization": f"Bearer {auth.token}"})
    bad = _req(srv, "GET", "/api/stackchan/settings", {"X-Forwarded-For": "1.2.3.4", "Authorization": "Bearer nope"})
    assert ok[0] == 200 and bad[0] == 401


def test_a_cross_site_post_with_the_cookie_is_refused(server):
    srv, auth = server
    headers = {
        "X-Forwarded-For": "1.2.3.4", "Cookie": f"maipai_settings={auth.token}",
        "Content-Type": "application/json", "Origin": "http://evil.example",
        "Host": "192.0.2.10:8051",
    }  # fmt: skip
    status, _, _ = _req(srv, "POST", "/api/stackchan/settings", headers, b"{}")
    assert status == 403


def test_too_many_wrong_tokens_lock_the_login_for_a_while(tmp_path):
    auth = local_guard.SettingsAuth(tmp_path / "t")
    for _ in range(local_guard.TOKEN_TRIES):
        assert not auth.valid({"Authorization": "Bearer wrong"}, "")
    assert not auth.valid({"Authorization": f"Bearer {auth.token}"}, "")  # locked even for the right one


def test_config_switch_and_cli_print_the_token(monkeypatch, tmp_path, capsys):
    import sys

    from maipai_body import cli, config
    from maipai_body.bodies.stackchan.xiaozhi import pairing

    assert config.RobotConfig().settings.lan is False  # off unless the owner turns it on
    (tmp_path / "robot.toml").write_text("[settings]\nlan = true\n")
    monkeypatch.setattr(config, "example_config_path", lambda: tmp_path / "robot.toml")
    monkeypatch.setattr(cli, "default_pairing_path", lambda: tmp_path / "p.json")
    monkeypatch.setattr(pairing, "default_pairing_path", lambda: tmp_path / "p.json")
    monkeypatch.setattr(sys, "argv", ["stackchan", "settings-token"])
    assert cli.main() == 0
    out = capsys.readouterr().out
    token = local_guard.SettingsAuth(tmp_path / "settings-token").token
    assert token in out and "/settings?token=" in out


def test_a_fresh_link_wins_over_an_old_cookie(tmp_path):
    auth = local_guard.SettingsAuth(tmp_path / "t")
    assert auth.valid({"Cookie": "maipai_settings=stale"}, f"token={auth.token}")
