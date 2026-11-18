#!/usr/bin/env python3
"""Intent: turn the answers of self.bench.camera_probe (one JSON object per line, as the bench collected them) into the one table of docs/dev/camera-quality.md:
achieved frames per second, bytes per frame, capture and encode milliseconds, memory and CPU during the run, and what limits each row (the sensor, the encoder,
the stream timer, the bytes on the air or memory). Usage: camera-sweep-table.py RESULTS.jsonl [--plan]   (--plan prints the calls to make).
Placement: host-side tool; no firmware change. Upstream: none."""
from __future__ import annotations

import json
import sys

SENSOR_FPS = {320: 20.0, 640: 16.0}  # the GC0308 driver modes (docs/dev/camera-quality.md)
PLAN = {"quality": [10, 20, 40, 60], "interval_ms": [350, 200, 100, 66, 50, 0], "seconds": 8, "images": ["plain/bench default 320x240", "cam640 build 640x480"]}


def limit(row: dict) -> str:
    """What holds the rate down, from the numbers of one run."""
    w = row.get("width", 0)
    fps = row.get("frames_per_s", 0.0)
    enc = row.get("encode_ms", {}).get("mean", 0.0)
    cap = row.get("capture_ms", {}).get("mean", 0.0)
    interval = row.get("interval_ms", 0)
    sensor = SENSOR_FPS.get(w, 20.0)
    if row.get("largest_internal_min", 1 << 30) < 16000 or row.get("min_free_internal", 1 << 30) < 24000:
        return "memory (under the gate floor)"
    if interval and fps >= (1000.0 / interval) * 0.9:
        return f"the stream timer ({interval} ms)"
    if fps >= sensor * 0.9:
        return "the sensor"
    if enc >= cap and enc > 0:
        return "the JPEG encoder"
    return "capture (the camera read)"


def table(rows: list[dict]) -> str:
    out = ["| Size | Quality | Timer ms | Frames/s | Bytes/frame | Capture ms | Encode ms | Bytes/s | Free internal | Largest block | PSRAM free | CPU idle % | Limit |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in sorted(rows, key=lambda r: (r.get("width", 0), r.get("quality", 0), -r.get("interval_ms", 0))):
        out.append(
            f"| {r.get('width')}x{r.get('height')} | {r.get('quality')} | {r.get('interval_ms', 0)} | {r.get('frames_per_s', 0):.1f} | {r.get('bytes', {}).get('mean', 0):.0f} | "
            f"{r.get('capture_ms', {}).get('mean', 0):.0f} | {r.get('encode_ms', {}).get('mean', 0):.0f} | {r.get('bytes_per_s', 0):.0f} | {r.get('min_free_internal', 0)} | "
            f"{r.get('largest_internal_min', 0)} | {r.get('min_free_psram', 0)} | {r.get('cpu_idle_percent', 0):.0f} | {limit(r)} |"
        )
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if "--plan" in argv:
        print(json.dumps(PLAN, indent=2))
        return 0
    if not argv:
        print("camera-sweep-table: give the file of probe answers, one JSON object per line (or --plan).", file=sys.stderr)
        return 2
    rows = []
    for line in open(argv[0]):
        line = line.strip()
        if line.startswith("{"):
            row = json.loads(line)
            if row.get("ok"):
                rows.append(row)
    print(table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
