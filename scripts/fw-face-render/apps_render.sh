#!/usr/bin/env bash
# Intent: draw the Apps wall, the games wall, the Timers and Alarms apps and the tabbed Settings screen with the real LVGL and the unit's own drawing
# and touch code (maipai_apps.cc) on this Mac, with a scripted finger on the real input path, so they can be judged and checked without flashing the unit
# (patch UI16). Usage: bash scripts/fw-face-render/apps_render.sh <firmware tree root, the folder that holds firmware/> <out dir>
# Needs a renderer build dir with lvgl.a (bash scripts/fw-face-render/build.sh makes one; the tree's hostrender/pg is the usual place).
# Placement: Mac that holds a firmware tree (development only). Upstream: none.
set -e
T="${1:?the firmware tree root (the folder that holds firmware/)}"
OUT="${2:?an output folder}"
R="$(cd "$(dirname "$0")" && pwd)"
FW="$T/firmware"
PG="${MAIPAI_PG_DIR:-$T/hostrender/pg}"
L="$FW/managed_components/lvgl__lvgl"
mkdir -p "$OUT"
[ -f "$PG/lvgl.a" ] || { echo "no $PG/lvgl.a: run bash scripts/fw-face-render/build.sh first (MAIPAI_FW_TREE=$FW)" >&2; exit 1; }
clang++ -std=gnu++20 -O1 -w -I"$PG/inc" -I"$L" -I"$L/src" -I"$R/stub" -I"$FW/main/hal" -I"$FW/main" -DESP_PLATFORM=1 -DLV_CONF_SKIP=1 -DMAIPAI_HOST_RENDER=1 \
  "$R/apps_render.cc" "$FW/main/hal/maipai_apps.cc" "$PG/lvgl.a" -o "$OUT/apps_render" -lz
S="$OUT/scene_apps.txt"
python3 "$R/scene_apps.py" "$OUT" > "$S"
"$OUT/apps_render" < "$S" | tee "$OUT/apps_render.log"
