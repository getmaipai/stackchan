#!/usr/bin/env python3
"""The two pictures of docs/plan/unit-settings-simplification.md (needs ffmpeg and git): the unit's Settings app and quick sheet before the simplification (the goldens of a git ref, default origin/main, where
patch UX30 is not in ORDER yet) and after it (the goldens in this checkout, made with UX30). Usage: settings_look_sheet.py [REF]. Placement: host-side development tool. Upstream: none."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
G = ROOT / "host" / "tests" / "golden" / "screens"
IMAGES = ROOT / "docs" / "images"


def sheet(paths, cols, out):
    inputs = []
    for p in paths:
        inputs += ["-i", str(p)]
    rows = [paths[i:i + cols] for i in range(0, len(paths), cols)]
    parts, labels, k = [], [], 0
    for r, row in enumerate(rows):
        parts.append("".join(f"[{k + j}]" for j in range(len(row))) + f"hstack=inputs={len(row)}[r{r}]")
        labels.append(f"[r{r}]")
        k += len(row)
    parts.append("".join(labels) + f"vstack=inputs={len(rows)}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(parts), str(out)], check=True)


def main() -> int:
    ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    names = ["screen-settings-general", "screen-settings-network", "screen-settings-faces", "screen-settings-info", "screen-control-sheet", "screen-control-sheet-tiles"]
    with tempfile.TemporaryDirectory() as tmp:
        before = []
        for n in names:
            f = Path(tmp) / f"{n}.png"
            f.write_bytes(subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:host/tests/golden/screens/{n}.png"], capture_output=True, check=True).stdout)
            before.append(f)
        sheet(before, 3, IMAGES / "unit-settings-before.png")
    after = [G / f"{n}.png" for n in ("screen-settings-general", "screen-settings-general-more", "screen-settings-network", "screen-settings-faces", "screen-settings-look-switches", "screen-settings-info")]
    sheet(after, 3, IMAGES / "unit-settings-after.png")
    print("wrote docs/images/unit-settings-before.png and unit-settings-after.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
