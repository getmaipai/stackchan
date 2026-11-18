#!/usr/bin/env python3
"""One contact sheet per face style (docs/dev/ledger-assets/faces-<style>.png): every mood drawn by the robot's own face code in the virtual unit, four to a row at half size, in the style's own look.
Usage: uv run --project host python scripts/virtual-unit/face_style_sheets.py   (needs the renderer: bash scripts/virtual-unit/build-face.sh)
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import importlib.util
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "dev" / "ledger-assets"
STYLES = ["big_eyes", "eyes_only", "stock", "classic", "minimal"]
MOODS = ["neutral", "happy", "sad", "angry", "doubt", "surprised", "sleepy", "tired", "closing", "sleeping", "love", "content", "thinking"]
COLS, SCALE, GAP = 4, 2, 4


def _load():
    spec = importlib.util.spec_from_file_location("vunit_sheets", ROOT / "scripts" / "virtual-unit" / "vunit.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["vunit_sheets"] = mod
    spec.loader.exec_module(mod)
    return mod


def read_png(data: bytes) -> np.ndarray:
    w, h = struct.unpack(">II", data[16:24])
    raw = zlib.decompress(data[data.index(b"IDAT") + 4 : data.rindex(b"IEND") - 8])
    return np.frombuffer(b"".join(raw[y * (w * 3 + 1) + 1 : (y + 1) * (w * 3 + 1)] for y in range(h)), dtype=np.uint8).reshape(h, w, 3)


def write_png(path: Path, img: np.ndarray) -> None:
    h, w, _ = img.shape
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))

    def chunk(tag: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main() -> int:
    vunit = _load()
    OUT.mkdir(parents=True, exist_ok=True)
    for style in STYLES:
        with vunit.VirtualUnit() as unit:
            unit.raw(f"style {style}")
            tiles = []
            for mood in MOODS:
                unit.call("self.face.bench_emotion", {"emotion": mood})
                unit.advance(900)
                img = read_png(unit.snapshot())
                tiles.append(img.reshape(img.shape[0] // SCALE, SCALE, img.shape[1] // SCALE, SCALE, 3).mean(axis=(1, 3)).astype(np.uint8))
        rows = []
        for i in range(0, len(tiles), COLS):
            row = tiles[i : i + COLS]
            row += [np.zeros_like(tiles[0])] * (COLS - len(row))
            rows.append(np.concatenate([np.pad(t, ((GAP, 0), (GAP, 0), (0, 0))) for t in row], axis=1))
        write_png(OUT / f"faces-{style}.png", np.concatenate(rows, axis=0))
        print(f"wrote {(OUT / f'faces-{style}.png').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
