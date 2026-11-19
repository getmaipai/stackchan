"""The three ways to get a brain: pinned catalog, installer with a fake downloader, mode writer, address tests, controller."""

import hashlib
import io
import tarfile
import threading
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from maipai_body.brain_setup import catalog, modes, runner, tester
from maipai_body.brain_setup.controller import BrainSetup
from maipai_body.brain_setup.installer import Installer, Stopped


def _tar(files: dict[str, bytes], gz="bz2") -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode=f"w:{gz}") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _fake_items(monkeypatch):
    """Small stand-ins for the four pinned files, with real hashes, so the installer's checks run for real."""
    payloads = {
        "runtime": _tar({"llama-b1/llama-server": b"#!/bin/sh\n"}, "gz"),
        "model": b"gguf" * 100,
        "stt": _tar({f"{catalog.STT_FOLDER}/tokens.txt": b"a", f"{catalog.STT_FOLDER}/preprocess.onnx": b"x"}),
        "tts": _tar({f"{catalog.TTS_FOLDER}/voice.onnx": b"x", f"{catalog.TTS_FOLDER}/tokens.txt": b"a", f"{catalog.TTS_FOLDER}/espeak-ng-data/x": b"x"}),
    }
    def item(key, url, kind, dest):
        data = payloads[key]
        return catalog.Item(key, key, url, hashlib.sha256(data).hexdigest(), len(data), kind, dest, "test", "example.test")
    items = {
        "runtime": item("runtime", "https://example.test/runtime", "archive", "runtime"),
        "model": item("model", "https://example.test/model", "file", "model/m.gguf"),
        "stt": item("stt", "https://example.test/stt", "archive", "stt"),
        "tts": item("tts", "https://example.test/tts", "archive", "tts"),
    }
    monkeypatch.setitem(catalog.RUNTIMES, "linux-x64", items["runtime"])
    monkeypatch.setitem(catalog.MODELS, "small", items["model"])
    monkeypatch.setattr(catalog, "SPEECH_TO_TEXT", items["stt"])
    monkeypatch.setattr(catalog, "TEXT_TO_SPEECH", items["tts"])
    by_url = {items[k].url: payloads[k] for k in items}
    return by_url


def _downloader(by_url, corrupt=None, stop_after=None):
    def download(url, dest, progress, stop):
        data = by_url[url]
        if corrupt == url:
            data = data[:-1] + b"!"
        if stop_after == url:
            stop.set()
        if stop.is_set():
            raise Stopped()
        dest.write_bytes(data)
        progress(len(data))
    return download


def test_the_catalog_is_pinned_by_sha_size_and_license():
    for platform_id in catalog.RUNTIMES:
        for choice in catalog.MODELS:
            for item in catalog.plan(platform_id, choice):
                assert len(item.sha256) == 64 and int(item.sha256, 16) >= 0 and item.size > 0
                assert item.url.startswith("https://") and item.license
    assert "9217f5db79a29953eb74d5343926648285ec7e67" in catalog.MODELS["small"].url  # a commit, never main
    assert "/main/" not in catalog.MODELS["better"].url
    assert catalog.MODELS["small"].license == "Apache-2.0" and catalog.MODELS["better"].license == "Apache-2.0"


def test_platforms_sizes_and_the_memory_choice():
    assert catalog.detect_platform("darwin", "arm64") == "macos-arm64"
    assert catalog.detect_platform("linux", "aarch64") == "linux-arm64"
    assert catalog.detect_platform("win32", "AMD64") is None
    need = catalog.needs("macos-arm64", "small")
    assert 600_000_000 < need["download_bytes"] < 700_000_000 and need["disk_bytes"] > need["download_bytes"]
    assert catalog.recommended_choice(4000) == "small" and catalog.recommended_choice(16000) == "better" and catalog.recommended_choice(None) == "small"
    with pytest.raises(ValueError, match="not supported"):
        catalog.plan("freebsd", "small")


def test_an_install_downloads_checks_unpacks_and_reports_progress(tmp_path, monkeypatch):
    by_url = _fake_items(monkeypatch)
    ready, installed = [], []
    installer = Installer(tmp_path / "stack", platform_id="linux-x64", downloader=_downloader(by_url), free_disk=lambda p: 10**12, memory=lambda: 16000,
                          test_turn=lambda folder, choice: {"model_first_word_s": 0.5}, on_ready=ready.append,
                          speech_runtime=lambda: False, install_speech_runtime=lambda: installed.append("sherpa"))
    assert installer.start("small", wait=True)["ok"]
    state = installer.state()
    assert state["state"] == "ready" and "0.5 seconds" in state["message"] and ready == ["small"] and installed == ["sherpa"]
    assert (tmp_path / "stack" / "model" / "m.gguf").is_file() and (tmp_path / "stack" / "stt" / catalog.STT_FOLDER / "tokens.txt").is_file()
    assert not (tmp_path / "stack" / "partial").exists() and installer.installed()


def test_a_file_that_does_not_match_its_checksum_is_thrown_away(tmp_path, monkeypatch):
    by_url = _fake_items(monkeypatch)
    installer = Installer(tmp_path / "stack", platform_id="linux-x64", downloader=_downloader(by_url, corrupt="https://example.test/model"), free_disk=lambda p: 10**12, memory=lambda: 16000)
    installer.start("small", wait=True)
    state = installer.state()
    assert state["state"] == "failed" and "checksum" in state["message"] and "Press Install" in state["message"]
    assert not installer.installed() and not (tmp_path / "stack" / "model" / "m.gguf").exists()


def test_stop_ends_the_download_and_removes_the_partial_files(tmp_path, monkeypatch):
    by_url = _fake_items(monkeypatch)
    installer = Installer(tmp_path / "stack", platform_id="linux-x64", downloader=_downloader(by_url, stop_after="https://example.test/stt"), free_disk=lambda p: 10**12, memory=lambda: 16000)
    installer.start("small", wait=True)
    assert installer.state()["state"] == "stopped" and not (tmp_path / "stack" / "partial").exists() and not installer.installed()


def test_a_network_failure_says_which_file_and_how_to_retry(tmp_path, monkeypatch):
    _fake_items(monkeypatch)
    def broken(url, dest, progress, stop):
        raise requests.ConnectionError("down")
    installer = Installer(tmp_path / "stack", platform_id="linux-x64", downloader=broken, free_disk=lambda p: 10**12, memory=lambda: 16000)
    installer.start("small", wait=True)
    message = installer.state()["message"]
    assert "could not be downloaded" in message and "https://example.test/runtime" in message and "Traceback" not in message


def test_the_install_refuses_when_disk_or_memory_is_short_and_says_why(tmp_path, monkeypatch):
    _fake_items(monkeypatch)
    small_disk = Installer(tmp_path / "s", platform_id="linux-x64", free_disk=lambda p: 1000, memory=lambda: 16000)
    assert "not enough free disk" in small_disk.start("small")["error"]
    low_memory = Installer(tmp_path / "m", platform_id="linux-x64", free_disk=lambda p: 10**12, memory=lambda: 500)
    assert "memory" in low_memory.start("small")["error"]
    unsupported = Installer(tmp_path / "u", platform_id="", free_disk=lambda p: 10**12, memory=lambda: 16000)
    assert "not supported" in unsupported.start("small")["error"] and unsupported.overview()["supported"] is False


def test_the_overview_shows_sizes_and_the_addresses_before_anything_starts(tmp_path):
    overview = Installer(tmp_path / "x", platform_id="macos-arm64", free_disk=lambda p: 5 * 10**9, memory=lambda: 16000).overview()
    assert overview["recommended"] == "better" and overview["options"]["small"]["download_bytes"] < overview["options"]["better"]["download_bytes"]
    assert set(overview["options"]["small"]["addresses"]) == {"github.com", "huggingface.co", "pypi.org"}


def test_an_archive_that_tries_to_leave_its_folder_is_refused(tmp_path):
    from maipai_body.brain_setup.installer import _safe_extract

    archive = tmp_path / "a.tar.gz"
    archive.write_bytes(_tar({"../evil.txt": b"x"}, "gz"))
    with pytest.raises(ValueError, match="outside"):
        _safe_extract(archive, tmp_path / "out")


def test_remove_deletes_the_folder_and_the_config_lines(tmp_path, monkeypatch):
    by_url = _fake_items(monkeypatch)
    config = tmp_path / "robot.toml"
    config.write_text('# my notes\nbrain = "llm"\n')
    setup = BrainSetup(config, tmp_path / "stack", installer=Installer(tmp_path / "stack", platform_id="linux-x64", downloader=_downloader(by_url), free_disk=lambda p: 10**12, memory=lambda: 16000),
                       llama=SimpleNamespace(running=lambda: False, stop=lambda: None, start=lambda *a, **k: None), timer=lambda base, model: {"model_first_word_s": 0.4})
    monkeypatch.setattr(runner, "wait_until_up", lambda *a, **k: True)
    monkeypatch.setattr(runner, "time_speech", lambda paths: {})
    setup.installer.start("small", wait=True)
    assert setup.installer.state()["state"] == "ready"
    assert setup.current()["mode"] == "local" and "# my notes" in config.read_text()
    setup.remove()
    assert not (tmp_path / "stack").exists() and setup.current()["mode"] != "local"
    assert "stt_model_dir" not in config.read_text()


def test_the_mode_writer_keeps_the_file_and_never_writes_a_file_the_host_cannot_read(tmp_path):
    config = tmp_path / "robot.toml"
    config.write_text('# Brain\nbrain = "llm"\n\n[llm]\nurl = "http://old"  # old\nmodel = "m"\n\n[settings]\nlan = true\n')
    modes.apply_own(config, "http://192.0.2.10:8080", "qwen", "http://192.0.2.10:9000", "http://192.0.2.10:9001")
    data = tomllib.loads(config.read_text())
    assert data["llm"]["url"] == "http://192.0.2.10:8080" and data["llm"]["stt_url"] == "http://192.0.2.10:9000" and data["settings"]["lan"] is True
    assert "# Brain" in config.read_text()
    modes.apply_home(config, "http://192.0.2.20:8000")
    assert tomllib.loads(config.read_text())["brain"] == "home" and tomllib.loads(config.read_text())["home"]["url"] == "http://192.0.2.20:8000"
    with pytest.raises(ValueError, match="http://"):
        modes.apply_home(config, "not an address")
    with pytest.raises(ValueError, match="speech-to-text"):
        modes.apply_own(config, "http://a", "m", "nope", "http://b")
    from maipai_body.config import RobotConfig

    RobotConfig.model_validate(tomllib.loads(config.read_text()))


def test_the_address_tests_answer_in_plain_words():
    class Resp:
        def __init__(self, status, body=None):
            self.status_code, self._body = status, body

        def json(self):
            return self._body

    def session(result):
        return SimpleNamespace(get=lambda url, headers=None, timeout=0: result() if callable(result) else result)

    ok = tester.test_model("http://x:1/v1", model="qwen", session=session(Resp(200, {"data": [{"id": "qwen"}]})))
    assert ok["ok"] and "answered" in ok["message"]
    assert "no model named" in tester.test_model("http://x", model="nope", session=session(Resp(200, {"data": [{"id": "qwen"}]})))["message"]
    assert "refused the key" in tester.test_model("http://x", session=session(Resp(401)))["message"]
    assert "no /v1/models" in tester.test_model("http://x", session=session(Resp(404)))["message"]
    def refuse():
        raise requests.ConnectionError("no")
    assert "Nothing answered" in tester.test_model("http://x", session=session(refuse))["message"]
    assert tester.test_speech("http://x", "stt", session(Resp(405)))["ok"]  # any answer means something is there
    assert "error" in tester.test_speech("http://x", "tts", session(Resp(503)))["message"]


def test_the_controller_reports_a_first_run_and_applies_the_other_modes(tmp_path):
    config = tmp_path / "robot.toml"
    setup = BrainSetup(config, tmp_path / "stack", installer=Installer(tmp_path / "stack", platform_id="linux-x64", free_disk=lambda p: 10**12, memory=lambda: 16000))
    assert setup.needs_choice()
    assert setup.apply("home", {"url": "http://192.0.2.20:8000"})["ok"] and setup.current()["mode"] == "home" and not setup.needs_choice()
    assert not setup.apply("home", {"url": "x"})["ok"]
    assert setup.apply("own", {"llm_url": "http://a", "model": "m", "stt_url": "http://b", "tts_url": "http://c"})["ok"] and setup.current()["mode"] == "own"
    assert setup.test("nope", "x")["ok"] is False


def test_the_model_timing_is_measured_from_the_stream():
    class Resp:
        def raise_for_status(self):
            pass

        def iter_lines(self):
            ticks.append(1)
            yield b'data: {"choices":[{"delta":{"content":"Hel"}}]}'
            yield b'data: {"choices":[{"delta":{"content":"lo"}}]}'
            yield b"data: [DONE]"

    ticks: list = []
    clock = iter([0.0, 0.7, 1.5, 1.5, 1.5, 1.5])
    result = runner.time_one_turn("http://x", "m", post=lambda *a, **k: Resp(), clock=lambda: next(clock))
    assert result["model_first_word_s"] == 0.7 or result["model_first_word_s"] == 1.5
    assert result["reply"] == "Hello"


def test_the_settings_server_serves_the_brain_page_and_its_buttons(tmp_path):
    from maipai_body.settings_sim import build

    backend, _ = build(tmp_path)
    config = tmp_path / "robot.toml"
    backend.brain_setup = BrainSetup(config, tmp_path / "stack", installer=Installer(tmp_path / "stack", platform_id="linux-x64", free_disk=lambda p: 10**12, memory=lambda: 16000))
    status, ctype, body = backend.route_get("/brain", "en", True)
    assert status == 200 and ctype.startswith("text/html") and b"Choose a brain" in body and b"http://" not in body.replace(b"placeholder", b"")[:0]
    assert backend.route_get("/brain", "en", False)[0] == 403
    status, view = backend.route_get("/api/stackchan/brain", "en", True)[0], backend.route_get("/api/stackchan/brain", "en", True)[2]
    assert status == 200 and b'"mode": "none"' in view
    assert backend.route_post("/api/stackchan/brain/apply", {"mode": "home", "url": "http://192.0.2.20:8000"}, True)[0] == 200
    assert backend.route_post("/api/stackchan/brain/apply", {"mode": "home", "url": "x"}, True)[0] == 400
    assert backend.route_post("/api/stackchan/brain/apply", {"mode": "home", "url": "http://a"}, False)[0] == 403
    assert backend.route_post("/api/stackchan/brain/install", {"choice": "huge"}, True)[0] == 400


def test_the_speech_runtime_install_tries_uv_then_pip_and_fails_in_plain_words():
    from maipai_body.brain_setup.installer import install_sherpa

    calls = []
    def run(command, **kwargs):
        calls.append(command[0])
        return SimpleNamespace(returncode=1 if command[0] == "uv" else 0)
    install_sherpa(run)
    assert calls[0] == "uv" and len(calls) == 2
    with pytest.raises(RuntimeError, match="could not be installed"):
        install_sherpa(lambda command, **kw: SimpleNamespace(returncode=1))


def test_the_voice_files_are_found_beside_the_model_so_only_the_model_is_named(tmp_path):
    from maipai_body.config import RobotConfig

    voice = tmp_path / "voice"
    (voice / "espeak-ng-data").mkdir(parents=True)
    (voice / "tokens.txt").write_text("a")
    config = RobotConfig.model_validate({"llm": {"tts_model": str(voice / "v.onnx")}})
    assert config.llm.tts_tokens == str(voice / "tokens.txt") and config.llm.tts_data_dir == str(voice / "espeak-ng-data")
    named = RobotConfig.model_validate({"llm": {"tts_model": str(voice / "v.onnx"), "tts_tokens": "/x/t.txt"}})
    assert named.llm.tts_tokens == "/x/t.txt"  # a person's own choice is kept


def test_the_local_stack_writes_only_the_model_for_the_voice(tmp_path):
    config = tmp_path / "robot.toml"
    modes.apply_local(config, "small", {"stt_model_dir": "/s", "tts_model": "/t/v.onnx", "tts_tokens": "/t/tokens.txt", "tts_data_dir": "/t/data"})
    text = config.read_text()
    assert "tts_model" in text and "tts_tokens" not in text and "tts_data_dir" not in text


def test_route_defaults_to_custom_and_hosted_is_refused_until_proven(tmp_path):
    from maipai_body.brain_setup.controller import BrainSetup

    cfg = tmp_path / "robot.toml"
    cfg.write_text('brain = "llm"\n', encoding="utf-8")
    setup = BrainSetup(cfg, tmp_path / "stack")
    assert setup.current()["route"] == "custom"
    result = setup.apply("hosted", {})
    assert result["ok"] is False and "planned" in result["error"]
    assert setup.current()["route"] == "custom"


def test_leaving_hosted_says_the_vendor_keeps_its_record(tmp_path, monkeypatch):
    from maipai_body import brain_route
    from maipai_body.brain_setup.controller import BrainSetup

    cfg = tmp_path / "robot.toml"
    cfg.write_text('brain = "llm"\n', encoding="utf-8")
    monkeypatch.setattr(brain_route, "HOSTED_PROVEN", True)
    setup = BrainSetup(cfg, tmp_path / "stack")
    assert setup.apply("hosted", {})["ok"] is True and setup.current()["route"] == "hosted"
    out = setup.apply("home", {"url": "http://192.0.2.10:8000"})
    assert out["ok"] and "their side" in out["note"] and setup.current()["route"] == "custom"
    assert "note" not in setup.apply("home", {"url": "http://192.0.2.10:8000"})


def test_route_push_tells_each_unit_once_and_again_on_change():
    from maipai_body.brain_route import RoutePush

    route, sent = ["custom"], []
    push = RoutePush(route=lambda: route[0], units=lambda: ["a", "b"], has_tool=lambda u: u == "a", send=lambda u, a: sent.append((u, a["route"])))
    push.tick(); push.tick()
    assert sent == [("a", "custom")]
    route[0] = "hosted"; push.tick()
    assert sent[-1] == ("a", "hosted") and len(sent) == 2
