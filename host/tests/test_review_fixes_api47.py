"""Review fix, second set (host update, health, brain modes, firmware download)."""

from __future__ import annotations

import hashlib
import os
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from maipai_body import health, service_cmd
from maipai_body.bodies.stackchan import firmware_update as fw
from maipai_body.bodies.stackchan.firmware_update import FirmwareUpdater
from maipai_body.brain_setup import modes
from maipai_body.host_update import HostUpdater, health_is_from, make_health_check


# -- stop on a service that is not running --------------------------------------------------------------------------------
def _run_for(answers):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        for prefix, (code, out) in answers.items():
            if " ".join(command).startswith(prefix):
                return SimpleNamespace(returncode=code, stdout=out, stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    return run, calls


def test_stop_counts_a_service_that_is_not_loaded_as_stopped_on_a_mac(tmp_path):
    run, calls = _run_for({"launchctl print": (113, "Could not find service"), "launchctl bootout": (1, "No such process")})
    said: list[str] = []
    service = service_cmd.Service(system="mac", home=tmp_path, run=run, uid=501, command=["/x/stackchan", "run"], say=said.append)
    assert service.stop() == 0
    assert not any(c[:2] == ["launchctl", "bootout"] for c in calls), "nothing is loaded, so there is nothing to boot out"


def test_stop_counts_a_unit_that_is_not_active_as_stopped_on_linux(tmp_path):
    run, calls = _run_for({"systemctl --user is-active": (3, "inactive\n"), "systemctl --user stop": (5, "Unit not loaded")})
    service = service_cmd.Service(system="linux", home=tmp_path, run=run, command=["/x/stackchan", "run"], say=lambda _t: None)
    assert service.stop() == 0


def test_stop_still_fails_when_a_loaded_service_will_not_stop(tmp_path):
    run, _ = _run_for({"launchctl print": (0, "state = running"), "launchctl bootout": (5, "Input/output error")})
    said: list[str] = []
    service = service_cmd.Service(system="mac", home=tmp_path, run=run, uid=501, command=["/x/stackchan", "run"], say=said.append)
    assert service.stop() == 1 and "stackchan service status" in said[-1]


# -- rollback that cannot stop the new version ----------------------------------------------------------------------------
class _Rig:
    def __init__(self, tmp: Path, stops: list[bool]):
        self.root = tmp / "host-versions"
        self.stops, self.calls, self.now = list(stops), [], 0.0
        first = self.root / "v1"
        (first / "bin").mkdir(parents=True)
        (self.root / "current").symlink_to(first)

    def updater(self, *, healthy=lambda: False) -> HostUpdater:
        def make_env(folder, source):
            (folder / "bin").mkdir(parents=True)

        def stop():
            self.calls.append("stop")
            return self.stops.pop(0) if self.stops else False

        def sleep(seconds):
            self.now += seconds

        return HostUpdater(self.root, make_env=make_env, stop=stop, activate=lambda f: self.calls.append(f"activate {f.name if f else 'original'}") or True,
                           healthy=healthy, clock=lambda: self.now, sleep=sleep, timeout_s=10, poll_s=2)


def test_a_rollback_whose_stop_fails_is_retried_and_never_starts_the_old_version_beside_it(tmp_path):
    rig = _Rig(tmp_path, [True, False, False, False])
    result = rig.updater().update("src")
    assert not result.ok and result.rolled_back
    assert "activate v1" not in rig.calls, "the old version must not start while the new one still runs"
    assert rig.calls.count("stop") >= 3, "the stop is retried"
    assert "old version is running again" not in result.message and "stackchan service stop" in result.message


def test_a_rollback_whose_second_stop_works_goes_back_to_the_old_version(tmp_path):
    rig = _Rig(tmp_path, [True, False, True])
    result = rig.updater().update("src")
    assert result.rolled_back and rig.calls[-1] == "activate v1" and "old version is running again" in result.message


# -- health says which program answered ------------------------------------------------------------------------------------
def test_the_health_document_names_the_version_the_process_and_the_folder():
    doc = health.build_health(None, connected=[], paired={}, started=0.0)
    assert doc["pid"] == os.getpid() and doc["version"] and doc["program"] == health.program_id(sys.prefix) and sys.prefix not in str(doc)


def test_health_from_another_folder_or_the_old_process_is_not_the_new_version(tmp_path):
    new = tmp_path / "v2"
    new.mkdir()
    good = {"state": "ok", "version": "1.2.3", "pid": 200, "program": health.program_id(new)}
    assert health_is_from(good, new, old_pid=100, version="1.2.3")
    assert not health_is_from({**good, "program": health.program_id(tmp_path / "v1")}, new, old_pid=100, version="1.2.3"), "another folder answered"
    assert not health_is_from({**good, "pid": 100}, new, old_pid=100, version="1.2.3"), "the old process still answers"
    assert not health_is_from({**good, "version": "1.0.0"}, new, old_pid=100, version="1.2.3")
    assert not health_is_from({"state": "ok"}, new, old_pid=100, version="1.2.3"), "an answer without the fields is not proof"
    assert not health_is_from({**good, "state": "failed"}, new, old_pid=100, version="1.2.3")
    assert not health_is_from(None, new, old_pid=None, version=None)


def test_the_updater_waits_for_the_new_folder_to_answer(tmp_path):
    rig = _Rig(tmp_path, [True, True])
    updater = rig.updater()
    docs = iter([{"state": "ok", "version": "1", "pid": 7, "program": health.program_id(tmp_path / "other")}, {"state": "ok", "version": "1", "pid": 8, "program": health.program_id(rig.root / "v2")}])
    check = make_health_check(updater, fetch=lambda: next(docs), old_pid=7, version="1")
    updater._healthy = check
    result = updater.update("src")
    assert result.ok and rig.now == 2, "the first answer came from another folder, so it waited one poll for the second, from v2"


# -- robot.toml with a multi-line string ----------------------------------------------------------------------------------
PASTED = 'note = """\nold settings:\nbrain_route = "stale"\n[llm]\nurl = "http://x"\n"""\nbrain = "home"\n'


def test_a_line_inside_a_multi_line_string_is_never_edited(tmp_path):
    cfg = tmp_path / "robot.toml"
    cfg.write_text(PASTED, encoding="utf-8")
    modes.set_values(cfg, "", {"brain_route": "llm"})
    data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    assert data["brain_route"] == "llm" and "brain_route" in data["note"] and "stale" in data["note"]
    modes.set_values(cfg, "llm", {"url": "http://y"})
    data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    assert data["llm"] == {"url": "http://y"} and "[llm]" in data["note"]


def test_literal_multi_line_strings_and_one_line_triple_quotes_are_handled(tmp_path):
    cfg = tmp_path / "robot.toml"
    cfg.write_text("a = '''\nbrain = \"x\"\n'''\nb = \"\"\"one line\"\"\"\nbrain = \"home\"\n", encoding="utf-8")
    modes.set_values(cfg, "", {"brain": "llm"})
    data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    assert data["brain"] == "llm" and data["a"] == 'brain = "x"\n' and data["b"] == "one line"


def test_a_file_the_editor_cannot_keep_valid_gives_a_plain_message(tmp_path):
    cfg = tmp_path / "robot.toml"
    cfg.write_text('brain = "home"\nbrain = "llm"\n', encoding="utf-8")
    before = cfg.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="robot.toml"):
        modes.set_values(cfg, "", {"x": 1})
    assert cfg.read_text(encoding="utf-8") == before


# -- firmware download ---------------------------------------------------------------------------------------------------
class _Response:
    def __init__(self, chunks, length=None):
        self.chunks, self.headers, self.read = chunks, ({"Content-Length": str(length)} if length is not None else {}), 0

    def iter_content(self, size):
        for chunk in self.chunks:
            self.read += len(chunk)
            yield chunk


def _endless():
    while True:
        yield b"x" * 65536


def test_the_download_stops_at_the_size_home_announced(tmp_path):
    response = _Response(_endless())
    with pytest.raises(ValueError, match="image_too_large"):
        fw.stream_to_file(response, tmp_path / "a.bin", expected=1000)
    assert response.read <= 1000 + 65536 and (tmp_path / "a.bin").stat().st_size <= 1000 + 65536


def test_the_download_has_a_fixed_cap_when_no_size_is_known(tmp_path, monkeypatch):
    monkeypatch.setattr(fw, "MAX_IMAGE_BYTES", 200_000)
    response = _Response(_endless())
    with pytest.raises(ValueError, match="image_too_large"):
        fw.stream_to_file(response, tmp_path / "a.bin", expected=None)
    assert response.read <= 200_000 + 65536


def test_a_declared_length_over_the_cap_is_refused_before_any_byte_is_read(tmp_path):
    response = _Response(_endless(), length=fw.MAX_IMAGE_BYTES + 1)
    with pytest.raises(ValueError, match="image_too_large"):
        fw.stream_to_file(response, tmp_path / "a.bin", expected=None)
    assert response.read == 0


def test_a_good_download_is_written_whole(tmp_path):
    response = _Response([b"abc", b"def"], length=6)
    fw.stream_to_file(response, tmp_path / "a.bin", expected=6)
    assert (tmp_path / "a.bin").read_bytes() == b"abcdef"


def _updater(image: bytes, writer, order):
    answer = {"available": True, "version": "1.1.0", "sha256": hashlib.sha256(image).hexdigest(), "size": len(image)}
    base = {"unit_version": "1.0.0", "target_version": "1.1.0", "link_healthy": True, "in_turn": False, "in_call": False, "timer_active": False,
            "alarm_active": False, "timer_due_in": None, "muted": False, "full_quiet": False, "battery_percent": 80, "charging": False,
            "failed_at": None, "failed_version": None, "running": False, "firmware_auto": "on"}
    updater = FirmwareUpdater(
        ask_home=lambda: answer, download=writer, serve_once=lambda path, signature=None: order.append("serve") or "http://body/x",
        download_signature=lambda: b"sig", verify=lambda data, sig: order.append("verify") or True, call_tool=lambda n, a: None,
        situation=lambda: dict(base), battery=lambda: {"percent": 80, "charging": False}, unit_version=lambda: "1.0.0", now=lambda: 100_000,
        report=lambda u, p: None,
    )
    return updater


def test_an_image_over_the_cap_is_never_hashed_or_read_into_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(fw, "MAX_IMAGE_BYTES", 100)
    image = b"y" * 300
    reads: list[str] = []
    real = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda self: reads.append(self.name) or real(self))
    updater = _updater(image, lambda path: path.write_bytes(image), [])
    updater.tick(100_000)
    assert updater.failure_reason == "image_too_large" and not [r for r in reads if r.startswith("maipai-stackchan-fw-")]


def test_a_good_image_is_read_into_memory_once_before_it_is_served(tmp_path, monkeypatch):
    image = b"z" * 300
    reads: list[str] = []
    real = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda self: reads.append(self.name) or real(self))
    order: list[str] = []
    updater = _updater(image, lambda path: path.write_bytes(image), order)
    updater.tick(100_000)
    assert order == ["verify", "serve"] and len([r for r in reads if r.startswith("maipai-stackchan-fw-")]) == 1


def test_a_key_whose_value_is_a_multi_line_string_is_replaced_whole(tmp_path):
    cfg = tmp_path / "robot.toml"
    cfg.write_text('brain = """\nline\n"""\nother = 1\n', encoding="utf-8")
    modes.set_values(cfg, "", {"brain": "llm"})
    assert tomllib.loads(cfg.read_text(encoding="utf-8")) == {"brain": "llm", "other": 1}
    cfg.write_text('brain = """\nline\n"""\nother = 1\n', encoding="utf-8")
    modes.set_values(cfg, "", {}, remove=("brain",))
    assert tomllib.loads(cfg.read_text(encoding="utf-8")) == {"other": 1}
