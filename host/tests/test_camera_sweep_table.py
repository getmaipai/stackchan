"""The camera sweep table builder (scripts/camera-sweep-table.py)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("camera_sweep_table", ROOT / "scripts" / "camera-sweep-table.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["camera_sweep_table"] = mod
spec.loader.exec_module(mod)


def row(**kw):
    base = {"ok": True, "width": 320, "height": 240, "quality": 20, "interval_ms": 0, "frames_per_s": 10.0, "bytes": {"mean": 9000}, "capture_ms": {"mean": 30},
            "encode_ms": {"mean": 60}, "bytes_per_s": 90000, "min_free_internal": 50000, "largest_internal_min": 25000, "min_free_psram": 7000000, "cpu_idle_percent": 40}
    base.update(kw)
    return base


def test_the_limit_is_named_from_the_numbers() -> None:
    assert mod.limit(row()) == "the JPEG encoder"
    assert mod.limit(row(frames_per_s=19.0)) == "the sensor"
    assert mod.limit(row(interval_ms=350, frames_per_s=2.8)) == "the stream timer (350 ms)"
    assert mod.limit(row(largest_internal_min=15000)) == "memory (under the gate floor)"
    assert mod.limit(row(width=640, frames_per_s=15.0)) == "the sensor"
    assert mod.limit(row(encode_ms={"mean": 10}, capture_ms={"mean": 90}, frames_per_s=9.0)) == "capture (the camera read)"


def test_the_table_has_one_line_per_run_and_a_header() -> None:
    text = mod.table([row(), row(width=640, height=480, quality=10)])
    lines = text.splitlines()
    assert len(lines) == 4 and lines[0].startswith("| Size |") and "640x480" in lines[3]
