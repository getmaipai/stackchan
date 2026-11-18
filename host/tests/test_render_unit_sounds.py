"""The robot's own game sounds rendered from its tone core (scripts/render-unit-sounds.py): the clips exist, they are normalized to the core's peak and the manifest says where they came from. Needs the overlay tree."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / ".runs" / "fixtree" / "firmware" / "main" / "hal" / "maipai_games_sfx_core.h").exists(), reason="overlay tree not built")


def test_the_unit_clips_render_at_the_cores_own_peak(tmp_path):
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "render-unit-sounds.py"), "--out", str(tmp_path), "good", "fanfare", "bad", "thud"], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    m = json.loads((tmp_path / "manifest.json").read_text())["clips"]
    assert [c["clip"] for c in m] == ["good", "fanfare", "bad", "thud"]
    for c in m:
        assert abs(c["peak"] - 22000) <= 2 and 100 <= c["ms"] <= 900, c   # MGS_SFX_PEAK: about the loudness of the notification chimes
    assert next(c for c in m if c["clip"] == "fanfare")["ms"] == 490    # 90 + 90 + 90 + 220 ms of the tone table
