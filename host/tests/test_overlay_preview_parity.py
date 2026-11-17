# ruff: noqa: E501
"""The overlays of the settings page preview (patch O01): one table, drawn the same as the unit draws.

``overlay_table.json`` must be what ``hal/maipai_overlay_core.h`` prints (``tests/firmware/overlay_dump.c``), and the page's JavaScript
(``overlay_shapes.py``) must draw every overlay and every named combination from it at the sizes the owner asked for. The drawing runs in
node on a recording canvas (no browser). Set ``MAIPAI_FW_TREE`` to a firmware folder to check a tree that has not been exported to patches
yet; otherwise the headers come from the firmware patches in order.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from maipai_body import overlay_shapes, reply_tags, settings_ui

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PATCHES = ROOT / "firmware" / "patches"
DUMP = HERE / "firmware" / "overlay_dump.c"
TREE = os.environ.get("MAIPAI_FW_TREE", "")
CHAIN = [
    "TA02-screen-effects-and-governor.patch",
    "TA03-overlay-engine.patch",
    "O01-overlay-engine-bigger-shapes-and-combinations.patch",
]


def _headers(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if TREE and Path(TREE, "main", "hal", "maipai_overlay_core.h").is_file():
        return Path(TREE, "main", "hal")
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    work = tmp_path_factory.mktemp("overlaycores")
    for name in CHAIN:
        text = (PATCHES / name).read_text()
        diff = work / "p.diff"
        diff.write_text(text[text.index("diff --git") :])
        run = subprocess.run(
            ["git", "apply", "--include=firmware/main/hal/*_core.h", str(diff)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        assert run.returncode == 0, f"{name}: {run.stderr}"
    return work / "firmware" / "main" / "hal"


@pytest.fixture(scope="module")
def dump(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    cores = _headers(tmp_path_factory)
    out = tmp_path_factory.mktemp("odump") / "dump"
    built = subprocess.run(
        [
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{cores}",
            str(DUMP),
            "-o",
            str(out),
            "-lm",
        ],
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stderr
    return out


def test_the_table_of_the_page_is_what_the_core_prints(dump: Path) -> None:
    printed = json.loads(
        subprocess.run([str(dump)], capture_output=True, text=True, check=True).stdout
    )
    assert printed == overlay_shapes.OVERLAY_TABLE, (
        "overlay_table.json is out of date: run overlay_dump > host/maipai_body/overlay_table.json"
    )


def test_the_page_offers_the_names_the_host_can_send() -> None:
    assert sorted(overlay_shapes.NAMES) == sorted(
        reply_tags.OVERLAYS
    )  # the picker, the tags and the unit's tool take the same 26 names
    assert set(overlay_shapes.OVERLAY_TABLE["presets"]) == set(reply_tags.COMBINED_OVERLAYS)
    table = overlay_shapes.OVERLAY_TABLE
    assert table["zones"] == {
        "banner": 28,
        "subtitles": 184,
    }  # the text zones the overlays leave alone (docs/design/banner-row-2026-11-16.md)
    assert table["sizes"]["zzz"]["sizes"] == [24, 36, 48] and table["sizes"]["rain"] == {
        "width": 3,
        "len": [14, 24],
    }


def test_the_page_script_carries_the_overlay_functions() -> None:
    assert "function drawOv(c,ov,t)" in settings_ui.JS and "function ovThumb(" in settings_ui.JS
    assert settings_ui.JS.count("const OVN=") == 1  # one list of names on the page
    assert "ov.t0" in settings_ui.JS and "const OT=" in settings_ui.JS


_DRIVER = r"""
const fs = require('fs');
const src = fs.readFileSync(0, 'utf8');
const ops = [];
let path = [], tx = 0, ty = 0, stack = [], lw = 1, fillStyle = '', strokeStyle = '', alpha = 1;
const grow = (x, y) => path.push([x + tx, y + ty]);
const ctx = {
  save() { stack.push([tx, ty, lw, alpha]); }, restore() { [tx, ty, lw, alpha] = stack.pop(); },
  translate(x, y) { tx += x; ty += y; }, rotate() {}, scale() {}, setTransform() {},
  beginPath() { path = []; }, closePath() {}, clip() {},
  moveTo: grow, lineTo: grow,
  quadraticCurveTo(a, b, x, y) { grow(a, b); grow(x, y); }, bezierCurveTo(a, b, c, d, x, y) { grow(a, b); grow(c, d); grow(x, y); },  // the control points bound the curve
  rect(x, y, w, h) { grow(x, y); grow(x + w, y + h); },
  arc(x, y, r) { grow(x - r, y - r); grow(x + r, y + r); }, ellipse(x, y, rx, ry) { grow(x - rx, y - ry); grow(x + rx, y + ry); },
  fillRect(x, y, w, h) { path = []; grow(x, y); grow(x + w, y + h); ops.push(box('fillRect')); },
  fill() { ops.push(box('fill')); }, stroke() { ops.push(box('stroke')); },
  createLinearGradient() { return { addColorStop() {} }; },
  set lineWidth(v) { lw = v; }, get lineWidth() { return lw; },
  set globalAlpha(v) { alpha = v; }, get globalAlpha() { return alpha; },
  set fillStyle(v) { fillStyle = v; }, set strokeStyle(v) { strokeStyle = v; }, set lineCap(v) {}, set lineJoin(v) {},
};
function box(kind) {
  const xs = path.map((p) => p[0]), ys = path.map((p) => p[1]);
  return { kind, w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys), lw, alpha, x: Math.min(...xs), y: Math.min(...ys), r: Math.max(...xs) };
}
const REDUCED = false;
eval(src + '\nglobalThis.__o = {drawOv, OT};');
const api = globalThis.__o;
const out = {};
for (const name of api.OT.names) {
  ops.length = 0;
  for (let t = 1; t <= 9; t += 0.5) { tx = 0; ty = 0; stack = []; api.drawOv(ctx, { name, intensity: 'heavy', t0: 0 }, t); }
  out[name] = ops.map((o) => [o.kind, o.w, o.h, o.lw, o.alpha, o.x, o.y]);
}
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def drawn() -> dict[str, list[list[object]]]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    run = subprocess.run(
        [node, "-e", _DRIVER],
        input=overlay_shapes.overlay_js(),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def test_every_overlay_and_combination_paints(drawn: dict[str, list[list[object]]]) -> None:
    assert set(drawn) == set(reply_tags.OVERLAYS)
    for name, ops in drawn.items():
        assert len(ops) > 5, f"{name} draws nothing in the preview"


def test_the_preview_keeps_the_sizes_of_the_unit(drawn: dict[str, list[list[object]]]) -> None:
    sizes = overlay_shapes.OVERLAY_TABLE["sizes"]
    # zzz: a stroked outline whose box plus its line is the glyph: 24, 36 and 48 px all show
    zz = {round(o[1] + o[3]) for o in drawn["zzz"] if o[0] == "stroke" and o[3] >= 4}
    assert zz == set(sizes["zzz"]["sizes"]), zz
    # rain: 3 px wide lines, 14 to 24 px long
    rain = [o for o in drawn["rain"] if o[0] == "stroke"]
    assert rain and {o[3] for o in rain} == {3}
    assert min(o[2] for o in rain) >= 13.9 and max(o[2] for o in rain) <= 24.5
    # snow: flakes of 5, 6, 8 and 10 px
    snow = {
        round(o[1])
        for o in drawn["snow"]
        if o[0] == "fill" and 4 <= o[1] <= 12 and abs(o[1] - o[2]) < 0.01
    }
    assert {5, 6, 8, 10} <= snow | {x + 2 for x in snow}
    # confetti: 8 to 14 px on both sides
    conf = [o for o in drawn["confetti"] if o[0] == "fillRect"]
    assert conf and all(7.99 <= o[1] <= 14.01 and 7.99 <= o[2] <= 14.01 for o in conf)
    # hearts: 24 to 40 px (the curve's box is a little wider than the stated size)
    hearts = [o for o in drawn["hearts"] if o[0] == "fill" and o[1] > 10]
    assert (
        hearts and min(o[1] for o in hearts) >= 24 * 0.9 and max(o[1] for o in hearts) <= 40 * 1.5
    )
    # leaves: 14 px long
    leaves = [o for o in drawn["leaves"] if o[0] == "fill"]
    assert leaves and all(abs(o[1] - 14) < 0.5 for o in leaves)
    # clouds: 96 px wide at the smallest
    clouds = [o for o in drawn["clouds"] if o[0] == "fill" and o[1] > 20]
    assert clouds and max(o[1] for o in clouds) >= 2 * 29 * 156 / 120 - 1
    # the sun: a 52 px disc with its rim
    sun = [o for o in drawn["sun"] if o[0] == "fill" and o[1] > 40]
    assert sun and max(o[1] for o in sun) >= 2 * sizes["sun"]["r"] - 0.5
    # fireworks: sparks 5 px thick with a trail, in bursts of 16 or more sparks that open to 60 to 100 px (the table's radius)
    fw = [o for o in drawn["fireworks"] if o[0] == "stroke"]
    assert len(fw) >= 16 and {o[3] for o in fw} == {5} and sizes["fireworks"]["radius"] == [60, 100]
