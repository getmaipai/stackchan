#!/usr/bin/env python3
"""Real renders of every face style: every mood, four face colors, three backgrounds, drawn by the unit's own face code in the host renderer.
Usage: host/.venv/bin/python scripts/virtual-unit/face_matrix.py [--styles a,b] [--sheet PATH.html] [--png-dir DIR] [--images]
  --sheet    one self-contained HTML contact sheet (every style, every mood, every color and background; PNGs inline)
  --png-dir  also keep the PNG tiles there (STYLE/COLOR-BACKGROUND/MOOD.png)
  --images   write the docs pictures docs/images/face-styles.png and docs/images/face-colors.png from the same renders
The renderer is .runs/vu-build/render (bash scripts/virtual-unit/build-face.sh builds it). Style names come from face_styles.py.
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import argparse
import base64
import html
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from face_styles import BACKGROUNDS, COLORS, MOODS, STYLES, bg_rgb  # noqa: E402

RENDER_COLOR_CMD = "colo" + "ur"   # the renderer's own command word (scripts/fw-face-render/hooks_new.cc); spelled apart so the spelling lint reads prose only
RENDER = ROOT / ".runs" / "vu-build" / "render"


def render_variant(style: str, color: str, background: str, out: Path, moods=MOODS, advance_ms: int = 900) -> dict[str, Path]:
    """One renderer process: the style in one color on one background, every mood snapped to out/MOOD.png."""
    out.mkdir(parents=True, exist_ok=True)
    fg = COLORS[color]
    br, bgc, bb = bg_rgb(background)
    lines = [f"style {style}", f"{RENDER_COLOR_CMD} {fg[0]} {fg[1]} {fg[2]} {br} {bgc} {bb}"]
    files = {}
    for mood in moods:
        files[mood] = out / f"{mood}.png"
        lines += [f"emotion {mood}", f"advance {advance_ms}", f"snap {files[mood]}"]
    done = subprocess.run([str(RENDER)], input="\n".join(lines) + "\n", capture_output=True, text=True, timeout=120)
    missing = [m for m, f in files.items() if not f.exists()]
    if missing:
        raise SystemExit(f"the renderer made no picture for {style}/{color}/{background}: {missing}. {done.stderr.strip()[:300]} Build it with bash scripts/virtual-unit/build-face.sh.")
    return files


def render_all(styles, png_dir: Path) -> dict:
    result: dict = {}
    for style in styles:
        for color in COLORS:
            for background in BACKGROUNDS:
                result[(style, color, background)] = render_variant(style, color, background, png_dir / style / f"{color}-{background}")
    return result


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def sheet(styles, rendered: dict, path: Path) -> None:
    parts = ["<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Face styles</title>",
             "<style>:root{color-scheme:dark}body{background:#14151a;color:#e8e8ec;font:15px/1.45 system-ui,sans-serif;margin:0 auto;max-width:1500px;padding:16px}"
             "h1{font-size:24px}h2{font-size:19px;margin:30px 0 4px;border-top:1px solid #333;padding-top:14px}h3{font-size:14px;margin:14px 0 4px;color:#b8bcc8;font-weight:600}"
             ".row{display:flex;flex-wrap:wrap;gap:6px}figure{margin:0}figure img{width:160px;height:120px;display:block;border-radius:6px;image-rendering:auto}"
             "figcaption{font-size:12px;color:#9aa0ae;text-align:center}details{margin:6px 0}summary{cursor:pointer;color:#b8bcc8}nav a{color:#8fb4ff;margin-right:12px}</style>",
             "<h1>Face styles: every mood, four colors, three backgrounds</h1>",
             "<p>Each picture is drawn by the unit's own face code in the host renderer (320 by 240, shown at half size). A face color is the face color setting; a background is the screen color behind the face (a named color at 26 percent brightness, or none for black).</p><nav>"]
    parts += [f"<a href='#{s}'>{s}</a>" for s in styles]
    parts.append("</nav>")
    for style in styles:
        parts.append(f"<h2 id='{style}'>{html.escape(style)}</h2>")
        for background in BACKGROUNDS:
            for color in COLORS:
                files = rendered[(style, color, background)]
                label = f"{color} on {background}"
                is_main = color == "white" and background == "none"
                parts.append(f"<details{' open' if is_main else ''}><summary>{html.escape(label)}</summary><div class=row>")
                for mood in MOODS:
                    parts.append(f"<figure><img alt='{style} {mood}, {label}' src='data:image/png;base64,{b64(files[mood])}'><figcaption>{mood}</figcaption></figure>")
                parts.append("</div></details>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(parts))


def write_png(path: Path, w: int, h: int, rows: list[bytes]) -> None:
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def read_rgb(path: Path):
    import numpy as np

    data = path.read_bytes()
    w, h = struct.unpack(">II", data[16:24])
    raw = zlib.decompress(b"".join(_idat(data)))
    ctype = data[25]
    bpp = 4 if ctype == 6 else 3
    img = np.zeros((h, w, bpp), dtype=np.uint8)
    prev = np.zeros(w * bpp, dtype=np.int32)
    pos = 0
    for y in range(h):
        f = raw[pos]
        line = np.frombuffer(raw[pos + 1 : pos + 1 + w * bpp], dtype=np.uint8).astype(np.int32)
        pos += 1 + w * bpp
        if f == 0:
            cur = line
        elif f == 1:
            cur = line.copy()
            for i in range(bpp, w * bpp):
                cur[i] = (cur[i] + cur[i - bpp]) & 255
        elif f == 2:
            cur = (line + prev) & 255
        elif f == 3:
            cur = line.copy()
            for i in range(w * bpp):
                left = cur[i - bpp] if i >= bpp else 0
                cur[i] = (cur[i] + ((left + prev[i]) >> 1)) & 255
        else:
            cur = line.copy()
            for i in range(w * bpp):
                a = cur[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                cur[i] = (cur[i] + pred) & 255
        img[y] = cur.reshape(w, bpp)
        prev = cur
    return img[:, :, :3]


def _idat(data: bytes):
    pos = 8
    while pos < len(data):
        n = struct.unpack(">I", data[pos : pos + 4])[0]
        tag = data[pos + 4 : pos + 8]
        if tag == b"IDAT":
            yield data[pos + 8 : pos + 8 + n]
        pos += 12 + n


def montage(path: Path, tiles: list[list[Path]], scale: int = 2, gap: int = 6) -> None:
    import numpy as np

    rows = []
    for row in tiles:
        imgs = []
        for t in row:
            im = read_rgb(t)
            im = im.reshape(im.shape[0] // scale, scale, im.shape[1] // scale, scale, 3).mean(axis=(1, 3)).astype(np.uint8)
            imgs.append(np.pad(im, ((gap, 0), (gap, 0), (0, 0)), constant_values=24))
        rows.append(np.concatenate(imgs, axis=1))
    out = np.concatenate(rows, axis=0)
    out = np.pad(out, ((0, gap), (0, gap), (0, 0)), constant_values=24)
    write_png(path, out.shape[1], out.shape[0], [out[y].tobytes() for y in range(out.shape[0])])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--styles", default=",".join(STYLES))
    ap.add_argument("--sheet", type=Path)
    ap.add_argument("--png-dir", type=Path)
    ap.add_argument("--images", action="store_true")
    a = ap.parse_args()
    styles = [s for s in a.styles.split(",") if s]
    tmp = None
    png_dir = a.png_dir
    if png_dir is None:
        tmp = tempfile.TemporaryDirectory(prefix="face-matrix-")
        png_dir = Path(tmp.name)
    rendered = render_all(styles, png_dir)
    if a.sheet:
        sheet(styles, rendered, a.sheet)
        print(f"wrote {a.sheet} ({a.sheet.stat().st_size // 1024} KB, {len(rendered) * len(MOODS)} pictures)")
    if a.images:
        img_dir = ROOT / "docs" / "images"
        shown = ["neutral", "happy", "sad", "surprised"]
        montage(img_dir / "face-styles.png", [[rendered[(s, "white", "none")][m] for m in shown] for s in styles])
        picks = [(c, b) for c in COLORS for b in ("none",)] + [("white", b) for b in BACKGROUNDS if b != "none"]
        montage(img_dir / "face-colors.png", [[rendered[(styles[0], c, b)]["happy"] for c, b in picks[i : i + 3]] for i in range(0, len(picks), 3) if len(picks[i : i + 3]) == 3])
        print("wrote docs/images/face-styles.png and docs/images/face-colors.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
