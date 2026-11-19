"""The feature ledger gives the same result under every interpreter and with stray untracked files around (it reads git-tracked files only)."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "feature-ledger.py"


def _check(py: str) -> int:
    return subprocess.run([py, "-I", str(SCRIPT), "--check"], cwd=ROOT, capture_output=True, text=True).returncode


def test_same_under_each_interpreter():
    pys = {sys.executable, shutil.which("python3") or sys.executable}
    for py in pys:
        assert _check(py) == 0, f"{py}: the ledger is out of date; run python3 scripts/feature-ledger.py"


def test_untracked_files_do_not_change_it():
    stray = ROOT / "host" / "tests" / "zz_stray_untracked_ledger_probe.py"
    stray.write_text("# patch H03 face overlay mouth eyes picture blink\n")
    try:
        assert _check(sys.executable) == 0
    finally:
        stray.unlink()
