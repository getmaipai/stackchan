# ruff: noqa: E501
"""The 2026-11-17 owner round (firmware patches NX01 to NX09): on ORDER after MF01 with their header lines, the pure cores they touch pass
their C tests against the headers as the whole ORDER leaves them, and the behavior the owner asked for is in the patch text."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parents[1] / "firmware" / "patches"
NAMES = [
    "NX01-quick-sheet-lock-tile-and-listening-light-row.patch",
    "NX02-info-tab-shows-every-row-no-ten-taps.patch",
    "NX03-one-surface-on-the-glass-sheet-and-pages-join-the-manager.patch",
    "NX04-snapshot-includes-the-system-layer-keypad-visible.patch",
    "NX05-face-seen-glyph-and-tool-in-the-banner-strip.patch",
    "NX06-face-seeker-default-always-and-safe-gates.patch",
    "NX07-no-z-letters-over-the-keypad.patch",
    "NX08-wall-tiles-with-pictures-colors-and-big-titles.patch",
    "NX09-timers-preset-column-and-tall-rows-no-word-timer.patch",
]


def _text(name: str) -> str:
    return (PATCHES / name).read_text()


def _added(name: str) -> str:
    return "\n".join(line[1:] for line in _text(name).splitlines() if line.startswith("+") and not line.startswith("+++"))


def _removed(name: str) -> str:
    return "\n".join(line[1:] for line in _text(name).splitlines() if line.startswith("-") and not line.startswith("---"))


def test_the_patches_follow_mf01_in_order_with_their_header_lines_and_no_em_dash():
    order = (PATCHES / "ORDER").read_text().split()
    positions = [order.index(n) for n in NAMES]
    assert positions == sorted(positions) and positions[0] == order.index("MF01-music-feature-task-stack-6144.patch") + 1
    for name in NAMES:
        text = _text(name)
        head = text.split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash", "# Kconfig:"):
            assert key in head, (name, key)
        assert chr(8212) not in text, name


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
@pytest.mark.parametrize(
    "test",
    [
        "apps_core_test.c",
        "pages_core_test.c",
        "screens_core_test.c",
        "status_core_test.c",
        "banner_core_test.c",
        "version_core_test.c",
        "prefs_core_test.c",
        "seek_core_test.c",
        "seek_wire_test.c",
    ],
)
def test_the_core_tests_pass_against_the_cores_the_whole_order_leaves(tmp_path, tmp_path_factory, test):
    hal = cores_dir(tmp_path_factory)
    binary = tmp_path / "t"
    build = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined", f"-I{hal}", str(HERE / "firmware" / test), "-o", str(binary), "-lm"],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=300)
    assert run.returncode == 0 and "passed" in run.stdout, run.stdout + run.stderr


def test_the_sheet_has_a_lock_tile_where_the_light_tile_was_and_the_light_switch_is_in_settings():
    core = _added(NAMES[0])
    assert "MPG_S_MUTE, MPG_S_QUIET, MPG_S_LOCK, MPG_S_TIMERS, MPG_S_GAMES" in core
    assert '#define MPG_SHEET_ALIAS_LIGHT "light"' in core and "return MPG_S_LOCK;" in core  # the old key is the same item
    assert "MPG_S_LIGHT" in _removed(NAMES[0]) and "MPG_S_LIGHT" not in core
    assert "MAC_R_LISTEN_LIGHT" in core and "g_host->toggle_light()" in core
    assert "Set a code on the settings page" in core and "lock_has_code()" in core and "s_host->lock_now()" in core


def test_the_ten_tap_gesture_is_gone_from_the_info_tab_and_the_version_screen():
    gone = _removed(NAMES[1])
    for word in ("MAC_SF_DETAILS", "MAC_S_TEN_TAPS", "MAC_R_I_HINT", "mv_tap(&S->ver", "mv_tap(&s_ver", "on_ver_tap"):
        assert word in gone, word
    added = _added(NAMES[1])
    for word in ("MAC_SF_DETAILS", "MAC_S_TEN_TAPS", "MAC_R_I_HINT", "mv_tap("):
        assert word not in added, word
    assert "mac_uptime_text" in added and "ids[n++] = MAC_R_SSID;" in added and "ids[n++] = MAC_R_I_UP;" in added


def test_opening_a_screen_closes_the_sheet_and_the_page_through_the_manager():
    added = _added(NAMES[2])
    assert "maipai_screen_open(MSCR_PAGE)" in added and "maipai_screen_open(MSCR_SHEET)" in added
    assert "maipai_screen_register(MSCR_SHEET, sheet_closer)" in added and "maipai_screen_register(MSCR_PAGE, maipai_pages_yield)" in added
    # the three sheet tiles that open a screen go straight to it: no sheet_pick() (which re-showed the page under the sheet) before them
    assert _removed(NAMES[2]).count("sheet_pick();") == 2 and "sheet_pick();" not in added
    assert "static inline unsigned mscr_enter" in added and "static inline int mscr_valid" in added


def test_the_snapshot_lays_the_system_layer_over_the_screen():
    added = _added(NAMES[3])
    assert "blend_layer(buf, lv_layer_top());" in added and "blend_layer(buf, lv_layer_sys());" in added


def test_the_face_glyph_is_its_own_slot_next_to_the_mic_and_follows_the_status_icons_switch():
    added = _added(NAMES[4])
    assert "MB_FLAG_MIC = 0, MB_FLAG_FACE, MB_FLAG_CAMERA, MB_FLAG_REMOTE" in added
    assert '"self.banner.face_seen"' in added and "Property(\"seconds\", kPropertyTypeInteger, 3, 1, 10)" in added
    assert "!s_status_icons.load()" in added and "maipai_banner_face_seen(0)" in added  # the unit's own detector calls it
    assert "maipai_banner_flag(MB_FLAG_FACE, false, 0)" in added  # switching the icons off clears the glyph
    assert "MB_FLAG_CAMERA" not in added.replace("MB_FLAG_FACE, MB_FLAG_CAMERA, MB_FLAG_REMOTE", "")  # the camera cue is not touched


def test_the_seeker_defaults_to_always_and_is_gated_for_lock_carry_and_night():
    added = _added(NAMES[5])
    assert "!in->locked && !in->carried" in added and "in->mode != MS_MODE_ALWAYS || in->night" in added
    assert "!e->locked && !e->carried" in added and "e->carried         = maipai_pickup_held()" in added
    assert 'MP_ENUM, 0, 2, 2, 1, MP_NAMES_TURN' in added and "out->turn_to_faces = 2;" in added


def test_the_face_glyph_objects_are_forgotten_when_the_strip_is_torn_down():
    """Found on the bench: the glyph timed out, the strip was deleted with it, and the next paint used the deleted objects (the unit stopped answering)."""
    added = _added(NAMES[4])
    assert "s_face_head = s_face_eye_a = s_face_eye_b = s_face_mouth = nullptr;" in added
    assert added.count("s_face_head = s_face_eye_a = s_face_eye_b = s_face_mouth = nullptr;") == 2  # delete_glyph and teardown_strip


def test_the_flush_time_overlays_stay_off_while_the_keypad_is_up():
    added = _added(NAMES[6])
    assert "maipai_lock_keypad_up()" in added and "s_keypad_a.store(true);" in added and "s_keypad_a.store(false);" in added


def test_the_pages_status_tool_lists_lock_not_light():
    added = _added(NAMES[0])
    assert '\\"quiet\\",\\"lock\\",\\"timers\\"' in added


def test_the_wall_tiles_have_pictures_accents_and_big_titles_and_the_host_names_the_game():
    added = _added(NAMES[7])
    for game in ("memory", "whack", "tictactoe", "bopit", "rps", "eightball", "dice"):
        assert f'strcmp(id, "{game}") == 0' in added, game
    assert "text_w(name, kBig) <= pw - 6 ? kBig" in added and "virtual const char* game_id(int)" in added
    assert "#define MAC_WALL_TILE_W 154" in added and "#define MAC_WALL_TILE_H 90" in added and "#define MAC_WALL_X0 4" in added


def test_the_timers_app_has_a_preset_column_tall_rows_and_never_writes_the_word_timer():
    added = _added(NAMES[8])
    assert "#define MAC_PRESETS 7" in added and "{1, 5, 10, 15, 30, 45, 60}" in added and "MAC_S_CUSTOM" in added
    assert "mac_bar_fill(" in added and "tx(MAC_S_TIMER)" not in added and "tx(MAC_S_ALARM)" not in added
    assert "tx(MAC_S_TIMER)" in _removed(NAMES[8]) and "tx(MAC_S_ALARM)" in _removed(NAMES[8])
