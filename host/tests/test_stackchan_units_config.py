# ruff: noqa: E501
"""[units.<name>] tables, `stackchan units` and `stackchan name`, and the unit pickers."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

from maipai_body import cli
from maipai_body.bench import BenchServer, SimUnit
from maipai_body.config import RobotConfig, load_config
from maipai_body.live_units import LiveUnits
from maipai_body.settings_page import SettingsBackend
from maipai_body.unit_settings import UnitSettingsStore
from maipai_body.units import UnitRegistry, default_unit

KITCHEN = "aa:bb:cc:dd:ee:01"
DEN = "aa:bb:cc:dd:ee:02"

TOML = f"""
[llm]
url = "http://192.0.2.1/v1"
model = "base"
persona = "base persona"

[units.kitchen]
device_id = "{KITCHEN}"
persona = "kitchen persona"
volume_cap = 60
[units.kitchen.llm]
url = "http://192.0.2.10/v1"
model = "kitchen-model"
[[units.kitchen.alarm]]
time = "07:30"
days = ["mon", "fri"]
label = "School"

[units.den]
device_id = "{DEN}"
"""


def _config(tmp_path, text=TOML):
    path = tmp_path / "robot.toml"
    path.write_text(text)
    return load_config(path)


def test_unit_tables_are_read_and_picked_by_device_id(tmp_path):
    config = _config(tmp_path)
    registry = UnitRegistry(
        config, UnitSettingsStore(tmp_path / "u.json"), brain_factory=lambda c: c
    )
    assert registry.config_for(KITCHEN).llm.model == "kitchen-model"
    assert registry.config_for(KITCHEN).llm.persona == "kitchen persona"
    assert registry.volume_cap_for(KITCHEN) == 60
    assert registry.alarms_for(KITCHEN)[0]["days"] == ["mon", "fri"]
    assert (
        registry.config_for(DEN).llm.model == "base"
    )  # a table with only an id inherits everything
    assert registry.config_for("aa:bb:cc:dd:ee:99") is config
    assert registry.snapshot(KITCHEN)["name"] == "kitchen"  # the table name is the label


def test_page_settings_win_over_the_toml_table(tmp_path):
    registry = UnitRegistry(
        _config(tmp_path), UnitSettingsStore(tmp_path / "u.json"), brain_factory=lambda c: c
    )
    registry.store.update(KITCHEN, {"persona": "from the page", "name": "Galley"})
    assert registry.config_for(KITCHEN).llm.persona == "from the page"
    assert registry.config_for(KITCHEN).llm.model == "kitchen-model"
    assert registry.snapshot(KITCHEN)["name"] == "Galley"


@pytest.mark.parametrize(
    ("snippet", "expect"),
    [
        ('device_id = "nope"', "not a unit address"),
        (
            f'device_id = "{KITCHEN}"\nvolume_cap = 300',
            "volume cap must be a whole number from 0 to 100",
        ),
        (f'device_id = "{KITCHEN}"\nvolum = 3', "volum is not a unit setting"),
        ('persona = "x"', "device_id is missing"),
        (
            f'device_id = "{KITCHEN}"\n[units.b]\ndevice_id = "{KITCHEN.upper()}"',
            "use the same device_id",
        ),
        (f'device_id = "{KITCHEN}"\n[units.a.llm]\nurl = "ftp://x"', "must start with http"),
        (f'device_id = "{KITCHEN}"\n[[units.a.alarm]]\ntime = "7pm"', "not HH:MM"),
    ],
)
def test_bad_unit_tables_are_refused_in_plain_words(tmp_path, snippet, expect):
    with pytest.raises(ValueError) as error:
        _config(tmp_path, f"[units.a]\n{snippet}\n")
    text = str(error.value)
    assert expect in text and "robot.toml" in text or expect in text
    assert "Correct or remove" in text or "Fix it" in text or "Give each" in text


def test_example_config_still_loads(tmp_path):
    from pathlib import Path

    example = Path(__file__).resolve().parents[1] / "robot.example.toml"
    assert RobotConfig.model_validate(__import__("tomllib").loads(example.read_text())).units == {}
    lines = example.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("# [units.kitchen]"))
    uncommented = "\n".join(lines[:start] + [line[2:] for line in lines[start:]])
    assert "kitchen" in RobotConfig.model_validate(__import__("tomllib").loads(uncommented)).units


class _Pairing:
    def __init__(self, ids):
        self.ids = ids

    def paired_devices(self):
        return {i: {} for i in self.ids}


def test_units_and_name_commands(tmp_path, monkeypatch, capsys):
    config = _config(tmp_path)
    monkeypatch.setattr("maipai_body.unit_settings.default_path", lambda: tmp_path / "u.json")
    pairing = _Pairing([KITCHEN, DEN, "aa:bb:cc:dd:ee:03"])
    monkeypatch.setattr(cli, "_online_from_host", lambda url: {KITCHEN})
    args = lambda **kw: type("A", (), kw)()  # noqa: E731
    assert cli._units_or_name(args(command="units", host_url="x"), config, pairing) == 0
    out = capsys.readouterr().out
    assert f"kitchen: {KITCHEN}, online" in out and f"den: {DEN}, offline" in out
    assert "StackChan ee:03: aa:bb:cc:dd:ee:03, offline" in out  # unnamed: a label from its id
    assert (
        cli._units_or_name(
            args(command="name", unit="aa:bb:cc:dd:ee:03", new_name="Attic"), config, pairing
        )
        == 0
    )
    assert "now called Attic" in capsys.readouterr().out
    # by current name, and the saved name shows afterwards
    assert (
        cli._units_or_name(args(command="name", unit="attic", new_name="Loft"), config, pairing)
        == 0
    )
    capsys.readouterr()
    cli._units_or_name(args(command="units", host_url="x"), config, pairing)
    assert "Loft: aa:bb:cc:dd:ee:03" in capsys.readouterr().out
    # plain refusals
    assert cli._units_or_name(args(command="name", unit="zzz", new_name="X"), config, pairing) == 2
    assert "Run `stackchan units`" in capsys.readouterr().err
    assert (
        cli._units_or_name(args(command="name", unit="kitchen", new_name="den"), config, pairing)
        == 2
    )
    assert "Pick a different name" in capsys.readouterr().err
    assert (
        cli._units_or_name(args(command="name", unit="kitchen", new_name=" "), config, pairing) == 2
    )
    assert "1 to 40 characters" in capsys.readouterr().err


def test_units_command_says_when_the_host_is_not_running(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("maipai_body.unit_settings.default_path", lambda: tmp_path / "u.json")
    monkeypatch.setattr(cli, "_online_from_host", lambda url: None)
    cli._units_or_name(
        type("A", (), {"command": "units", "host_url": "http://h"})(),
        RobotConfig(),
        _Pairing([KITCHEN]),
    )
    out = capsys.readouterr().out
    assert "unknown" in out and "Start the StackChan host" in out


def test_default_unit_is_the_only_one_or_the_first_online():
    one = [{"device_id": KITCHEN, "online": False}]
    two = [{"device_id": KITCHEN, "online": False}, {"device_id": DEN, "online": True}]
    none = [{"device_id": KITCHEN, "online": False}, {"device_id": DEN, "online": False}]
    assert default_unit(one) == KITCHEN and default_unit(two) == DEN and default_unit(none) is None


def test_status_page_state_names_the_default_unit(tmp_path):
    live = {KITCHEN: {"online": False}, DEN: {"online": True}}
    backend = SettingsBackend(
        devices=lambda: {KITCHEN: {}, DEN: {}},
        store=UnitSettingsStore(tmp_path / "u.json"),
        live=lambda d: live[d],
    )
    assert backend.state()["default_unit"] == DEN
    alone = SettingsBackend(
        devices=lambda: {KITCHEN: {}}, store=UnitSettingsStore(tmp_path / "u.json")
    )
    assert alone.state()["default_unit"] == KITCHEN
    assert b"role:'tab'" in backend.route_get("/settings", "en", True)[2]


def test_live_version_comes_from_the_fw_event_not_a_guessed_status_key():
    class Voice:
        def connected_devices(self):
            return [KITCHEN, DEN]

        def call_device_tool(self, name, arguments, *, timeout=5.0, device_id=None):
            if name == "self.get_device_status":
                raise AssertionError("the status tool carries no firmware version")
            return []

    live = LiveUnits(Voice(), sole_unit_version=lambda: "9.9.9")
    assert "firmware_version" not in live.live(KITCHEN)  # two units: the single fact is not theirs
    live.note_event(DEN, "fw", {"version": "0.2.31", "rssi": -60})
    assert live.live(DEN)["firmware_version"] == "0.2.31"
    live.note_event(KITCHEN, "fw", {"version": "unknown", "rssi": 0})
    assert "firmware_version" not in live.live(KITCHEN)


# -- the bench: two fake units ----------------------------------------------------------------


def _bench():
    kitchen, den = SimUnit(), SimUnit()
    den.connected = False
    server = BenchServer(
        port=0, units={KITCHEN: kitchen, DEN: den}, names={KITCHEN: "kitchen", DEN: "den"}
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.address[1]}", kitchen, den


def _post(url, path, data):
    request = urllib.request.Request(
        url + path, json.dumps(data).encode(), {"Content-Type": "application/json"}
    )
    try:
        return json.loads(urllib.request.urlopen(request, timeout=2).read())
    except urllib.error.HTTPError as error:
        return json.loads(error.read())


def test_bench_controls_take_a_unit_and_default_to_the_first_online():
    server, url, kitchen, den = _bench()
    try:
        listing = json.loads(urllib.request.urlopen(url + "/api/units").read())
        assert listing["default"] == KITCHEN and [u["name"] for u in listing["units"]] == [
            "kitchen",
            "den",
        ]
        _post(url, "/api/head", {"yaw": 20, "pitch": 10, "unit": DEN})
        assert (den.yaw, kitchen.yaw) == (20, 0)
        _post(url, "/api/head", {"yaw": -30, "pitch": 12})  # no unit: the first online
        assert (kitchen.yaw, den.yaw) == (-30, 20)
        _post(url, "/api/brightness", {"value": 40, "unit": DEN})
        assert (den.brightness, kitchen.brightness) == (40, 100)
        _post(url, "/api/lights", {"mode": "all", "rgb": [1, 2, 3], "unit": DEN})
        assert den.colors[0] == (1, 2, 3) and kitchen.colors[0] == (0, 0, 0)
        _post(url, "/api/privacy", {"camera_off": True, "unit": DEN})
        assert den.camera_off is True and kitchen.camera_off is False
        status = json.loads(urllib.request.urlopen(url + "/api/status?unit=" + DEN).read())
        assert status["unit"] == DEN and status["connected"] is False
        assert {
            c["unit"] for c in json.loads(urllib.request.urlopen(url + "/api/log").read())["calls"]
        } == {KITCHEN, DEN}
        bad = _post(url, "/api/head", {"yaw": 1, "pitch": 10, "unit": "aa:bb:cc:dd:ee:99"})
        assert "Pick a unit from the unit list" in bad["error"]
        assert b"id=unit" in urllib.request.urlopen(url + "/").read()
    finally:
        server.httpd.shutdown()
        server.httpd.server_close()


def test_bench_with_two_units_offline_asks_for_a_pick():
    a, b = SimUnit(), SimUnit()
    a.connected = b.connected = False
    server = BenchServer(port=0, units={KITCHEN: a, DEN: b})
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.address[1]}"
    try:
        assert "none is online" in _post(url, "/api/head", {"yaw": 1, "pitch": 10})["error"]
    finally:
        server.httpd.shutdown()
        server.httpd.server_close()
