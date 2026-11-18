"""Workers under a watchdog: a dead or silent worker is restarted alone, with back-off, and a worker that keeps failing is reported, not hidden.

Each worker is a name, a ``start`` that returns the running thread (or any object with ``is_alive``), an optional heartbeat limit, and the unit it
belongs to (``""`` for the host). The clock and sleeping are injected so tests run in no time. See docs/plan/service-and-supervision.md.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

LOG = logging.getLogger(__name__)

BACKOFF_S = (1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0)
FAIL_AFTER = 5  # restarts inside FAIL_WINDOW_S before the worker is marked failed
FAIL_WINDOW_S = 600.0
STABLE_S = 120.0  # a worker that runs this long starts its back-off over


@dataclass
class Worker:
    name: str
    start: Callable[[], Any]
    unit: str = ""
    heartbeat_limit_s: float | None = None
    plain: str = ""  # what the person sees for this part ("the settings page"), used in messages
    advice: str = "Restart the host with `stackchan service start`. If it keeps failing, run `stackchan service logs`."
    handle: Any = None
    kill: Callable[[], None] | None = None  # makes this worker die on purpose (the chaos hook); None: it cannot be killed that way
    state: str = "off"  # off | ok | restarting | failed
    last_error: str = ""
    since: float = 0.0
    last_start: float = 0.0
    last_beat: float = 0.0
    restarts: list[float] = field(default_factory=list)
    next_try: float = 0.0
    attempt: int = 0
    stopping: bool = False


class Supervisor:
    def __init__(self, *, clock: Callable[[], float] = time.monotonic, wall: Callable[[], float] = time.time) -> None:
        self._clock, self._wall = clock, wall
        self._lock = threading.RLock()
        self._workers: dict[tuple[str, str], Worker] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- registering -------------------------------------------------------------------------------------------------------
    def add(self, worker: Worker, *, start_now: bool = True) -> Worker:
        with self._lock:
            self._workers[(worker.unit, worker.name)] = worker
            worker.since = self._wall()
        if start_now:
            self._start(worker)
        return worker

    def remove(self, name: str, unit: str = "") -> None:
        with self._lock:
            worker = self._workers.pop((unit, name), None)
        if worker is not None:
            worker.stopping = True

    def beat(self, name: str, unit: str = "") -> None:
        """A worker says it is alive."""
        with self._lock:
            worker = self._workers.get((unit, name))
            if worker is not None:
                worker.last_beat = self._clock()

    def kill(self, name: str, unit: str = "") -> bool:
        """Make a worker die on purpose (the chaos hook, chaos.py). True when the worker has a way to be killed and it ran."""
        with self._lock:
            worker = self._workers.get((unit, name))
        if worker is None or worker.kill is None:
            return False
        worker.kill()
        return True

    def restart(self, name: str, unit: str = "") -> bool:
        """A person pressed restart: forget the failure history and start the worker now."""
        with self._lock:
            worker = self._workers.get((unit, name))
            if worker is None:
                return False
            worker.restarts.clear()
            worker.attempt = 0
        self._start(worker)
        return True

    # -- running -----------------------------------------------------------------------------------------------------------
    def _start(self, worker: Worker) -> None:
        now = self._clock()
        try:
            worker.handle = worker.start()
        except Exception as error:
            worker.state, worker.last_error = "restarting", f"{type(error).__name__}: {str(error)[:120]}"
            LOG.warning("worker %s could not start", worker.name, exc_info=True)
            worker.handle = None
        else:
            worker.state, worker.last_error = "ok", ""
            worker.last_start = worker.last_beat = now
        worker.since = self._wall()

    def check(self) -> None:
        """One watchdog pass (called by the thread, and directly by tests)."""
        with self._lock:
            workers = list(self._workers.values())
        now = self._clock()
        for worker in workers:
            if worker.stopping or worker.state == "failed":
                continue
            if worker.state == "ok" and now - worker.last_start >= STABLE_S:
                worker.attempt = 0
            reason = self._problem(worker, now)
            if worker.state == "ok" and reason is None:
                continue
            if worker.state == "restarting" and now < worker.next_try:
                continue
            if worker.state == "ok":  # newly found broken
                worker.last_error = reason or ""
                LOG.warning("worker %s needs a restart: %s", worker.name, reason)
            worker.restarts = [t for t in worker.restarts if now - t < FAIL_WINDOW_S]
            if len(worker.restarts) >= FAIL_AFTER:
                worker.state, worker.since = "failed", self._wall()
                LOG.error("worker %s failed %d times in %d minutes and is not restarted again", worker.name, FAIL_AFTER, int(FAIL_WINDOW_S // 60))
                continue
            worker.restarts.append(now)
            delay = BACKOFF_S[min(worker.attempt, len(BACKOFF_S) - 1)]
            worker.attempt += 1
            worker.state, worker.next_try = "restarting", now + delay
            self._start_after_delay(worker, delay)

    def _start_after_delay(self, worker: Worker, delay: float) -> None:
        # the first restart is immediate; later ones wait their back-off through the next watchdog passes (state "restarting" until next_try)
        if delay <= BACKOFF_S[0]:
            self._start(worker)
            if worker.state == "ok":
                worker.state = "ok"
        else:
            worker.state = "restarting"

    def _problem(self, worker: Worker, now: float) -> str | None:
        handle = worker.handle
        if handle is None:
            return "it is not running"
        alive = getattr(handle, "is_alive", None)
        if callable(alive) and not alive():
            return "it stopped"
        if worker.heartbeat_limit_s is not None and now - worker.last_beat > worker.heartbeat_limit_s:
            return "it was not responding"
        return None

    def _tick_pending(self) -> None:
        now = self._clock()
        with self._lock:
            pending = [w for w in self._workers.values() if w.state == "restarting" and now >= w.next_try and not w.stopping]
        for worker in pending:
            self._start(worker)

    def run(self, interval: float = 1.0) -> None:
        while not self._stop.wait(interval):
            try:
                self._tick_pending()
                self.check()
            except Exception:
                LOG.warning("the watchdog pass failed", exc_info=True)

    def start(self, interval: float = 1.0) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self.run, args=(interval,), name="stackchan-watchdog", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            for worker in self._workers.values():
                worker.stopping = True
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=3)

    # -- reporting ---------------------------------------------------------------------------------------------------------
    def report(self) -> list[dict[str, Any]]:
        with self._lock:
            workers = list(self._workers.values())
        rows = []
        for w in sorted(workers, key=lambda w: (w.unit, w.name)):
            rows.append({
                "part": w.name, "unit": w.unit, "state": w.state, "label": w.plain or w.name, "since": w.since,
                "message": _message(w), "advice": w.advice if w.state in ("failed", "restarting") else "",
            })
        return rows

    def degraded(self) -> list[dict[str, Any]]:
        return [row for row in self.report() if row["state"] in ("failed", "restarting")]


def _message(w: Worker) -> str:
    label = w.plain or w.name
    if w.state == "ok":
        return f"{label}: running."
    if w.state == "restarting":
        return f"{label}: restarting ({w.last_error or 'it stopped'})."
    if w.state == "failed":
        return f"{label}: stopped after repeated failures ({w.last_error or 'it kept stopping'}). It is not being restarted any more."
    return f"{label}: off."
