"""Install, stop and remove the minimal local stack. The downloader is injected, so tests never touch the network.

State is one small dict the settings page polls: ``{"state": "idle|downloading|unpacking|testing|ready|failed|stopped", ...}`` with
plain words in ``message``. Every file is checked for size and SHA-256 before it is used; a file that does not match is deleted.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from maipai_body.brain_setup import catalog


class Stopped(Exception):
    """The person pressed Stop."""


class Downloader(Protocol):
    def __call__(self, url: str, dest: Path, progress: Callable[[int], None], stop: threading.Event) -> None: ...


def http_download(url: str, dest: Path, progress: Callable[[int], None], stop: threading.Event) -> None:
    """Stream one address into ``dest`` (the real downloader)."""
    import requests

    with requests.get(url, stream=True, timeout=30, allow_redirects=True) as response:
        response.raise_for_status()
        done = 0
        with dest.open("wb") as handle:
            for chunk in response.iter_content(1 << 20):
                if stop.is_set():
                    raise Stopped()
                handle.write(chunk)
                done += len(chunk)
                progress(done)


def free_disk_bytes(folder: Path) -> int:
    probe = folder
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return shutil.disk_usage(probe).free


def memory_mb() -> int | None:
    """Installed memory in megabytes, or None when it cannot be read."""
    try:
        if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names:
            return int(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1e6)
    except (ValueError, OSError):
        pass
    return None


def sherpa_importable() -> bool:
    try:
        import sherpa_onnx  # noqa: F401
    except Exception:
        return False
    return True


def install_sherpa(run: Callable[..., Any] = subprocess.run) -> None:
    """Install the pinned speech runtime into the host's own Python (uv when it is there, else pip). Raises RuntimeError in plain words."""
    commands = [["uv", "pip", "install", "--python", sys.executable, catalog.SHERPA_PACKAGE], [sys.executable, "-m", "pip", "install", catalog.SHERPA_PACKAGE]]
    for command in commands:
        try:
            result = run(command, capture_output=True, text=True, timeout=600)
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0:
            return
    raise RuntimeError(f"The speech runtime ({catalog.SHERPA_PACKAGE}) could not be installed from {catalog.SHERPA_SOURCE}. Check your connection, then press Install again.")


def _safe_extract(archive: Path, target: Path) -> None:
    root = target.resolve()
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if not (target / member.name).resolve().is_relative_to(root) or member.issym() and Path(member.linkname).is_absolute():
                raise ValueError("The download holds a file outside its folder, so it was not unpacked.")
        tar.extractall(target, filter="data")


class Installer:
    def __init__(
        self,
        folder: Path,
        *,
        platform_id: str | None = None,
        downloader: Downloader = http_download,
        free_disk: Callable[[Path], int] = free_disk_bytes,
        memory: Callable[[], int | None] = memory_mb,
        test_turn: Callable[[Path, str], dict[str, Any]] | None = None,
        speech_runtime: Callable[[], bool] = sherpa_importable,
        install_speech_runtime: Callable[[], None] = install_sherpa,
        on_ready: Callable[[str], None] | None = None,
    ) -> None:
        self.folder = Path(folder)
        self.platform_id = catalog.detect_platform() if platform_id is None else platform_id
        self._download, self._free_disk, self._memory = downloader, free_disk, memory
        self._test_turn, self._on_ready = test_turn, on_ready
        self._speech_runtime, self._install_speech_runtime = speech_runtime, install_speech_runtime
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._state: dict[str, Any] = {"state": "ready" if self.installed() else "idle", "message": ""}

    # -- what the page shows before anything starts ------------------------------------------------------------------
    def installed(self) -> bool:
        return (self.folder / "installed.json").is_file()

    def overview(self) -> dict[str, Any]:
        """Sizes, the addresses that will be contacted and whether this computer can do it."""
        memory = self._memory()
        choice = catalog.recommended_choice(memory)
        if self.platform_id is None or self.platform_id not in catalog.RUNTIMES:
            return {"supported": False, "message": "This computer type is not supported by the local stack yet. Use your own stack or MaiPai Home."}
        options = {}
        for name in catalog.MODELS:
            need = catalog.needs(self.platform_id, name)
            items = catalog.plan(self.platform_id, name)
            options[name] = {**need, "label": catalog.MODELS[name].label, "addresses": sorted({i.source for i in items} | {catalog.SHERPA_SOURCE}), "files": [i.label for i in items]}
        return {
            "supported": True,
            "platform": self.platform_id,
            "recommended": choice,
            "memory_mb": memory,
            "free_disk_bytes": self._free_disk(self.folder),
            "folder": str(self.folder),
            "options": options,
            "installed": self.installed(),
        }

    def state(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def _set(self, **fields: Any) -> None:
        with self._lock:
            self._state = fields

    # -- install -----------------------------------------------------------------------------------------------------
    def start(self, choice: str, *, wait: bool = False) -> dict[str, Any]:
        """Begin the install in the background. Refuses, in plain words, when it cannot run."""
        if self._thread is not None and self._thread.is_alive():
            return {"ok": False, "error": "An install is already running. Wait for it, or press Stop."}
        try:
            items = catalog.plan(self.platform_id or "", choice)
            need = catalog.needs(self.platform_id or "", choice)
        except ValueError as error:
            return {"ok": False, "error": str(error)}
        free = self._free_disk(self.folder)
        if free < need["disk_bytes"]:
            return {"ok": False, "error": f"There is not enough free disk space in {self.folder}. It needs about {need['disk_bytes'] // 10**6} MB and {free // 10**6} MB is free. Free some space, or pick the small model."}
        memory = self._memory()
        if memory is not None and memory < need["memory_mb"]:
            return {"ok": False, "error": f"This computer has {memory} MB of memory and the stack needs about {need['memory_mb']} MB. Pick the small model, or use your own stack or MaiPai Home."}
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, args=(choice, items), name="local-stack-install", daemon=True)
        self._thread.start()
        if wait:
            self._thread.join()
        return {"ok": True}

    def _run(self, choice: str, items: list[catalog.Item]) -> None:
        part_dir = self.folder / "partial"
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            part_dir.mkdir(exist_ok=True)
            total = sum(i.size for i in items)
            before = 0
            for number, item in enumerate(items, 1):
                part = part_dir / f"{item.id}.part"
                self._set(state="downloading", file=item.label, number=number, of=len(items), percent=int(100 * before / total), message=f"Downloading {item.label} ({number} of {len(items)}) from {item.source}.")

                def progress(done: int, _n=number, _item=item, _before=before) -> None:
                    self._set(state="downloading", file=_item.label, number=_n, of=len(items), percent=int(100 * (_before + done) / total), message=f"Downloading {_item.label} ({_n} of {len(items)}) from {_item.source}.")

                try:
                    self._download(item.url, part, progress, self._stop)
                except Stopped:
                    raise
                except Exception as error:
                    raise RuntimeError(f"{item.label} could not be downloaded from {item.url}: {type(error).__name__}. Check your connection, then press Install again.") from error
                self._verify(part, item)
                before += item.size
                self._place(part, item)
            if not self._speech_runtime():
                self._set(state="downloading", percent=99, file="Speech runtime", message=f"Installing the speech runtime ({catalog.SHERPA_PACKAGE}) from {catalog.SHERPA_SOURCE}.")
                self._install_speech_runtime()
            self._set(state="testing", percent=100, message="Everything is in place. Running a test turn.")
            result = self._test_turn(self.folder, choice) if self._test_turn else {}
            (self.folder / "installed.json").write_text(_json({"choice": choice, "platform": self.platform_id, "installed_at": time.time(), "test": result}))
            shutil.rmtree(part_dir, ignore_errors=True)
            self._set(state="ready", percent=100, message=_ready_message(result), test=result)
            if self._on_ready:
                self._on_ready(choice)
        except Stopped:
            shutil.rmtree(part_dir, ignore_errors=True)
            self._set(state="stopped", message="Stopped. The partly downloaded files were removed.")
        except Exception as error:  # reported in plain words, never a trace
            shutil.rmtree(part_dir, ignore_errors=True)
            self._set(state="failed", message=str(error) if isinstance(error, (RuntimeError, ValueError)) else f"The install stopped: {type(error).__name__}. Press Install to try again.")

    def _verify(self, path: Path, item: catalog.Item) -> None:
        size = path.stat().st_size if path.exists() else -1
        digest = hashlib.sha256()
        if size >= 0:
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(block)
        if size != item.size or digest.hexdigest() != item.sha256:
            path.unlink(missing_ok=True)
            raise RuntimeError(f"{item.label} did not match its pinned checksum, so it was thrown away and nothing was installed. Press Install to try again; if it happens again, tell us which file it was.")

    def _place(self, part: Path, item: catalog.Item) -> None:
        self._set(state="unpacking", message=f"Unpacking {item.label}.", file=item.label)
        target = self.folder / item.dest
        if item.kind == "file":
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(part, target)
            return
        target.mkdir(parents=True, exist_ok=True)
        _safe_extract(part, target)
        part.unlink(missing_ok=True)

    # -- stop and remove ---------------------------------------------------------------------------------------------
    def stop(self) -> None:
        self._stop.set()

    def remove(self) -> dict[str, Any]:
        """Stop an install and delete the whole stack folder. The caller removes the config lines."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
        if self.folder.exists():
            shutil.rmtree(self.folder, ignore_errors=True)
        self._set(state="idle", message="The local stack was removed.")
        return {"ok": True}

    # -- where things are, for the config and the runner ---------------------------------------------------------------
    def paths(self, choice: str) -> dict[str, str]:
        model = catalog.MODELS[choice].dest
        stt = self.folder / catalog.SPEECH_TO_TEXT.dest / catalog.STT_FOLDER
        tts = self.folder / catalog.TEXT_TO_SPEECH.dest / catalog.TTS_FOLDER
        return {
            "model": str(self.folder / model),
            "stt_model_dir": str(stt),
            "tts_model": str(next(iter(sorted(tts.glob("*.onnx"))), tts / "voice.onnx")),
            "tts_tokens": str(tts / "tokens.txt"),
            "tts_data_dir": str(tts / "espeak-ng-data"),
            "server": str(next(iter(sorted((self.folder / "runtime").rglob("llama-server"))), self.folder / "runtime" / "llama-server")),
        }


def _json(value: Any) -> str:
    import json

    return json.dumps(value)


def _ready_message(result: dict[str, Any]) -> str:
    if not result:
        return "Installed."
    first = result.get("model_first_word_s")
    if first is None:
        return "Installed."
    parts = [f"The model starts its answer about {first:.1f} seconds after it is asked (measured on this computer)."]
    if "stt_s" in result:
        parts.append(f"Speech to text took {result['stt_s']:.2f} seconds for a {result.get('stt_clip_s', 3)} second clip; the first spoken sentence took {result['tts_first_sentence_s']:.2f} seconds.")
        total = first + result["stt_s"] + result["tts_first_sentence_s"]
        parts.append(f"In all, a spoken answer starts about {total:.1f} seconds after you stop talking.")
        if total > 6:
            parts.append("That is slow for talking. Pick the small model, or use your own stack or MaiPai Home.")
    else:
        parts.append("The speech stages are timed on the first real turn.")
    return "Installed. " + " ".join(parts)
