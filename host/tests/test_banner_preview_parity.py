# ruff: noqa: E501
"""The banner row of the settings page preview (patch N01): one table, one set of rules, checked against the core.

``banner_table.json`` must be what ``hal/maipai_banner_core.h`` prints, and the page's JavaScript (``banner_shapes.py``) must give
the same answers as the C core for fitting, the marquee, the eased shift of the face, the strip room and when battery and Wi-Fi
show. Set ``MAIPAI_FW_TREE`` to a firmware folder to check a tree that has not been exported to patches yet; otherwise the
headers come from the firmware patches in order.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from maipai_body import banner_shapes, settings_ui, unit_prefs

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PATCHES = ROOT / "firmware" / "patches"
DUMP = HERE / "firmware" / "banner_dump.c"
TREE = os.environ.get("MAIPAI_FW_TREE", "")


def _headers(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if TREE and Path(TREE, "main", "hal", "maipai_banner_core.h").is_file():
        return Path(TREE, "main", "hal")
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    work = tmp_path_factory.mktemp("bannercores")
    for name in [
        "N01-banner-row-and-subtitles.patch"
    ]:  # the one patch that adds the core (a new file, so it needs no other patch)
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
    core = work / "firmware" / "main" / "hal" / "maipai_banner_core.h"
    if not core.is_file():
        pytest.skip("the banner patch is not in the patch list yet")
    return core.parent


@pytest.fixture(scope="module")
def dump(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    cores = _headers(tmp_path_factory)
    out = tmp_path_factory.mktemp("bdump") / "dump"
    built = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{cores}", str(DUMP), "-o", str(out)],
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stderr
    return out


def test_the_table_of_the_page_is_what_the_core_prints(dump: Path) -> None:
    printed = json.loads(
        subprocess.run([str(dump), "table"], capture_output=True, text=True, check=True).stdout
    )
    assert printed == banner_shapes.BANNER_TABLE, (
        "banner_table.json is out of date: run banner_dump table > host/maipai_body/banner_table.json"
    )


_DRIVER = r"""
const recs = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const rrPath = () => {};
%s
const bad = [];
const eq = (id, a, b) => { if (a !== b) bad.push(id + ': ' + a + ' vs ' + b); };
let n = 0;
for (const r of recs) {
  const id = r.k + '#' + (n++);
  if (r.k === 'fit') eq(id, mbFit(r.w, r.room), r.v);
  else if (r.k === 'marquee') { eq(id, mbMarqueeX(r.t, r.overflow), r.v); eq(id + ' pass', mbMarqueePass(r.overflow), r.pass); }
  else if (r.k === 'fade') { let cur = r.visible ? 0 : 255; r.opa.forEach((q, i) => { cur = mbFadeStep(cur, r.visible, 33); eq(id + ' step ' + i, cur, q); }); }
  else if (r.k === 'page_ms') eq(id, msPageMs(r.chars), r.v);
  else if (r.k === 'text_top') eq(id, msTextTop(r.lines, r.line_h), r.v);
  else if (r.k === 'room') { eq(id, mbStripW(r.bits), r.strip_w); eq(id + ' room', mbTextRoom(r.bits, r.icon), r.v); }
  else if (r.k === 'caption_hold') eq(id, mbCaptionHold(r.chars), r.v);
  else if (r.k === 'battery') eq(id, mbBatteryShown(r.level, r.charging, r.charging, r.mode, r.blip), r.v);
  else if (r.k === 'wifi') eq(id, mbWifiShown(r.wifi, r.hub, r.mode), r.v);
}
console.log(JSON.stringify({ checked: n, bad }));
"""


def test_the_page_gives_the_same_answers_as_the_core(dump: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    scenarios = subprocess.run(
        [str(dump), "scenarios"], capture_output=True, text=True, check=True
    ).stdout
    recs = json.loads(scenarios)
    assert len(recs) > 400
    run = subprocess.run(
        [node, "-e", _DRIVER % banner_shapes.banner_js()],
        input=scenarios,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr[-1500:]
    result = json.loads(run.stdout.strip().splitlines()[-1])
    assert result["checked"] == len(recs)
    assert result["bad"] == [], result["bad"][:12]


def test_the_page_draws_the_banner_and_the_subtitles_in_their_zones() -> None:
    js = settings_ui.JS
    assert (
        "paintBanner(sc,bn,this.t,bn.fade)" in js and "paintSubtitles(sc,sub.text" in js
    )  # the preview draws both
    assert "sc.rect(0,BT.zones.face[0]" in js  # the face is clipped to its zone, as on the unit
    assert (
        "mbShiftPx" not in js and "bannerTarget" not in js
    )  # nothing moves for the banner any more
    assert (
        "pseg(pv,put,'captions_mode'" in js and "pseg(pv,put,'top_bar'" in js
    )  # the Captions and Top bar options
    assert "['off','subtitles','banner']" in js


def test_the_zones_of_the_table_do_not_overlap() -> None:
    zones = banner_shapes.BANNER_TABLE["zones"]
    assert zones["banner"][1] == zones["face"][0] and zones["face"][1] == zones["subtitles"][0]
    assert (
        zones["banner"][0] == 0 and zones["subtitles"][1] == banner_shapes.BANNER_TABLE["screen_h"]
    )
    row = banner_shapes.BANNER_TABLE["row"]
    assert (
        zones["banner"][0] <= row["y"] and row["y"] + row["h"] <= zones["banner"][1]
    )  # the one row sits in the banner zone
    assert (
        row["x"] * 2 + row["w"] == banner_shapes.BANNER_TABLE["screen_w"]
    )  # equal margins, full width


def test_the_two_settings_are_in_the_hosts_table() -> None:
    assert unit_prefs.PREFS["captions_mode"] == (
        "enum",
        ("off", "subtitles", "banner"),
        "off",
        True,
    )
    assert unit_prefs.PREFS["top_bar"] == ("enum", ("hidden", "always"), "hidden", True)
    assert {"captions_mode", "top_bar"} <= set(unit_prefs.UNIT_KEYS)
