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
export MAIPAI_RENDER_EXTRA="$B/firmware/main/hal/maipai_banner.cc $B/firmware/main/hal/maipai_subtitles.cc $B/firmware/main/hal/maipai_pages.cc $B/firmware/main/hal/maipai_apps.cc"
export MAIPAI_RENDER_DEFS="-DBUILTIN_TEXT_FONT=font_noto_sans_basic_20_4 -DMAIPAI_PAGES_RENDER=1"
export MAIPAI_RENDER_CFILES="$B/firmware/managed_components/78__xiaozhi-fonts/src/font_noto_sans_basic_20_4.c"
[ -d "$OUT" ] || mkdir -p "$OUT"
# the LVGL archive is the same as the face build's: reuse it when there
[ -f "$OUT/lvgl.a" ] || { [ -f "$(dirname "$OUT")/vu-build/lvgl.a" ] && mkdir -p "$OUT/obj" && cp "$(dirname "$OUT")/vu-build/lvgl.a" "$OUT/lvgl.a" && cp -R "$(dirname "$OUT")/vu-build/inc" "$OUT/inc"; } || true
bash "$R/build.sh" "$OUT"
# the passcode lock screen and keypad are drawn by their own small program (patch LK02)
mkdir -p "$OUT/lock"
L="$B/firmware/managed_components/lvgl__lvgl"
clang++ -std=gnu++20 -O1 -w -I"$OUT/inc" -I"$L" -I"$L/src" -I"$R/stub" -I"$B/firmware/main/hal" -DESP_PLATFORM=1 -DLV_CONF_SKIP=1 "$R/lock_render.cc" "$OUT/lvgl.a" -o "$OUT/lock/lock_render" -lz
echo "built $OUT/lock/lock_render"
# the link covers (Wi-Fi connecting, Wi-Fi setup, waiting for approval): the unit's own code, cut out of stackchan_display.cc
mkdir -p "$OUT/cover"
python3 "$(dirname "$0")/cover_gen.py" "$B" "$OUT/cover"
clang++ -std=gnu++20 -O1 -w -I"$OUT/inc" -I"$OUT/cover" -I"$L" -I"$L/src" -I"$R/stub" -DESP_PLATFORM=1 -DLV_CONF_SKIP=1 "$(dirname "$0")/cover_render.cc" "$OUT/obj/font_noto_sans_basic_20_4.c.o" "$OUT/lvgl.a" -o "$OUT/cover/cover_render" -lz
echo "built $OUT/cover/cover_render"
