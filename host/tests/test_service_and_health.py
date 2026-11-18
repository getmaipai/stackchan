"""`stackchan service`, the health document, its page and its route, and the rotating log."""

import json
import logging
import plistlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from maipai_body import health, service_cmd
from maipai_body.supervisor import Supervisor, Worker


def _fake_run(log, returncode=0, stdout=""):
    def run(command, **kwargs):
        log.append(command)
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")
    return run


def test_the_launchd_file_runs_the_program_at_login_and_restarts_it():
    text = service_cmd.render_launchd(["/opt/x/stackchan", "run"], Path("/tmp/x.log"), {"A": "b&c"})
    data = plistlib.loads(text.encode())
    assert data["Label"] == "com.maipai.stackchan" and data["ProgramArguments"] == ["/opt/x/stackchan", "run"]
    assert data["RunAtLoad"] is True and data["KeepAlive"] is True and data["ThrottleInterval"] == 10
    assert data["EnvironmentVariables"]["A"] == "b&c" and data["StandardErrorPath"] == "/tmp/x.log"


def test_the_systemd_unit_restarts_after_a_crash_and_starts_at_boot():
    text = service_cmd.render_systemd(["/home/me/.local/bin/stackchan", "run"], {"MAIPAI_LOG_FILE": "/x/log"})
    assert "ExecStart=/home/me/.local/bin/stackchan run" in text and "Restart=on-failure" in text and "RestartSec=5" in text
    assert "WantedBy=default.target" in text and 'Environment="MAIPAI_LOG_FILE=/x/log"' in text and "StartLimitIntervalSec=0" in text


def test_install_status_start_stop_logs_and_uninstall_on_a_mac(tmp_path, monkeypatch):
    monkeypatch.setenv("MAIPAI_BOT_DATA_DIR", str(tmp_path / "data"))
    calls, said = [], []
    service = service_cmd.Service(system="mac", home=tmp_path, run=_fake_run(calls, stdout="state = running"), uid=501, command=["/x/stackchan", "run"], say=said.append)
    assert service.install() == 0 and (tmp_path / "Library/LaunchAgents/com.maipai.stackchan.plist").exists()
    assert ["launchctl", "bootstrap", "gui/501", str(tmp_path / "Library/LaunchAgents/com.maipai.stackchan.plist")] in calls
    assert "starts at login" in said[-1]
    assert service.status() == 0 and "running" in said[-1]
    assert service.start() == 0 and service.stop() == 0
    assert service.logs() == 1 and "No log yet" in said[-1]
    service_cmd.log_path().write_text("line one\nline two\n")
    assert service.logs(1) == 0 and said[-1] == "line two"
    assert service.uninstall() == 0 and not (tmp_path / "Library/LaunchAgents/com.maipai.stackchan.plist").exists()
    assert service.status() == 1 and "not installed" in said[-1]


def test_install_on_linux_enables_the_unit_and_linger_and_says_what_failed(tmp_path, monkeypatch):
    monkeypatch.setenv("MAIPAI_BOT_DATA_DIR", str(tmp_path / "data"))
    calls, said = [], []
    service = service_cmd.Service(system="linux", home=tmp_path, run=_fake_run(calls), command=["/x/stackchan", "run"], say=said.append)
    assert service.install() == 0
    assert ["systemctl", "--user", "enable", "--now", "stackchan.service"] in calls and any(c[:2] == ["loginctl", "enable-linger"] for c in calls)
    broken = service_cmd.Service(system="linux", home=tmp_path / "b", run=_fake_run([], returncode=1), command=["/x/stackchan", "run"], say=said.append)
    assert broken.install() == 1 and "failed" in said[-1]
    assert service_cmd.Service(system="other", home=tmp_path, say=said.append).install() == 1 and "not supported" in said[-1]


def test_a_stopped_service_says_what_to_do(tmp_path):
    said = []
    service = service_cmd.Service(system="linux", home=tmp_path, run=_fake_run([], stdout="inactive"), command=["/x/stackchan", "run"], say=said.append)
    service.file().parent.mkdir(parents=True)
    service.file().write_text("x")
    assert service.status() == 1 and "stackchan service start" in said[-1]


def _doc(failing=False):
    sup = Supervisor()
    sup.add(Worker("settings page", lambda: None, plain="the settings page", advice="Open it again in a minute."), start_now=False)
    sup.add(Worker("privacy", lambda: None, unit="unit-a", plain="the privacy loop"), start_now=False)
    for w in sup._workers.values():
        w.state = "failed" if failing else "ok"
        w.last_error = "port busy"
    return health.build_health(sup, connected=["unit-a"], paired={"unit-a": {"last_seen": 1700000000.0}, "unit-b": {"last_seen": 1700000100.0}}, started=0.0, names={"unit-a": "Kitchen"}, now=7200)


def test_the_health_document_says_what_runs_and_what_does_not_in_plain_words():
    ok = _doc()
    assert ok["state"] == "ok" and ok["summary"] == "Everything is running." and ok["uptime_s"] == 7200
    assert [u["connected"] for u in ok["units"]] == [True, False]
    assert ok["units"][0]["parts"][0]["part"] == "privacy" and "Kitchen: connected" in ok["units"][0]["message"] and "not connected" in ok["units"][1]["message"]
    bad = _doc(failing=True)
    assert bad["state"] == "failed" and "the settings page" in bad["summary"] and bad["advice"]
    text = health.render_text(bad)
    assert "What to do" in text and "Kitchen" in text and "2 hours" in text


def test_the_health_page_escapes_and_names_the_state():
    page = health.render_page(_doc(failing=True)).decode()
    assert "Health" in page and "Something needs you" in page and "<script" not in page


def test_the_settings_routes_serve_the_health_document_to_this_computer_only(tmp_path):
    from maipai_body.settings_sim import build

    backend, _ = build(tmp_path)
    backend.health = lambda: _doc()
    status, ctype, body = backend.route_get("/api/stackchan/health", "en", True)
    assert status == 200 and json.loads(body)["state"] == "ok"
    assert backend.route_get("/health", "en", True)[1].startswith("text/html")
    assert backend.route_get("/health", "en", False)[0] == 403


def test_a_host_that_is_not_running_gives_no_document(monkeypatch):
    monkeypatch.setenv("MAIPAI_STACKCHAN_SETTINGS_PORT", "9")
    assert health.fetch_health(timeout=0.5) is None


def test_the_rotating_log_keeps_at_most_five_files_of_five_megabytes(tmp_path, monkeypatch):
    from maipai_body.logging_setup import configure_logging

    monkeypatch.setenv("MAIPAI_LOG_FILE", str(tmp_path / "logs" / "stackchan.log"))
    root = logging.Logger("probe")
    configure_logging(True, root=root)
    handler = next(h for h in root.handlers if getattr(h, "_maipai_file", False))
    assert handler.maxBytes == 5_000_000 and handler.backupCount == 5
    configure_logging(True, root=root)
    assert len([h for h in root.handlers if getattr(h, "_maipai_file", False)]) == 1
    root.warning("hello")
    assert "hello" in (tmp_path / "logs" / "stackchan.log").read_text()
