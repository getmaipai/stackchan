"""The exit guard: a native abort during interpreter shutdown must not turn a green run into exit 134, and a red run must still exit 1."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

HOST = Path(__file__).resolve().parents[1]


def _run(tmp_path, body, env_extra=None):
    test = tmp_path / "test_inner.py"
    test.write_text(textwrap.dedent(body))
    env = {**os.environ, "PYTHONPATH": str(HOST), **(env_extra or {})}
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "tests.exit_guard", "-p", "no:cacheprovider", "--rootdir", str(tmp_path), str(test)], capture_output=True, text=True, env=env, cwd=tmp_path, timeout=120)


ABORT_AT_SHUTDOWN = """
import atexit, os, threading, time

def test_green():
    threading.Thread(target=lambda: time.sleep(60), daemon=True).start()   # a worker that outlives its test
    atexit.register(os.abort)                                               # the native abort at shutdown
"""


def test_a_green_run_with_leftover_threads_exits_zero_despite_an_abort_at_shutdown(tmp_path):
    done = _run(tmp_path, ABORT_AT_SHUTDOWN)
    assert "1 passed" in done.stdout and done.returncode == 0, done.stdout + done.stderr


def test_a_failing_test_still_exits_one(tmp_path):
    done = _run(tmp_path, ABORT_AT_SHUTDOWN.replace("def test_green():", "def test_green():\n    assert False, 'red'\n\ndef helper():"))
    assert "1 failed" in done.stdout and done.returncode == 1, done.stdout + done.stderr


def test_the_normal_shutdown_can_be_asked_for(tmp_path):
    done = _run(tmp_path, ABORT_AT_SHUTDOWN, {"MAIPAI_PYTEST_NATIVE_EXIT": "1"})
    assert done.returncode != 0  # the abort is allowed to show
