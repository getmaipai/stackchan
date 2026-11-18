#!/usr/bin/env python3
"""Touch target sizes on the golden screens: find the button and tile shapes in each frame and report their size in panel pixels.
A target is a connected region of non-black pixels that is big enough (area 700 or more, both sides 24 or more) and mostly filled (a rounded rectangle, not
a letter). The standard: both sides at least 40 pixels on the 320 by 240 panel (about 6.5 mm on the unit's 2 inch screen). Frames that are not touch screens
(faces, covers, the update screen) are skipped.
Usage: touch_targets.py [--json]   exit 0 always; the review (docs/dev/four-users-review.md) is made from its output.
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import importlib.util
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "host" / "tests" / "golden" / "screens"
_spec = importlib.util.spec_from_file_location("contact_sheets", Path(__file__).with_name("contact_sheets.py"))
_cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cs)
SKIP = ("cover-", "first-run-started", "screen-eyes-only", "screen-muted", "screen-listening", "screen-offline", "screen-status-normal", "screen-charging", "screen-low-battery", "screen-wifi-flag")
MIN_SIDE = 40


def components(mask: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    """(x0, y0, x1, y1, area) of each 4-connected region of the mask."""
    h, w = mask.shape
    seen = np.zeros_like(mask)
    out = []
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not seen[y, x]:
                q = deque([(y, x)])
                seen[y, x] = True
                x0 = x1 = x
                y0 = y1 = y
                area = 0
                while q:
                    cy, cx = q.popleft()
                    area += 1
                    x0, x1, y0, y1 = min(x0, cx), max(x1, cx), min(y0, cy), max(y1, cy)
                    for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            q.append((ny, nx))
                out.append((x0, y0, x1, y1, area))
    return out


def targets(path: Path) -> list[dict]:
    img = _cs.read_png(path).astype(int)
    mask = img.max(axis=2) > 24
    found = []
    for x0, y0, x1, y1, area in components(mask):
        w, h = x1 - x0 + 1, y1 - y0 + 1
        if area >= 700 and w >= 24 and h >= 24 and area / (w * h) >= 0.6 and not (w >= 300 and h >= 220):
            found.append({"x": x0, "y": y0, "w": w, "h": h})
    return found


def main() -> int:
    result = {}
    for path in sorted(GOLDEN.glob("*.png")):
        if path.stem.startswith(SKIP) or "-es" in path.stem or "-de" in path.stem or "-fr" in path.stem or "-it" in path.stem or "-pt" in path.stem:
            continue
        result[path.stem] = targets(path)
    if "--json" in sys.argv:
        print(json.dumps(result, indent=1))
        return 0
    small = 0
    for name, items in result.items():
        small_items = [t for t in items if min(t["w"], t["h"]) < MIN_SIDE]
        small += len(small_items)
        sizes = ", ".join(f"{t['w']}x{t['h']}" for t in items[:14]) or "none found"
        print(f"{name}: {len(items)} targets ({sizes}){'  SMALL: ' + ', '.join(f'{t['w']}x{t['h']} at {t['x']},{t['y']}' for t in small_items) if small_items else ''}")
    print(f"{small} targets under {MIN_SIDE} px in {len(result)} frames")
    return 0


if __name__ == "__main__":
    sys.exit(main())
