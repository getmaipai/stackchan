"""Leave the test process without the interpreter's native shutdown when worker threads are still running.

The suite starts host threads that outlive their tests (state reporters, alarm backstops, roster pollers: dozens by the end of a run) in a process that has loaded
native libraries (an inference runtime among them). Once in a while the interpreter's shutdown destroyed a native global while one of those threads still used it and the
process aborted after the summary ("libc++abi: recursive_mutex lock failed", exit 134), hiding a green run behind a crash code. After pytest has reported, this plugin
flushes and exits with pytest's own status, so the result is the suite's result. A failing test still exits 1; set MAIPAI_PYTEST_NATIVE_EXIT=1 to use the normal shutdown.
"""

from __future__ import annotations

import os
import sys
import threading

import pytest

_STATUS: dict[str, int] = {}


def pytest_sessionfinish(session, exitstatus):
    _STATUS["code"] = int(exitstatus)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    if os.environ.get("MAIPAI_PYTEST_NATIVE_EXIT") == "1" or "code" not in _STATUS or hasattr(config, "workerinput"):
        return
    if threading.active_count() > 1:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(_STATUS["code"])
