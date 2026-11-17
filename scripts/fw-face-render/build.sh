#!/usr/bin/env bash
# Intent: draw the real face (LVGL and the unit's own face classes) into memory on this Mac, so a look can be judged and tested
# without flashing the unit. render < script.txt writes PNGs (commands: style, emotion, speak, advance, snap, tile, sheet, count).
# MAIPAI_RENDER_SRC=<render_fx.cc> builds the version that also draws overlays, screen effects and the speech bubble (patches TA01 to TA04).
# Usage: MAIPAI_FW_TREE=<a built firmware tree: its firmware/ folder with managed_components and build-bench/config> bash build.sh [OUTDIR]
# Placement: Mac that holds a firmware tree (development only). Upstream: none.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
FW="${MAIPAI_FW_TREE:?set MAIPAI_FW_TREE to the firmware folder of a built tree, for example ~/esp/stackchan-rebase/faces/firmware}"
OUT="${1:-$HERE/build}"
mkdir -p "$OUT/obj/lv" "$OUT/inc"
cp "$FW/build-bench/config/sdkconfig.h" "$OUT/inc/sdkconfig.h" 2>/dev/null || cp "$FW/build/config/sdkconfig.h" "$OUT/inc/sdkconfig.h"
L="$FW/managed_components/lvgl__lvgl"
S="$FW/main/stackchan/avatar/skins/default"; H="$FW/main/hal"
U="$FW/components/smooth_ui_toolkit/src"
CFLAGS=(-O1 -w -I"$OUT/inc" -I"$HERE/stub" -I"$L" -I"$L/src" -DESP_PLATFORM=1 -DLV_CONF_SKIP=1)
if [ ! -f "$OUT/lvgl.a" ]; then
  OBJS=()
  while IFS= read -r f; do
    o="$OUT/obj/lv/$(echo "${f#$L/}" | tr '/' '_').o"
    [ -f "$o" ] || nice -n 15 clang "${CFLAGS[@]}" -c "$f" -o "$o"
    OBJS+=("$o")
  done < <(find "$L/src" -name '*.c')
  rm -f "$OUT/lvgl.a"; ar rcs "$OUT/lvgl.a" "${OBJS[@]}"
fi
CXXFLAGS=(-std=gnu++20 -O1 -w -I"$OUT/inc" -I"$HERE" -I"$HERE/stub" -I"$L" -I"$L/src" -DESP_PLATFORM=1 -DLV_CONF_SKIP=1 -I"$U" -I"$U/lvgl" -I"$U/.." -I"$FW/main" -I"$H")
OBJS=()
for f in "${MAIPAI_RENDER_SRC:-$HERE/render.cc}" "$HERE/hooks_new.cc" "$S/eyes.cpp" "$S/mouth.cpp" "$S/default.cpp" "$S/speech_bubble.cpp" "$H/maipai_facefx.cc"; do
  o="$OUT/obj/$(basename "$f").o"; nice -n 15 clang++ "${CXXFLAGS[@]}" -c "$f" -o "$o"; OBJS+=("$o")
done
o="$OUT/obj/arrow.o"; nice -n 15 clang "${CFLAGS[@]}" -c "$S/assets/default_bubble_arrow.c" -o "$o"; OBJS+=("$o")
nice -n 15 clang++ "${OBJS[@]}" "$OUT/lvgl.a" -o "$OUT/render" -lz
echo "built $OUT/render"
