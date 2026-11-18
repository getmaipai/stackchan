#!/usr/bin/env python3
"""Face consistency across the five styles and the emotions: white faces, a mouth wide enough to read, no hairline strokes.
Usage: face_consistency.py [--table] [--update-known]   prints violations (exit 1 when one is new or fixed); --table prints every measurement;
--update-known rewrites host/tests/golden/face-known.json with today's violations (do it only after reading them).
Measured on the real LVGL face through the virtual unit. host/tests/golden/face-known.json lists violations that exist today, each with the reason; a fixed one must be removed
from that file (the check says so), and a new one fails. Rules (from the 2026-11-18 review): the strongest color channel of the brightest face pixel is full (240+; emotion tints are allowed, a dim face is not);
a face that is not tired or asleep has no gray fill (pixels 100..220 stay under 12 percent of the lit ones); a mouth, when the style has one,
is at least 30 px wide; no stroke is 2 px or thinner (more than 12 lit pixels whose horizontal and vertical runs are both 2 or less).
Placement: host-side development tool. Upstream: none."""
import importlib.util
import json
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("vunit", HERE / "vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)

STYLES = ["big_eyes", "eyes_only", "stock", "classic", "minimal"]
HAIRLINE_ONLY = ["closing", "sleeping"]  # resting closed eyes: only the stroke rule applies
EMOTIONS = ["neutral", "happy", "sad", "angry", "doubtful", "surprised", "sleepy", "love", "content"]
MOUTH_ZONE = (100, 140, 220, 190)  # x0 y0 x1 y1: the mouth center sits at y 162 in every style
KNOWN_FILE = HERE.parents[1] / "host" / "tests" / "golden" / "face-known.json"
KNOWN: dict[str, str] = json.loads(KNOWN_FILE.read_text()) if KNOWN_FILE.exists() else {}


def pixels(png: bytes):
    w, h = 320, 240
    raw = zlib.decompress(png[png.index(b"IDAT") + 4 : png.rindex(b"IEND") - 8])
    rows = [raw[y * (w * 3 + 1) + 1 : (y + 1) * (w * 3 + 1)] for y in range(h)]
    return [[max(r[x * 3], r[x * 3 + 1], r[x * 3 + 2]) for x in range(w)] for r in rows]  # strongest channel: emotion tints stay full strength in one channel


def measure(g):
    lit = [[v > 128 for v in row] for row in g]
    n_lit = sum(map(sum, lit))
    bright = max(max(r) for r in g)
    gray = sum(1 for row in g for v in row if 100 <= v <= 220)
    thin = 0
    for y in range(240):
        for x in range(320):
            if not lit[y][x]:
                continue
            xl = xr = x
            while xl > 0 and lit[y][xl - 1]: xl -= 1
            while xr < 319 and lit[y][xr + 1]: xr += 1
            yu = yd = y
            while yu > 0 and lit[yu - 1][x]: yu -= 1
            while yd < 239 and lit[yd + 1][x]: yd += 1
            if xr - xl + 1 <= 2 and yd - yu + 1 <= 2:
                thin += 1
    x0, y0, x1, y1 = MOUTH_ZONE
    cols = [x for x in range(x0, x1) if any(lit[y][x] for y in range(y0, y1))]
    mouth_w = (max(cols) - min(cols) + 1) if cols else 0
    return {"bright": bright, "gray_pct": round(100 * gray / max(1, n_lit), 1),  # above 100: the whole face is gray
            "thin_px": thin, "mouth_w": mouth_w, "lit": n_lit}


def main() -> int:
    table = "--table" in sys.argv
    found: dict[str, str] = {}
    with vunit.VirtualUnit() as u:
        for style in STYLES:
            for emo in EMOTIONS + HAIRLINE_ONLY:
                u.raw(f"style {style}")
                u.call("self.face.bench_emotion", {"emotion": emo})
                u.advance(1800)
                m = measure(pixels(u.snapshot()))
                key = f"{style}/{emo}"
                if table:
                    print(key, m)
                if emo in HAIRLINE_ONLY:
                    if m["thin_px"] > 12:
                        found[key + ":hairline"] = f"{m['thin_px']} pixels of a 2 px stroke or thinner"
                    continue
                if emo != "sleepy" and m["bright"] < 240:  # sleepy is dim gray by design (owner default, 2026-11-17)
                    found[key + ":not-white"] = f"brightest pixel {m['bright']}"
                if emo != "sleepy" and m["gray_pct"] > 12:
                    found[key + ":gray"] = f"{m['gray_pct']} percent gray"
                if m["thin_px"] > 12:  # a few stray anti-alias pixels move with the gaze; a stroke is longer
                    found[key + ":hairline"] = f"{m['thin_px']} pixels of a 2 px stroke or thinner"
                if style != "eyes_only" and emo not in ("sleepy", "surprised") and m["mouth_w"] < 30:
                    found[key + ":mouth"] = f"mouth {m['mouth_w']} px wide (under 30)"
    if "--update-known" in sys.argv:
        KNOWN_FILE.write_text(json.dumps(dict(sorted(found.items())), indent=1) + "\n")
        print(f"wrote {KNOWN_FILE} ({len(found)} violations)")
        return 0
    new = {k: v for k, v in found.items() if k not in KNOWN}
    fixed = [k for k in KNOWN if k not in found]
    for k, v in new.items():
        print(f"NEW {k}: {v}")
    for k in fixed:
        print(f"FIXED {k}: remove it from host/tests/golden/face-known.json")
    print(f"{len(found)} violations, {len(new)} new, {len(fixed)} fixed")
    return 1 if new or fixed else 0


if __name__ == "__main__":
    sys.exit(main())
