#!/usr/bin/env bash
# Intent: build the host renderer that also draws the banner row, subtitles, swipe pages, control sheet and Apps (patches N01, P12, UI16),
# into .runs/vu-screens/render, so the virtual unit can show screens other than the bare face. No firmware build; clang only.
# Usage: bash scripts/virtual-unit/build-screens.sh [firmware tree root, default ~/esp/stackchan-rebase/final15]
# Placement: host-side development tool. Upstream: none.
set -e
B="${1:-$HOME/esp/stackchan-rebase/final15}"
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
