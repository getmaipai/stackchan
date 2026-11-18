#!/usr/bin/env python3
"""Count the font sizes and color literals the app screen sources use, on the overlay tree built by build-face.sh.
Usage: ui_style_check.py [tree root, default .runs/fixtree]   prints sizes and literals; exit 1 when the standard (docs/design/screen-style.md) is not met.
Standard: font sizes 16 and 20 only (the Noto Sans basic fonts, which carry the Latin-1 letters) (the clock page's 48 is allowed); color literals only in hal/maipai_ui_style.h.
Placement: host-side development tool. Upstream: none."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
tree = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".runs" / "fixtree"
hal = tree / "firmware" / "main" / "hal"
files = ["maipai_apps.cc", "maipai_pages.cc"]
sizes, colors = set(), {}
for f in files:
    text = (hal / f).read_text()
    sizes |= set(re.findall(r"lv_font_montserrat_(\d+)", text)) | set(re.findall(r"font_noto_sans_basic_(\d+)_", text))
    hdr = (hal / "maipai_ui_style.h").read_text()
    sizes |= set(re.findall(r"font_noto_sans_basic_(\d+)_", hdr))
    for c in re.findall(r"0x[0-9A-Fa-f]{6}\b", text):
        colors[c.upper()] = colors.get(c.upper(), 0) + 1
bad = []
if not sizes <= {"16", "20", "48"}:
    bad.append(f"font sizes {sorted(sizes, key=int)}: only 16 and 20 (and the clock's 48) are in the standard")
if colors:
    bad.append(f"{len(colors)} color literals outside maipai_ui_style.h: {', '.join(sorted(colors))}")
print(f"sizes {sorted(sizes, key=int)}; color literals in screen files: {len(colors)}")
for b in bad:
    print("STANDARD NOT MET:", b)
sys.exit(1 if bad else 0)
