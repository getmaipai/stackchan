# ruff: noqa: E501
"""The face as LVGL draws it, run across the 2^31 ms and 2^32 ms clock points (lane P, report 4).

The same script (a mood, speech, sleep, a mood again) runs with the fake clock starting at 1000 ms and at start times that put the
whole run before, across and after 2^31 and 2^32 ms. Pictures are not compared pixel for pixel (blinks and breathing follow the
absolute clock, so their phase differs with the start). What must hold: with the eyes open, the lit pixels of the eye zone and of the
mouth zone stay within 12 percent of the reference run. A pre-SF01 tree draws one eye shut for good once the clock is past 2^31 ms
(the wink stamp of patch MD02 read as pending against its own zero), which halves the eye count: this test catches that.

Needs the built face renderer (`bash scripts/virtual-unit/build-face.sh`), which the repo does not carry: skipped without it."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RENDER = ROOT / ".runs" / "vu-build" / "render"
STARTS = [2**31 - 1200, 2**31 - 9000, 2**31 + 500, 2**32 - 1200, 2**32 - 5000, 2**32 - 300000]
TOLERANCE = 0.12
SAMPLES = 12

pytestmark = pytest.mark.skipif(not RENDER.is_file(), reason="needs the built face renderer (scripts/virtual-unit/build-face.sh)")


def _sample() -> list[str]:
    out: list[str] = []
    for _ in range(SAMPLES):
        out += ["advance 200", "count 0 30 320 150", "count 0 150 320 240"]
    return out


def _run(start_ms: int | None) -> list[tuple[int, int]]:
    commands = ([f"clock {start_ms}"] if start_ms is not None else []) + ["emotion happy"] + _sample() + ["speak 6"] + _sample()
    commands += ["speak 0", "emotion sleepy", "advance 3000"] + _sample() + ["emotion neutral", "advance 2000"] + _sample()
    done = subprocess.run([str(RENDER)], input="\n".join(commands) + "\n", capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    counts = [int(line.split()[1]) for line in done.stdout.splitlines() if line.startswith("count")]
    per = 2 * SAMPLES
    return [(max(counts[i : i + per][0::2]), max(counts[i : i + per][1::2])) for i in range(0, len(counts), per)]


def test_the_face_keeps_both_eyes_and_the_mouth_across_the_wrap_points():
    if "clock" not in (ROOT / "scripts" / "fw-face-render" / "render.cc").read_text():
        pytest.skip("the renderer has no clock command")
    reference = _run(None)
    assert len(reference) == 4
    for start in STARTS:
        for step, (got, want) in enumerate(zip(_run(start), reference, strict=True)):
            for zone, (g, w) in enumerate(zip(got, want, strict=True)):
                assert abs(g - w) <= TOLERANCE * w, f"start {start} ms, step {step}, {'eyes' if zone == 0 else 'mouth'} zone: {g} lit pixels, the reference run has {w}"
