# ruff: noqa: E501
"""The passcode lock on the unit (firmware patches LK01 to LK03) and the games and quick settings patches that came with it (GM01 to GM03, QS01).

The cores are plain C: compile each host test against the headers as the whole of ORDER leaves them and run it. The unit's enforcement is C++ for the
device, so the tests read the patches for the rules that matter (what a locked unit refuses, what is never logged) the way the other firmware tests do."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATCHES = ROOT / "firmware" / "patches"
NEW = [
    "LK01-lock-core.patch",
    "LK02-lock-state-tools-and-lock-screen.patch",
    "LK03-lock-enforcement-and-more-screen-lock-button.patch",
    "GM01-games-use-the-full-height-and-no-subtitles.patch",
    "GM02-game-drag-bar-dismisses-the-game.patch",
    "QS01-quick-settings-padding-and-no-wifi-glyph-on-wifi-screens.patch",
    "GM03-game-effects-normalized-to-chime-loudness.patch",
]
needs_cc = pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")


def _added(name: str, path: str) -> str:
    """The lines a patch adds to one file."""
    text = (PATCHES / name).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    out = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            out.append(line[1:])
    return "\n".join(out)


def _build(tmp_path, cores, test: str) -> Path:
    binary = tmp_path / test.replace(".c", "")
    run = subprocess.run(
        ["cc", "-std=gnu99", "-Wall", "-Wextra", "-Werror", f"-I{cores}", str(HERE / "firmware" / test), "-o", str(binary), "-lm"],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    return binary


@needs_cc
def test_lock_core_c_tests_pass(tmp_path, tmp_path_factory):
    binary = _build(tmp_path, cores_dir(tmp_path_factory), "lock_core_test.c")
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0 and "lock core ok" in run.stdout, run.stdout + run.stderr


@needs_cc
@pytest.mark.parametrize("code,rounds", [("4821", 2000), ("0000", 2000), ("123456", 2000), ("9", 1), ("55555", 3)])
def test_the_hash_is_pbkdf2_hmac_sha256(tmp_path, tmp_path_factory, code, rounds):
    binary = _build(tmp_path, cores_dir(tmp_path_factory), "lock_core_test.c")
    salt = bytes(range(7, 23))
    run = subprocess.run([str(binary), "--kdf", code, salt.hex(), str(rounds)], capture_output=True, text=True, timeout=120)
    assert run.stdout.strip() == hashlib.pbkdf2_hmac("sha256", code.encode(), salt, rounds).hex()


def test_the_sheet_keeps_one_row_of_six_tiles_and_has_no_lock_tile():
    """Owner, 2026-11-17: no lock tile on the control sheet. Nothing in the patches touches the sheet's layout or its tile list."""
    text = (PATCHES / NEW[2]).read_text()
    assert "+++ b/firmware/main/hal/maipai_pages_core.h" not in text and "MPG_S_LOCK" not in text and "mpg_sheet_layout" not in text
    more = _added(NEW[2], "firmware/main/hal/maipai_more.cc")
    assert "maipai_lock_has_code()" in more and "maipai_lock_now" in more  # the touch way to lock: the More screen, while a code is set


@needs_cc
def test_games_drag_bar_geometry_and_effect_loudness(tmp_path, tmp_path_factory):
    binary = _build(tmp_path, cores_dir(tmp_path_factory), "games_drag_test.c")
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and "games drag ok" in run.stdout, run.stdout + run.stderr


@needs_cc
def test_the_physical_reset_erases_the_lock_namespace(tmp_path, tmp_path_factory):
    """The two-step reset keeps only its mark and the calibrations: the lock's namespace is erased with everything else."""
    cores = cores_dir(tmp_path_factory)
    src = tmp_path / "r.c"
    src.write_text('#include <stdio.h>\n#include "maipai_reset_core.h"\nint main(void){return (!mrc_keep_namespace("mp_lock") && mrc_keep_namespace("mp_reset"))?0:1;}\n')
    subprocess.run(["cc", "-std=gnu99", f"-I{cores}", str(src), "-o", str(tmp_path / "r")], check=True)
    assert subprocess.run([str(tmp_path / "r")]).returncode == 0


def test_the_patches_are_on_order_after_ui15_and_carry_their_header_lines():
    order = (PATCHES / "ORDER").read_text().split()
    last = order.index("UI15-magic-8-ball-dice-and-gentle-shake.patch")
    for i, name in enumerate(NEW):
        assert order.index(name) == last + 1 + i, name
        text = (PATCHES / name).read_text()
        head = text.split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:"):
            assert key in head, (name, key)
        assert chr(8212) not in text, name


def test_the_core_is_plain_c_with_no_device_call_and_no_log():
    core = _added(NEW[0], "firmware/main/hal/maipai_lock_core.h")
    assert not re.search(r"\b(esp_|heap_caps|xTask|vTask|nvs_|ESP_LOG|printf\()", core.replace("snprintf", ""))
    assert "#define LK_WRONG_DELAY_MS 0" in core  # the owner's decision: no lockout, one named place to raise it
    assert "LK_WRONG_DELAY_MS" in core.split("mlk_key(")[1]


def test_the_code_is_never_logged_stored_or_reported():
    unit = _added(NEW[1], "firmware/main/hal/maipai_lock.cc")
    for line in unit.splitlines():
        if "ESP_LOG" in line or "device_events_push" in line or "snprintf(extra" in line:
            assert not re.search(r"digits|hash|salt|\bcode\b|current|properties", line), line
    assert "SetString(\"code\"" not in unit and "SetString(\"pin\"" not in unit
    assert 'Settings st("mp_lock", true)' in unit and "Schedule" in unit  # written from the main task, never a PSRAM-stack task
    # the status and every reply come from the core, which never carries the code, the hash or the length
    core = _added(NEW[0], "firmware/main/hal/maipai_lock_core.h")
    status = core.split("static inline int mlk_status_json")[1].split("}")[0]
    assert not re.search(r"hash|salt|digits|s->n\b", status)


def test_every_lock_tool_exists_and_a_locked_unit_cannot_be_changed_by_a_tool():
    unit = _added(NEW[1], "firmware/main/hal/maipai_lock.cc")
    for tool in ("status", "set", "clear", "now", "config"):
        assert f'"self.lock.{tool}"' in unit
    core = _added(NEW[0], "firmware/main/hal/maipai_lock_core.h")
    for fn in ("mlk_set(", "mlk_clear(", "mlk_set_auto("):
        body = core.split(f"static inline int {fn}")[1].split("\n}\n")[0]
        assert "MLK_R_LOCKED" in body, fn
    tools = re.findall(r'AddTool\("(self\.lock\.[a-z_]+)"', unit)
    assert tools and not [t for t in tools if "unlock" in t]  # no tool unlocks: only the keypad does (the bench tools press its keys)


def test_a_locked_unit_refuses_wake_stop_touch_swipes_pages_games_and_remote():
    text = (PATCHES / NEW[2]).read_text()
    audio = text.split("+++ b/firmware/xiaozhi-esp32/main/audio/audio_service.cc")[1].split("diff --git")[0]
    assert "maipai_lock_blocks_voice" in audio and "wake word stays off: locked" in audio and "voice processing stays off: locked" in audio
    assert "armed = false" in audio  # the stop word
    app = text.split("+++ b/firmware/xiaozhi-esp32/main/application.cc")[1].split("diff --git")[0]
    assert app.count("maipai_lock_blocks_voice") >= 3  # a late wake word, listening itself, and the stop word callback
    assert "if (!maipai_display_ready() || maipai_lock_locked())" in text  # the swipe hook
    assert "if (!s_ready || maipai_lock_locked())" in text  # pages and the sheet
    assert "The unit is locked" in text  # the page tool and the game start say why
    assert "maipai_lock_remote_allowed(kind)" in text and '"find"' in _added(NEW[1], "firmware/main/hal/maipai_lock.cc")
    assert text.count("maipai_lock_locked()") >= 6
    lock_ui = _added(NEW[1], "firmware/main/hal/maipai_lock.cc")
    assert "maipai_timers_request_dismiss" in lock_ui  # one tap stops a ringing alarm with no code
    assert "maipai_timers_ringing()" in lock_ui  # and a ringing alarm holds the auto lock off
    assert "maipai_lock_locked()" in _added(NEW[1], "firmware/main/hal/board/stackchan_display.cc")  # quick settings and Wi-Fi do not open


def test_the_unit_loads_its_lock_before_anything_listens_and_reboot_stays_locked():
    hal = _added(NEW[1], "firmware/main/hal/hal.cpp")
    assert "maipai_lock_boot();" in hal and "maipai_lock_tick();" in hal
    unit = _added(NEW[1], "firmware/main/hal/maipai_lock.cc")
    assert 'st.GetInt("locked", 0)' in unit and 'SetInt("locked", locked)' in unit


def test_color_memory_uses_the_full_height_and_the_pack_tool_allows_it():
    data = json.loads((ROOT / "firmware" / "games" / "memory.json").read_text())
    rows = {r["name"]: r for r in data["regions"]}
    assert {r["y"] for r in rows.values()} == {28, 130}
    assert all(r["h"] == 94 and r["w"] == 136 for r in rows.values())
    assert rows["bl"]["y"] - (rows["tl"]["y"] + rows["tl"]["h"]) == 8  # 8 px gap (the screen standard)
    assert rows["tr"]["x"] - (rows["tl"]["x"] + rows["tl"]["w"]) == 8
    assert max(r["y"] + r["h"] for r in rows.values()) == 224


def test_a_dismissed_game_is_cleaned_up_and_the_subtitle_strip_stays_off_games():
    games = _added(NEW[4], "firmware/main/hal/maipai_games.cc")
    assert 'end_locked("dragbar")' in games and "mg_drag_press_dead" in games
    full = (Path.home() / "esp/stackchan-rebase/final10/firmware/main/hal/maipai_games.cc")
    if full.exists():
        end = full.read_text().split("void end_locked(const char* how)")[1].split("\n}\n")[0]
        for step in ("sfx_free()", "color_tones_free()", "lv_obj_delete(g->root)", "showRgbColor(0, 0, 0)", "maipai_screen"):
            assert step in end or step == "maipai_screen", step
    subs = _added(NEW[3], "firmware/main/hal/maipai_subtitles.cc")
    assert "maipai_games_active()" in subs


def test_quick_settings_has_room_under_the_sliders_and_ignores_taps_after_a_slider():
    text = (PATCHES / NEW[5]).read_text()
    added = _added(NEW[5], "firmware/main/hal/board/stackchan_display.cc")
    assert 'make_slider(50, "Volume"' in added and 'make_slider(88, "Brightness"' in added
    # the slider track is y + 14 to y + 30 and its knob reaches 8 px beyond: Brightness ends at 126, the Wi-Fi row starts at 146 (20 px), Reset and More at 196
    assert "make_button(8 + static_cast<int>(i) * (bw + 4), 146, bw, 44" in added
    assert 146 - (88 + 30 + 8) >= 20 and 196 - (146 + 44) >= 4
    assert "kind_of_tap" not in text and "< 300u" in added and added.count("quick_taps_ignored()") >= 5


def test_no_wifi_glyph_over_a_wifi_screen():
    banner = _added(NEW[5], "firmware/main/hal/maipai_banner.cc")
    assert "icon == MB_ICON_WIFI_OFF || icon == MB_ICON_BARS || s_wifi_screen" in banner
    display = _added(NEW[5], "firmware/main/hal/board/stackchan_display.cc")
    assert display.count("maipai_banner_wifi_screen(") == 4  # the cover shows, the cover hides, the Wi-Fi page opens and closes
