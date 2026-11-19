"""Patch UX26 (the Four in a Row richer look, bench only) and its bench manifest: the patch has its header lines and is the last line of ORDER on the branch that carries it; the manifest is valid JSON,
names only tools the bench has, and measures the three looks and the box times. They wait on the branch ux/unproven-games for the bench's numbers; the tests skip while the patch is not in firmware/patches."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
PATCHES = ROOT / "firmware" / "patches"
NAME = "UX26-four-in-a-row-richer-look-bench.patch"
if not (PATCHES / NAME).exists():
    pytest.skip(NAME + " is not in firmware/patches yet", allow_module_level=True)


def test_the_patch_has_its_header_lines_and_is_on_order():
    assert NAME in (PATCHES / "ORDER").read_text().split()
    head = (PATCHES / NAME).read_text().split("diff --git", 1)[0]
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:"):
        assert key in head, key
    assert "BENCH ONLY" in head


def test_the_patch_adds_no_lvgl_object_and_keeps_level_zero_the_old_look():
    text = (PATCHES / NAME).read_text()
    added = "\n".join(l[1:] for l in text.splitlines() if l.startswith("+") and not l.startswith("+++"))
    for banned in ("lv_obj_create(g->", "lv_label_create", "lv_image_create", "lv_canvas"):
        assert banned not in added.split("self.game.bench_box")[0], banned   # the draw path has no objects (the bench box tool makes one box, on purpose)
    assert "if (s_look > 0)" in added   # level 0 falls through to the old drawing


def test_the_bench_manifest_measures_the_looks_the_boxes_and_the_heap():
    m = json.loads((ROOT / "scripts" / "bench-trains" / "c4-richer-look.json").read_text())
    tools = json.loads((ROOT / "schema" / "tools.json").read_text())["tools"]
    names = {c["tool"] for c in m["checks"]}
    assert {"self.bench.heap_info", "self.game.start", "self.game.bench_record", "self.game.bench_frames", "self.game.bench_tap", "self.game.stop"} <= names
    for n in names - {"self.game.bench_look", "self.game.bench_box"}:   # these two are the patch's own
        assert n in tools, n
    assert sum(1 for c in m["checks"] if c["tool"] == "self.game.bench_box") == 8
    assert [c["args"]["level"] for c in m["checks"] if c["tool"] == "self.game.bench_look"] == [0, 1, 2]
