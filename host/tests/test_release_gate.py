"""The release gate (decision 23): a failed check, scan, exposure step or test stops the release before anything is built; a scan step that did not run stops it too."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _tree(tmp: Path, **stubs: str) -> tuple[Path, list[str]]:
    scripts = tmp / "scripts"
    scripts.mkdir()
    shutil.copy(ROOT / "scripts" / "release.sh", scripts / "release.sh")
    defaults = {"check.sh": "exit 0", "test-all.sh": "exit 0", "security-scan.py": "print('[PASS] x: ok')", "exposure-test.py": "print('[PASS] y: ok')"}
    defaults.update(stubs)
    for name, body in defaults.items():
        text = f"#!/usr/bin/env bash\n{body}\n" if name.endswith(".sh") else f"{body}\n"
        (scripts / name).write_text(text)
    build = tmp / "build"
    build.mkdir()
    (build / "flasher_args.json").write_text("{}")
    key = tmp / "key.pem"
    key.write_text("not a real key")
    out = tmp / "out"
    return out, ["bash", str(scripts / "release.sh"), "--build-dir", str(build), "--version", "1.0.0", "--date", "2026-11-18", "--build-number", "5", "--signing-key", str(key), "--minisign-key", str(key), "--last-build-file", str(tmp / "last"), "--output", str(out)]


def test_a_failing_check_stops_the_release_before_anything_is_built(tmp_path):
    out, cmd = _tree(tmp_path, **{"check.sh": "echo broken; exit 1"})
    run = subprocess.run(cmd, capture_output=True, text=True)
    assert run.returncode == 1 and "check FAILED" in run.stderr and "Nothing was built" in run.stderr
    assert not out.exists() or not any(out.iterdir())


def test_a_failing_test_run_stops_the_release(tmp_path):
    out, cmd = _tree(tmp_path, **{"test-all.sh": "exit 3"})
    run = subprocess.run(cmd, capture_output=True, text=True)
    assert run.returncode == 1 and "tests FAILED" in run.stderr


def test_a_scan_step_that_did_not_run_stops_the_release(tmp_path):
    out, cmd = _tree(tmp_path, **{"security-scan.py": "print('[NOT RUN] Secrets scan: gitleaks is not installed')"})
    run = subprocess.run(cmd, capture_output=True, text=True)
    assert run.returncode == 1 and "did not run or failed" in run.stderr and "NOT RUN" in run.stderr


def test_a_real_release_cannot_skip_the_gate(tmp_path):
    out, cmd = _tree(tmp_path)
    run = subprocess.run(cmd + ["--skip-gate"], capture_output=True, text=True)
    assert run.returncode != 0  # the flag does not exist any more
