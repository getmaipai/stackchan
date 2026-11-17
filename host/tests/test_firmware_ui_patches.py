# ruff: noqa: E501
"""The on-unit UI fixes (firmware patches UI01 to UI06): the patches are on ORDER after FI07 with their header lines, the pure cores
they touch pass their C tests against the headers as the whole ORDER leaves them, the memory game's lit time equals its tone, and the
screens the owner asked for exist in the code (find me gone, status icons off by default, sleepy without Z, sleeping that snores)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATCHES = ROOT / "firmware" / "patches"
NAMES = [
    "UI01-bigger-targets-longer-sheet-no-find-clock-games.patch",
    "UI02-quick-settings-and-more-screens-dismissable.patch",
    "UI03-color-memory-tone-and-light-together.patch",
    "UI04-status-icons-banner-events-pref-face-style.patch",
    "UI05-icon-sheet-status-row-and-bot-settings-screen.patch",
    "UI06-sleepy-nods-off-sleeping-snores.patch",
    "UI07-remote-chip-short-text-status-never-covers-it.patch",
    "UI08-game-buttons-inside-the-safe-area.patch",
    "UI09-single-overlay-screen-wifi-page-die-icon.patch",
]


def _patch_text(name: str) -> str:
    return (PATCHES / name).read_text()


def test_the_patches_are_on_order_after_fi07_with_their_header_lines_and_no_em_dash():
    order = (PATCHES / "ORDER").read_text().split()
    positions = [order.index(n) for n in NAMES]
    assert positions == sorted(positions) and positions[0] > order.index(
        "FI07-picface-uses-psram-inflate.patch"
    )
    for name in NAMES:
        text = _patch_text(name)
        head = text.split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash"):
            assert key in head, (name, key)
        assert chr(8212) not in text, name


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
@pytest.mark.parametrize("test", ["status_core_test.c", "look_core_test.c", "prefs_core_test.c", "screens_core_test.c"])
def test_the_core_tests_pass_against_the_cores_the_whole_order_leaves(
    tmp_path, tmp_path_factory, test
):
    hal = cores_dir(tmp_path_factory)
    binary = tmp_path / "t"
    build = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{hal}", str(HERE / "firmware" / test), "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0 and "passed" in run.stdout, run.stdout + run.stderr


def test_the_memory_game_lit_time_equals_the_tone_length():
    text = _patch_text(NAMES[2])
    assert "#define MG_COLOR_LIT_MS 450" in text
    game = json.loads((ROOT / "firmware" / "games" / "memory.json").read_text())
    for state in ("show", "echo", "correct"):
        assert game["states"][state]["timer"] == [450, 450], state


def test_find_me_is_gone_from_the_unit_tables_and_the_old_key_is_still_read():
    text = _patch_text(NAMES[0])
    assert 'static const char* const MPG_ACTION_NAMES[MPG_A_COUNT] = {"beep", "dance", "game", "hello"};' in text
    assert "MPG_LEGACY_FIND" in text and "mpg_is_legacy" in text


def test_status_icons_are_off_by_default_in_unit_and_host():
    assert '{"status_icons", "status_icons", MP_BOOL, 0, 1, 0, 1, NULL}' in _patch_text(NAMES[3])
    from maipai_body import unit_prefs

    assert unit_prefs.PREFS["status_icons"][2] is False and unit_prefs.DEFAULTS["status_icons"] is False
    assert "status_icons" in unit_prefs.UNIT_KEYS


def test_the_remote_chip_and_the_mic_glyph_ignore_the_status_icons_setting():
    text = _patch_text(NAMES[3])
    # the mic glyph is checked every tick whatever the setting says; only maipai_banner_status() looks at the setting
    assert "mst_mic_shown(s_mic_event.load()" in text
    assert "if (!s_status_icons.load())" in text
    added = "\n".join(l for l in text.splitlines() if l.startswith("+"))
    assert "MB_FLAG_REMOTE" not in added and "maipai_banner_session" not in added  # the remote chip is untouched


def test_sleepy_has_no_z_and_sleeping_snores():
    text = _patch_text(NAMES[5])
    assert 'avatar.setSpeech("");  // patch UI06: the sleepy look has no Z' in text
    assert '(strcmp(emotion, "closing") == 0 || strcmp(emotion, "sleeping") == 0)' in text
    assert "snore_start();" in text and "s_snore_drool" in text
    from maipai_body import settings_ui

    page = settings_ui.__dict__.get("PAGE_JS") or "".join(
        v for v in vars(settings_ui).values() if isinstance(v, str) and "nodLid" in v
    )
    assert "nodLid(" in page and "snoreOf(" in page


def test_every_game_button_is_inside_the_safe_area_in_the_sources():
    """The packs' own tables: no button below y 184 (the subtitle strip), none above y 28 (the banner row), each at least 44 px high."""
    for game in ("memory", "reaction", "whack"):
        description = json.loads((ROOT / "firmware" / "games" / f"{game}.json").read_text())
        for region in description["regions"]:
            assert region["y"] >= 28 and region["y"] + region["h"] <= 184, (game, region)
            assert region["h"] >= 44 and region["w"] >= 44, (game, region)
            assert region["x"] >= 8 and region["x"] + region["w"] <= 312, (game, region)


def test_the_remote_chip_is_short_and_fits_whole():
    text = _patch_text(NAMES[6])
    assert 'strcpy(chip, "Remote");' in text and "MB_SESSION_LABEL_MAX 12" in text
    from maipai_body import remote_activity as ra

    assert ra.SESSION_LABEL_MAX == 12 and ra.LOCAL_LABEL == "Settings"
    assert len("Remote: " + ra.LOCAL_LABEL) <= 20


def test_the_wifi_button_opens_a_wifi_page_not_quick_settings():
    text = _patch_text(NAMES[5]) + _patch_text(NAMES[8])
    assert 'label(p, "Wi-Fi", 10, 16);' in text and "maipai_display_open_wifi" in text
    assert "open_wifi()" in _patch_text(NAMES[4]) and "s_host->open_wifi();" in _patch_text(NAMES[4])
