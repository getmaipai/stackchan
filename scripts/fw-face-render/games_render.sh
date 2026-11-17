#!/usr/bin/env bash
# Intent: draw every game screen with the real LVGL and the unit's own drawing code (maipai_games_draw.h), so a look can be judged and checked without
# flashing the unit (patch UI13). Usage: bash scripts/fw-face-render/games_render.sh <firmware tree root, the folder that holds firmware/> <out dir>
# Needs a renderer build dir with lvgl.a (bash scripts/fw-face-render/build.sh makes one; the tree's hostrender/pg is the usual place).
# Placement: Mac that holds a firmware tree (development only). Upstream: none.
set -e
T="${1:?the firmware tree root (the folder that holds firmware/)}"
OUT="${2:?an output folder}"
R="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$R/../.." && pwd)"
FW="$T/firmware"
PG="${MAIPAI_PG_DIR:-$T/hostrender/pg}"
L="$FW/managed_components/lvgl__lvgl"
mkdir -p "$OUT"
[ -f "$PG/lvgl.a" ] || { echo "no $PG/lvgl.a: run bash scripts/fw-face-render/build.sh first (MAIPAI_FW_TREE=$FW)" >&2; exit 1; }
clang++ -std=gnu++20 -O1 -w -I"$PG/inc" -I"$L" -I"$L/src" -I"$R/stub" -I"$FW/main/hal" -DESP_PLATFORM=1 -DLV_CONF_SKIP=1 "$R/games_render.cc" "$PG/lvgl.a" -o "$OUT/games_render" -lz
python3 "$R/scene_games.py" "${MAIPAI_GAMES_DIR:-$REPO/firmware/games}" "$OUT" > "$OUT/scene_games.txt"
"$OUT/games_render" < "$OUT/scene_games.txt"
