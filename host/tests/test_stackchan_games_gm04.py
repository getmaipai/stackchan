# ruff: noqa: E501
"""Firmware patches GM04 to GM06 (2026-11-17): Do It with the Reaction Time interface, the best-of-three Rock Paper Scissors with a real
count and window, the removal of Reaction Time, and the games on the full play area (y 28 to 224).

The two state machines are played by a scripted player in C (host/tests/firmware/games_gm_test.c); this file checks what the C test cannot
see: the patches are on ORDER with their headers, the compiler and the engine agree on the new shape, action and sizes, Reaction Time is
gone from every list, and every game keeps its words, sizes and touch areas inside the play area."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir
from test_stackchan_games import COMPILER, GAMES_DIR, IDS
from test_stackchan_games_v2 import _enum_values  # noqa: PLC2701

from maipai_body.bodies.stackchan import games

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATCHES = ROOT / "firmware" / "patches"
NAMES = [
    "GM04-games-icon-shape-ceil-action-and-xlarge-text.patch",
    "GM05-games-draw-icons-pop-and-bump.patch",
    "GM06-remove-the-reaction-time-game.patch",
]
HAVE_CC = shutil.which("cc") is not None
TRADEMARK = "bop" + " it"  # the old toy's two-word name is never written in code or docs


def _patch(name: str) -> str:
    return (PATCHES / name).read_text()


def test_the_patches_are_on_order_after_the_game_fixes_with_their_header_lines() -> None:
    order = [n.strip() for n in (PATCHES / "ORDER").read_text().splitlines() if n.strip()]
    positions = [order.index(n) for n in NAMES]
    assert positions == sorted(positions) and positions[0] > order.index(
        "GM03-game-effects-normalized-to-chime-loudness.patch"
    )
    for name in NAMES:
        text = _patch(name)
        head = text.split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash", "# Kconfig: none"):
            assert key in head, (name, key)
        assert chr(8212) not in text and TRADEMARK not in text.lower(), name


@pytest.fixture(scope="module")
def core_text(tmp_path_factory: pytest.TempPathFactory) -> str:
    return (cores_dir(tmp_path_factory) / "maipai_games_core.h").read_text()


def test_the_compiler_and_the_core_agree_on_the_icon_shape_the_ceil_action_the_icons_and_the_text_sizes(
    core_text: str,
) -> None:
    shapes = _enum_values(core_text, "typedef enum {\n    MG_SH_FILL")
    assert shapes["MG_SH_ICON"] == COMPILER.SHAPES["icon"] == 9 and shapes["MG_SH_MAX"] == 9
    ops = _enum_values(core_text, "typedef enum {\n    MG_OP_SET")
    assert ops["MG_OP_CEIL"] == COMPILER.OPS["ceil"] == 25 and ops["MG_OP_MAX"] == 25
    icons = _enum_values(core_text, "typedef enum {\n    MG_ICON_TAP")
    assert {k.removeprefix("MG_ICON_").lower(): v for k, v in icons.items() if k != "MG_ICONS"} == {
        "tap": 0,
        "swipe_l": 1,
        "swipe_r": 2,
        "shake": 3,
        "pet": 4,
        "tilt": 5,
        "rock": 6,
        "paper": 7,
        "scissors": 8,
    }
    assert {k.replace("_left", "_l").replace("_right", "_r"): v for k, v in COMPILER.ICONS.items()} == {
        k.removeprefix("MG_ICON_").lower(): v for k, v in icons.items() if k != "MG_ICONS"
    }
    assert COMPILER.SIZES["xlarge"] == 3 and "s.aux > 3" in core_text
    for name, bit in (("mirror", "0x100"), ("pop", "0x200"), ("bump", "0x400")):
        assert f"#define MG_ICON_{name.upper()} {bit}" in core_text
        assert COMPILER.ICON_FLAGS[name] == int(bit, 16)


@pytest.mark.skipif(not HAVE_CC, reason="no C compiler on this machine")
def test_the_do_it_and_rock_paper_scissors_state_machines_pass_the_scripted_player(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    hal = cores_dir(tmp_path_factory)
    binary = tmp_path / "games_gm_test"
    flags = ["-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{hal}"]
    source = str(HERE / "firmware" / "games_gm_test.c")
    build = subprocess.run(["cc", *flags, "-fsanitize=address,undefined", source, "-o", str(binary)], capture_output=True, text=True)
    if build.returncode != 0:
        build = subprocess.run(["cc", *flags, source, "-o", str(binary)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary), str(GAMES_DIR / "bopit.mpk"), str(GAMES_DIR / "rps.mpk")], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all passed" in run.stdout and "round 16:  650 ms to answer" in run.stdout


# --------------------------------------------------------------------------------------------- Reaction Time is gone


def test_reaction_time_is_removed_from_the_packs_the_player_the_host_and_the_lists() -> None:
    assert not (GAMES_DIR / "reaction.json").exists() and not (GAMES_DIR / "reaction.mpk").exists()
    assert len(IDS) == 7 and "reaction" not in IDS and games.IDS == IDS
    patch = _patch(NAMES[2])
    assert "foreach(f memory.mpk whack.mpk tictactoe.mpk bopit.mpk rps.mpk eightball.mpk dice.mpk)" in patch
    assert "constexpr int kBuiltIns   = 7;" in patch and "-    {_binary_reaction_mpk_start, _binary_reaction_mpk_end}," in patch
    assert "reaction.mpk" not in patch.split("+foreach", 1)[-1].split("\n", 1)[0] if "+foreach" in patch else True
    for text in (patch,):
        added = [ln for ln in text.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
        assert not any("reaction" in ln.lower() for ln in added)
    for phrase in ("play reaction time", "start reaction time", "tiempo de reaccion", "juega a reaccion", "reaction"):
        assert games.parse_ask(phrase) is None, phrase
    for text in (games._PLAIN["en"]["no_game"], games._PLAIN["es"]["no_game"]):
        assert "reaction" not in text.lower() and "reaccion" not in text.lower()
    for path in (
        "host/maipai_body/settings_sim.py",
        "host/maipai_body/settings_ui_pages.py",
        "host/maipai_body/i18n_pages.py",
        "host/maipai_body/bodies/stackchan/games.py",
        "docs/design/games-v2-2026-11-17.md",
    ):
        assert "reaction time" not in (ROOT / path).read_text().lower().replace("reaction time is", "").replace("reaction time is gone", ""), path


def test_every_game_still_has_a_start_phrase_in_english_and_spanish_and_the_list_names_seven() -> None:
    for game in games.GAMES:
        assert games.parse_ask(f"play {game.title['en']}") == ("start", game.id), game.id
        assert games.parse_ask(f"juega a {game.title['es']}") == ("start", game.id), game.id
    assert games.parse_ask("let's play do it") == ("start", "bopit")
    assert games.parse_ask("play rock paper scissors") == ("start", "rps")
    assert games.parse_ask("flip a coin") == ("start", "dice")


# --------------------------------------------------------------------------------------------- Do It and Rock Paper Scissors, the packs


def test_do_it_is_one_big_button_with_a_wait_then_a_large_icon_and_large_words_and_gets_faster_each_round() -> None:
    bop = json.loads((GAMES_DIR / "bopit.json").read_text())
    assert [r["name"] for r in bop["regions"]] == ["big"] and bop["regions"][0] == {"name": "big", "x": 20, "y": 28, "w": 280, "h": 196}
    assert list(bop["states"]) == ["intro", "wait", "show", "ok", "over"]
    assert bop["states"]["wait"]["timer"] == {"ctr": "wait"} and bop["states"]["show"]["timer"] == {"ctr": "limit"}
    icons = [s for s in bop["shapes"] if s["type"] == "icon"]
    assert len(icons) == 1 and icons[0]["size"] >= 120 and icons[0]["states"] == ["show"] and icons[0]["value"] == "act"
    big_words = [s for s in bop["shapes"] if s["type"] == "text" and s["size"] == "xlarge" and s["states"] == ["show"]]
    assert len(big_words) == 6 and {s["when"][1] for s in big_words} == set(range(6))
    ok = next(r for r in bop["rules"] if r["state"] == "ok" and r["on"] == "enter")["do"]
    assert ["div", "tmp", 7] in ok and ["floor", "limit", 650] in ok  # the time to answer shrinks by a seventh to 650 ms
    assert ["div", "tmp", 10] in ok and ["floor", "base", 600] in ok  # the wait before the reveal shrinks by a tenth to 600 ms
    assert ["ceil", "cue", 5] in ok and ["add", "cue", 18] in ok and ["tone", "good"] in ok  # the cue steps up five times
    wait_to_show = next(r for r in bop["rules"] if r["state"] == "wait" and r["on"] == "timer")["do"]
    assert ["tone_ctr", "cue"] in wait_to_show  # the rising tone starts with the reveal
    fills = [s for s in bop["shapes"] if s["type"] == "fill" and "when" in s]
    assert len(fills) == 12 and {s["when"][1] for s in fills} == set(range(18, 24))  # a background color for each level, waiting and reveal
    assert next(r for r in bop["rules"] if r["state"] == "over" and r["on"] == "enter")["do"] == [["tone", "bad"], ["save"]]
    assert bop["tap_on_release"] is True
    for game in ("bopit", "rps"):
        description = json.loads((GAMES_DIR / f"{game}.json").read_text())
        for key, text in description["texts"].items():
            assert text.get("es"), (game, key)  # English and Spanish; the other languages fall back to English


def test_rock_paper_scissors_is_a_best_of_three_with_a_count_a_window_and_two_big_buttons() -> None:
    rps = json.loads((GAMES_DIR / "rps.json").read_text())
    assert rps["counters"][:3] == ["score", "me", "bot"]
    assert rps["states"]["shoot"]["timer"] == [1200, 1200]  # the player's window
    assert [rps["states"][s]["timer"] for s in ("c1", "c2", "c3")] == [[560, 560]] * 3
    regions = {r["name"]: r for r in rps["regions"]}
    assert list(regions) == ["rock", "paper", "scissors", "again", "quit"]
    assert regions["rock"]["x"] == 20 and regions["scissors"]["x"] + regions["scissors"]["w"] == 300
    assert all(regions[n]["h"] >= 88 for n in ("rock", "paper", "scissors"))
    assert all(regions[n]["w"] >= 136 and regions[n]["y"] + regions[n]["h"] == 224 for n in ("again", "quit"))
    c1 = next(r for r in rps["rules"] if r["state"] == "c1" and r["on"] == "enter")["do"]
    assert ["rand", "bot", 3] in c1  # the unit's pick is drawn when the round starts
    changes_bot = [r for r in rps["rules"] for a in r.get("do", []) if a[0] in ("set", "rand", "copy") and a[1] == "bot"]
    assert [r["state"] for r in changes_bot if r["state"] != "intro"] == ["c1"]  # and in no other place: no peeking, no change after the tap
    for key in ("b1", "b2", "b3", "shoot", "early", "slow", "again", "rematch", "quit", "mwin", "mlose"):
        assert key in rps["texts"]
    assert rps["texts"]["early"]["en"] == "Too early!" and rps["texts"]["slow"]["en"] == "Too slow!"
    assert rps["texts"]["again"]["en"] == "Play again" and rps["texts"]["rematch"]["en"] == "Rematch" and rps["texts"]["quit"]["en"] == "Quit"
    assert rps["texts"]["shoot"]["es"] and rps["texts"]["again"]["es"] and rps["texts"]["rematch"]["es"]
    tones = {a[1] for r in rps["rules"] for a in r.get("do", []) if a[0] == "tone"}
    assert {"cue0", "cue1", "cue2", "cue5", "bad", "fanfare", "wah"} <= tones  # a beat sound each bump, a higher one at SHOOT


# --------------------------------------------------------------------------------------------- the full play area


@pytest.mark.parametrize("game", IDS)
def test_every_game_uses_the_play_area_between_y_28_and_224_with_the_text_inside_it(game: str) -> None:
    description = json.loads((GAMES_DIR / f"{game}.json").read_text())
    regions = description["regions"]
    assert regions, game
    assert min(r["y"] for r in regions) <= 78  # the area starts under the title strip at the latest (Rock Paper Scissors keeps its round and score lines above its tiles)
    assert max(r["y"] + r["h"] for r in regions) >= 196
    assert all(r["y"] >= 28 and r["y"] + r["h"] <= 224 for r in regions)
    for shape in description["shapes"]:
        if shape["type"] == "text":
            assert shape["y"] <= 216, (game, shape)  # the words never reach the 8 px margin at the bottom of the glass
            assert shape["y"] >= 28, (game, shape)
        if shape["type"] == "box" and shape.get("w", 0) < 320:
            assert shape["y"] + shape["h"] <= 224, (game, shape)
    assert not (GAMES_DIR / f"{game}.json").read_text().lower().count(TRADEMARK)
