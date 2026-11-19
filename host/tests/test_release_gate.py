"""The release gate (decision 23): a failed check, scan, exposure step or test stops the release before anything is built; a scan step that did not run stops it too."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _tree(tmp: Path, **stubs: str) -> tuple[Path, list[str]]:
    scripts = tmp / "scripts"
    scripts.mkdir()
    shutil.copy(ROOT / "scripts" / "release.sh", scripts / "release.sh")
    defaults = {"build-clean-host-env.sh": "exit 0", "check.sh": "exit 0", "test-all.sh": "exit 0", "security-scan.py": "print('[PASS] x: ok')", "exposure-test.py": "print('[PASS] y: ok')"}
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


# ---- review fix: the web flasher's pinned key list ------------------------------------------------------------------

def _pinned_tree(tmp: Path, keys: list[str]) -> tuple[Path, list[str]]:
    import json

    out, cmd = _tree(tmp)
    shutil.copy(ROOT / "scripts" / "pinned-key-check.py", tmp / "scripts" / "pinned-key-check.py")
    (tmp / "flasher").mkdir()
    (tmp / "flasher" / "trusted-keys.json").write_text(json.dumps({"keys": keys}))
    (tmp / "host").symlink_to(ROOT / "host", target_is_directory=True)
    return out, cmd


def _ed25519_pair(tmp: Path, name: str) -> tuple[Path, str]:
    from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli

    key = tmp / f"{name}.pem"
    subprocess.run([openssl_cli(), "genpkey", "-algorithm", "Ed25519", "-out", str(key)], check=True, capture_output=True)
    pub = subprocess.run([openssl_cli(), "pkey", "-in", str(key), "-pubout"], check=True, capture_output=True).stdout.decode()
    return key, pub


def test_review_fix_a_real_release_is_refused_while_the_pinned_key_list_is_empty(tmp_path):
    out, cmd = _pinned_tree(tmp_path, [])
    run = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(ROOT / "host")})
    assert run.returncode == 1 and "pinned-key FAILED" in run.stderr and "Nothing was built" in run.stderr
    assert not out.exists() or not any(out.iterdir())


def test_review_fix_the_pinned_key_check_wants_the_signing_key_in_the_list(tmp_path):
    import sys

    key, pub = _ed25519_pair(tmp_path, "real")
    _, other_pub = _ed25519_pair(tmp_path, "other")
    keys = tmp_path / "trusted-keys.json"

    def check(listed: list[str]):
        import json

        keys.write_text(json.dumps({"keys": listed}))
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "pinned-key-check.py"), str(keys), str(key)], capture_output=True, text=True,
                              env={**os.environ, "PYTHONPATH": str(ROOT / "host")})

    assert check([pub]).returncode == 0
    assert check([other_pub, pub]).returncode == 0
    empty = check([])
    assert empty.returncode == 1 and "empty" in empty.stderr
    wrong = check([other_pub])
    assert wrong.returncode == 1 and "not the key" in wrong.stderr
    junk = check(["not a pem"])
    assert junk.returncode == 1 and "damaged" in junk.stderr
