"""T-4, B-3: the key scanner refuses real-looking keys and lets the marked test fakes through."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check-no-keys.py"
spec = importlib.util.spec_from_file_location("check_no_keys", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_a_real_looking_key_is_refused(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"key = tskey-auth-" + b"k9Xq2LmZp4Rt7Vw1" + b"\n")
    assert mod.scan_file(str(f))


def test_the_marked_test_fake_is_allowed(tmp_path):
    f = tmp_path / "b.txt"
    f.write_bytes(b'key = "tskey-auth-FAKETESTKEY0000000000"\n')
    assert mod.scan_file(str(f)) == []


def test_a_real_key_next_to_a_fake_is_still_refused(tmp_path):
    f = tmp_path / "c.txt"
    f.write_bytes(b"tskey-auth-FAKETESTKEY000 tskey-auth-" + b"k9Xq2LmZp4Rt7Vw1\n")
    assert mod.scan_file(str(f))
