"""The chaos hook: kill a named host worker on a timer, ONLY when the MAIPAI_CHAOS environment variable is set (tests and the e2e rig).

``MAIPAI_CHAOS="kill=settings page@5,kill=installed-set-retry@12"`` kills the worker named, that many seconds after the host starts. The
supervisor must then bring it back with nobody acting. Nothing in a release path sets the variable; when it is set the host logs one
warning line saying so. A name that has no kill hook is logged and skipped. See docs/plan/service-and-supervision.md."""

from __future__ import annotations

import logging
import os
import threading
from typing import Any

LOG = logging.getLogger(__name__)


def parse(spec: str) -> list[tuple[str, float]]:
    """[(worker name, seconds)] from ``kill=NAME@SECONDS,kill=NAME@SECONDS``; a malformed item is skipped."""
    out: list[tuple[str, float]] = []
    for item in spec.split(","):
        item = item.strip()
        if not item.startswith("kill=") or "@" not in item:
            continue
        name, _, seconds = item[5:].rpartition("@")
        try:
            out.append((name.strip(), max(0.0, float(seconds))))
        except ValueError:
            continue
    return out


def start_from_environment(supervisor: Any, environ: dict[str, str] | None = None) -> list[threading.Timer]:
    spec = (environ if environ is not None else os.environ).get("MAIPAI_CHAOS", "")
    if not spec:
        return []
    plan = parse(spec)
    LOG.warning("MAIPAI_CHAOS is set: %d worker kill(s) are scheduled. This is for tests only.", len(plan))
    timers = []
    for name, seconds in plan:
        def fire(n: str = name) -> None:
            ok = supervisor.kill(n)
            LOG.warning("chaos: worker %r %s", n, "killed" if ok else "has no kill hook or is not running; skipped")

        timer = threading.Timer(seconds, fire)
        timer.daemon = True
        timer.start()
        timers.append(timer)
    return timers
