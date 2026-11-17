#!/usr/bin/env bash
# Intent: draw the lock screen and the keypad with the real LVGL and the unit's own drawing code (maipai_lock_draw.h) on this Mac, so they can be judged
# without flashing the unit (patch LK02). Usage: bash scripts/fw-face-render/lock_render.sh <firmware tree root, the folder that holds firmware/> <out dir>
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
clang++ -std=gnu++20 -O1 -w -I"$PG/inc" -I"$L" -I"$L/src" -I"$R/stub" -I"$FW/main/hal" -DESP_PLATFORM=1 -DLV_CONF_SKIP=1 "$R/lock_render.cc" "$PG/lvgl.a" -o "$OUT/lock_render" -lz
cat > "$OUT/scene_lock.txt" <<SCENE
banner on
lock $OUT/lock_screen.png
pad 0 0 $OUT/keypad_empty.png
pad 3 0 $OUT/keypad_three.png
pad 6 1 $OUT/keypad_wrong.png
lang es
pad 0 1 $OUT/keypad_es_wrong.png
SCENE
"$OUT/lock_render" < "$OUT/scene_lock.txt"
