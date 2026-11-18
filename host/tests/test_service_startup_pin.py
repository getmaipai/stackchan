"""Pins what the StackChan service starts, before the wiring is moved behind the robot seam (docs/plan/seam-refactor.md, step P0).

It runs `_serve_stackchan_channels` for a few seconds with no robot connected and lists the background threads it started. The
list must stay the same through the refactor; a change here is a decision, not an accident."""

import json
import subprocess
import sys
from pathlib import Path

HOST = Path(__file__).resolve().parents[1]

PROBE = r"""
import asyncio, json, os, tempfile, threading, time
d = tempfile.mkdtemp()
os.environ.update({"MAIPAI_BOT_DATA_DIR": d, "HOME": d, "MAIPAI_BODY": "stackchan", "MAIPAI_STACKCHAN_SETTINGS_PORT": "0"})
from maipai_body import app
stop = threading.Event()
threading.Thread(target=lambda: asyncio.run(app._serve_stackchan_channels(stop, "127.0.0.1", 0, "127.0.0.1", 0)), daemon=True).start()
time.sleep(7)
print("THREADS " + json.dumps(sorted(t.name for t in threading.enumerate() if t.name.startswith("stackchan-"))))
stop.set()
"""

EXPECTED = [
    "stackchan-estop-recovery",
    "stackchan-light-poll",
    "stackchan-light-service",
    "stackchan-night",
    "stackchan-power-idle",
    "stackchan-privacy-ticks",
    "stackchan-sound-ticks",
    "stackchan-sounds",
    "stackchan-timer-ticks",
    "stackchan-unit-events",
]


def test_the_service_starts_the_same_background_threads():
    result = subprocess.run([sys.executable, "-c", PROBE], capture_output=True, text=True, cwd=HOST, timeout=90)
    line = next((ln for ln in result.stdout.splitlines() if ln.startswith("THREADS ")), "")
    assert line, result.stdout[-500:] + result.stderr[-500:]
    assert json.loads(line[len("THREADS "):]) == EXPECTED


PROBE_STOP = PROBE.replace(
    'stop.set()\n',
    'stop.set()\ntime.sleep(5)\nprint("LEFT " + json.dumps(sorted(t.name for t in threading.enumerate() if t.name != "MainThread")))\n',
)


def test_no_service_thread_remains_after_stop():
    result = subprocess.run([sys.executable, "-c", PROBE_STOP], capture_output=True, text=True, cwd=HOST, timeout=90)
    line = next((ln for ln in result.stdout.splitlines() if ln.startswith("LEFT ")), "")
    assert line, result.stdout[-500:] + result.stderr[-500:]
    left = [n for n in json.loads(line[len("LEFT "):]) if n != "Thread-1"]
    assert left == [], f"threads still running after stop: {left}"
