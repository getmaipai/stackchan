# ruff: noqa: E501
"""The Apps wall, the Timers and Alarms apps and the tabbed Settings screen (firmware patches UI16 and UI17): the patches are on ORDER after the
games and lock patches with their header lines, the pure core passes its C test against the header as the whole ORDER leaves it, the Python
tables below agree with the core's (apps, tabs, words in English and Spanish, paging, the time picker, the scroll bar), the screens keep the
owner's rules (one row of six tiles, no Lock tile, nothing at rest, one overlay screen at a time), and, where a renderer build exists, the
real input path is driven on the real LVGL."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATCHES = ROOT / "firmware" / "patches"
NAMES = [
    "UI16-apps-core-layout-words-and-sheet-tile.patch",
    "UI17-apps-wall-timers-alarms-and-tabbed-settings.patch",
]

# the tables the core must agree with (the owner's list, in the owner's order)
APPS = ["timers", "alarms", "clock", "quick", "pictures", "dashboard", "dance", "lock"]
APP_TITLE_EN = ["Timers", "Alarms", "Clock", "Quick actions", "Pictures", "Dashboard", "Dance", "Lock"]
TABS = ["general", "network", "faces", "info"]
PRESET_MIN = [1, 5, 10, 15]
AUTO_MIN = [0, 1, 5, 15, 30, 60]
WALL_PER_PAGE = 4


def _patch_text(name: str) -> str:
    return (PATCHES / name).read_text()


def _added(name: str, path: str) -> str:
    text = _patch_text(name)
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    lines = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


def _all_patch_text() -> str:
    return "\n".join(_patch_text(n) for n in NAMES)


def test_the_patches_are_on_order_after_the_games_and_lock_patches_with_header_lines_and_no_em_dash():
    order = [n for n in (PATCHES / "ORDER").read_text().split() if not n.startswith("#")]
    positions = [order.index(n) for n in NAMES]
    assert positions == sorted(positions) and positions[0] > order.index("GM03-game-effects-normalized-to-chime-loudness.patch")
    assert positions[1] == positions[0] + 1
    for name in NAMES:
        text = _patch_text(name)
        head = text.split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash"):
            assert key in head, (name, key)
        assert chr(8212) not in text, name


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_the_core_test_passes_against_the_cores_the_whole_order_leaves(tmp_path, tmp_path_factory):
    hal = cores_dir(tmp_path_factory)
    binary = tmp_path / "t"
    build = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{hal}", str(HERE / "firmware" / "apps_core_test.c"), "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0 and "passed" in run.stdout, run.stdout + run.stderr


def _core() -> str:
    return _added(NAMES[0], "firmware/main/hal/maipai_apps_core.h")


def test_the_apps_tabs_and_presets_in_the_core_match_the_tables_here():
    core = _core()
    names = re.search(r"MAC_APP_NAMES\[MAC_APP_COUNT\] = \{([^}]*)\}", core).group(1)
    assert re.findall(r'"([^"]+)"', names) == APPS
    titles = re.search(r"MAC_APP_TITLE\[2\]\[MAC_APP_COUNT\] = \{\s*\{([^}]*)\},\s*\{([^}]*)\}", core)
    en, es = (re.findall(r'"([^"]+)"', titles.group(i)) for i in (1, 2))
    assert en == APP_TITLE_EN and len(es) == len(APPS)
    tabs = re.search(r"MAC_TAB_NAMES\[MAC_TAB_COUNT\] = \{([^}]*)\}", core).group(1)
    assert re.findall(r'"([^"]+)"', tabs) == TABS
    assert [int(v) for v in re.search(r"MAC_PRESET_MIN\[MAC_PRESETS\] = \{([^}]*)\}", core).group(1).split(",")] == PRESET_MIN
    assert [int(v) for v in re.search(r"MAC_AUTO_MIN\[MAC_AUTO_COUNT\] = \{([^}]*)\}", core).group(1).split(",")] == AUTO_MIN


def test_every_word_has_an_english_and_a_spanish_form_in_plain_ascii():
    core = _core()
    block = re.search(r"MAC_STR\[MAC_S_COUNT\]\[2\] = \{(.*?)\n\};", core, re.S).group(1)
    pairs = re.findall(r'\{"([^"]*)", "([^"]*)"\}', block)
    enum = re.search(r"enum \{\s*MAC_S_APPS = 0,(.*?)MAC_S_COUNT\s*\};", core, re.S).group(1)
    ids = [w for w in re.findall(r"MAC_S_[A-Z_0-9]+", enum)]
    assert len(pairs) == len(ids) + 1, (len(pairs), len(ids))  # the first id is written as "MAC_S_APPS = 0"
    for en, es in pairs:
        assert en and es and en.isascii() and es.isascii() and len(en) < 64 and len(es) < 64
    assert ("Cancel", "Cancelar") in pairs and ("Save", "Guardar") in pairs and ("Add alarm", "Agregar alarma") in pairs
    assert chr(8212) not in block
    # the other four languages read the English words: the unit asks only for Spanish
    assert "spanish()" in _added(NAMES[1], "firmware/main/hal/maipai_apps.cc")


# ---- a model of the core in Python, checked against the C code on a grid ----
def wall_pages(total: int) -> int:
    return 1 if total <= 0 else (total + WALL_PER_PAGE - 1) // WALL_PER_PAGE


def wall_count(page: int, total: int) -> int:
    left = total - page * WALL_PER_PAGE
    return 0 if left <= 0 else min(left, WALL_PER_PAGE)


def wall_clamp(page: int, total: int) -> int:
    return max(0, min(page, wall_pages(total) - 1))


def pick_hour(h: int, d: int) -> int:
    return (h + 24 + (-1 if d < 0 else 1)) % 24


def pick_minute(m: int, d: int) -> int:
    return (m + 60 + (-1 if d < 0 else 1)) % 60


def shown_hour(h: int, c24: int) -> int:
    return h if c24 else (12 if h % 12 == 0 else h % 12)


def set_pm(h: int, pm: int) -> int:
    return h % 12 + (12 if pm else 0)


def scroll_bar(content: int, view: int, scroll: int) -> tuple[int, int] | None:
    if content <= view or view <= 0:
        return None
    h = max(16, view * view // content)
    travel, mx = view - h, content - view
    s = max(0, min(scroll, mx))
    return (s * travel // mx if mx > 0 else 0), h


DRIVER = r"""
#include <stdio.h>
#include "maipai_apps_core.h"
int main(void)
{
    for (int total = 0; total <= 17; total++) {
        printf("wall %d %d", total, mac_wall_pages(total));
        for (int p = -1; p <= 5; p++) printf(" %d:%d", mac_wall_count(p < 0 ? 0 : p, total), mac_wall_clamp(p, total));
        printf("\n");
    }
    for (int h = 0; h < 24; h++) {
        mac_pick_t p; p.hour = (uint8_t)h; p.minute = 0;
        printf("hour %d", h);
        mac_pick_hour(&p, 1); printf(" %d", p.hour);
        p.hour = (uint8_t)h; mac_pick_hour(&p, -1); printf(" %d", p.hour);
        p.hour = (uint8_t)h; printf(" %d %d", mac_pick_shown_hour(&p, 0), mac_pick_shown_hour(&p, 1));
        mac_pick_set_pm(&p, 0); printf(" %d", p.hour);
        p.hour = (uint8_t)h; mac_pick_set_pm(&p, 1); printf(" %d\n", p.hour);
    }
    for (int m = 0; m < 60; m++) {
        mac_pick_t p; p.hour = 5; p.minute = (uint8_t)m;
        mac_pick_minute(&p, 1); const int up = p.minute;
        p.minute = (uint8_t)m; mac_pick_minute(&p, -1);
        printf("minute %d %d %d\n", m, up, p.minute);
    }
    const int contents[] = {100, 138, 139, 276, 480, 5000};
    for (unsigned c = 0; c < sizeof(contents) / sizeof(contents[0]); c++)
        for (int s = -10; s <= 600; s += 37) {
            int by = -1, bh = -1;
            const int r = mac_scroll_bar(contents[c], 138, s, &by, &bh);
            printf("bar %d %d %d %d %d\n", contents[c], s, r, r ? by : -1, r ? bh : -1);
        }
    return 0;
}
"""


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_the_paging_the_picker_and_the_scroll_bar_match_the_python_model(tmp_path, tmp_path_factory):
    hal = cores_dir(tmp_path_factory)
    src = tmp_path / "driver.c"
    src.write_text(DRIVER)
    binary = tmp_path / "driver"
    build = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{hal}", str(src), "-o", str(binary)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    out = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60).stdout.splitlines()
    expect: list[str] = []
    for total in range(0, 18):
        cells = " ".join(f"{wall_count(max(p, 0), total)}:{wall_clamp(p, total)}" for p in range(-1, 6))
        expect.append(f"wall {total} {wall_pages(total)} {cells}")
    for h in range(24):
        expect.append(f"hour {h} {pick_hour(h, 1)} {pick_hour(h, -1)} {shown_hour(h, 0)} {shown_hour(h, 1)} {set_pm(h, 0)} {set_pm(h, 1)}")
    for m in range(60):
        expect.append(f"minute {m} {pick_minute(m, 1)} {pick_minute(m, -1)}")
    for c in (100, 138, 139, 276, 480, 5000):
        for s in range(-10, 601, 37):
            bar = scroll_bar(c, 138, s)
            expect.append(f"bar {c} {s} {1 if bar else 0} {bar[0] if bar else -1} {bar[1] if bar else -1}")
    assert out == expect


def test_the_sheet_stays_one_row_of_six_tiles_with_no_lock_tile_and_the_apps_tile_keeps_its_saved_key():
    core = _patch_text(NAMES[0])
    assert '"Apps", "Games", "Wi-Fi"' in core and '"Apps", "Juegos", "Wi-Fi"' in core
    assert 'MPG_SHEET_ALIAS_APPS "apps"' in core and "return MPG_S_TIMERS;" in core   # the key "timers" keeps working, "apps" reads the same
    assert "MPG_S_LOCK" not in core                                                     # no Lock tile on the sheet
    wiring = _patch_text(NAMES[1])
    assert "maipai_apps_show(item == MPG_S_TIMERS ? MAV_APPS : MAV_GAMES)" in wiring    # Apps and Games tiles open the walls
    assert "maipai_apps_show(MAV_SETTINGS)" in wiring                                   # the gear opens the tabbed settings


def test_nothing_exists_at_rest_and_one_overlay_screen_at_a_time():
    cc = _added(NAMES[1], "firmware/main/hal/maipai_apps.cc")
    assert cc.count("lv_timer_create(") == 1 and cc.index("lv_timer_create(") > cc.index("bool maipai_apps_show(")   # the 250 ms timer starts with a view
    assert "xTaskCreate" not in cc and "std::thread" not in cc and "std::string" not in cc and "std::vector" not in cc
    assert "maipai_screen_open(id);" in cc and "maipai_screen_register(MSCR_APPS, close_all);" in cc and "maipai_screen_closed(id);" in cc
    assert "delete S;" in cc and "lv_obj_delete_async(S->root)" in cc                                              # closing frees the state and the objects
    assert "maipai_lock_locked()" in cc                                                                              # no screen while locked (patch LK03)
    core = _core()
    assert "MSCR_APPS" in _patch_text(NAMES[0])
    assert "(patch UI16)" in core or "patch UI16" in core


def test_the_countdown_button_is_a_reserved_off_hook_and_the_lock_app_reuses_the_lock_hooks():
    assert "#define MAC_COUNTDOWN_READY 0" in _core()
    cc = _added(NAMES[1], "firmware/main/hal/maipai_apps.cc")
    assert "countdown_open(" in cc and "MAC_COUNTDOWN_READY != 0" in cc
    wiring = _patch_text(NAMES[1])
    assert 'maipai_lock_now("apps")' in wiring and "maipai_lock_has_code()" in wiring
    assert "MAC_S_LOCK_HINT" in cc and "lock_has_code()" in cc                          # no code set: the hint, never a keypad


def test_the_internal_ram_cost_at_rest_is_a_few_words():
    cc = _added(NAMES[1], "firmware/main/hal/maipai_apps.cc")
    # every static at file scope: pointers, flags and three atomics; the big state is one heap record made when a view opens
    statics = re.findall(r"^(?:std::atomic<[a-z]+> g_\w+\{[^}]*\};|[A-Za-z_:<>\* ]+ g_\w+\s*=\s*[^;]+;|St\* S\s*=\s*nullptr;|lv_timer_t\* g_timer\s*=\s*nullptr;)", cc, re.M)
    assert 4 <= len(statics) <= 16, statics
    assert "static char" not in cc and "static uint8_t" not in cc


@pytest.mark.skipif(shutil.which("python3") is None, reason="python3 missing")
def test_the_psram_stack_lint_stays_clean_on_a_tree_that_has_the_patch_when_one_is_given():
    tree = os.environ.get("MAIPAI_UI_TREE", "")
    if not tree or not Path(tree, "firmware", "main", "hal", "maipai_apps.cc").exists():
        pytest.skip("set MAIPAI_UI_TREE to a patched tree root to run the lint")
    run = subprocess.run(["python3", str(ROOT / "scripts" / "psram-stack-lint.py"), "--tree", str(Path(tree, "firmware"))], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr


@pytest.mark.skipif(shutil.which("clang++") is None, reason="needs clang++")
def test_the_real_input_path_on_the_real_lvgl_when_a_renderer_build_is_given(tmp_path):
    tree = os.environ.get("MAIPAI_UI_TREE", "")
    if not tree or not Path(tree, "hostrender", "pg", "lvgl.a").exists() or not Path(tree, "firmware", "main", "hal", "maipai_apps.cc").exists():
        pytest.skip("set MAIPAI_UI_TREE to a patched firmware tree root with hostrender/pg/lvgl.a")
    run = subprocess.run(["bash", str(ROOT / "scripts" / "fw-face-render" / "apps_render.sh"), tree, str(tmp_path)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr[-2000:]
    for shot in ("apps_page1", "apps_page2", "games_page2", "timers_0", "timers_3", "alarms_3", "alarm_picker_12h", "settings_general", "settings_faces"):
        assert (tmp_path / f"{shot}.png").stat().st_size > 1000, shot
    script = tmp_path / "touch.txt"
    script.write_text(
        "games 8\nlockcode off\nclearall\nshow apps\ntap 90 70\ntap 100 60\nstate\ntap 265 108\nstate\nswipe 160 32 160 120 300\nstate\n"
        "show apps\nswipe 250 120 80 120 200\ntap 230 160\nstate\nshow apps\ntap 230 160\nstate\nshow games\ntap 90 70\nstate\n"
    )
    out = subprocess.run([str(tmp_path / "apps_render")], input=script.read_text(), capture_output=True, text=True, timeout=120).stdout
    states = [line for line in out.splitlines() if line.startswith("state")]
    assert states[0].endswith("log timer300;") and "open 1" in states[0]       # the Timers tile opened Timers and the 5 minute preset started one
    assert states[1].endswith("log cancel;")                                   # the big Cancel
    assert "open 0" in states[2]                                               # a swipe down from the drag strip dismissed the screen
    assert states[3].endswith("log ") and "open 1" in states[3]                # the Lock tile with no code set only shows the hint
    assert states[4].endswith("log strip3;") and "open 0" in states[4]         # Quick actions opened the strip page
    assert states[5].endswith("log game0;") and "open 0" in states[5]          # a game tile started the game
