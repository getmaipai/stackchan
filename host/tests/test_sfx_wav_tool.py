"""scripts/sfx-wav.sh renders every game clip of the unit's sound core to a WAV file (owner can audition the real sounds). Uses the newest replayed firmware tree; skips without one."""

from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TREES = sorted((Path.home() / "esp" / "stackchan-rebuild").glob("b[0-9]*"), key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 0)


@pytest.mark.skipif(not TREES or not (TREES[-1] / "firmware/main/hal/maipai_games_sfx_core.h").exists(), reason="no replayed firmware tree on this machine")
def test_every_clip_is_written_as_a_valid_wav(tmp_path):
    out = subprocess.run(["bash", str(ROOT / "scripts" / "sfx-wav.sh"), str(tmp_path), str(TREES[-1])], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    files = sorted(tmp_path.glob("*.wav"))
    assert len(files) >= 23
    for f in files:
        with wave.open(str(f)) as w:
            assert (w.getnchannels(), w.getframerate(), w.getsampwidth()) == (1, 16000, 2)
            assert 0 < w.getnframes() <= 16000 * 0.9 + 1
