#!/usr/bin/env bash
# Intent: build the virtual robot's browser pieces with Emscripten: the face (Spike A: the unit's real LVGL face code) and the C cores (Spike B).
# Output goes to scripts/virtual-unit/wasm/build/ (ignored by git); index.html loads it from there.
# Needs: emcc on PATH (source an emsdk, tested with 3.1.74), git, python3. Network only for the first run: the firmware tree replay and LVGL.
# Usage: bash scripts/virtual-unit/wasm/build.sh [face|cores|all]   (default all)
#   WASM_WORK   work folder for the replayed tree and fetched sources (default .runs/wasm)
#   MAIPAI_FW_TREE  an existing replayed tree root (default: replay into $WASM_WORK/fwtree with scripts/fw-rebuild.sh)
# Placement: host-side development tool. Upstream: none.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
WORK="${WASM_WORK:-$ROOT/.runs/wasm}"
OUT="$HERE/build"
WHAT="${1:-all}"
command -v emcc >/dev/null || { echo "emcc is not on PATH. Install Emscripten (git clone https://github.com/emscripten-core/emsdk, ./emsdk install 3.1.74, ./emsdk activate 3.1.74), source emsdk_env.sh, run this again."; exit 1; }
mkdir -p "$WORK" "$OUT"
now() { date +%s.%N; }

fetch_tree() {
  TREE="${MAIPAI_FW_TREE:-$WORK/fwtree}"
  if [ ! -d "$TREE/firmware/main/hal" ]; then
    # The replay applies every patch; its own final ESP-IDF build fails without IDF, which is expected here (the tree is complete before that step).
    rm -rf "$TREE"
    bash "$ROOT/scripts/fw-rebuild.sh" "$TREE" > "$WORK/fw-rebuild.log" 2>&1 || true
    [ -d "$TREE/firmware/main/hal" ] || { echo "firmware replay failed: read $WORK/fw-rebuild.log, fix the network or the patch order, run again."; exit 1; }
  fi
  FW="$TREE/firmware"
  # Sources the IDF component manager would fetch (its registry is not needed): LVGL at the pinned tag and the font package.
  [ -d "$WORK/lvgl" ] || git clone -q --depth 1 --branch v9.5.0 https://github.com/lvgl/lvgl "$WORK/lvgl"
  [ -d "$WORK/fonts" ] || git clone -q --depth 1 https://github.com/78/xiaozhi-fonts "$WORK/fonts"
}

# sdkconfig.h from the firmware's own defaults files (only the CONFIG_LV_* and font lines matter to the face).
make_sdkconfig() {
  mkdir -p "$WORK/inc"
  cat "$FW/sdkconfig.defaults" "$FW/sdkconfig.bench.defaults" | python3 -I -c '
import sys
out = {}
for line in sys.stdin:
    line = line.strip()
    if not line.startswith("CONFIG_") or "=" not in line: continue
    k, v = line.split("=", 1)
    if v == "n": out.pop(k, None); continue
    out[k] = "1" if v == "y" else v
print("#pragma once")
for k, v in out.items(): print("#define %s %s" % (k, v))
' > "$WORK/inc/sdkconfig.h"
}

build_face() {
  local t0 t1 t2
  t0=$(now)
  fetch_tree; make_sdkconfig
  local L="$WORK/lvgl" R="$ROOT/scripts/fw-face-render" S="$FW/main/stackchan/avatar/skins/default" H="$FW/main/hal" U="$FW/components/smooth_ui_toolkit/src"
  local CF=(-O2 -w -I"$WORK/inc" -I"$R/stub" -I"$L" -I"$L/src" -DESP_PLATFORM=1 -DLV_CONF_SKIP=1)
  mkdir -p "$WORK/obj/lv"
  # LVGL objects, built once and kept; parallel.
  export WORK L; export -f 2>/dev/null || true
  find "$L/src" -name '*.c' | while read -r f; do
    o="$WORK/obj/lv/$(echo "${f#$L/}" | tr '/' '_').o"
    [ -f "$o" ] || echo "$f $o"
  done | xargs -r -P "$(nproc)" -L1 bash -c 'emcc '"${CF[*]}"' -c "$0" -o "$1"'
  t1=$(now)
  local CXXF=(-std=gnu++20 -O2 -w -I"$WORK/inc" -I"$R" -I"$R/stub" -I"$L" -I"$L/src" -DESP_PLATFORM=1 -DMAIPAI_HOST_RENDER=1 -DMD_HOST_SWITCH=1 -DLV_CONF_SKIP=1 -I"$U" -I"$U/lvgl" -I"$U/.." -I"$FW/main" -I"$H")
  mkdir -p "$WORK/obj/face"
  local OBJS=()
  for f in "$HERE/face_api.cc" "$R/hooks_new.cc" "$S/eyes.cpp" "$S/mouth.cpp" "$S/default.cpp" "$S/speech_bubble.cpp" "$H/maipai_facefx.cc" "$R/mumble_stub.cc"; do
    o="$WORK/obj/face/$(basename "$f").o"; emcc "${CXXF[@]}" -c "$f" -o "$o"; OBJS+=("$o")
  done
  o="$WORK/obj/face/arrow.o"; emcc "${CF[@]}" -c "$S/assets/default_bubble_arrow.c" -o "$o"; OBJS+=("$o")
  emcc -O2 "${OBJS[@]}" "$WORK"/obj/lv/*.o -o "$OUT/face.js" \
    -sMODULARIZE=1 -sEXPORT_NAME=FaceModule -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=16MB -sENVIRONMENT=web,node \
    -sEXPORTED_RUNTIME_METHODS=cwrap,ccall,HEAPU8 -sFILESYSTEM=0 -sSTACK_SIZE=1MB
  t2=$(now)
  printf 'face: lvgl %.1fs (cached after first run), face+link %.1fs, face.wasm %s bytes, face.js %s bytes\n' "$(echo "$t1 - $t0" | bc)" "$(echo "$t2 - $t1" | bc)" "$(stat -c %s "$OUT/face.wasm")" "$(stat -c %s "$OUT/face.js")"
}

build_cores() {
  fetch_tree
  local H="$FW/main/hal" t0 t1
  t0=$(now)
  # the dance ladder wrapper is the Python virtual unit's own (scripts/virtual-unit/dance/ladder_sim.c); it is included, not copied
  emcc -O2 -std=c99 -w -I"$H" "$HERE/cores_api.c" -o "$OUT/cores.js" \
    -sMODULARIZE=1 -sEXPORT_NAME=CoresModule -sENVIRONMENT=web,node -sFILESYSTEM=0 -sALLOW_MEMORY_GROWTH=0 -sINITIAL_MEMORY=1MB -sSTACK_SIZE=256KB \
    -sEXPORTED_FUNCTIONS=_malloc,_free,_lock_reset,_lock_set,_lock_lock_now,_lock_touch,_lock_key,_lock_keypad_tick,_lock_is_locked,_lock_entered,_lock_wrong_shown,_lock_status,_lock_reply,_limit_reset,_limit_step,_limit_orient,_limit_state,_limit_scale,_limit_speed_cap,_limit_dance_max,_limit_angle,_sim_new,_sim_start,_sim_set_max,_sim_stage,_sim_down,_sim_tick,_sim_effective,_sim_dwell,_sim_budget_reset,_sim_budget_take,_sim_swell,_sim_pose,_sim_consts \
    -sEXPORTED_RUNTIME_METHODS=cwrap,ccall,UTF8ToString,HEAP32,HEAPU8
  t1=$(now)
  printf 'cores: %.1fs, cores.wasm %s bytes, cores.js %s bytes\n' "$(echo "$t1 - $t0" | bc)" "$(stat -c %s "$OUT/cores.wasm")" "$(stat -c %s "$OUT/cores.js")"
}

case "$WHAT" in
  face) build_face ;;
  cores) build_cores ;;
  all) build_face; build_cores ;;
  *) echo "Unknown target $WHAT. Use face, cores or all."; exit 1 ;;
esac
