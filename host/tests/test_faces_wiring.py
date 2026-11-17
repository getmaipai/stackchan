"""Face settings wired in: the CLI command, the settings page and routes, the turn cue and sync."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from maipai_body import cli, faces
from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
from maipai_body.config import RobotConfig
from maipai_body.i18n import CATALOG, t
from maipai_body.settings_page import SettingsBackend, render_page
from maipai_body.unit_settings import UnitSettingsStore
from tests.test_faces import UNIT, FakeFirmware

KEYS = [k for k in CATALOG["en"] if k.startswith("settings.face")]


def _backend(tmp_path: Path, firmware: FakeFirmware | None = None) -> SettingsBackend:
    store = faces.FaceStore(tmp_path / "f.json")
    service = faces.FaceService(firmware or faces.offline_call, store)
    return SettingsBackend(
        devices=lambda: {UNIT: {}},
        store=UnitSettingsStore(tmp_path / "units.json"),
        faces=service,
    )


def test_face_strings_exist_in_both_languages() -> None:
    assert KEYS and all(k in CATALOG["es"] for k in KEYS)
    assert t("es", "settings.face.save") != t("en", "settings.face.save")
    for lang in ("en", "es"):
        page = render_page(lang).decode()
        assert t(lang, "settings.face.captions") in page and "BUILDERS.look" in page


def test_page_routes_show_and_save_a_unit_face(tmp_path: Path) -> None:
    firmware = FakeFirmware()
    backend = _backend(tmp_path, firmware)
    status, _, body = backend.route_get(f"/api/stackchan/faces/{UNIT}", "en", True)
    assert status == 200 and json.loads(body)["values"]["captions"] is False
    status, payload = backend.route_post(
        f"/api/stackchan/faces/{UNIT}",
        {"lang": "es", "style": "big_eyes", "color": "mint", "captions": True, "tod": True},
        True,
    )
    assert status == 200 and payload["pushed"] is True
    assert firmware.state["style"] == "big_eyes" and firmware.state["tod"] is True
    status, payload = backend.route_post(f"/api/stackchan/faces/{UNIT}", {"style": "huge"}, True)
    assert status == 400 and "big_eyes, eyes_only, stock, classic or minimal" in payload["error"]
    status, payload = backend.route_post(
        f"/api/stackchan/faces/{UNIT}", {"color": "#101010", "lang": "es"}, True
    )
    assert status == 400 and "oscuro" in payload["error"]
    status, payload = backend.route_post(f"/api/stackchan/faces/{UNIT}/reset", {}, True)
    assert status == 200 and firmware.state["style"] == "big_eyes"


def test_page_routes_refuse_non_local_and_unpaired(tmp_path: Path) -> None:
    backend = _backend(tmp_path)
    assert backend.route_get(f"/api/stackchan/faces/{UNIT}", "en", False)[0] == 403
    assert backend.route_post(f"/api/stackchan/faces/{UNIT}", {}, False)[0] == 403
    status, payload = backend.route_post("/api/stackchan/faces/zz", {"style": "minimal"}, True)
    assert status == 400 and "not paired" in payload["error"]


def test_offline_unit_saves_and_says_so(tmp_path: Path) -> None:
    backend = _backend(tmp_path)
    status, payload = backend.route_post(f"/api/stackchan/faces/{UNIT}", {"captions": True}, True)
    assert status == 200 and payload["pushed"] is False and "reconnects" in payload["message"]
    view = json.loads(backend.route_get(f"/api/stackchan/faces/{UNIT}", "en", True)[2])
    assert view["values"]["captions"] is True and view["pending"] is True


def test_turn_cue_starts_on_thinking_and_ends_on_speaking_and_settle(tmp_path: Path) -> None:
    firmware = FakeFirmware()
    service = faces.FaceService(firmware, faces.FaceStore(tmp_path / "f.json"))
    seen = lambda: [c[1]["on"] for c in firmware.calls if c[0] == "self.face.thinking"]  # noqa: E731
    for state in ("listening", "thinking", "speaking", "thinking", "settle"):
        faces.turn_cue(service, lambda: [UNIT], state)
    assert seen() == [True, False, True, False]


def test_turn_cue_never_fails_the_turn(tmp_path: Path) -> None:
    firmware = FakeFirmware()
    service = faces.FaceService(firmware, faces.FaceStore(tmp_path / "f.json"))
    firmware.link = False
    faces.turn_cue(service, lambda: [UNIT], "thinking")
    firmware.link, firmware.has_tools = True, False
    faces.turn_cue(service, lambda: [UNIT], "thinking")
    faces.turn_cue(service, lambda: [], "thinking")


def test_sync_on_connect_pushes_saved_settings_and_never_raises(tmp_path: Path) -> None:
    firmware = FakeFirmware()
    service = faces.FaceService(firmware, faces.FaceStore(tmp_path / "f.json"))
    service.store.set(UNIT, faces.FaceConfig(style="minimal", captions=True))
    faces.sync_on_connect(service, UNIT)
    assert firmware.state["style"] == "minimal" and firmware.state["captions"] is True

    def boom(*_a: object, **_k: object) -> object:
        raise RuntimeError("broken")

    faces.sync_on_connect(faces.FaceService(boom, service.store), UNIT)


def test_turn_sink_starts_and_ends_the_cue(tmp_path: Path) -> None:
    from maipai_body.app import _turn_sink

    class Quiet:
        def render_turn_state(self, state: str, *, mood: str | None = None) -> None:
            pass

        def update(self, **_kw: object) -> None:
            pass

    firmware = FakeFirmware()
    service = faces.FaceService(firmware, faces.FaceStore(tmp_path / "f.json"))
    sink = _turn_sink(Quiet(), Quiet(), service, lambda: [UNIT])
    for state in ("thinking", "speaking", "settle"):
        sink(state)
    import time

    for _ in range(50):
        if len([c for c in firmware.calls if c[0] == "self.face.thinking"]) >= 3:
            break
        time.sleep(0.05)
    assert [c[1]["on"] for c in firmware.calls if c[0] == "self.face.thinking"] == [
        True,
        False,
        False,
    ]


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    store = PairingStore(tmp_path / "pairing.json")
    client = "11111111-1111-4111-8111-111111111111"
    store.redeem_pair_code(UNIT.lower(), client, store.create_pair_code())
    monkeypatch.setattr(cli, "load_config", lambda: RobotConfig(brain="home"))
    monkeypatch.setattr(cli, "default_pairing_path", lambda: tmp_path / "pairing.json")
    return tmp_path


def _run(monkeypatch: pytest.MonkeyPatch, *argv: str) -> int:
    monkeypatch.setattr(
        "sys.argv", ["stackchan", "face", *argv, "--host-url", "http://127.0.0.1:1"]
    )
    return cli.main()


def test_cli_face_set_and_show_without_a_host(cli_env: Path, monkeypatch, capsys) -> None:
    code = _run(
        monkeypatch,
        "set",
        UNIT,
        "--style",
        "minimal",
        "--color",
        "sky",
        "--captions",
        "on",
        "--schedule",
        "on",
        "--hours",
        "5,8,19,22",
    )
    out = capsys.readouterr().out
    assert code == 0 and "host is not running" in out
    assert _run(monkeypatch, "show", UNIT) == 0
    shown = capsys.readouterr().out
    assert "style: minimal" in shown and "color: sky" in shown and "captions: True" in shown
    assert "tod_hours: [5, 8, 19, 22]" in shown
    assert _run(monkeypatch, "reset", UNIT) == 0
    capsys.readouterr()
    _run(monkeypatch, "show", UNIT)
    assert "style: big_eyes" in capsys.readouterr().out


def test_cli_face_errors_say_what_to_do(cli_env: Path, monkeypatch, capsys) -> None:
    assert _run(monkeypatch, "set", UNIT, "--style", "huge") == 2
    assert "big_eyes, eyes_only, stock, classic or minimal" in capsys.readouterr().err
    assert _run(monkeypatch, "set", UNIT, "--hours", "a,b") == 2
    assert "four whole numbers" in capsys.readouterr().err
    assert _run(monkeypatch, "set", UNIT) == 2
    assert "Nothing to set" in capsys.readouterr().err
    assert _run(monkeypatch, "show", "nobody") == 2
    assert "stackchan units" in capsys.readouterr().err
