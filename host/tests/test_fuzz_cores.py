"""A short run of the sanitizer fuzz of the unit's parsers (scripts/fuzz-cores.sh, docs/dev/fuzzing-and-hostile-peer.md): every *_core.h parser built with the address and
undefined behavior sanitizers and fed seeded noise and mutated seeds. Needs cc, git and uv; MAIPAI_FUZZ=0 turns it off. The long run is `bash scripts/fuzz-cores.sh 300000 N`."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

pytestmark = [pytest.mark.slow, pytest.mark.skipif(os.environ.get("MAIPAI_FUZZ") == "0" or shutil.which("cc") is None or shutil.which("uv") is None or shutil.which("git") is None, reason="needs cc, git, uv and MAIPAI_FUZZ not 0")]


def test_the_unit_parsers_survive_a_short_sanitizer_fuzz():
    done = subprocess.run(["bash", str(ROOT / "scripts" / "fuzz-cores.sh"), "3000", "11"], capture_output=True, text=True, timeout=900, cwd=ROOT)
    out = done.stdout + done.stderr
    assert done.returncode == 0, out[-3000:]
    assert out.count(", ok") >= 13, out[-1500:]
