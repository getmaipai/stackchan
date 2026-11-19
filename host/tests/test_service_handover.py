"""The "Keep the host running" handover (decision 28): success, and every failure leaves the person with a running host."""

from __future__ import annotations

import json

from maipai_body.service_handover import handover


class Rig:
    def __init__(self, *, gone=True, install_ok=True, healthy_after=0):
        self.calls: list[str] = []
        self.gone, self.install_ok, self.healthy_after = gone, install_ok, healthy_after
        self.now = 0.0
        self.polls = 0

    def run(self) -> dict:
        def wait_gone():
            self.calls.append("wait")
            return self.gone

        def install():
            self.calls.append("install")
            return self.install_ok

        def healthy():
            self.polls += 1
            return self.healthy_after is not None and self.polls > self.healthy_after

        def sleep(seconds):
            self.now += seconds

        return handover(
            wait_gone=wait_gone,
            install=install,
            healthy=healthy,
            uninstall=lambda: self.calls.append("uninstall"),
            start_by_hand=lambda: self.calls.append("by hand"),
            clock=lambda: self.now,
            sleep=sleep,
        )


def test_a_healthy_service_ends_the_handover_with_nothing_started_by_hand():
    rig = Rig(healthy_after=2)
    result = rig.run()
    assert result["ok"] and rig.calls == ["wait", "install"]


def test_a_service_that_never_gets_healthy_is_removed_and_the_host_is_started_by_hand():
    rig = Rig(healthy_after=None)
    result = rig.run()
    assert not result["ok"] and "removed" in result["message"] and rig.calls == ["wait", "install", "uninstall", "by hand"]
    assert rig.now >= 60


def test_an_install_that_fails_starts_the_host_by_hand_and_touches_nothing_else():
    rig = Rig(install_ok=False)
    result = rig.run()
    assert not result["ok"] and rig.calls == ["wait", "install", "by hand"] and "old way" in result["message"]


def test_a_host_that_will_not_stop_changes_nothing():
    rig = Rig(gone=False)
    result = rig.run()
    assert not result["ok"] and rig.calls == ["wait"], "no install, no second copy"


def test_the_button_route_needs_the_host_computer_a_confirm_and_a_service_that_is_not_installed(tmp_path):
    from maipai_body.settings_page import SettingsBackend

    backend = SettingsBackend.__new__(SettingsBackend)
    backend.language = "en"
    started: list[int] = []
    backend.service_state = lambda: {"can_install": True}
    backend.service_handover = lambda: started.append(1) or {"ok": True, "message": "Starting"}
    url = "/api/stackchan/service/keep-running"
    assert backend.route_post(url, {"confirm": True}, False)[0] == 403
    assert backend.route_post(url, {}, True)[0] == 400 and not started
    status, payload = backend.route_post(url, {"confirm": True}, True)
    assert status == 200 and payload["ok"] and started == [1]
    backend.service_state = lambda: {"can_install": False}
    assert backend.route_post(url, {"confirm": True}, True)[0] == 400 and started == [1], "an installed service is not installed twice"


def test_the_status_page_shows_the_button_only_when_it_can_work():
    from maipai_body.health import render_page

    doc = {"state": "ok", "summary": "Everything is running.", "uptime_s": 5, "parts": [], "units": [], "advice": []}
    assert b"Keep the host running" not in render_page(doc)
    shown = render_page({**doc, "service": {"can_install": True}})
    assert b"Keep the host running" in shown and b"administrator rights" in shown
    assert b'http-equiv="refresh"' not in shown, "the page must not refresh over the message"
    assert json.loads('{"a":1}')


def test_a_host_started_by_hand_keeps_its_ports_and_home_when_it_hands_over(monkeypatch):
    from maipai_body import service_cmd

    monkeypatch.setenv("MAIPAI_XIAOZHI_PORT", "18999")
    monkeypatch.setenv("MAIPAI_STACKCHAN_SETTINGS_PORT", "18998")
    monkeypatch.setenv("HOME", "/home/example")
    monkeypatch.setenv("MAIPAI_BOT_DATA_DIR", "/tmp/example-data")
    env = service_cmd.service_env()
    assert env["MAIPAI_XIAOZHI_PORT"] == "18999" and env["MAIPAI_STACKCHAN_SETTINGS_PORT"] == "18998" and env["HOME"] == "/home/example" and env["MAIPAI_BOT_DATA_DIR"] == "/tmp/example-data"
    monkeypatch.delenv("MAIPAI_VISION_PORT", raising=False)
    assert "MAIPAI_VISION_PORT" not in service_cmd.service_env()  # only what the host had is carried over


def test_the_service_label_can_be_overridden_for_a_throwaway_test_label_and_defaults_to_the_real_one():
    import subprocess
    import sys

    code = "import maipai_body.service_cmd as s; print(s.LABEL)"
    plain = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "PYTHONPATH": "."})
    assert plain.stdout.strip() == "com.maipai.stackchan"
    custom = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "PYTHONPATH": ".", "MAIPAI_SERVICE_LABEL": "com.maipai.stackchan.testing"})
    assert custom.stdout.strip() == "com.maipai.stackchan.testing"
