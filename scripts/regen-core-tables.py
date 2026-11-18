#!/usr/bin/env python3
"""Regenerate the tables the host page draws from, as the unit's cores print them after the whole firmware/patches/ORDER:
host/maipai_body/face_table.json (look_shapes_dump table) and host/maipai_body/pages_table.json (pages_core_test --table).
Run from the repo root after a patch changes a core (layout, style table): uv run --project host python scripts/regen-core-tables.py
The tests test_face_preview_parity and test_swipe_pages fail with "out of date" when this was forgotten.
Placement: host-side development tool. Upstream: none."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "host" / "tests"))
from firmware_order_cores import build_cores  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    hal = build_cores(Path(tmp))
    for src, args, target in (("look_shapes_dump.c", ["table"], "face_table.json"), ("pages_core_test.c", ["--table"], "pages_table.json")):
        exe = Path(tmp) / src.replace(".c", "")
        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{hal}", str(ROOT / "host" / "tests" / "firmware" / src), "-o", str(exe), "-lm"], check=True)
        printed = subprocess.run([str(exe), *args], capture_output=True, text=True, check=True).stdout
        out = ROOT / "host" / "maipai_body" / target
        old = out.read_text()
        out.write_text(printed if printed.endswith("\n") or not old.endswith("\n") else printed + "\n")
        print(f"wrote {out.name} ({'changed' if json.loads(old) != json.loads(printed) else 'same'})")
