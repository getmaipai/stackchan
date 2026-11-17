# ruff: noqa: E501
"""Firmware patches UI11 to UI13 (2026-11-17): the dim floor, the redrawn whack-a-mole with funny sounds, and the new games
(Tic-Tac-Toe, the Do It button game, Rock Paper Scissors, the magic 8 ball, dice and coin) with the engine they need.

The engine and the packs are played by a scripted bot in C (host/tests/firmware/games_v2_core_test.c); this file checks what the
C test cannot see: the compiler and the header agree, the patches are on ORDER, the device hooks stay lock free, the voice asks for
the new games, and the dim levels the host sends."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir
from test_rest_routine import _FakeClient, _rest_output  # noqa: PLC2701
from test_stackchan_games import COMPILER, GAMES_DIR, IDS

from maipai_body.bodies.stackchan import games
from maipai_body.bodies.stackchan.profile import STACKCHAN_PROFILE
from maipai_body.bodies.stackchan.routines import RestRenderer
from maipai_body.presence import night as night_module

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATCHES = ROOT / "firmware" / "patches"
NAMES = [
    "UI11-dim-floor-readable-night.patch",
    "UI12-games-engine-inputs-board-and-sounds.patch",
    "UI13-games-v2-draw-inputs-and-page.patch",
    "UI14-do-it-buttons-and-no-simon-says.patch",
    "UI15-magic-8-ball-dice-and-gentle-shake.patch",
]
HAVE_CC = shutil.which("cc") is not None


def _patch(name: str) -> str:
    return (PATCHES / name).read_text()


def _added(name: str, path: str) -> str:
    text = _patch(name)
    block = text.split(f"+++ b/{path}\n", 1)[1]
    lines = []
    for line in block.split("\n", 1)[1].splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------------------------- patches


def test_the_patches_are_appended_to_order_in_order_with_their_header_lines_and_no_em_dash() -> (
    None
):
    order = (PATCHES / "ORDER").read_text().split()
    positions = [order.index(n) for n in NAMES]
    assert positions == sorted(positions) and positions[0] > order.index(
        "UI10-remote-banner-one-fill.patch"
    )
    assert order[-1] == NAMES[-1] or order.index(NAMES[-1]) > order.index(NAMES[0])
    for name in NAMES:
        text = _patch(name)
        head = text.split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash"):
            assert key in head, (name, key)
        assert chr(8212) not in text, name


def test_the_three_patches_replay_in_order_and_leave_the_new_cores(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """The shared helper replays the whole of ORDER (UI11 to UI13 last) onto an empty folder and keeps the pure cores."""
    cores = cores_dir(tmp_path_factory)
    for core in (
        "maipai_games_core.h",
        "maipai_games_sfx_core.h",
        "maipai_games_input_core.h",
        "maipai_face_tod_core.h",
        "maipai_pages_core.h",
    ):
        assert (cores / core).exists(), core


# --------------------------------------------------------------------------------------------- the engine, in C


@pytest.mark.skipif(not HAVE_CC, reason="no C compiler on this machine")
def test_the_new_engine_pieces_and_the_eight_games_pass_the_bot_test(
    tmp_path: Path, tmp_path_factory
) -> None:
    hal = cores_dir(tmp_path_factory)
    binary = tmp_path / "games_v2_core_test"
    flags = ["-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{hal}"]
    source = str(HERE / "firmware" / "games_v2_core_test.c")
    build = subprocess.run(
        ["cc", *flags, "-fsanitize=address,undefined", source, "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        build = subprocess.run(
            ["cc", *flags, source, "-o", str(binary)], capture_output=True, text=True
        )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(
        [str(binary), *(str(GAMES_DIR / f"{i}.mpk") for i in IDS)], capture_output=True, text=True
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all passed" in run.stdout


def _enum_values(text: str, first: str) -> dict[str, int]:
    """The members of the enum that starts with `first`, with their numbers (explicit or counting up)."""
    member = first.split()[-1]  # the enum's first member, which is part of `first`
    block = re.sub(
        r"/\*.*?\*/", "", member + text.split(first, 1)[1].split("}", 1)[0], flags=re.S
    )  # comments hold commas
    out: dict[str, int] = {}
    nxt = 0
    for raw in block.replace("\n", " ").split(","):
        item = re.sub(r"/\*.*?\*/", "", raw).strip()
        if not item:
            continue
        name, _, value = item.partition("=")
        name = name.strip()
        if value.strip():
            word = value.strip()
            nxt = (
                out[word] if word in out else int(word, 0)
            )  # a number, or an earlier member (an alias such as MG_SH_MAX)
        out[name] = nxt
        nxt += 1
    return out


@pytest.fixture(scope="module")
def core_text(tmp_path_factory: pytest.TempPathFactory) -> str:
    return (cores_dir(tmp_path_factory) / "maipai_games_core.h").read_text()


@pytest.fixture(scope="module")
def sfx_text(tmp_path_factory: pytest.TempPathFactory) -> str:
    return (cores_dir(tmp_path_factory) / "maipai_games_sfx_core.h").read_text()


def test_the_compiler_and_the_core_agree_on_events_shapes_actions_and_guards(
    core_text: str,
) -> None:
    events = _enum_values(core_text, "typedef enum {\n    MG_EV_ENTER")
    assert {
        k.removeprefix("MG_EV_").lower(): v for k, v in events.items() if k != "MG_EV_COUNT"
    } == COMPILER.EVENTS
    shapes = _enum_values(core_text, "typedef enum {\n    MG_SH_FILL")
    assert {
        k.removeprefix("MG_SH_").lower(): v for k, v in shapes.items() if k != "MG_SH_MAX"
    } == COMPILER.SHAPES
    ops = _enum_values(core_text, "typedef enum {\n    MG_OP_SET")
    compiler_ops = {k.removeprefix("MG_OP_").lower(): v for k, v in ops.items() if k != "MG_OP_MAX"}
    assert {k: v for k, v in compiler_ops.items()} == {k: v for k, v in COMPILER.OPS.items()}
    guards = _enum_values(core_text, "typedef enum {\n    MG_G_NONE")
    assert {
        k.removeprefix("MG_G_").lower(): v
        for k, v in guards.items()
        if k != "MG_G_MAX" and k != "MG_G_NONE"
    } == COMPILER.GUARDS


def test_the_compiler_and_the_sound_core_agree_on_every_clip_and_group(sfx_text: str) -> None:
    before, after = sfx_text.split("/* The groups:", 1)
    clips = re.findall(r'\{"([a-z0-9_]+)", \d+, \{', before)
    assert tuple(clips) == COMPILER.CLIPS
    groups = re.findall(r'\{"(bonk|miss|escape)", \d+, \{', after)
    assert tuple(groups) == COMPILER.GROUPS
    assert COMPILER.TONE_IDS["cue0"] == 5 + COMPILER.CLIPS.index("cue0") == 18
    assert (
        COMPILER.TONE_IDS["bonk"] == 0x80
        and COMPILER.TONE_IDS["escape"] == 0x82
        and COMPILER.TONE_IDS["popup"] == 0
    )
    assert "MGS_SFX_RATE 16000" in sfx_text and "MGS_SFX_MAX_MS 900" in sfx_text


def test_the_new_packs_are_what_the_compiler_makes_and_use_the_new_features() -> None:
    for game in ("whack", "tictactoe", "bopit", "rps", "eightball", "dice"):
        description = json.loads((GAMES_DIR / f"{game}.json").read_text())
        assert COMPILER.build(description) == (GAMES_DIR / f"{game}.mpk").read_bytes()
        assert len(description["shapes"]) <= 64 and len(description["texts"]) <= 32
    whack = json.loads((GAMES_DIR / "whack.json").read_text())
    assert any(s["type"] == "mole" for s in whack["shapes"])
    tones = {a[1] for r in whack["rules"] for a in r.get("do", []) if a[0] == "tone"}
    assert {"bonk", "miss", "escape"} <= tones  # the funny sounds: a hit, a miss, an escaped mole
    bop = json.loads((GAMES_DIR / "bopit.json").read_text())
    assert bop["tap_on_release"] is True and bop["states"]["show"]["timer"] == {"ctr": "limit"}  # patch GM04: Do It is a reaction game
    events = {r["on"] for r in bop["rules"]}
    assert {
        "tap",
        "swipe_l",
        "swipe_r",
        "shake",
        "pet",
        "tilt_l",
        "tilt_r",
        "tilt_f",
        "tilt_b",
    } <= events
    assert len(bop["regions"]) == 1  # patch GM04: one big button, the whole play area (UI14 had six tiles)
    assert (
        not (GAMES_DIR / "simonsays.json").exists() and not (GAMES_DIR / "simonsays.mpk").exists()
    )
    ttt = json.loads((GAMES_DIR / "tictactoe.json").read_text())
    assert len(ttt["regions"]) == 9 and all(r["w"] >= 44 and r["h"] >= 44 for r in ttt["regions"])
    assert any(a[0] == "board_bot" for r in ttt["rules"] for a in r.get("do", []))


def test_a_tone_name_the_sound_core_does_not_have_is_refused_in_plain_words() -> None:
    description = json.loads((GAMES_DIR / "whack.json").read_text())
    description["rules"][4]["do"].append(["tone", "scream"])
    with pytest.raises(COMPILER.PackError) as error:
        COMPILER.build(description)
    assert "tone" in str(error.value) and "Fix" in str(error.value)


# --------------------------------------------------------------------------------------------- the device side


def test_the_player_lists_the_eight_packs_in_the_cmake_list_and_the_table() -> None:
    patch = _patch(NAMES[4])
    assert (
        "foreach(f memory.mpk reaction.mpk whack.mpk tictactoe.mpk bopit.mpk rps.mpk eightball.mpk dice.mpk)"
        in patch
    )
    assert "constexpr int kBuiltIns   = 8;" in patch
    for game in IDS:
        assert game != "simonsays"


def test_the_sensor_hooks_use_atomics_only_so_a_psram_stack_task_never_touches_flash() -> None:
    patch = _patch(NAMES[2])
    # the three entry points the imu and head touch tasks call
    for fn in (
        "void maipai_games_post_input(int ev)",
        "void maipai_games_imu_feed(",
        "void maipai_games_shake(",
    ):
        assert fn in patch, fn
    body = patch.split("void maipai_games_post_input(int ev)", 1)[1].split(
        "const char* maipai_games_stop_locked", 1
    )[0]
    body = body.split("// ---- the tools ----", 1)[0]
    for forbidden in (
        "nvs_",
        "Settings",
        "heap_caps_",
        "malloc",
        "LvglLockGuard",
        "lv_",
        "std::mutex",
        "esp_flash",
        "Schedule(",
    ):
        assert forbidden not in body, forbidden
    assert "fetch_or" in body
    # and the two task files call only those entry points
    imu = _added_diff_lines(patch, "firmware/main/hal/hal_imu.cpp")
    assert "maipai_games_imu_feed(" in imu and "maipai_games_shake(" in imu
    touch = _added_diff_lines(patch, "firmware/main/hal/hal_head_touch.cpp")
    assert "maipai_games_post_input(MAIPAI_GAME_EV_PET)" in touch


def _added_diff_lines(patch: str, path: str) -> str:
    block = patch.split(f"+++ b/{path}\n", 1)[1]
    out = []
    for line in block.split("\n", 1)[1].splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+") and not line.startswith("+++"):
            out.append(line[1:])
    return "\n".join(out)


def test_the_sound_waits_for_the_picture_the_way_color_memory_does() -> None:
    patch = _patch(NAMES[2])
    assert (
        "sfx_play_now();  // patch UI13: a funny sound starts with the strip that carries its picture"
        in patch
    )
    assert "now - s_sfx.since_ms >= 100" in patch  # a dark screen starts it after 100 ms anyway
    assert (
        'maipai_sounds_gate("popup")' in patch.split("void sfx_queue(", 1)[1]
    )  # mute, sounds off and night decide
    assert "PlayPcm(s_sfx_buf, s_sfx.n, MGS_SFX_RATE)" in patch  # the unit's volume is the codec's
    # no new sound file: the clips are made in code
    assert ".ogg" not in _patch(NAMES[1]) and ".wav" not in _patch(NAMES[1])


def test_a_game_that_takes_taps_on_release_is_the_only_one_that_hears_the_release() -> None:
    patch = _patch(NAMES[2])
    assert "if (g == nullptr || g->tap_on_release) {" in patch  # the press is not a tap for Do It
    assert "if (g == nullptr || !g->tap_on_release) {" in patch  # the release is for Do It only
    assert (
        "maipai_games_release(s_trace.x0" in patch and "s_trace.region0 != MTC_REGION_EDGE" in patch
    )


def test_the_games_page_has_a_more_tile_and_every_tile_is_at_least_44_px() -> None:
    patch = _patch(NAMES[2])
    assert "MPG_GAMES_TILE_H 44" in patch and "mpg_games_has_more(total)" in patch
    assert 'tx("More games", "Mas juegos")' in patch


def test_dim_parts_on_the_unit_are_raised() -> None:
    patch = _patch(NAMES[0])
    assert "case MF_BAND_NIGHT: return 75;" in patch and "#define MPG_NIGHT_DIM_PCT 55" in patch


# --------------------------------------------------------------------------------------------- the host


@pytest.mark.parametrize(
    ("said", "expect"),
    [
        ("play tic tac toe", ("start", "tictactoe")),
        ("let's play tic-tac-toe", ("start", "tictactoe")),
        ("play noughts and crosses", ("start", "tictactoe")),
        ("juega al tres en raya", ("start", "tictactoe")),
        ("let's play do it", ("start", "bopit")),
        ("play magic 8 ball", ("start", "eightball")),
        ("ask the magic 8 ball", ("start", "eightball")),
        ("juega a la bola 8 magica", ("start", "eightball")),
        ("roll a dice", ("start", "dice")),
        ("please flip a coin", ("start", "dice")),
        ("tira un dado", ("start", "dice")),
        ("lanza una moneda", ("start", "dice")),
        ("play dice", ("start", "dice")),
        ("juguemos a hazlo", ("start", "bopit")),
        ("play simon", ("start", "memory")),  # plain Simon is the color game
        ("play rock paper scissors", ("start", "rps")),
        ("play rps", ("start", "rps")),
        ("juega a piedra papel tijera", ("start", "rps")),
        ("what is my best score in tic tac toe", ("scores", "tictactoe")),
    ],
)
def test_voice_phrases_for_the_new_games(said: str, expect: tuple[str, str | None]) -> None:
    assert games.parse_ask(said) == expect


def test_every_game_has_two_languages_a_unit_and_a_start_tool_name() -> None:
    assert games.IDS == IDS
    for game in games.GAMES:
        assert game.title["en"] and game.title["es"] and game.unit["en"] and game.unit["es"]
        assert game.aliases and game.id in game.aliases


def test_the_host_names_every_new_game_in_the_sentences_it_says() -> None:
    en = games._PLAIN["en"]["no_game"].lower()
    for word in ("tic-tac-toe", "do it", "rock paper scissors"):
        assert word in en
    es = games._PLAIN["es"]["no_game"].lower()
    for word in ("tres en raya", "hazlo", "piedra papel tijera"):
        assert word in es


# --------------------------------------------------------------------------------------------- the dim floor


def test_the_night_level_and_the_resting_level_are_readable_and_never_below_the_floor() -> None:
    assert night_module.DIM_FLOOR == 25
    assert (
        35 <= night_module.NIGHT_BRIGHTNESS <= 40
        and night_module.NIGHT_BRIGHTNESS >= night_module.DIM_FLOOR
    )


def test_the_rest_stage_dims_to_the_floor_or_more_by_default_and_a_lower_asked_level_is_raised() -> (
    None
):
    sent: list[int] = []
    renderer = RestRenderer(set_brightness=sent.append)
    renderer.render(_rest_output("asleep", 0.6, "sleepy"), _FakeClient(), STACKCHAN_PROFILE)
    assert sent and sent[0] >= night_module.DIM_FLOOR and sent[0] == 35
    low: list[int] = []
    RestRenderer(set_brightness=low.append, sleep_brightness=5).render(
        _rest_output("asleep", 0.6, "sleepy"), _FakeClient(), STACKCHAN_PROFILE
    )
    assert low and low[0] == night_module.DIM_FLOOR


def test_the_settings_slider_and_the_saved_level_still_work() -> None:
    from maipai_body import unit_settings

    for level in (10, 35, 100):
        assert unit_settings._clean({"brightness": level})["brightness"] == level
    with pytest.raises(unit_settings.SettingsError):
        unit_settings._clean({"brightness": 9})


def test_the_settings_preview_dims_the_pages_by_the_same_percent_as_the_unit(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Parity table: the preview on the settings page (settings_ui_pages.py) and the unit (maipai_pages_core.h) dim a night page by one number."""
    from maipai_body import settings_ui_pages

    header = (cores_dir(tmp_path_factory) / "maipai_pages_core.h").read_text()
    unit = int(re.search(r"#define MPG_NIGHT_DIM_PCT (\d+)", header).group(1))
    source = Path(settings_ui_pages.__file__).read_text()
    assert unit == 55 and source.count(f"dim?{unit}:100") == 2 and "dim?35:100" not in source
    face = (cores_dir(tmp_path_factory) / "maipai_face_tod_core.h").read_text()
    assert (
        re.search(r"case MF_BAND_NIGHT: return (\d+);", face.split("mf_band_dim_pct", 1)[1]).group(
            1
        )
        == "75"
    )


def test_every_shake_hint_says_gently_in_both_languages_and_never_hard() -> None:
    """Owner rule (2026-11-17): nobody should shake the unit hard. Hints, tiles and call-outs say gently."""
    for game, needles in (
        ("bopit", ("Gentle shake!", "Agita suave!")),
        ("eightball", ("gently shake", "agita suavemente")),
        ("dice", ("gently shake", "agita suavemente")),
    ):
        text = (GAMES_DIR / f"{game}.json").read_text()
        for needle in needles:
            assert needle in text, (game, needle)
        assert "hard" not in text.lower().replace("too hard", ""), game
        assert "Shake it" not in text and "Sacudeme" not in text, game


def test_the_gentle_shake_numbers_in_the_input_core(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    header = (cores_dir(tmp_path_factory) / "maipai_games_input_core.h").read_text()
    assert "#define MGI_SHAKE_STROKE 2.2f" in header and "#define MGI_SHAKE_STROKES 3" in header
    assert (
        "#define MGI_SHAKE_TOO_HARD 20.0f" in header
        and "#define MGI_SHAKE_WINDOW_MS 900u" in header
    )


def test_the_imu_task_feeds_the_games_every_20_ms_and_a_shake_that_is_too_hard_is_easy() -> None:
    patch = _patch(NAMES[4])
    assert "maipai_games_imu_feed(_bmi270->getData().accel_x" in patch
    assert "shake == MGI_SHAKE_OK ? MG_EV_SHAKE : MG_EV_EASY" in patch
    body = patch.split("const int shake = mgi_shake_update", 1)[1].split(
        "if (++s_imu_pass % 5 != 0)", 1
    )[0]
    for forbidden in (
        "nvs_",
        "Settings",
        "heap_caps_",
        "malloc",
        "LvglLockGuard",
        "lv_",
        "std::mutex",
        "Schedule(",
    ):
        assert forbidden not in body, forbidden


def test_the_ring_light_cue_starts_with_its_sound_and_goes_dark_by_itself() -> None:
    patch = _patch(NAMES[4])
    assert "s_pending_light = r.light;  // it waits for its sound" in patch
    assert "light_apply(s_pending_light);  // the light starts with the sound" in patch
    assert "now - s_light_off_ms" in patch.replace(
        "static_cast<int32_t>(now - s_light_off_ms)", "now - s_light_off_ms"
    )


def test_the_motion_code_finds_its_shapes_where_the_packs_put_them() -> None:
    """maipai_games_draw.h animates shapes by their place in the pack (UI15); the packs must keep those places."""
    # patch GM04: Do It and Rock Paper Scissors draw their moving parts as icon shapes (found by type and flag, not by place)
    rps = json.loads((GAMES_DIR / "rps.json").read_text())["shapes"]
    assert sum(s["type"] == "icon" and "pop" in s.get("flags", []) for s in rps) == 2
    assert sum(s["type"] == "icon" and "bump" in s.get("flags", []) for s in rps) == 1
    bop = json.loads((GAMES_DIR / "bopit.json").read_text())["shapes"]
    assert sum(s["type"] == "icon" and "pop" in s.get("flags", []) for s in bop) == 1
    ball = json.loads((GAMES_DIR / "eightball.json").read_text())["shapes"]
    assert (
        ball[0]["type"] == "fill"
        and all(s["type"] in ("circle", "box") for s in ball[1:11])
        and ball[11]["type"] == "text"
    )


def test_celebration_is_wired_through_the_overlay_engine_and_the_new_best() -> None:
    patch = _patch(NAMES[4])
    assert (
        "bool maipai_fx_celebrate(int level)" in patch
        and 'mo_id(level >= 2 ? "celebrate" : "confetti")' in patch
    )
    assert (
        "celebrate(mg_celebration_for_rank(rank));" in patch and "celebrate(r.celebrate);" in patch
    )
    for game, count, states in (("tictactoe", 3, ("win",)), ("rps", 2, ("win", "mwin"))):
        rules = json.loads((GAMES_DIR / f"{game}.json").read_text())["rules"]
        wins = [r for r in rules if any(a[0] == "celebrate" for a in r.get("do", []))]
        assert len(wins) == count and all(r["state"] in states for r in wins), game
    for game in (
        "whack",
        "memory",
        "bopit",
        "eightball",
        "dice",
    ):  # a new best only, never by rule
        rules = json.loads((GAMES_DIR / f"{game}.json").read_text())["rules"]
        assert not any(a[0] == "celebrate" for r in rules for a in r.get("do", [])), game
