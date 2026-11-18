"""The memory gate fails when the host calls it drives fail (a run that exercised nothing cannot pass)."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "fw-stress.py"
spec = importlib.util.spec_from_file_location("fw_stress", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

LINE = "mem internal_free=60000 internal_min=30000 int_big=30000 psram_free=7000000 psram_min=7000000\n"


def _log(tmp_path):
    path = tmp_path / "unit.log"
    path.write_text(LINE * 20)
    return str(path)


def _run(tmp_path, ok, failed, monkeypatch):
    monkeypatch.setattr(mod, "HOST_LOG", str(tmp_path / "none.log"))
    mod.CALL_STATS.update(ok=ok, failed=failed, first_error="connection refused")
    return mod.report(_log(tmp_path), 0.0, 100.0)


def test_healthy_memory_with_working_calls_passes(tmp_path, monkeypatch, capsys):
    assert _run(tmp_path, 40, 0, monkeypatch) == 0
    assert "GATE PASS" in capsys.readouterr().out


def test_every_call_failing_fails_the_gate_even_with_good_memory(tmp_path, monkeypatch, capsys):
    assert _run(tmp_path, 0, 40, monkeypatch) == 1
    out = capsys.readouterr().out
    assert "GATE FAIL" in out and "host calls" in out and "connection refused" in out


def test_no_calls_at_all_fails(tmp_path, monkeypatch):
    assert _run(tmp_path, 0, 0, monkeypatch) == 1


def test_a_few_failures_are_tolerated_but_many_are_not(tmp_path, monkeypatch):
    assert _run(tmp_path, 95, 5, monkeypatch) == 0
    assert _run(tmp_path, 60, 40, monkeypatch) == 1
