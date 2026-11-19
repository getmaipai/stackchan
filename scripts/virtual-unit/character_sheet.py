#!/usr/bin/env python3
"""The six default characters, each in its own face style, color and background, in six moods: docs/images/characters.png and (with --sheet) an HTML sheet with the persona and voice settings beside each.
Drawn by the unit's own face code in the host renderer; the recipe styles (cat, robot, sleepy, rubber hose, neon anime) need a renderer built with patch UXF01 (bash scripts/virtual-unit/build-face.sh on branch ux/faces).
Usage: host/.venv/bin/python scripts/virtual-unit/character_sheet.py [--sheet FILE.html] [--images]
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import argparse
import html
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import face_matrix as fm  # noqa: E402
from face_styles import PALETTE, bg_rgb  # noqa: E402

CHARS = ROOT / "host" / "maipai_body" / "characters"
MOODS = ["neutral", "happy", "sad", "angry", "surprised", "sleepy"]


def rgb(value: str) -> tuple[int, int, int]:
    if value in ("", "none"):
        return (255, 255, 255)
    if value.startswith("#"):
        return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))
    return PALETTE[value]


def background(value: str) -> tuple[int, int, int]:
    if value.startswith("#"):
        return rgb(value)
    return bg_rgb(value or "none")


def render(char: dict, out: Path) -> dict[str, Path]:
    face = char["face"]
    fg, bg = rgb(face.get("color", "none")), background(face.get("background", "none"))
    style = face["style"]
    recipe = ROOT / "firmware" / "styles" / (style + ".rcp")
    if style not in fm.BASE_STYLES and (face.get("iris") or face.get("tongue")):   # the host sets bytes 14 and 15 of a copy of the style recipe: iris, and tongue in the high four bits
        import importlib.util

        spec = importlib.util.spec_from_file_location("face_recipe", ROOT / "scripts" / "face-recipe.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        raw = bytearray(recipe.read_bytes())
        if face.get("iris"):
            raw[14] = list(mod.PAL).index(face["iris"]) + 1
        if face.get("tongue"):
            raw[15] = (raw[15] & 0x0F) | ((list(mod.PAL).index(face["tongue"]) + 1) << 4)
        recipe = out / f"{char['id']}-copy.rcp"
        recipe.write_bytes(bytes(raw))
    cmds = [f"style {style}" if style in fm.BASE_STYLES else f"recipe {recipe}", f"{fm.RENDER_COLOR_CMD} {fg[0]} {fg[1]} {fg[2]} {bg[0]} {bg[1]} {bg[2]}"]
    files = {}
    for mood in MOODS:
        files[mood] = out / f"{char['id']}-{mood}.png"
        cmds += [f"emotion {mood}", "advance 900", f"snap {files[mood]}"]
    done = fm.subprocess.run([str(fm.RENDER)], input="\n".join(cmds) + "\n", capture_output=True, text=True, timeout=120)
    missing = [m for m, f in files.items() if not f.exists()]
    if missing:
        raise SystemExit(f"no picture for {char['id']} ({style}): {done.stderr.strip()[:200]}. Build the renderer with patch UXF01 (branch ux/faces): bash scripts/virtual-unit/build-face.sh.")
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", type=Path)
    ap.add_argument("--images", action="store_true")
    a = ap.parse_args()
    chars = [json.loads(p.read_text()) for p in sorted(CHARS.glob("*.json"))]
    with tempfile.TemporaryDirectory() as tmp:
        shots = {c["id"]: render(c, Path(tmp)) for c in chars}
        if a.sheet:
            parts = ["<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Characters</title><style>:root{color-scheme:dark}body{background:#14151a;color:#e8e8ec;font:15px/1.45 system-ui,sans-serif;margin:0 auto;max-width:1100px;padding:16px}h2{font-size:19px;margin:26px 0 2px;border-top:1px solid #333;padding-top:12px}.row{display:flex;flex-wrap:wrap;gap:6px}figure{margin:0}img{width:160px;height:120px;border-radius:6px;display:block}figcaption{font-size:12px;color:#9aa0ae;text-align:center}p{margin:4px 0;color:#c8ccd6}small{color:#9aa0ae}</style><h1>The six default characters</h1>"]
            for c in chars:
                f = c["face"]
                parts.append(f"<h2>{html.escape(c['name'])}</h2><p>{html.escape(c['about'])}</p><small>face {f['style']}, color {f.get('color', 'none')}, background {f.get('background', 'none')}; voice speed {c['voice']['speed']}, pitch {c['voice']['pitch']}</small><p>{html.escape(c['persona'])}</p><div class=row>")
                for m in MOODS:
                    parts.append(f"<figure><img alt='{c['name']} {m}' src='data:image/png;base64,{fm.b64(shots[c['id']][m])}'><figcaption>{m}</figcaption></figure>")
                parts.append("</div>")
            a.sheet.write_text("".join(parts))
            print(f"wrote {a.sheet}")
        if a.images:
            fm.montage(ROOT / "docs" / "images" / "characters.png", [[shots[c["id"]][m] for m in MOODS] for c in chars])
            print("wrote docs/images/characters.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
