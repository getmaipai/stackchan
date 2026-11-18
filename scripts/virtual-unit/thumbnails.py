#!/usr/bin/env python3
"""Thumbnails for the dashboard's catalog (owner decision 17), drawn by the real renderer: every face style (each as the face with a speech mouth and a happy mood), every overlay and named
combination (on the plain face), and a language sample (the first-run language step in each language, patch UX12). Writes PNGs of 160x120 (half size) and a manifest.json with the name, kind,
file, size, the sha-256 of the file and what drew it (the tree stamp), so the dashboard can show them and a changed look shows as a changed hash.
Usage: python3 scripts/virtual-unit/thumbnails.py [--out DIR] [--full]   (default DIR .runs/thumbnails; --full keeps 320x240). Needs the screens renderer.
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import vunit  # noqa: E402

STYLES = ("big_eyes", "eyes_only", "stock", "classic", "minimal")
OVERLAYS = ("rain", "snow", "sun", "clouds", "wind", "thunder", "fog", "stars", "disco", "leaves", "confetti", "fireworks", "hearts", "steam", "balloons", "zzz", "stormy", "rainy", "snowy", "sunny", "windy", "night", "party", "celebrate", "love", "sleeping")
LANGUAGES = ("en", "es", "fr", "de", "pt", "it")
OVERLAY_SECONDS = {"thunder": 6, "fireworks": 5, "confetti": 3}


def _chunks(png: bytes):
    i = 8
    while i < len(png):
        n = struct.unpack(">I", png[i : i + 4])[0]
        yield png[i + 4 : i + 8], png[i + 8 : i + 8 + n]
        i += 12 + n


def _rows(png: bytes) -> tuple[int, int, list[bytes]]:
    w, h = struct.unpack(">II", png[16:24])
    raw = zlib.decompress(b"".join(d for t, d in _chunks(png) if t == b"IDAT"))
    stride = 1 + w * 3
    rows, prev = [], bytearray(w * 3)
    for y in range(h):
        f, line = raw[y * stride], bytearray(raw[y * stride + 1 : (y + 1) * stride])
        for x in range(len(line)):
            a = line[x - 3] if x >= 3 else 0
            b = prev[x]
            c = prev[x - 3] if x >= 3 else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(line))
        prev = line
    return w, h, rows


def _png(w: int, h: int, rows: list[bytes]) -> bytes:
    raw = b"".join(b"\0" + r for r in rows)

    def chunk(t: bytes, d: bytes) -> bytes:
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def half(png: bytes) -> bytes:
    """A 2 by 2 box average: 320x240 to 160x120."""
    w, h, rows = _rows(png)
    out = []
    for y in range(0, h - 1, 2):
        a, b = rows[y], rows[y + 1]
        line = bytearray()
        for x in range(0, w - 1, 2):
            for c in range(3):
                i = x * 3 + c
                line.append((a[i] + a[i + 3] + b[i] + b[i + 3] + 2) // 4)
        out.append(bytes(line))
    return _png(w // 2, h // 2, out)


def tree_stamp() -> dict:
    p = ROOT / ".runs" / "vu-build" / "tree-stamp.json"
    return json.loads(p.read_text()) if p.exists() else {}


def main(argv: list[str]) -> int:
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / ".runs" / "thumbnails"
    full = "--full" in argv
    out.mkdir(parents=True, exist_ok=True)
    items = []

    def save(kind: str, name: str, png: bytes, extra: dict | None = None) -> None:
        data = png if full else half(png)
        f = f"{kind}-{name}.png"
        (out / f).write_bytes(data)
        w, h = struct.unpack(">II", data[16:24])
        items.append({"kind": kind, "name": name, "file": f, "width": w, "height": h, "sha256": hashlib.sha256(data).hexdigest(), **(extra or {})})

    for style in STYLES:
        with vunit.VirtualUnit(profile="screens") as u:
            u.raw(f"style {style}")
            u.call("self.face.bench_emotion", {"emotion": "happy"})
            u.advance(1200)
            save("face", style, u.snapshot())
    for name in OVERLAYS:
        with vunit.VirtualUnit(profile="screens") as u:
            u.raw("style big_eyes")
            u.raw(f"overlay {name} 2 0")
            u.advance(2500 if name not in OVERLAY_SECONDS else OVERLAY_SECONDS[name] * 1000)
            save("overlay", name, u.snapshot())
    for lang_i, lang in enumerate(LANGUAGES):
        with vunit.VirtualUnit(profile="screens") as u:
            u.raw(f"frun step 0 {lang_i} -1")
            u.advance(400)
            save("language", lang, u.snapshot(), {"sample": "the first-run language step"})
    manifest = {"version": 1, "size": "320x240" if full else "160x120", "drawn_by": "the screens renderer of the virtual unit (the unit's own LVGL display code)", "tree": tree_stamp().get("tree", ""), "items": items}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"thumbnails: {len(items)} pictures and manifest.json in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
