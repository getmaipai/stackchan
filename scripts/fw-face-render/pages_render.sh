#!/usr/bin/env bash
# Intent: rebuild the host renderer with the swipe pages and the control sheet (patch P12) and write every page and the sheet as PNGs.
# Usage: MAIPAI_PG_TREE=<firmware tree root, default ~/esp/stackchan-rebase/pages> bash pages_render.sh [OUTDIR]
# Placement: Mac that holds a firmware tree (development only). Upstream: none.
set -e
B="${MAIPAI_PG_TREE:-$HOME/esp/stackchan-rebase/pages}"
R="$(cd "$(dirname "$0")" && pwd)"
export MAIPAI_FW_TREE=$B/firmware MAIPAI_RENDER_SRC=$R/render.cc MAIPAI_RENDER_HOOKS=$R/hooks_banner.cc
export MAIPAI_RENDER_EXTRA="$B/firmware/main/hal/maipai_banner.cc $B/firmware/main/hal/maipai_subtitles.cc $B/firmware/main/hal/maipai_pages.cc"
export MAIPAI_RENDER_DEFS="-DBUILTIN_TEXT_FONT=font_noto_sans_basic_20_4 -DMAIPAI_PAGES_RENDER=1" MAIPAI_RENDER_CFILES="$B/firmware/managed_components/78__xiaozhi-fonts/src/font_noto_sans_basic_20_4.c"
OUT="${1:-$B/hostrender/out/pages}"
mkdir -p "$OUT" "$B/hostrender/pg"
bash "$R/build.sh" "$B/hostrender/pg"
python3 "$R/scene_pages.py" "$OUT"
cd "$OUT" && for s in scene_*.txt; do "$B/hostrender/pg/render" < "$s"; done
