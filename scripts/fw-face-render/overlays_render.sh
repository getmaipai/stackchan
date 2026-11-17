#!/usr/bin/env bash
# Intent: rebuild the host renderer with the overlay engine, the banner row and the subtitle strip, and write every overlay sheet (patch O01).
# Usage: MAIPAI_OV_TREE=<firmware tree root, default ~/esp/stackchan-rebase/overlays> bash overlays_render.sh [OUTDIR]
# Placement: Mac that holds a firmware tree (development only). Upstream: none.
set -e
B="${MAIPAI_OV_TREE:-$HOME/esp/stackchan-rebase/overlays}"
R="$(cd "$(dirname "$0")" && pwd)"
export MAIPAI_FW_TREE=$B/firmware MAIPAI_RENDER_SRC=$R/render_ov.cc MAIPAI_RENDER_HOOKS=$R/hooks_banner.cc MAIPAI_RENDER_EXTRA="$B/firmware/main/hal/maipai_banner.cc $B/firmware/main/hal/maipai_subtitles.cc"
export MAIPAI_RENDER_DEFS="-DBUILTIN_TEXT_FONT=font_noto_sans_basic_20_4" MAIPAI_RENDER_CFILES="$B/firmware/managed_components/78__xiaozhi-fonts/src/font_noto_sans_basic_20_4.c"
OUT="${1:-$B/hostrender/out/overlays}"
mkdir -p "$OUT" "$B/hostrender/ov"
bash "$R/build.sh" "$B/hostrender/ov"
python3 "$R/scene_overlays.py" "$OUT"
cd "$OUT" && for s in scene_*.txt; do "$B/hostrender/ov/render" < "$s"; done
