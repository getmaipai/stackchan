# ruff: noqa: E501
"""The memory model of the virtual unit (owner decision 15, scripts/virtual-unit/memory_model.py, schema/memory-budget.json): every screen, overlay, picture face, language pack, task and
optional feature has a declared cost; the model tracks what is loaded as the scenarios run, fails when the budget would break, and is a leak canary (back at the face, the loaded set is the
baseline again). The numbers are the firmware track's (entries marked placeholder wait for a measure). Needs the screens renderer."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VU = ROOT / "scripts" / "virtual-unit"
sys.path.insert(0, str(VU))

needs_render = pytest.mark.skipif(not (ROOT / ".runs" / "vu-screens" / "render").exists(), reason="screens renderer not built")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, VU / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mm = _load("memory_model")
vunit = _load("vunit")
walk = _load("memory_walk")
TABLE = json.loads((ROOT / "schema" / "memory-budget.json").read_text())


def test_every_item_declares_its_cost_and_when_it_is_loaded_and_freed():
    for i in TABLE["items"]:
        for key in ("internal", "psram", "flash", "largest_block"):
            assert isinstance(i[key], int) and i[key] >= 0, (i["id"], key)
        assert i["loaded_when"] and i["freed_when"] and i["source"], i["id"]
        assert i["status"] in ("measured", "verified", "estimate", "placeholder", "to measure", "not built"), i["id"]
        assert i["kind"] in ("screen", "overlay", "picture_face", "language_pack", "task", "feature"), i["id"]
        assert i["largest_block"] <= i["internal"] or i["internal"] == 0 or i["largest_block"] == 0, i["id"]   # one block cannot be bigger than all of it
    ids = [i["id"] for i in TABLE["items"]]
    assert len(ids) == len(set(ids))


def test_the_gate_and_baseline_are_the_numbers_of_the_memory_note():
    g, b = TABLE["gate"], TABLE["baseline"]
    assert (g["internal_free_median_min"], g["internal_free_lowest_min"], g["largest_block_median_min"], g["largest_block_lowest_min"]) == (40000, 24000, 24000, 16000)
    assert b["internal_free_median"] == 68500 and b["largest_block_median"] == 32024   # b47 bench window 14 (docs/dev/heap-map-b47.md); windows 10 and 11 read 64,093 and 25,600 before SF47
    assert b["internal_free_median"] > g["internal_free_median_min"] and b["internal_free_lowest"] > g["internal_free_lowest_min"]


def test_every_screen_the_unit_can_show_has_a_declared_cost():
    ids = {i["id"] for i in TABLE["items"]}
    core = ROOT / ".runs" / "fixtree" / "firmware" / "main" / "hal" / "maipai_pages_core.h"
    if core.exists():
        import re

        names = re.search(r"MPG_PAGE_NAMES\[MPG_P_COUNT\] = \{([^}]*)\}", core.read_text()).group(1)
        for n in re.findall(r'"(\w+)"', names):
            assert f"screen.page.{n}" in ids, f"the firmware has a {n} page with no declared cost"
    for n in mm.PAGES:
        assert f"screen.page.{n}" in ids
    for k in ("screen.sheet", "screen.settings", "screen.apps_wall", "screen.games_wall", "screen.first_run", "screen.banner", "screen.keypad", "overlay.layer.back", "overlay.layer.event", "decor.notes", "picture.frame",
              "feature.link_tls", "feature.avatar_stream", "feature.echo_canceller", "feature.music_dance", "task.game_pack"):
        assert k in ids, k
    for lang in ("en", "es", "fr", "de", "pt", "it"):
        assert f"language.{lang}" in ids


def test_a_language_pack_and_the_always_on_tasks_cost_no_new_internal_ram():
    t = mm.MemoryModel(None, TABLE).totals()
    assert all(i["internal"] == 0 for i in TABLE["items"] if i["kind"] == "language_pack")   # read in place from flash
    assert t["items"] == len(TABLE["items"]) and t["always_on_internal"] > 0


def test_the_budget_breaks_when_too_much_is_open_at_once():
    order = ["screen.settings", "screen.first_run", "overlay.layer.back", "overlay.layer.event", "decor.notes", "screen.sheet", "screen.apps_wall", "screen.games_wall"]
    m = mm.MemoryModel(None, TABLE, strict=True)
    with pytest.raises(mm.MemoryBudgetError, match="internal_free_lowest.*under its gate"):   # the transient items add up past the margin above the lowest floor
        for k in order:
            m.open(k)
    assert m.loaded, "the first items fit"
    soft = mm.MemoryModel(None, TABLE, strict=False)
    for k in order:
        soft.open(k)
    assert soft.violations and any("internal_free_lowest" in v for v in soft.violations)


def test_the_camera_stream_as_a_standing_feature_breaks_the_largest_block_gate():
    base = TABLE["baseline"]["largest_block_median"]
    item = next(i for i in TABLE["items"] if i["id"] == "feature.avatar_stream")
    if base - item["largest_block"] >= TABLE["gate"]["largest_block_median_min"]:
        pytest.skip("the table no longer says the stream breaks the largest block gate")
    m = mm.MemoryModel(None, TABLE, strict=False)
    m.open("feature.avatar_stream")   # a block that stays: the largest block falls under the median floor (docs/dev/memory-budget.md says the same)
    assert any("largest_block_median" in v for v in m.violations)
    assert m.numbers()["largest_block_median"] == base - item["largest_block"]


def test_an_item_with_no_declared_cost_is_refused():
    m = mm.MemoryModel(None, TABLE)
    with pytest.raises(mm.MemoryBudgetError, match="no declared cost"):
        m.open("screen.nobody_declared_this")


def test_the_leak_canary_names_what_stayed_loaded():
    m = mm.MemoryModel(None, TABLE)
    base = m.snapshot()
    m.open("screen.page.clock")
    m.close("screen.page.clock")
    m.assert_back_to(base)
    m.open("overlay.layer.back")
    with pytest.raises(mm.MemoryBudgetError, match="still loaded: overlay.layer.back"):
        m.assert_back_to(base)


@needs_render
def test_opening_every_screen_in_turn_returns_to_the_baseline_and_keeps_the_budget():
    with vunit.VirtualUnit(profile="screens") as u:
        out = walk.walk(u)
    assert len(out["opened"]) >= 15 and not out["violations"]
    assert out["numbers"]["margin"]["internal_free_lowest"] > 0


@needs_render
def test_a_screen_left_open_is_a_leak_and_the_walk_fails():
    with vunit.VirtualUnit(profile="screens") as u:
        mem = u.memory
        base = mem.snapshot()
        u.raw("pshow settings")
        u.advance(300)
        mem.open("screen.apps_wall")   # opened by a touch and never closed
        u.raw("pshow face")
        u.advance(300)
        with pytest.raises(mm.MemoryBudgetError, match="screen.apps_wall"):
            mem.assert_back_to(base, "after the settings screen closed")


@needs_render
def test_overlays_and_notes_that_end_by_themselves_are_freed_and_the_dance_frees_on_stop():
    with vunit.VirtualUnit(profile="screens") as u:
        mem = u.memory
        u.raw("overlay rain 2 2")
        u.raw("notes 2")
        assert {"overlay.layer.back", "decor.notes"} <= set(mem.loaded)
        u.advance(2500)
        assert "overlay.layer.back" not in mem.loaded and "decor.notes" in mem.loaded   # the notes last 30 s
        u.advance(30000)
        assert not mem.loaded
        u.call("sim.music", {"action": "start", "song": "fast", "mode": "home"})
        u.advance(4000)
        assert "feature.music_dance" in mem.loaded
        u.call("sim.music", {"action": "stop"})
        u.advance(300)
        assert not mem.loaded
