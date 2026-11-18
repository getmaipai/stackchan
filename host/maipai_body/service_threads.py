"""Background threads of the host service, each started with the stop event it waits on.

Every long-lived service thread is started through `start` so one call, `stop_all`, can end and join all
of them: the service's shutdown path and the test suite's teardown both use it. A thread that outlives
the service keeps running beside loaded native libraries and can abort the interpreter at exit.
A thread started here must leave its loop when its stop event is set, and must not call into a native
library after that.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

_LOCK = threading.Lock()
_STARTED: list[tuple[threading.Thread, threading.Event]] = []
SUPERVISOR: Any = None  # set by the host: every thread started here is then watched and restarted when it dies (supervisor.py)
_CURRENT: dict[str, threading.Thread] = {}


def start(target: Callable[..., Any], *, name: str, stop: threading.Event, args: tuple = ()) -> threading.Thread:
    """Start a daemon thread that ends when `stop` is set, and remember it for `stop_all`."""
    def spawn() -> threading.Thread:
        thread = threading.Thread(target=target, args=args, name=name, daemon=True)
        with _LOCK:
            _STARTED[:] = [(t, e) for t, e in _STARTED if t.is_alive()]
            _STARTED.append((thread, stop))
            _CURRENT[name] = thread
        thread.start()
        return thread

    thread = spawn()
    if SUPERVISOR is not None:
        from maipai_body.supervisor import Worker

        # a restart makes a new thread; the supervisor asks for it only while the thread's stop event is not set
        def die() -> None:  # the chaos hook: the thread ends, and the supervisor starts it again
            stop.set()
            _CURRENT[name].join(3.0)
            stop.clear()

        worker = SUPERVISOR.add(Worker(name, lambda: spawn() if not stop.is_set() else _CURRENT[name]), start_now=False)
        worker.handle, worker.kill = thread, die
    return thread


def running() -> list[str]:
    """Names of the registered threads that are still alive."""
    with _LOCK:
        return [t.name for t, _ in _STARTED if t.is_alive()]


def stop_all(timeout: float = 3.0) -> list[str]:
    """Set every registered stop event and join the threads, waiting `timeout` seconds in all. Returns the names that did not end in time."""
    with _LOCK:
        entries = list(_STARTED)
    for _, event in entries:
        event.set()
    if SUPERVISOR is not None:
        for thread, _ in entries:
            SUPERVISOR.remove(thread.name)  # being stopped on purpose is not a failure
    me = threading.current_thread()
    deadline = time.monotonic() + timeout  # one budget for all joins, so a thread stuck in a network call costs it once
    for thread, _ in entries:
        if thread is not me:
            thread.join(max(0.0, deadline - time.monotonic()))
    with _LOCK:
        _STARTED[:] = [(t, e) for t, e in _STARTED if t.is_alive()]
        return [t.name for t, _ in _STARTED]
