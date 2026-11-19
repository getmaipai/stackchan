# ruff: noqa: E501
"""End to end on the virtual unit (scripts/virtual-unit/e2e.py): the real host in a clean venv, the virtual unit as the robot, scripted model and speech servers.
It is the spoken-turn check of the gate without hardware. Needs the screens renderer, `uv`, and the host's dependencies in uv's cache (it installs the repo's host
package into .runs/e2e-venv); it skips with the reason when one is missing. MAIPAI_E2E=0 turns it off."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RENDER = ROOT / ".runs" / "vu-screens" / "render"

pytestmark = [pytest.mark.slow, pytest.mark.skipif(
    os.environ.get("MAIPAI_E2E") == "0" or not RENDER.exists() or shutil.which("uv") is None,
    reason="needs the screens renderer, uv and MAIPAI_E2E not 0 (see docs/dev/e2e-virtual-unit.md)",
)]


def test_every_scenario_passes_against_the_real_host():
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "virtual-unit" / "e2e.py"), "--fresh-venv", "--jobs", os.environ.get("MAIPAI_E2E_JOBS", "4")], capture_output=True, text=True, timeout=1800, cwd=ROOT)
    out = done.stdout + done.stderr
    (ROOT / ".runs").mkdir(exist_ok=True)
    (ROOT / ".runs" / "e2e-virtual-unit.last.log").write_text(out)  # the whole run, so a failure under load can be read in full (the assertion message keeps only the tail)
    if "uv" in out and "failed to" in out.lower() and "install" in out.lower():
        pytest.skip("the clean venv could not be installed here (offline?): " + out[-300:])
    assert done.returncode == 0, out[-3000:]
    assert "e2e: ok" in out
