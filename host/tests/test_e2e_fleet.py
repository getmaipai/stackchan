# ruff: noqa: E501
"""Many robots on one host and faults that heal on their own (owner decision 16): scripts/virtual-unit/e2e_fleet.py through e2e.py --fleet. N virtual units with their own names, pairings and canned
voices ask at once (2, 10, 25 connected); a slow unit does not hold the others; a timer lives on one unit only; a connection is cut mid-turn; the host is killed (SIGKILL) mid-turn with 2 and 10 units
and restarted by a keep-alive; the speech, model and voice servers go down in turn; a relay delays, swallows and cuts packets; and, on a Mac, the host runs as a launchd service under a temporary label
and survives kill -9. Needs the screens renderer, uv, and MAIPAI_E2E not 0. Known gaps print GAP and are listed in docs/dev/e2e-virtual-unit.md."""

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


def test_the_fleet_and_chaos_scenarios_pass_against_the_real_host():
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "virtual-unit" / "e2e.py"), "--fresh-venv", "--fleet", "--jobs", os.environ.get("MAIPAI_E2E_FLEET_JOBS", "2")], capture_output=True, text=True, timeout=2400, cwd=ROOT)
    out = done.stdout + done.stderr
    (ROOT / ".runs").mkdir(exist_ok=True)
    (ROOT / ".runs" / "e2e-fleet.last.log").write_text(out)  # the whole run, so a failure under load can be read in full (the assertion message keeps only the tail)
    if "uv" in out and "failed to" in out.lower() and "install" in out.lower():
        pytest.skip("the clean venv could not be installed here (offline?): " + out[-300:])
    assert done.returncode == 0, out[-3000:]
    assert "e2e: ok" in out
    for name in ("fleet_2", "fleet_10", "fleet_25", "fleet_slow_unit", "fleet_unit_state", "chaos_cut_connection", "chaos_host_kill_2", "chaos_host_kill_10", "chaos_worker_down", "chaos_packets"):
        assert f"scenario {name}" in out, name
    assert "service_kill9" in out
