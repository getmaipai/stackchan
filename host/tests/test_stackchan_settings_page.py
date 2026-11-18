import http.client
import json
import os

os.environ["TMPDIR"] = "/private/tmp"

import pytest

from maipai_body.bodies.reachy_mini.fake import FakeReachyMiniClient
from maipai_body.bodies.reachy_mini.profile import REACHY_MINI_PROFILE
from maipai_body.dashboard import DashboardServer
from maipai_body.i18n import CATALOG, t
from maipai_body.settings_page import SettingsBackend, render_page
from maipai_body.unit_settings import SettingsError, UnitSettingsStore
from tests.test_stackchan_updater import make_release

KITCHEN = "aa:bb:cc:dd:ee:01"
DEN = "aa:bb:cc:dd:ee:02"


def _backend(tmp_path, **extra):
    return SettingsBackend(
        devices=lambda: {KITCHEN: {}, DEN: {}},
        store=UnitSettingsStore(tmp_path / "units.json"),
        live=lambda d: {"firmware_version": "1.1.0", "wifi_configured": d == KITCHEN},
        host_address="192.0.2.10:8050",
        **extra,
    )


def test_spanish_catalog_covers_every_english_key():
    assert set(CATALOG["en"]) == set(CATALOG["es"])
    assert t("es", "settings.update") == "Actualizar"
    assert t("fr", "settings.update") == "Mettre à jour" and t("zz", "settings.update") == "Update"


def test_settings_are_per_unit_and_persist(tmp_path):
    backend = _backend(tmp_path)
    backend.save(
        KITCHEN,
        {
            "name": "kitchen",
            "persona": "Be brief.",
            "volume_cap": 40,
            "llm": {"url": "http://192.0.2.5:8080/v1", "model": "m", "api_key_env": "STACKCHAN_KITCHEN_KEY"},
            "alarms": [{"time": "07:30", "days": ["mon", "fri"], "label": "up"}],
            "muted": True,
        },
    )
    state = {u["device_id"]: u for u in backend.state()["units"]}
    assert state[KITCHEN]["name"] == "kitchen" and state[KITCHEN]["volume_cap"] == 40
    assert state[KITCHEN]["wifi"] == "set" and state[DEN]["wifi"] == "unset"
    assert state[DEN]["persona"] == "" and state[DEN]["volume_cap"] == 100
    assert state[KITCHEN]["alarms"][0]["days"] == ["mon", "fri"]
    assert UnitSettingsStore(tmp_path / "units.json").get(KITCHEN)["persona"] == "Be brief."
    assert backend.state()["host_address"] == "192.0.2.10:8050"


@pytest.mark.parametrize(
    "bad,match",
    [
        ({"volume_cap": 101}, "0 to 100"),
        ({"volume_cap": True}, "0 to 100"),
        ({"alarms": [{"time": "25:00"}]}, "HH:MM"),
        ({"alarms": [{"time": "07:00", "days": ["xyz"]}]}, "Alarm days"),
        ({"llm": {"url": "ftp://x"}}, "http://"),
        ({"llm": {"api_key_env": "sk-abc def"}}, "NAME of the environment variable"),
        ({"llm": {"api_key_env": "AWS_SECRET_ACCESS_KEY"}}, "must start with STACKCHAN_"),
        ({"name": ""}, "1 to 40"),
        ({"color": "red"}, "Unknown setting color"),
    ],
)
def test_bad_values_are_refused_with_a_fix(tmp_path, bad, match):
    with pytest.raises(SettingsError, match=match):
        _backend(tmp_path).save(KITCHEN, bad)


def test_unpaired_unit_is_refused(tmp_path):
    with pytest.raises(SettingsError, match="not paired"):
        _backend(tmp_path).save("aa:bb:cc:dd:ee:99", {"name": "x"})


def test_effective_overlays_unit_values_on_top_level(tmp_path):
    store = UnitSettingsStore(tmp_path / "u.json")
    store.update(
        KITCHEN,
        {"persona": "Kitchen persona", "llm": {"url": "", "model": "big", "api_key_env": ""}},
    )
    base = {"persona": "Base", "llm": {"url": "http://192.0.2.9/v1", "model": "small"}}
    merged = store.effective(KITCHEN, base)
    assert merged["persona"] == "Kitchen persona" and merged["llm"] == {
        "url": "http://192.0.2.9/v1",
        "model": "big",
    }
    assert store.effective(DEN, base) == base


def test_update_button_checks_signed_release_then_pushes(tmp_path):
    folder, public, _ = make_release(tmp_path, version="1.2.0")
    pushed = []
    backend = _backend(
        tmp_path, update_source=folder, public_key=public, push=lambda *a: pushed.append(a)
    )
    # The default is a dry run: everything is checked, nothing is pushed.
    assert "Dry run" in backend.update(KITCHEN)
    assert not pushed
    # Only an explicit confirm pushes.
    assert "Update started" in backend.update(KITCHEN, dry_run=False)
    assert pushed and pushed[0][0] == KITCHEN
    assert "Actualizacion iniciada" in backend.update(KITCHEN, "es", dry_run=False)


def test_update_button_refusals(tmp_path):
    from maipai_body.bodies.stackchan.updater import UpdateRefused

    with pytest.raises(UpdateRefused, match="No update source"):
        _backend(tmp_path).update(KITCHEN)
    unsigned, public, _ = make_release(tmp_path, sign=False)
    with pytest.raises(UpdateRefused, match="not signed"):
        _backend(tmp_path, update_source=unsigned, public_key=public).update(KITCHEN)
    old, public2, _ = make_release(tmp_path, version="1.1.0")
    with pytest.raises(UpdateRefused, match="already runs the newest"):
        _backend(tmp_path, update_source=old, public_key=public2, push=lambda *a: None).update(
            KITCHEN
        )


def test_page_is_translated_and_escapes_nothing_unsafe():
    en, es = render_page("en").decode(), render_page("es").decode()
    assert "StackChan settings" in en and "Ajustes de StackChan" in es and "lang='es'" in es
    assert "Firmware version" in en and "Version del firmware" in es


def _call(server, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection(server.host, server.port, timeout=5)
    h = {"Content-Type": "application/json", **(headers or {})}
    conn.request(method, path, json.dumps(body) if body is not None else None, h)
    r = conn.getresponse()
    return r.status, r.read().decode()


def test_http_routes(tmp_path):
    folder, public, _ = make_release(tmp_path, version="1.2.0")
    pushed = []
    backend = _backend(
        tmp_path, update_source=folder, public_key=public, push=lambda *a: pushed.append(a)
    )
    server = DashboardServer(
        FakeReachyMiniClient(REACHY_MINI_PROFILE),
        REACHY_MINI_PROFILE,
        port=0,
        state_hz=50.0,
        settings=backend,
    )
    server.start()
    try:
        status, page = _call(server, "GET", "/settings?lang=es")
        assert status == 200 and "Ajustes de StackChan" in page
        status, data = _call(server, "GET", "/api/stackchan/settings")
        assert status == 200 and len(json.loads(data)["units"]) == 2
        status, data = _call(
            server, "POST", f"/api/stackchan/settings/{KITCHEN}", {"volume_cap": 30}
        )
        assert status == 200 and json.loads(data)["volume_cap"] == 30
        status, data = _call(
            server, "POST", f"/api/stackchan/settings/{KITCHEN}", {"volume_cap": 300}
        )
        assert status == 400 and "0 to 100" in json.loads(data)["error"]
        status, data = _call(
            server, "POST", f"/api/stackchan/settings/{KITCHEN}/update", {"lang": "en"}
        )
        assert status == 200 and not pushed and "Dry run" in json.loads(data)["message"]
        status, data = _call(
            server,
            "POST",
            f"/api/stackchan/settings/{KITCHEN}/update",
            {"lang": "en", "confirm": True},
        )
        assert status == 200 and pushed
        status, data = _call(
            server,
            "POST",
            f"/api/stackchan/settings/{KITCHEN}",
            {"volume_cap": 1},
            {"Origin": "http://evil.example"},
        )
        assert status == 403
    finally:
        server.stop()


def test_robot_toml_may_name_any_key_variable_but_the_page_may_not():
    from maipai_body.config import RobotConfig

    owned = RobotConfig.model_validate(
        {"units": {"k": {"device_id": "aa:bb:cc:dd:ee:01", "llm": {"url": "http://192.0.2.5:8080", "model": "m", "api_key_env": "MY_OWN_KEY"}}}}
    )
    assert owned.units["k"].llm.api_key_env == "MY_OWN_KEY"
