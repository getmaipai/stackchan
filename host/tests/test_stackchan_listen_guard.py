"""Host tests for patch SF03 (listening guard) and the spoken-turn gate verdict in scripts/fw-voice-bench.py."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_listen_guard_core(tmp_path, tmp_path_factory):
    binary = tmp_path / "listen_guard_core_test"
    build = subprocess.run(
        ["cc", "-std=gnu99", "-Wall", "-Wextra", "-Werror", f"-I{cores_dir(tmp_path_factory)}", str(HERE / "firmware" / "listen_guard_core_test.c"), "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout
    assert "listen guard ok" in run.stdout


def _bench():
    spec = importlib.util.spec_from_file_location("fw_voice_bench", ROOT / "scripts" / "fw-voice-bench.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_passes_on_a_clean_run():
    assert _bench().gate_verdict("rst:0x1 boot\nLAT: 5 tts_start\n", 2, 2) == []


def test_gate_fails_on_a_host_error_and_on_missing_replies():
    bench = _bench()
    failures = bench.gate_verdict("rst:0x1\nFailed to receive server hello\n", 3, 1)
    assert any("1 of 3" in f for f in failures)
    assert any("server hello" in f for f in failures)
    assert any("reset" in f for f in bench.gate_verdict("rst:0x1\nrst:0x1\n", 0, 0))


def test_noise_gate_verdict():
    bench = _bench()
    assert bench.noise_verdict([9, 8, 10]) == []
    assert any("more than half" in f for f in bench.noise_verdict([60, 59, 60]))
    assert any("cap" in f for f in bench.noise_verdict([75]))
    assert bench.noise_verdict([])  # nothing read is a failure, not a pass


def test_aec_verdict():
    bench = _bench()
    good = "\n".join(f"AEC mic=1000 ref=3000 out={80 + i}" for i in range(10))
    assert bench.aec_verdict(good) == []
    weak = "\n".join("AEC mic=1000 ref=3000 out=400" for _ in range(10))
    assert any("only" in f for f in bench.aec_verdict(weak))
    assert any("silent" in f for f in bench.aec_verdict("AEC mic=1000 ref=1 out=900"))
    assert bench.aec_verdict("nothing")


def test_barge_and_soak_verdicts():
    bench = _bench()
    ok = "\n".join(f"barge wake_to_silence_ms={150 + i}" for i in range(19))
    assert bench.barge_verdict(ok, 20) == []
    assert any("only 10 of 20" in f for f in bench.barge_verdict("\n".join("barge wake_to_silence_ms=100" for _ in range(10)), 20))
    slow = "\n".join("barge wake_to_silence_ms=500" for _ in range(20))
    assert any("median" in f for f in bench.barge_verdict(slow, 20))
    assert bench.soak_verdict(0) == [] and bench.soak_verdict(2)
