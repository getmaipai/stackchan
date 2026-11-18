# ruff: noqa: E501
"""The feature ledger (scripts/feature-ledger.py, docs/dev/feature-ledger.html): it is current, it covers what the repository holds (every game of the pack, every language, every mood, every
patch family), its statuses follow the stated rules (nothing is "proven on the unit" without a bench note, a robot screenshot or a named override), and the bench evidence copies carry no paths,
serial ports, hashes or addresses."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def ledger():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("feature_ledger_t", ROOT / "scripts" / "feature-ledger.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["feature_ledger_t"] = mod
    spec.loader.exec_module(mod)
    rows, meta = mod.build()
    return mod, rows, meta


def test_the_committed_ledger_is_current(ledger):
    mod, rows, meta = ledger
    assert mod.main(["--check"]) == 0, "run python3 scripts/feature-ledger.py and commit docs/dev/feature-ledger.md and .html"


def test_the_ledger_has_hundreds_of_rows_in_both_lists_and_the_progress_view(ledger):
    _, rows, _ = ledger
    user = [r for r in rows if r["audience"] == "user"]
    maker = [r for r in rows if r["audience"] == "maker"]
    assert len(user) >= 250 and len(maker) >= 250
    html = (ROOT / "docs" / "dev" / "feature-ledger.html").read_text()
    assert "<script src=" not in html and "<link rel=\"stylesheet\"" not in html and "http://" not in html.split("<script id=\"data\"")[0]   # self-contained, no outside scripts or styles
    assert "prefers-color-scheme" in html and "viewport" in html and "type=\"search\"" in html


def test_every_game_language_mood_and_patch_family_has_a_row(ledger):
    mod, rows, meta = ledger
    names = {r["name"] for r in rows}
    for game in mod.GAME_NAMES.values():
        assert f"Game: {game}" in names, game
    for label in ("Spanish", "French", "German", "Portuguese", "Italian", "English"):
        assert f"Language: {label}" in names, label
    import ledger_sources as src

    for mood in src.moods():
        assert f"Mood: {mood}" in names, mood
    families = {p["family"] for p in src.patches()}
    covered = {r["name"] for r in rows if r["area"] == "Firmware patch series"}
    assert len(covered) == len(families)
    assert not meta["unmapped"] or len(meta["unmapped"]) < 20   # patches no row names are listed on the page


def test_statuses_follow_the_rules(ledger):
    _, rows, _ = ledger
    for r in rows:
        assert r["status"] in ("idea", "designed", "built", "proven virtual", "proven on unit", "needs person"), r["name"]
        assert 0 <= r["percent"] <= 100
        if r["status"] == "needs person":
            assert r["percent"] <= 89, r["name"]
        if r["status"] == "designed":
            assert r["percent"] <= 10, r["name"]
        if r["status"] == "proven on unit":
            assert r["percent"] >= 90 and (r["bench"] or r["image"].startswith("docs/images/unit-") or r["rule"]), f"{r['name']}: proven on the unit with no bench note, no robot screenshot and no stated reason"
        assert r["where"] or r["audience"] == "user" or r["status"] != "proven on unit", r["name"]
        if r["image"]:
            assert (ROOT / r["image"]).is_file(), f"{r['name']}: image {r['image']} is missing"


def test_the_bench_evidence_copies_carry_no_paths_serial_ports_hashes_or_addresses():
    for note in (ROOT / "docs" / "dev" / "bench-evidence").glob("*.md"):
        text = note.read_text()
        assert not re.search(r"/Users/|/private/|usbmodem|/dev/cu\.", text), note.name
        assert not re.search(r"\b[0-9a-f]{16,}\b", text), note.name
        assert not re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text), note.name
