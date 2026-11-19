"""The host update (decision 16e): install beside the old, switch, wait for health, and a bad new version rolls back by itself."""

from __future__ import annotations

from pathlib import Path

from maipai_body.host_update import HostUpdater


class Rig:
    def __init__(self, tmp: Path, *, install_ok=True, stop_ok=True, new_healthy=True, old_starts=True):
        self.calls: list[str] = []
        self.root = tmp / "host-versions"
        self.install_ok, self.stop_ok, self.new_healthy, self.old_starts = install_ok, stop_ok, new_healthy, old_starts
        self.running: Path | None = None
        self.clock_now = 0.0

    def make_env(self, folder: Path, source: str) -> None:
        self.calls.append(f"install {folder.name}")
        if not self.install_ok:
            raise RuntimeError("pip could not reach the source")
        (folder / "bin").mkdir(parents=True)

    def stop(self) -> bool:
        self.calls.append("stop")
        return self.stop_ok

    def activate(self, folder: Path | None) -> bool:
        self.calls.append(f"activate {folder.name if folder else 'original'}")
        self.running = folder
        return True if folder is None else (self.new_healthy or True)

    def healthy(self) -> bool:
        is_new = self.running is not None and self.running.name == "v2"
        return self.new_healthy if is_new else True

    def updater(self) -> HostUpdater:
        def clock() -> float:
            return self.clock_now

        def sleep(seconds: float) -> None:
            self.clock_now += seconds

        return HostUpdater(self.root, make_env=self.make_env, stop=self.stop, activate=self.activate, healthy=self.healthy, clock=clock, sleep=sleep, timeout_s=60, poll_s=2)


def _first_version(rig: Rig) -> None:
    """The state after one good update: current points at v1."""
    first = rig.root / "v1"
    (first / "bin").mkdir(parents=True)
    (rig.root / "current").symlink_to(first)


def test_a_good_update_switches_to_the_new_version_and_keeps_the_old_one(tmp_path):
    rig = Rig(tmp_path)
    _first_version(rig)
    result = rig.updater().update("src")
    assert result.ok and result.version == "v2"
    assert (rig.root / "current").resolve().name == "v2" and (rig.root / "v1").exists()
    assert rig.calls == ["install v2", "stop", "activate v2"]


def test_a_new_version_that_never_gets_healthy_is_rolled_back_to_the_old_one(tmp_path):
    rig = Rig(tmp_path, new_healthy=False)
    _first_version(rig)
    result = rig.updater().update("src")
    assert not result.ok and result.rolled_back and "did not take" in result.message and "old version is running again" in result.message
    assert (rig.root / "current").resolve().name == "v1", "current must point at the old version again"
    assert not (rig.root / "v2").exists(), "the failed version is removed"
    assert rig.calls == ["install v2", "stop", "activate v2", "stop", "activate v1"]
    assert rig.clock_now >= 60, "it waited the whole health window before giving up"


def test_a_failed_first_update_goes_back_to_the_original_install(tmp_path):
    rig = Rig(tmp_path, new_healthy=False)
    rig.healthy = lambda: rig.running is None  # only the original install is healthy
    result = rig.updater().update("src")
    assert not result.ok and result.rolled_back
    assert not (rig.root / "current").exists() and rig.running is None
    assert rig.calls[-1] == "activate original"


def test_an_install_that_fails_touches_nothing_and_never_stops_the_host(tmp_path):
    rig = Rig(tmp_path, install_ok=False)
    _first_version(rig)
    result = rig.updater().update("src")
    assert not result.ok and "Nothing changed" in result.message and "still running the old version" in result.message
    assert "stop" not in rig.calls and (rig.root / "current").resolve().name == "v1"


def test_a_host_that_cannot_be_stopped_starts_no_update(tmp_path):
    rig = Rig(tmp_path, stop_ok=False)
    _first_version(rig)
    result = rig.updater().update("src")
    assert not result.ok and "could not be stopped" in result.message
    assert (rig.root / "current").resolve().name == "v1" and not (rig.root / "v2").exists()


def test_the_outcome_is_kept_for_the_status_page(tmp_path):
    import json

    rig = Rig(tmp_path, new_healthy=False)
    _first_version(rig)
    rig.updater().update("src")
    kept = json.loads((rig.root / "last-update.json").read_text())
    assert kept["ok"] is False and kept["rolled_back"] is True and "did not take" in kept["message"]


def test_the_service_runs_the_updated_version_once_there_is_one(tmp_path, monkeypatch):
    from maipai_body import service_cmd

    monkeypatch.setenv("MAIPAI_BOT_DATA_DIR", str(tmp_path))
    before = service_cmd.program()
    folder = tmp_path / "host-versions" / "v1"
    (folder / "bin").mkdir(parents=True)
    (folder / "bin" / "stackchan").write_text("#!/bin/sh\n")
    (tmp_path / "host-versions" / "current").symlink_to(folder)
    assert service_cmd.program() == [str(tmp_path / "host-versions" / "current" / "bin" / "stackchan"), "run"]
    assert service_cmd.original_program() == before


def test_status_reports_an_update_that_did_not_take(tmp_path, monkeypatch):
    import json

    from maipai_body.service_cmd import Service

    monkeypatch.setenv("MAIPAI_BOT_DATA_DIR", str(tmp_path))
    (tmp_path / "host-versions").mkdir()
    (tmp_path / "host-versions" / "last-update.json").write_text(json.dumps({"ok": False, "message": "The update did not take: test"}))
    said: list[str] = []
    Service(system="linux", home=tmp_path, say=said.append)._say_last_update()
    assert said == ["Last update: The update did not take: test"]


def test_an_activate_that_raises_is_rolled_back_and_recorded(tmp_path):
    import json

    rig = Rig(tmp_path)
    _first_version(rig)
    real = rig.activate

    def activate(folder):
        if folder is not None and folder.name == "v2":
            raise OSError("read-only folder")
        return real(folder)

    rig.activate = activate
    result = rig.updater().update("src")
    assert not result.ok and result.rolled_back
    assert (rig.root / "current").resolve().name == "v1" and not (rig.root / "v2").exists()
    kept = json.loads((rig.root / "last-update.json").read_text())
    assert kept["rolled_back"] is True and kept["ok"] is False


def test_a_health_check_that_raises_is_rolled_back(tmp_path):
    rig = Rig(tmp_path)
    _first_version(rig)

    def healthy():
        if rig.running is not None and rig.running.name == "v2":
            raise OSError("status page unreadable")
        return True

    rig.healthy = healthy
    result = rig.updater().update("src")
    assert not result.ok and result.rolled_back and (rig.root / "current").resolve().name == "v1"


def test_a_second_update_while_one_runs_is_refused_and_touches_nothing(tmp_path):
    rig = Rig(tmp_path)
    _first_version(rig)
    inner: list = []
    real = rig.make_env

    def make_env(folder, source):
        real(folder, source)
        inner.append(rig.updater().update("src"))

    rig.make_env = make_env
    outer = rig.updater().update("src")
    assert outer.ok and outer.version == "v2"
    assert len(inner) == 1 and not inner[0].ok and "already running" in inner[0].message
    assert (rig.root / "current").resolve().name == "v2" and (rig.root / "v2").exists()
    assert rig.calls.count("stop") == 1


def test_the_lock_is_released_after_an_update(tmp_path):
    rig = Rig(tmp_path)
    _first_version(rig)
    assert rig.updater().update("src").ok
    assert rig.updater().update("src").ok


def test_a_pip_timeout_is_recorded_without_the_credentials_in_the_source(tmp_path):
    import json
    import subprocess

    rig = Rig(tmp_path)
    _first_version(rig)

    def make_env(folder, source):
        raise subprocess.TimeoutExpired(["pip", "install", source], 1800)

    rig.make_env = make_env
    result = rig.updater().update("git+https://user:SECRETTOKEN@example.com/x.git")
    kept = (rig.root / "last-update.json").read_text()
    assert "SECRETTOKEN" not in result.message and "SECRETTOKEN" not in kept
    assert "pip did not finish in 30 minutes" in json.loads(kept)["message"]


def test_a_failed_pip_run_is_recorded_without_the_command(tmp_path):
    import subprocess

    rig = Rig(tmp_path)

    def make_env(folder, source):
        raise subprocess.CalledProcessError(1, ["pip", "install", source])

    rig.make_env = make_env
    result = rig.updater().update("git+https://user:SECRETTOKEN@example.com/x.git")
    assert "SECRETTOKEN" not in result.message and "pip" in result.message


def test_redact_removes_user_and_password_from_a_url():
    from maipai_body.host_update import redact

    assert redact("git+https://user:tok@example.com/a") == "git+https://example.com/a"
    assert redact("git+https://tok@example.com/a") == "git+https://example.com/a"
    assert redact("git+https://example.com/a") == "git+https://example.com/a"


def test_a_source_that_starts_with_a_dash_is_refused_before_anything_is_installed(tmp_path, monkeypatch):
    from maipai_body import host_update

    monkeypatch.setenv("MAIPAI_BOT_DATA_DIR", str(tmp_path))
    said: list[str] = []
    assert host_update.run_update("--index-url=http://evil.example", say=said.append) == 1
    assert any("starts with" in line and "-" in line for line in said)
    assert not (tmp_path / "host-versions").exists()


def test_pip_gets_the_source_after_a_double_dash_and_the_source_is_printed(tmp_path, monkeypatch):
    import subprocess
    from types import SimpleNamespace

    from maipai_body import host_update

    seen: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        seen.append([str(c) for c in cmd])
        (tmp_path / "bin").mkdir(exist_ok=True)
        (tmp_path / "bin" / "stackchan").write_text("")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    said: list[str] = []
    host_update.make_env(tmp_path, "git+https://user:SECRETTOKEN@example.com/x.git", say=said.append)
    pip = next(c for c in seen if "install" in c)
    assert pip[-2] == "--" and pip[-1].startswith("git+https://user:SECRETTOKEN@")
    assert said and "SECRETTOKEN" not in " ".join(said) and "example.com/x.git" in " ".join(said)
