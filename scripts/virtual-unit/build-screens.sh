#!/usr/bin/env bash
# Intent: build the host renderer that also draws the banner row, subtitles, swipe pages, control sheet and Apps (patches N01, P12, UI16),
# into .runs/vu-screens/render, so the virtual unit can show screens other than the bare face. No firmware build; clang only.
# Usage: bash scripts/virtual-unit/build-screens.sh [firmware tree root, default the overlay tree from build-face.sh]
# Placement: host-side development tool. Upstream: none.
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# default: the overlay tree build-face.sh makes (the tree plus the UX patches); the goldens are drawn from it
B="${1:-$ROOT/.runs/fixtree}"
[ -d "$B/firmware" ] || { echo "no overlay tree: run bash scripts/virtual-unit/build-face.sh first (or pass a firmware tree root)"; exit 1; }
R="$(cd "$(dirname "$0")/../fw-face-render" && pwd)"
OUT="$(cd "$(dirname "$0")/../.." && pwd)/.runs/vu-screens"
export MAIPAI_FW_TREE=$B/firmware MAIPAI_RENDER_SRC=$R/render.cc MAIPAI_RENDER_HOOKS=$R/hooks_banner.cc
mkdir -p "$OUT/more"; sed 's|#include "hal.h"|// hal.h left out in the host build|' "$B/firmware/main/hal/maipai_more.cc" > "$OUT/more/maipai_more.cc"   # the whole HAL header is not needed by the More screen
export MAIPAI_RENDER_EXTRA="$OUT/more/maipai_more.cc $R/more_host.cc $B/firmware/main/hal/maipai_banner.cc $B/firmware/main/hal/maipai_subtitles.cc $B/firmware/main/hal/maipai_pages.cc $B/firmware/main/hal/maipai_apps.cc $( [ -f "$B/firmware/main/hal/maipai_firstrun.cc" ] && echo "$B/firmware/main/hal/maipai_firstrun.cc" )"
export MAIPAI_RENDER_DEFS="-DBUILTIN_TEXT_FONT=font_noto_sans_basic_20_4 -DMAIPAI_PAGES_RENDER=1"
export MAIPAI_RENDER_CFILES="$B/firmware/managed_components/78__xiaozhi-fonts/src/font_noto_sans_basic_20_4.c $B/firmware/managed_components/78__xiaozhi-fonts/src/font_noto_sans_basic_16_4.c"
[ -d "$OUT" ] || mkdir -p "$OUT"
# the LVGL archive is the same as the face build's: reuse it when there
[ -f "$OUT/lvgl.a" ] || { [ -f "$(dirname "$OUT")/vu-build/lvgl.a" ] && mkdir -p "$OUT/obj" && cp "$(dirname "$OUT")/vu-build/lvgl.a" "$OUT/lvgl.a" && cp -R "$(dirname "$OUT")/vu-build/inc" "$OUT/inc"; } || true
bash "$R/build.sh" "$OUT"
# the passcode lock screen and keypad are drawn by their own small program (patch LK02)
mkdir -p "$OUT/lock"
L="$B/firmware/managed_components/lvgl__lvgl"
clang++ -std=gnu++20 -O1 -ffp-contract=off -w -I"$OUT/inc" -I"$L" -I"$L/src" -I"$R/stub" -I"$B/firmware/main/hal" -DESP_PLATFORM=1 -DLV_CONF_SKIP=1 "$R/lock_render.cc" "$OUT/lvgl.a" -o "$OUT/lock/lock_render" -lz
echo "built $OUT/lock/lock_render"
# the link covers (Wi-Fi connecting, Wi-Fi setup, waiting for approval): the unit's own code, cut out of stackchan_display.cc
mkdir -p "$OUT/cover"
python3 "$(dirname "$0")/cover_gen.py" "$B" "$OUT/cover"
clang++ -std=gnu++20 -O1 -ffp-contract=off -w -I"$OUT/inc" -I"$OUT/cover" -I"$B/firmware/main" -I"$L" -I"$L/src" -I"$R/stub" -DESP_PLATFORM=1 -DLV_CONF_SKIP=1 "$(dirname "$0")/cover_render.cc" "$OUT/obj/font_noto_sans_basic_20_4.c.o" "$OUT/lvgl.a" -o "$OUT/cover/cover_render" -lz
echo "built $OUT/cover/cover_render"
# the grid games in play (Four in a Row, Memory Match, Hangman, Mine Finder): the unit's own drawing code cut out of maipai_grid.cc (grid_gen.py)
mkdir -p "$OUT/grid"
python3 "$(dirname "$0")/grid_gen.py" "$B" "$OUT/grid"
clang++ -std=gnu++20 -O1 -ffp-contract=off -w -I"$OUT/inc" -I"$OUT/grid" -I"$L" -I"$L/src" -I"$R/stub" -I"$B/firmware/main/hal" -DESP_PLATFORM=1 -DLV_CONF_SKIP=1 $(grep -q MGO_TIMEUP "$B/firmware/main/hal/maipai_game_over_core.h" && echo -DHAVE_MGO_NEUTRAL) $(grep -q build_lang "$B/firmware/main/hal/maipai_game_over.h" && echo -DHAVE_MGO_LOOK) $(grep -q "int s_look" "$B/firmware/main/hal/maipai_grid.cc" && echo -DHAVE_LOOK) $(grep -q "pg_dirty" "$B/firmware/main/hal/maipai_pong_core.h" 2>/dev/null && echo -DPG_DIRTY_API) $(grep -q "fl_dirty" "$B/firmware/main/hal/maipai_flyer_core.h" 2>/dev/null && echo -DFL_DIRTY_API) "$R/grid_render.cc" "$OUT/lvgl.a" -o "$OUT/grid/grid_render" -lz
echo "built $OUT/grid/grid_render"
# the data-pack games' renderer (games_render.cc): used by games_audit.py to list every pack's touch regions
mkdir -p "$OUT/games"
clang++ -std=gnu++20 -O1 -ffp-contract=off -w -I"$OUT/inc" -I"$L" -I"$L/src" -I"$R/stub" -I"$B/firmware/main/hal" -DESP_PLATFORM=1 -DLV_CONF_SKIP=1 $(grep -q "struct Scene" "$B/firmware/main/hal/maipai_games_draw.h" && echo -DMGD_SCENE=1) "$R/games_render.cc" "$OUT/lvgl.a" -o "$OUT/games/games_render" -lz
echo "built $OUT/games/games_render"
