"""A settings-token login (a phone) reaches the settings pages but not the host-only controls."""

from maipai_body.settings_page import TOKEN_ACCESS
from maipai_body.settings_sim import KITCHEN, build

UNIT = "/api/stackchan/unit/{}/"


def _backend(tmp_path):
    backend, _ = build(tmp_path)
    return backend


def test_token_access_reads_and_saves_ordinary_settings(tmp_path):
    backend = _backend(tmp_path)
    assert backend.route_get("/api/stackchan/settings", "en", TOKEN_ACCESS)[0] == 200
    status, _ = backend.route_post(UNIT.format(KITCHEN) + "clock", {"zone": "america_chicago"}, TOKEN_ACCESS)
    assert status == 200


def test_token_access_cannot_use_remote_access_admin_update_or_lock(tmp_path):
    backend = _backend(tmp_path)
    assert backend.route_get("/api/stackchan/remote-access", "en", TOKEN_ACCESS)[0] == 403
    assert backend.route_post("/api/stackchan/remote-access", {"enabled": True}, TOKEN_ACCESS)[0] == 403
    assert backend.route_post("/api/stackchan/settings/" + KITCHEN + "/update", {"confirm": True}, TOKEN_ACCESS)[0] == 403
    assert backend.route_post(UNIT.format(KITCHEN) + "lock", {"code": "1234", "confirm_code": "1234"}, TOKEN_ACCESS)[0] == 403


def test_the_host_computer_keeps_every_control(tmp_path):
    backend = _backend(tmp_path)
    assert backend.route_get("/api/stackchan/remote-access", "en", True)[0] == 200
