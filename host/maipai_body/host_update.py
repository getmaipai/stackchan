# ruff: noqa: E501
"""`stackchan service update`: install the new host beside the old, switch, start, and go back by itself if the new one is not healthy (decision 16e).

Each version lives in its own folder with its own virtual environment under ``<data>/host-versions/``. A symlink named ``current`` points at the one the service runs.
The steps that touch the system (make an environment, stop, activate, ask for health) are passed in, so the rollback rule is tested without a service manager.
Nothing is installed silently: the person runs this command, and the result is kept in ``last-update.json`` for the status page."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SOURCE = "git+https://github.com/getmaipai/stackchan#subdirectory=host"
HEALTH_WAIT_S = 60.0
KEEP_VERSIONS = 2  # the running one and the one before it
_CREDENTIALS = re.compile(r"(://)[^/@\s'\"]+@")


def redact(text: str) -> str:
    """Drop `user:password@` from every URL in the text, so a token in a source never reaches a file or the terminal."""
    return _CREDENTIALS.sub(r"\1", text)


def pip_failure_text(error: BaseException) -> str:
    """One plain sentence for a failed install; never the pip command line, which carries the source."""
    if isinstance(error, subprocess.TimeoutExpired):
        return "pip did not finish in 30 minutes"
    if isinstance(error, subprocess.CalledProcessError):
        return f"pip stopped with exit status {error.returncode}"
    return redact(str(error))[:160]


@contextmanager
def _update_lock(root: Path) -> Iterator[bool]:
    """An exclusive lock for the whole update; yields False when another update holds it. The lock goes away with the process, so a crash never leaves it stuck."""
    try:
        import fcntl
    except ImportError:  # Windows: no flock; the update still runs, without the guard
        yield True
        return
    with open(root / ".update.lock", "a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@dataclass
class UpdateResult:
    ok: bool
    message: str
    version: str | None = None
    rolled_back: bool = False


def versions_root(data_dir: Path) -> Path:
    return data_dir / "host-versions"


def current_program(data_dir: Path) -> Path | None:
    """The `stackchan` the service should run once an update has been done, or None while the install is still the original one."""
    link = versions_root(data_dir) / "current"
    exe = link / "bin" / "stackchan"
    return exe if link.is_symlink() and exe.exists() else None


class HostUpdater:
    def __init__(
        self,
        root: Path,
        *,
        make_env: Callable[[Path, str], None],
        stop: Callable[[], bool],
        activate: Callable[[Path | None], bool],
        healthy: Callable[[], bool],
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        timeout_s: float = HEALTH_WAIT_S,
        poll_s: float = 2.0,
    ) -> None:
        self.root = root
        self._make_env, self._stop, self._activate, self._healthy = make_env, stop, activate, healthy
        self._clock, self._sleep, self._timeout, self._poll = clock, sleep, timeout_s, poll_s

    @property
    def link(self) -> Path:
        return self.root / "current"

    def current(self) -> Path | None:
        return Path(os.readlink(self.link)) if self.link.is_symlink() else None

    def _switch(self, target: Path | None) -> None:
        """Point `current` at a version folder (atomic), or remove it so the service runs the original install again."""
        if target is None:
            if self.link.is_symlink():
                self.link.unlink()
            return
        tmp = self.root / ".current.new"
        if tmp.is_symlink() or tmp.exists():
            tmp.unlink()
        tmp.symlink_to(target)
        os.replace(tmp, self.link)

    def _next_dir(self) -> Path:
        numbers = [int(p.name[1:]) for p in self.root.glob("v[0-9]*") if p.name[1:].isdigit()]
        return self.root / f"v{max(numbers, default=0) + 1}"

    def _wait_healthy(self) -> bool:
        deadline = self._clock() + self._timeout
        while True:
            if self._healthy():
                return True
            if self._clock() >= deadline:
                return False
            self._sleep(self._poll)

    def _record(self, result: UpdateResult) -> UpdateResult:
        try:
            (self.root / "last-update.json").write_text(json.dumps({"ok": result.ok, "rolled_back": result.rolled_back, "message": result.message, "version": result.version, "at": time.time()}), encoding="utf-8")
        except OSError:
            pass
        return result

    def _prune(self, keep: set[Path]) -> None:
        folders = sorted((p for p in self.root.glob("v[0-9]*") if p.is_dir()), key=lambda p: int(p.name[1:]))
        for old in folders[:-KEEP_VERSIONS]:
            if old not in keep:
                shutil.rmtree(old, ignore_errors=True)

    def update(self, source: str) -> UpdateResult:
        self.root.mkdir(parents=True, exist_ok=True)
        with _update_lock(self.root) as got:
            if not got:
                return UpdateResult(False, "Another update is already running, so this one did not start. Nothing changed. Wait for it to finish, check `stackchan service status`, then run the update again if you still need to.")
            return self._update_locked(source)

    def _update_locked(self, source: str) -> UpdateResult:
        previous = self.current()
        new = self._next_dir()
        try:
            self._make_env(new, source)
        except Exception as error:  # nothing has been stopped or switched yet
            shutil.rmtree(new, ignore_errors=True)
            return self._record(UpdateResult(False, f"The new version could not be installed ({pip_failure_text(error)}). Nothing changed and the host is still running the old version. Check the network and the source, then run the update again."))
        if not self._stop():
            shutil.rmtree(new, ignore_errors=True)
            return self._record(UpdateResult(False, "The host could not be stopped, so the update did not start. Nothing changed. Run `stackchan service stop`, read why it failed, then run the update again."))
        reason = f"the new version was not healthy within {int(self._timeout)} seconds"
        try:
            self._switch(new)
            if self._activate(new) and self._wait_healthy():
                self._prune({new, *([previous] if previous else [])})
                return self._record(UpdateResult(True, f"Updated. The host now runs {new.name} and reports healthy.", new.name))
        except Exception as error:
            reason = f"the new version could not be started ({redact(str(error))[:120]})"
        # The new version did not come up healthy: go back to the old one and say so.
        back = False
        try:
            self._stop()
            self._switch(previous)
            back = self._activate(previous)
        except Exception:
            back = False
        shutil.rmtree(new, ignore_errors=True)
        tail = "and the old version is running again." if back else "but the old version did not start either: run `stackchan service start` and `stackchan service logs`."
        return self._record(UpdateResult(False, f"The update did not take: {reason}, {tail} Nothing else changed.", None, True))


def check_source(source: str) -> str | None:
    """Why a source cannot be used, or None. A leading `-` would be read by pip as an option."""
    if not source.strip():
        return "The update source is empty. Unset MAIPAI_HOST_UPDATE_SOURCE or give a package address."
    if source.lstrip().startswith("-"):
        return "The update source starts with '-', which pip would read as an option, so nothing was installed. Give a package address such as git+https://host/path, or unset MAIPAI_HOST_UPDATE_SOURCE."
    return None


def make_env(folder: Path, source: str, say: Callable[[str], None] = print) -> None:
    """A fresh virtual environment with the new host installed, checked by importing it."""
    say(f"Installing from {redact(source)}")
    subprocess.run([sys.executable, "-m", "venv", str(folder)], check=True, capture_output=True, timeout=300)
    pip = folder / "bin" / "pip"
    done = subprocess.run([str(pip), "install", "--quiet", "--", source], capture_output=True, text=True, timeout=1800)
    if done.returncode != 0:
        raise RuntimeError(redact((done.stderr or done.stdout).strip().splitlines()[-1]) if (done.stderr or done.stdout).strip() else "pip failed")
    check = subprocess.run([str(folder / "bin" / "python"), "-c", "import maipai_body"], capture_output=True, text=True, timeout=120)
    if check.returncode != 0 or not (folder / "bin" / "stackchan").exists():
        raise RuntimeError("the installed package did not import")


def run_update(source: str | None = None, *, say: Callable[[str], None] = print) -> int:
    """The command: wire the updater to the real service and the real health page."""
    from maipai_body.health import fetch_health
    from maipai_body.service_cmd import Service, _data_dir

    chosen = source or os.environ.get("MAIPAI_HOST_UPDATE_SOURCE") or DEFAULT_SOURCE
    refused = check_source(chosen)
    if refused:
        say(refused)
        return 1
    data = _data_dir()
    service = Service()

    def activate(folder: Path | None) -> bool:
        exe = (folder / "bin" / "stackchan") if folder else None
        service.command = [str(exe), "run"] if exe else service.original_command()
        return service.install() == 0

    updater = HostUpdater(
        versions_root(data),
        make_env=lambda folder, src: make_env(folder, src, say),
        stop=lambda: service.stop() == 0,
        activate=activate,
        healthy=lambda: bool((fetch_health() or {}).get("state") == "ok"),
    )
    say("Installing the new version beside the old one. This can take a few minutes.")
    result = updater.update(chosen)
    say(result.message)
    return 0 if result.ok else 1
