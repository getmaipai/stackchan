"""Source contracts for the replay-only firmware review fixes.

Set STACKCHAN_FW_REPLAY_TREE to the replay root when running these checks.
"""
from __future__ import annotations

import os
from pathlib import Path
import re

import pytest

ROOT_VALUE = os.environ.get("STACKCHAN_FW_REPLAY_TREE")
ROOT = Path(ROOT_VALUE) if ROOT_VALUE else Path(".")
pytestmark = pytest.mark.skipif(not ROOT_VALUE, reason="set STACKCHAN_FW_REPLAY_TREE to the firmware replay root")


def source(path: str) -> str:
    return (ROOT / path).read_text()


def block(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def test_review_saved_settings_guard_precedes_nvs_open():
    sounds = source("main/hal/maipai_sounds.cc")
    load = block(sounds, "void load_policy_locked()", "std::string_view sound_data")
    assert load.index("maipai_flash_stack_ok") < load.index("nvs_open")

    settings = source("xiaozhi-esp32/main/settings.cc")
    ctor = block(settings, "Settings::Settings(", "Settings::~Settings()")
    assert "maipai_stack_is_internal()" in ctor
    assert ctor.index("return;") < ctor.index("nvs_open")


def test_review_serial_tools_schedule_and_bound_reply_wait():
    serial = source("main/hal/maipai_serial_tools.cc")
    handler = block(serial, "void handle_line(", "void reader_task(")
    assert "Application::GetInstance().Schedule" in handler
    assert "pdMS_TO_TICKS(30000)" in handler
    assert "server.ParseMessage" not in handler


def test_review_motion_peak_reads_are_shared_and_keep_first_step():
    servo = source("main/stackchan/motion/servo.cpp")
    peak = block(servo, "int Servo::peakTenthDps(", "void Servo::init()")
    assert "_peak_tenth_dps = 0" not in peak
    written = block(servo, "void Servo::note_written(", "void Servo::move(")
    assert "dt >= 500" in written and "_first_step_tenth_dps" in written
    motion = source("main/hal/maipai_motion_limit.cc")
    assert "yaw_first_step_deg" in motion and "yaw_window" in motion


def test_review_reconnect_stops_and_waits_without_deleting_task():
    ws = source("xiaozhi-esp32/main/protocols/websocket_protocol.cc")
    restart = block(ws, "void WebsocketProtocol::RestartReconnectTask()", "void WebsocketProtocol::ReconnectTask(")
    assert "vTaskDelete" not in restart
    assert "WEBSOCKET_PROTOCOL_STOP_EVENT" in restart
    assert "WEBSOCKET_PROTOCOL_STOPPED_EVENT" in restart
    assert "maipai_heal_restart" in restart


def test_review_avatar_endpoint_requires_client_start():
    avatar = source("main/hal/hal_ws_avatar.cpp")
    apply = block(avatar, "void applyAnnouncedEndpoint(", "bool isConnected()")
    assert re.search(r"if\s*\(!_local_client->start\(\)\)", apply)
    assert apply.index("return;") < apply.index("setEndpoint")


def test_review_allocator_scope_restores_at_depth_zero():
    mcp = source("xiaozhi-esp32/main/mcp_server.cc")
    scope = block(mcp, "struct PsramAllocScope", "}  // namespace")
    assert "s_psram_alloc_scope_depth++ == 0" in scope
    assert "--s_psram_alloc_scope_depth == 0" in scope


def test_review_alert_quiet_policy_is_intentional():
    app = source("xiaozhi-esp32/main/application.cc")
    alert = block(app, "void Application::Alert(", "void Application::DismissAlert()")
    assert "status and error alerts" in alert
