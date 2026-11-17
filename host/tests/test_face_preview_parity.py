# ruff: noqa: E501
"""The settings page preview draws the unit's face (patch V10): one table, one set of shape builders, checked against the core.

The unit's face model is ``maipai_look_core.h``. ``face_table.json`` must be what the core prints, and the page's JavaScript
(``face_shapes.py``) must make the same shapes from the same inputs: the same kinds in the same order, the same count, the
same positions within a pixel (the C core uses single precision, the page double), for every style and every pose that matters.

The headers come from the firmware patches in order (as ``test_stackchan_train4.cores`` does) plus the V10 patches; set
``MAIPAI_FW_TREE`` to a firmware folder to check a tree that has not been exported to patches yet.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from maipai_body import face_shapes, settings_ui

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PATCHES = ROOT / "firmware" / "patches"
DUMP = HERE / "firmware" / "look_shapes_dump.c"
TREE = os.environ.get("MAIPAI_FW_TREE", "")


def _headers(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if TREE and Path(TREE, "main", "hal", "maipai_look_core.h").is_file():
        return Path(TREE, "main", "hal")
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    import importlib.util

    spec = importlib.util.spec_from_file_location("_train4_chain", HERE / "test_stackchan_train4.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    work = tmp_path_factory.mktemp("v10cores")
    for name in mod.CORE_CHAIN:  # the same chain the other core tests use (it ends with the face design, V10)
        text = (PATCHES / name).read_text()
        diff = work / "p.diff"
        diff.write_text(text[text.index("diff --git") :])
        run = subprocess.run(["git", "apply", "--include=firmware/main/hal/*_core.h", str(diff)], cwd=work, capture_output=True, text=True)
        assert run.returncode == 0, f"{name}: {run.stderr}"
    return work / "firmware" / "main" / "hal"


@pytest.fixture(scope="module")
def dump(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    cores = _headers(tmp_path_factory)
    out = tmp_path_factory.mktemp("dump") / "dump"
    built = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{cores}", str(DUMP), "-o", str(out), "-lm"], capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    return out


def test_the_table_of_the_page_is_what_the_core_prints(dump: Path) -> None:
    printed = json.loads(subprocess.run([str(dump), "table"], capture_output=True, text=True, check=True).stdout)
    assert printed == face_shapes.FACE_TABLE, "face_table.json is out of date: run look_shapes_dump table > host/maipai_body/face_table.json"


_DRIVER = r"""
const recs = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const rr = () => {};
%s
const styleOf = i => FT.styles[i];
const bad = [];
const cmp = (id, a, b) => {
  if (a.length !== b.length) { bad.push(id + ': count ' + a.length + ' vs ' + b.length); return; }
  for (let i = 0; i < a.length; i++) {
    if (a[i][0] !== b[i][0] || a[i][1] !== b[i][1]) { bad.push(id + ': shape ' + i + ' kind/color ' + a[i].slice(0, 2) + ' vs ' + b[i].slice(0, 2)); return; }
    if (Math.abs(a[i][2] - b[i][2]) > 1) { bad.push(id + ': shape ' + i + ' opacity ' + a[i][2] + ' vs ' + b[i][2]); return; }
    for (let k = 3; k < 11; k++) if (Math.abs(a[i][k] - b[i][k]) > 0.02) { bad.push(id + ': shape ' + i + ' value ' + (k - 3) + ': ' + a[i][k] + ' vs ' + b[i][k]); return; }
  }
};
let n = 0;
for (const r of recs) {
  const id = r.k + '#' + (n++);
  if (r.k === 'eye') cmp(id + ' ' + styleOf(r.style).name, r.shapes, eyeShapes(styleOf(r.style), r.in));
  else if (r.k === 'brow') { const q = r.in; cmp(id + ' ' + styleOf(r.style).name, r.shapes, browShapes(styleOf(r.style), q.side, q.ew, q.eh, q.es, q.gx, q.rlift, q.br, q.on, q.blift, q.btilt)); }
  else if (r.k === 'mouth') {
    const st = styleOf(r.style), q = r.in, t = mouthTarget(st, q.emo, q.sealed, q.speaking, q.open, q.ms);
    const tv = [t.w, t.bend, t.t, t.wob, t.split, t.tilt];
    for (let k = 0; k < 6; k++) if (Math.abs(tv[k] - r.target[k]) > 0.02) { bad.push(id + ' target ' + k + ': ' + tv[k] + ' vs ' + r.target[k]); break; }
    const b = mouthOf(FT.looks[0].stock.mouth), c = mouthFollow(b, t, 33, mouthTauFor(b, t, q.speaking, q.open));
    cmp(id + ' ' + st.name, r.shapes, mouthShapes(c, q.phase, q.on));
  }
  else if (r.k === 'dot') { const d = dotOf(styleOf(r.style), r.i, r.t); for (let k = 0; k < 4; k++) if (Math.abs(d[k] - r.dot[k]) > 1) bad.push(id + ' dot ' + d + ' vs ' + r.dot); }
  else if (r.k === 'blink') { if (Math.abs(blinkFactor(r.t) - r.v) > 0.001) bad.push(id + ' blink ' + r.t); }
  else if (r.k === 'spring') {
    if (!globalThis.__sp) { const a = FT.pose.big_eyes.neutral, b = FT.pose.big_eyes.surprised; globalThis.__sp = { s: newSpring(a), a, b, i: 0 }; }
    const g = globalThis.__sp;
    while (g.i <= r.step) { springStep(g.s, g.i < 20 ? g.b : g.a, 0.033); g.i++; }
    for (let k = 0; k < MP.N; k++) if (Math.abs(g.s.x[k] - r.x[k]) > 0.02) { bad.push(id + ' spring step ' + r.step + ' key ' + k + ': ' + g.s.x[k] + ' vs ' + r.x[k]); break; }
  }
}
console.log(JSON.stringify({ checked: n, bad }));
"""


def test_the_page_makes_the_same_shapes_as_the_core(dump: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    scenarios = subprocess.run([str(dump), "scenarios"], capture_output=True, text=True, check=True).stdout
    recs = json.loads(scenarios)
    assert len(recs) > 1000  # every style, both eyes, lids, slants, gazes, blinks, brows, mouths, dots, the spring
    run = subprocess.run([node, "-e", _DRIVER % face_shapes.face_js()], input=scenarios, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr[-1500:]
    result = json.loads(run.stdout.strip().splitlines()[-1])
    assert result["checked"] == len(recs)
    assert result["bad"] == [], result["bad"][:12]


def test_every_style_card_and_state_of_the_look_page_uses_the_shape_model() -> None:
    """The Look page, its style cards and the Home overview all draw through one Face class, and that class has no second table."""
    js = settings_ui.JS
    assert "eyeShapes(st,{side:" in js and "mouthShapes(this.mc," in js and "browShapes(st,side," in js  # the page draws shapes
    assert "const LK={};FT.emotions.forEach" in js  # the stock rows come from the table, not typed again
    assert "const GEO={big_eyes" not in js and "SLK" not in js  # the old duplicated tables are gone
    assert js.count("new Face(") >= 4  # Look preview, style cards, Home overview, the unit face view
    assert "isArt()" in js and "stepArt(dt)" in js and "paintArt(c)" in js
    # the blink and the voice use the unit's numbers
    assert "blinkFactor(el)" in js and "want>this.mo?.038:.105" in js
