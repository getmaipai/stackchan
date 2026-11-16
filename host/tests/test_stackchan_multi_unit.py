# ruff: noqa: E501
"""Several robots on one host: each unit's settings are picked by its Device-Id (two fake units)."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest
from websockets.asyncio.server import serve

from maipai_body.bodies.stackchan.avatar.server import AvatarServer
from maipai_body.bodies.stackchan.turn import StackChanTurnBridge
from maipai_body.bodies.stackchan.volume import VolumeCommand, VolumeControl
from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
from maipai_body.brain.fake import FakeBrain
from maipai_body.config import RobotConfig
from maipai_body.live_units import LiveUnits
from maipai_body.settings_page import SettingsBackend
from maipai_body.unit_settings import UnitSettingsStore
from maipai_body.units import UnitRegistry
from tests.stackchan_sim.avatar_peer import AvatarPeer

KITCHEN = "aa:bb:cc:dd:ee:01"
DEN = "aa:bb:cc:dd:ee:02"
STRANGER = "aa:bb:cc:dd:ee:99"


class _Brain(FakeBrain):
    def __init__(self, config):
        super().__init__(reply=config.llm.persona)
        self.config = config


@pytest.fixture
def registry(tmp_path):
    store = UnitSettingsStore(tmp_path / "units.json")
    store.update(
        KITCHEN,
        {
            "name": "kitchen",
            "persona": "You are a cheerful kitchen helper.",
            "llm": {"url": "http://192.0.2.10:8080", "model": "kitchen-model", "api_key_env": ""},
            "volume_cap": 40,
            "alarms": [{"time": "23:58", "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"], "label": "bread"}],
        },
    )
    store.update(
        DEN,
        {
            "name": "den",
            "persona": "You are a calm den companion.",
            "llm": {"url": "http://192.0.2.11:8080", "model": "den-model", "api_key_env": ""},
            "alarms": [{"time": "23:59", "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"], "label": "bed"}],
        },
    )
    # 2026-11-16 12:00 local, a Monday.
    noon = time.mktime((2026, 11, 16, 12, 0, 0, 0, 0, -1))
    return UnitRegistry(RobotConfig(), store, brain_factory=_Brain, clock=lambda: noon)


def test_each_unit_gets_its_own_model_persona_and_brain(registry):
    kitchen, den = registry.brain_for(KITCHEN), registry.brain_for(DEN)
    assert kitchen is not den
    assert (kitchen.config.llm.model, kitchen.config.llm.persona) == (
        "kitchen-model",
        "You are a cheerful kitchen helper.",
    )
    assert (den.config.llm.model, den.config.llm.persona) == (
        "den-model",
        "You are a calm den companion.",
    )
    assert registry.brain_for(KITCHEN) is kitchen


def test_unknown_unit_gets_the_default_and_its_own_brain(registry):
    stranger = registry.brain_for(STRANGER)
    assert stranger.config.llm.model == RobotConfig().llm.model
    assert stranger.config.llm.persona == RobotConfig().llm.persona
    assert stranger is not registry.brain_for(KITCHEN)
    assert not registry.has_own_llm(STRANGER) and registry.volume_cap_for(STRANGER) == 100
    assert registry.alarms_for(STRANGER) == []


def test_history_is_never_shared_between_units(registry):
    registry.turn_for(KITCHEN).stream("what is for dinner")
    list(registry.turn_for(KITCHEN).stream("what is for dinner"))
    list(registry.turn_for(DEN).stream("good night"))
    kitchen, den = registry.brain_for(KITCHEN), registry.brain_for(DEN)
    assert [t.text for t in kitchen.turns] == ["what is for dinner"]
    assert [t.text for t in den.turns] == ["good night"]
    assert kitchen.turns[0].conversation_id == KITCHEN and den.turns[0].conversation_id == DEN


def test_changing_a_setting_rebuilds_only_that_units_brain(registry):
    before_kitchen, before_den = registry.brain_for(KITCHEN), registry.brain_for(DEN)
    registry.store.update(DEN, {"persona": "You are a bedtime storyteller."})
    assert registry.brain_for(KITCHEN) is before_kitchen
    assert registry.brain_for(DEN) is not before_den
    assert registry.brain_for(DEN).config.llm.persona == "You are a bedtime storyteller."


def test_alarms_are_pushed_to_the_unit_that_owns_them_only(registry):
    calls = []
    record = lambda device, name, args: calls.append((device, name, args))  # noqa: E731
    assert registry.push_alarms(KITCHEN, record) == 1
    assert registry.push_alarms(KITCHEN, record) == 0  # a reconnect does not push twice
    assert registry.push_alarms(STRANGER, record) == 0
    assert registry.push_alarms(DEN, record) == 1
    assert [(c[0], c[2]["label"], c[2]["hour"], c[2]["minute"]) for c in calls] == [
        (KITCHEN, "bread", 23, 58),
        (DEN, "bed", 23, 59),
    ]
    assert all(c[1] == "self.timer.alarm" for c in calls)


def test_volume_cap_is_the_units_own(registry):
    sets = []
    control = VolumeControl(lambda *_: {"speaker": {"volume": 30}}, sets.append)
    _, kitchen = control.apply(VolumeCommand("max"), registry.volume_cap_for(KITCHEN))
    _, den = control.apply(VolumeCommand("max"), registry.volume_cap_for(DEN))
    assert kitchen == 40 and den == 100


def test_voice_link_picks_the_units_turn_client(registry):
    home = object()
    bridge = SimpleNamespace(units=registry, turn_factory=lambda base, cookie: home)
    pick = StackChanTurnBridge._turn_for
    kitchen_turn = pick(bridge, KITCHEN, "b", "c")
    assert kitchen_turn is not home and kitchen_turn._brain.config.llm.model == "kitchen-model"
    assert pick(bridge, STRANGER, "b", "c") is home  # no own model: the Home turn client
    assert StackChanTurnBridge._volume_cap(bridge, KITCHEN) == 40
    assert StackChanTurnBridge._volume_cap(SimpleNamespace(units=None), KITCHEN) is None


def test_avatar_socket_reads_only_its_own_units_settings(registry):
    asyncio.run(_avatar_socket_case(registry))


async def _avatar_socket_case(registry):
    pairing = PairingStore()
    peers, tokens = [], {}
    avatar = AvatarServer(pairing)
    avatar.units = registry
    for index, device in enumerate((KITCHEN, DEN, STRANGER)):
        client = f"00000000-0000-4000-8000-0000000000{index + 20}"
        pairing.request(device, client)
        tokens[device] = (client, pairing.approve(device, client))
    server = await serve(avatar.handle, "127.0.0.1", 0)
    url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/stackChan/ws?deviceType=StackChan"
    try:
        for device, (client, token) in tokens.items():
            peer = AvatarPeer(url, device, client, token)
            await peer.connect()
            peers.append(peer)
        assert avatar.unit_config[KITCHEN]["persona"] == "You are a cheerful kitchen helper."
        assert avatar.unit_config[KITCHEN]["volume_cap"] == 40
        assert avatar.unit_config[DEN]["persona"] == "You are a calm den companion."
        assert avatar.unit_config[DEN]["volume_cap"] == 100
        assert avatar.unit_config[STRANGER]["persona"] == RobotConfig().llm.persona
        assert avatar.unit_config[STRANGER]["alarms"] == []
    finally:
        for peer in peers:
            await peer.close()
        server.close()
        await server.wait_closed()


class _Voice:
    def __init__(self):
        self.sessions = {KITCHEN: {"version": "1.1.0", "wifi": [{"ssid": "home"}]}}
        self.calls, self.served = [], []

    def connected_devices(self):
        return list(self.sessions)

    def call_device_tool(self, name, arguments, *, timeout=5.0, device_id=None):
        self.calls.append((device_id, name, arguments))
        unit = self.sessions[device_id]
        if name == "self.get_device_status":
            return {"version": unit["version"]}
        if name == "self.wifi.list_saved":
            return unit["wifi"]
        return {}

    def serve_firmware_once(self, path, device_id=None):
        self.served.append(device_id)
        return f"http://192.0.2.1/firmware/{device_id}/x"


def test_live_state_is_per_unit_and_offline_is_plain(tmp_path):
    voice = _Voice()
    live = LiveUnits(voice)
    assert live.live(KITCHEN) == {"online": True, "firmware_version": "1.1.0", "wifi_configured": True}
    assert live.live(DEN) == {"online": False}
    backend = SettingsBackend(
        devices=lambda: {KITCHEN: {}, DEN: {}},
        store=UnitSettingsStore(tmp_path / "u.json"),
        live=live.live,
    )
    units = {u["device_id"]: u for u in backend.state()["units"]}
    assert units[KITCHEN]["online"] is True and units[KITCHEN]["firmware_version"] == "1.1.0"
    assert units[KITCHEN]["wifi"] == "set"
    assert units[DEN]["online"] is False and units[DEN]["firmware_version"] is None


def test_ota_push_targets_the_one_unit(tmp_path):
    voice = _Voice()
    LiveUnits(voice).push(KITCHEN, tmp_path / "app.bin", "ab" * 32, 10, "1.2.0")
    assert voice.served == [KITCHEN]
    assert voice.calls[-1][:2] == (KITCHEN, "self.firmware.update")


def test_a_device_tool_call_for_an_absent_unit_says_which_one(tmp_path):
    from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer

    server = XiaozhiServer(PairingStore(), robot=None)
    server._sessions = {KITCHEN: object()}
    with pytest.raises(ConnectionError, match="ee:99|e:99|not connected"):
        server.call_device_tool("self.get_device_status", {}, device_id=STRANGER)
    with pytest.raises(ConnectionError, match="not connected"):
        server.serve_firmware_once(tmp_path / "x.bin", STRANGER)


def test_published_firmware_image_is_served_once(tmp_path):
    from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer

    image = tmp_path / "app.bin"
    image.write_bytes(b"image-bytes")
    server = XiaozhiServer(PairingStore(), robot=None)
    server._sessions = {KITCHEN: object(), DEN: object()}
    server.advertised_vision_url = "http://192.0.2.1:8767/vision/x"
    url = server.serve_firmware_once(image, DEN)
    assert f"/firmware/{DEN}/" in url
    token = url.rsplit("/", 1)[1]
    request = SimpleNamespace(match_info={"device_id": DEN, "token": token})
    response = asyncio.run(server._serve_firmware_file(request))
    assert response.body == b"image-bytes"
    with pytest.raises(Exception):  # a second read is refused
        asyncio.run(server._serve_firmware_file(request))
    with pytest.raises(ConnectionError, match="Device-Id"):
        server.serve_firmware_once(image)


def test_live_settings_server_serves_live_state_and_dry_runs_update(tmp_path):
    import http.client
    import json

    from maipai_body.settings_server import SettingsServer
    from tests.test_stackchan_updater import make_release

    folder, public, _ = make_release(tmp_path, version="1.2.0")
    pushed = []
    backend = SettingsBackend(
        devices=lambda: {KITCHEN: {}, DEN: {}},
        store=UnitSettingsStore(tmp_path / "u.json"),
        live=LiveUnits(_Voice()).live,
        update_source=folder,
        public_key=public,
        push=lambda *a: pushed.append(a),
    )
    server = SettingsServer(backend, "127.0.0.1", 0)
    server.start()

    def call(method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", server.port)
        headers = {"Content-Type": "application/json", "Host": f"127.0.0.1:{server.port}"}
        conn.request(method, path, json.dumps(body) if body is not None else None, headers)
        reply = conn.getresponse()
        return reply.status, json.loads(reply.read() or b"{}")

    try:
        status, state = call("GET", "/api/stackchan/settings")
        assert status == 200 and {u["device_id"]: u["online"] for u in state["units"]} == {
            KITCHEN: True,
            DEN: False,
        }
        status, saved = call("POST", f"/api/stackchan/settings/{DEN}", {"volume_cap": 25})
        assert status == 200 and saved["volume_cap"] == 25
        path = f"/api/stackchan/settings/{KITCHEN}/update"
        status, reply = call("POST", path, {})
        assert status == 200 and "Dry run" in reply["message"] and not pushed
        status, reply = call("POST", path, {"confirm": True})
        assert status == 200 and pushed
    finally:
        server.stop()
