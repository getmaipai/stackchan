# ruff: noqa: E501
"""The host side of the remote trust boundary (firmware patch FM03): controllers cannot set source or token, and the host
stamps its own session id on every cued call that is not a controller's, at the one place every unit call passes."""

from __future__ import annotations

import asyncio
import threading
from unittest.mock import AsyncMock, patch

import pytest

from maipai_body import remote_trust as rt
from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiServer
from maipai_body.settings_sim import KITCHEN, build

HOST = 424242
CUED_CALLS = (
    ("self.robot.set_head_angles", {"yaw": 80, "pitch": 10}),
    ("self.robot.dance", {"name": "groove"}),
    ("self.game.start", {"name": "memory"}),
    ("self.audio.play_sound", {"name": "chirp", "find": 1}),
    ("self.listen.test", {}),
    ("self.camera.take_photo", {"question": "x"}),
)


def _access(backend, rest, body=None, local=True):
    return backend.route_post(
        "/api/stackchan/remote-access" + ("/" + rest if rest else ""),
        {"lang": "en", **(body or {})},
        local,
    )


def _paired(backend) -> str:
    _access(backend, "", {"enabled": True})
    pair = _access(backend, "pair", {"label": "Phone"}, local=False)[1]
    _access(backend, "allow", {"id": pair["id"]})
    return pair["token"]


@pytest.mark.parametrize(
    ("name", "arguments"), CUED_CALLS, ids=lambda v: v if isinstance(v, str) else ""
)
def test_a_call_that_is_not_a_controllers_gets_the_host_id_as_its_token(name, arguments) -> None:
    out = rt.stamp_call(name, arguments, HOST)
    assert (
        out["token"] == HOST and arguments.get("token") is None
    )  # the caller's dict is not changed


def test_other_calls_and_marked_remote_calls_are_left_alone() -> None:
    assert rt.stamp_call("self.audio.play_sound", {"name": "x", "find": 2}, HOST) == {
        "name": "x",
        "find": 2,
    }
    assert rt.stamp_call("self.robot.get_head_angles", {}, HOST) == {}
    marked = {"yaw": 5, "source": "remote", "token": 7}
    assert (
        rt.stamp_call("self.robot.set_head_angles", marked, HOST) == marked
    )  # exactly as the cue marked it


def test_the_session_heartbeat_announces_the_host_id_and_a_caller_cannot_choose_it() -> None:
    assert rt.stamp_call(rt.SESSION_TOOL, {"active": True, "label": "Phone"}, HOST)["host"] == HOST
    assert rt.stamp_call(rt.SESSION_TOOL, {"active": True, "host": 1}, HOST)["host"] == HOST


def test_a_controllers_own_unit_calls_are_never_stamped() -> None:
    with rt.controller_scope():
        assert rt.in_controller_scope()
        assert "token" not in rt.stamp_call(
            "self.robot.set_head_angles", {"yaw": 90}, HOST
        )  # the unit then refuses it
    assert not rt.in_controller_scope()
    seen: list[bool] = []
    with rt.controller_scope():
        thread = threading.Thread(
            target=lambda: seen.append(rt.in_controller_scope())
        )  # another thread is not a controller's
        thread.start()
        thread.join()
    assert seen == [False]


def test_a_controller_scope_follows_an_async_task_and_ends_with_it() -> None:
    import asyncio

    async def inside() -> bool:
        await asyncio.sleep(0)  # a task switch must not drop the marker
        return rt.in_controller_scope()

    async def run() -> tuple[bool, bool]:
        with rt.controller_scope():
            scoped = await inside()
        return scoped, await inside()

    assert asyncio.run(run()) == (True, False)


def test_reserved_keys() -> None:
    assert rt.reserved_in({"do": "head", "yaw": 3}) == []
    assert rt.reserved_in(
        {"do": "head", "source": "user", "token": 5, "cue_kind": "find", "host": 1}
    ) == ["cue_kind", "host", "source", "token"]


def test_a_controller_request_that_names_source_or_host_is_refused_before_the_unit_hears_anything(
    tmp_path,
) -> None:
    backend, units = build(tmp_path, next_unit=True)
    token = _paired(backend)
    kitchen = units[KITCHEN]
    for reserved in (
        {"source": "user"},
        {"host": 5},
        {"cue_kind": "find"},
        {"host_id": 9},
        {"cue": "x"},
    ):
        kitchen.calls.clear()
        status, payload = _access(
            backend,
            "act",
            {"token": token, "unit": KITCHEN, "do": "head", "yaw": 5, "pitch": 20, **reserved},
            local=False,
        )
        assert status == 400 and "only the host may set" in payload["error"], reserved
        assert not [
            n for n, _ in kitchen.calls if n in {"self.robot.set_head_angles", "self.remote.action"}
        ]
    rows = backend.activity.log.rows()
    assert rows and all(r["result"] == "refused" and r["controller"] == "Phone" for r in rows[:5])


def test_a_controller_cannot_pass_its_own_token_as_the_cue_token(tmp_path) -> None:
    """The route spends the controller's pairing token to find who it is and drops it; the cue token on the call is the unit's."""
    backend, units = build(tmp_path, next_unit=True)
    token = _paired(backend)
    kitchen = units[KITCHEN]
    assert (
        _access(
            backend,
            "act",
            {"token": token, "unit": KITCHEN, "do": "head", "yaw": 5, "pitch": 20},
            local=False,
        )[0]
        == 200
    )
    call = next(a for n, a in kitchen.calls if n == "self.robot.set_head_angles")
    assert call["source"] == "remote" and call["token"] == 4242 and call["token"] != token


def test_the_local_owner_page_is_not_a_controller_and_is_not_refused_for_extra_keys(
    tmp_path,
) -> None:
    backend, units = build(tmp_path, next_unit=True)
    status, _ = backend.route_post(
        f"/api/stackchan/unit/{KITCHEN}/remote",
        {"lang": "en", "do": "head", "yaw": 5, "pitch": 20},
        True,
    )
    assert status == 200


class _Stamping:
    """XiaozhiServer.call_device_tool with the socket stubbed: records what would have been sent to the unit."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, dict]] = []

    async def run(
        self, service: XiaozhiServer, name: str, arguments: dict, scoped: bool = False
    ) -> None:
        async def send(_device_id, _websocket, _request_id, tool, args):
            self.sent.append((tool, args))

        service._loop = asyncio.get_running_loop()
        service._sessions["02:00:00:00:00:20"] = object()  # type: ignore[assignment]

        def call() -> object:
            if scoped:
                with rt.controller_scope():
                    return service.call_device_tool(name, arguments, timeout=1.0)
            return service.call_device_tool(name, arguments, timeout=1.0)

        with (
            patch.object(service, "_session_authorized", return_value=True),
            patch.object(service, "_send_device_tool", new=send),
            patch.object(service, "_await_device_reply", new=AsyncMock(return_value="ok")),
        ):
            await asyncio.to_thread(call)


def test_every_unit_call_passes_the_one_chokepoint_that_stamps_it() -> None:
    service = XiaozhiServer(PairingStore(), None)
    assert 0 < service.remote_host_id < 2**31 - 1
    other = XiaozhiServer(PairingStore(), None)
    assert other.remote_host_id != service.remote_host_id  # a new host process is a new id

    async def scenario() -> list[tuple[str, dict]]:
        rig = _Stamping()
        await rig.run(service, "self.robot.dance", {"name": "happy"})
        await rig.run(service, "self.robot.dance", {"name": "happy"}, scoped=True)
        await rig.run(service, "self.remote.session", {"active": True, "label": "Phone"})
        await rig.run(service, "self.robot.get_head_angles", {})
        return rig.sent

    sent = asyncio.run(scenario())
    assert sent[0][1]["token"] == service.remote_host_id  # the brain's or the owner's call
    assert "token" not in sent[1][1]  # a controller's action: never stamped
    assert sent[2][1]["host"] == service.remote_host_id
    assert sent[3][1] == {}
