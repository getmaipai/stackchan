"""MAIPAI_BENCH_MIN_LISTEN_S (developer only, unset by default) makes the host wait at least that long for speech after the wake word."""

import subprocess
import sys
from pathlib import Path

HOST = Path(__file__).resolve().parents[1]


def _patience(env_value):
    env = {"PATH": "/usr/bin:/bin"}
    if env_value is not None:
        env["MAIPAI_BENCH_MIN_LISTEN_S"] = env_value
    out = subprocess.run([sys.executable, "-c", "from maipai_body.speech.stt_stream import WAKE_PATIENCE_S as p; print(p)"], capture_output=True, text=True, cwd=HOST, env={**env, "PYTHONPATH": str(HOST)})
    return float(out.stdout.strip())


def test_unset_the_patience_is_the_normal_six_seconds():
    assert _patience(None) == 6.0


def test_a_developer_can_raise_it_but_never_lower_it():
    assert _patience("12") == 12.0
    assert _patience("2") == 6.0
    assert _patience("not a number") == 6.0
    assert _patience("500") == 60.0
