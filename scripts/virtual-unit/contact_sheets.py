#!/usr/bin/env python3
"""One contact sheet PNG per language from the golden screens (docs/dev/screens/sheet-<lang>.png) plus an index with the names in order.
Usage (needs numpy: run with the host environment): uv run --project host python scripts/virtual-unit/contact_sheets.py
English: every golden screen that has no language (each frame at half size, 6 per row). Spanish: the es-* screens and the Spanish first-run steps.
French, German, Portuguese, Italian: the first-run steps only (the unit's app screens have English and Spanish words only; the others are a gap, see the index).
Placement: host-side development tool. Upstream: none."""

import re
import struct
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "host" / "tests" / "golden" / "screens"
OUT = ROOT / "docs" / "dev" / "screens"
LANGS = ["en", "es", "fr", "de", "pt", "it"]
COLS, GAP, SCALE = 6, 4, 2


def read_png(path: Path) -> np.ndarray:
    data = path.read_bytes()
    raw = zlib.decompress(data[data.index(b"IDAT") + 4 : data.rindex(b"IEND") - 8])
    rows = [raw[y * 961 + 1 : (y + 1) * 961] for y in range(240)]
    return np.frombuffer(b"".join(rows), dtype=np.uint8).reshape(240, 320, 3)


def write_png(path: Path, img: np.ndarray) -> None:
    h, w, _ = img.shape
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))
    comp = zlib.compress(raw, 9)

    def chunk(tag: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")
    )


def half(img: np.ndarray) -> np.ndarray:
    return img.reshape(240 // SCALE, SCALE, 320 // SCALE, SCALE, 3).mean(axis=(1, 3)).astype(np.uint8)


def names_for(lang: str) -> list[str]:
    allnames = sorted(p.stem for p in GOLD.glob("*.png"))
    lang_tag = re.compile(r"-(en|es|fr|de|pt|it)$")
    if lang == "en":
        return [n for n in allnames if not n.startswith("es-") and (not lang_tag.search(n) or n.endswith("-en"))]
    if lang == "es":
        return [n for n in allnames if n.startswith("es-") or n.endswith("-es")]
    return [n for n in allnames if n.endswith(f"-{lang}")]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = ["# Screens contact sheets", "", "One PNG per language, built from the golden frames drawn by the unit's own code (`python3 scripts/virtual-unit/scenarios.py`). Frames run left to right, top to bottom, at half size.", ""]
    for lang in LANGS:
        names = names_for(lang)
        if not names:
            continue
        tile_h, tile_w = 240 // SCALE, 320 // SCALE
        rows = (len(names) + COLS - 1) // COLS
        sheet = np.full((rows * (tile_h + GAP) + GAP, COLS * (tile_w + GAP) + GAP, 3), 60, dtype=np.uint8)
        for i, n in enumerate(names):
            r, c = divmod(i, COLS)
            y, x = GAP + r * (tile_h + GAP), GAP + c * (tile_w + GAP)
            sheet[y : y + tile_h, x : x + tile_w] = half(read_png(GOLD / f"{n}.png"))
        write_png(OUT / f"sheet-{lang}.png", sheet)
        index += [f"## {lang}  ([sheet-{lang}.png](screens/sheet-{lang}.png))", "", ", ".join(f"{i + 1} {n}" for i, n in enumerate(names)), ""]
    index += ["## What the sheets show (read 2026-11-18)", "", "- Spanish: every screen fits. The first-run titles and the Spanish words are written without accents and without the opening question and exclamation marks (\"Hola!\", \"Como me llamo?\"): the built-in fonts appear to be ASCII only. This is a real gap for Spanish, French, German and Portuguese; the fix is a font with Latin-1 letters and a firmware memory check.", "- First-run titles drop from 24 to 16 px when the longer title does not fit, so the size changes from step to step; acceptable, listed for the style pass.", "- Portuguese, French, German and Italian first-run steps fit with no clipping.", ""]
    index += ["## Not covered", "", "French, German, Portuguese and Italian have only the first-run steps: the unit's app screens (sheet, Settings, Apps and Games walls, pages) carry English and Spanish words only. Translating them into the other four needs the unit's word tables extended and a font with the accented letters (the built-in 16 and 24 px fonts appear to hold ASCII only: not verified).", ""]
    (ROOT / "docs" / "dev" / "screens-contact-sheets.md").write_text("\n".join(index))
    print("sheets:", ", ".join(f"{p.name}" for p in sorted(OUT.glob("sheet-*.png"))))


if __name__ == "__main__":
    main()
