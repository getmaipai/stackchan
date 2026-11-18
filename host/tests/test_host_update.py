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
