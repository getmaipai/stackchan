"""The link key reference script checks X25519 against RFC 7748 and HKDF against RFC 5869, then prints the fixed fake exchange."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_self_test_passes():
    run = subprocess.run([sys.executable, str(ROOT / "scripts" / "link-key-vector.py"), "--self-test"], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert "self-test ok" in run.stdout


def test_the_c_vectors_are_the_script_output():
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "link-key-vector.py"), "--print"], capture_output=True, text=True).stdout
    values = dict(line.split(" ", 1) for line in out.strip().splitlines())
    text = (ROOT / "host" / "tests" / "firmware" / "linkkey_core_test.c").read_text()
    for key in ("pk_u", "pk_h", "z", "commit", "K", "psk"):
        assert values[key] in text, key
    assert values["sas"].lstrip("0") in text
