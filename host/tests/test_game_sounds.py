"""The synthesized game sounds (scripts/make-game-sounds.py): deterministic, none clipping, all at the same chime level, tiny, each with a license, and the committed files are what the script makes."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("make_game_sounds", ROOT / "scripts" / "make-game-sounds.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_the_script_makes_the_same_bytes_twice_and_the_committed_files_match(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    assert mod.main(["--out", str(a)]) == 0 and mod.main(["--out", str(b)]) == 0
    for f in a.iterdir():
        assert f.read_bytes() == (b / f.name).read_bytes(), f.name
    committed = ROOT / "docs" / "dev" / "game-sounds"
    for name in ("manifest.json", "win_fanfare.wav", "chip_land_3.ulaw", "loudness.md"):
        assert (a / name).read_bytes() == (committed / name).read_bytes(), f"{name} is out of date: run python3 scripts/make-game-sounds.py"


def test_every_sound_is_small_unclipped_at_chime_level_and_has_a_license(tmp_path):
    mod.main(["--out", str(tmp_path)])
    m = json.loads((tmp_path / "manifest.json").read_text())["sounds"]
    ids = {s["id"] for s in m}
    assert {"chip_land_1", "chip_land_6", "drop_whoosh", "move_unit", "win_fanfare", "lose", "draw", "illegal_thud", "tap_tick", "flip", "slide", "pop", "match_found", "mine_flag", "hangman_ok", "hangman_bad"} <= ids
    for s in m:
        assert s["clipped"] == 0 and -11.5 <= s["peak_dbfs"] <= -9.9, s["id"]
        assert s["ulaw_bytes"] <= 2048 and s["license"] == "CC0-1.0" and s["author"], s["id"]
    assert sorted(s["ms"] for s in m if s["id"].startswith("chip_land")) == [90] * 6
