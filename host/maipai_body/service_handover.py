# ruff: noqa: E501
"""The "Keep the host running" button (decision 28): the host that is running by hand hands over to the service.

A host that installed the service from inside itself would start a second copy on the same ports. So the button starts a small detached helper and then ends this host; the
helper waits until this host is gone, installs and starts the service, waits for the status page to say it is healthy, and if it is not, puts the host back the old way
(`stackchan run`) and says so. The result is kept in ``service-handover.json`` for the status page. The rule is a pure function with every system step passed in, so the
success and the failure paths are tested with no service manager."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path


def handover(
    *,
    wait_gone: Callable[[], bool],
    install: Callable[[], bool],
    healthy: Callable[[], bool],
    uninstall: Callable[[], object],
    start_by_hand: Callable[[], object],
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    health_wait_s: float = 60.0,
    poll_s: float = 2.0,
) -> dict:
    """Returns {"ok", "message"}. Never leaves the person with no host: a failed handover starts the host by hand again."""
    if not wait_gone():
        return {"ok": False, "message": "The running host did not stop, so nothing was changed. Run `stackchan service install` yourself after stopping it."}
    if not install():
        start_by_hand()
        return {"ok": False, "message": "The service could not be installed, so the host was started the old way. Nothing else changed. Run `stackchan service install` to see why."}
    deadline = clock() + health_wait_s
    while True:
        if healthy():
            return {"ok": True, "message": "The host now runs as a service. It starts at login and restarts itself if it stops."}
        if clock() >= deadline:
            break
        sleep(poll_s)
    uninstall()
    start_by_hand()
    return {"ok": False, "message": f"The service did not report healthy within {int(health_wait_s)} seconds, so it was removed and the host was started the old way. Run `stackchan service logs` to see why."}


def _record(data_dir: Path, result: dict) -> None:
    try:
        (data_dir / "service-handover.json").write_text(json.dumps({**result, "at": time.time()}), encoding="utf-8")
    except OSError:
        pass


def last_result(data_dir: Path) -> dict | None:
    try:
        return json.loads((data_dir / "service-handover.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def run_helper(wait_pid: int) -> int:
    """The detached helper (`stackchan service handover --wait-pid N`)."""
    from maipai_body.health import fetch_health
    from maipai_body.service_cmd import Service, _data_dir

    service = Service(say=lambda _text: None)

    def wait_gone() -> bool:
        for _ in range(60):
            try:
                os.kill(wait_pid, 0)
            except ProcessLookupError:
                return True
            except PermissionError:
                pass
            time.sleep(0.5)
        return False

    def start_by_hand() -> None:
        subprocess.Popen([*service.original_command()], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    result = handover(
        wait_gone=wait_gone,
        install=lambda: service.install() == 0,
        healthy=lambda: bool((fetch_health() or {}).get("state") == "ok"),
        uninstall=service.uninstall,
        start_by_hand=start_by_hand,
    )
    _record(_data_dir(), result)
    return 0 if result["ok"] else 1


def start_handover(stop_self: Callable[[], None] | None = None) -> dict:
    """Called by the host when the person confirmed: start the helper, answer the page, then end this host a moment later."""
    helper = [sys.executable, "-m", "maipai_body.cli", "service", "handover", "--wait-pid", str(os.getpid())]
    subprocess.Popen(helper, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    stop = stop_self or (lambda: os.kill(os.getpid(), signal.SIGTERM))
    threading.Timer(1.5, stop).start()
    return {"ok": True, "message": "Starting the service. This page will stop for about a minute while the host restarts as a service; open it again then."}
