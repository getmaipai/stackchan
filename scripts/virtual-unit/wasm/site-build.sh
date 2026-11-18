#!/usr/bin/env bash
# Intent: build the static playground (docs-site/playground/): the unit's screens renderer, the lock keypad and the link covers as WebAssembly (the same C++ the native renderers
# build, with main() split by shim_main.py), the C cores as one module with a generated wrapper, the pinned Pyodide runtime (downloaded here, never committed), the virtual unit's
# Python (copied, with the documented shim layer), the viewer files, and the page.
# Needs: emcc 3.1.74 on PATH (emsdk), git, python3, node; network on the first run (firmware replay, LVGL, fonts, zlib, Pyodide). Nothing is fetched when the page runs.
# Usage: bash scripts/virtual-unit/wasm/site-build.sh [screens|cores|pyodide|site|all]   (default all)
#   WASM_WORK        work folder for the replayed tree and fetched sources (default .runs/wasm, shared with build.sh)
#   MAIPAI_FW_TREE   an existing replayed tree root (default: replay into $WORK/fwtree with scripts/fw-rebuild.sh)
#   PLAYGROUND_OUT   output folder (default docs-site/playground)
# Placement: host-side development tool. Upstream: none.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
WORK="${WASM_WORK:-$ROOT/.runs/wasm}"
OUT="${PLAYGROUND_OUT:-$ROOT/docs-site/playground}"
VU="$ROOT/scripts/virtual-unit"
R="$ROOT/scripts/fw-face-render"
WHAT="${1:-all}"
PYODIDE_VERSION="0.27.7"
ZLIB_TAG="v1.3.1"
command -v emcc >/dev/null || { echo "emcc is not on PATH. Install Emscripten (git clone https://github.com/emscripten-core/emsdk, ./emsdk install 3.1.74, ./emsdk activate 3.1.74), source emsdk_env.sh, run this again."; exit 1; }
mkdir -p "$WORK" "$OUT/wasm"
export EMCC_SKIP_SANITY_CHECK=1

fetch_tree() {
  TREE="${MAIPAI_FW_TREE:-$WORK/fwtree}"
  if [ ! -d "$TREE/firmware/main/hal" ]; then
    rm -rf "$TREE"
    bash "$ROOT/scripts/fw-rebuild.sh" "$TREE" > "$WORK/fw-rebuild.log" 2>&1 || true   # its final ESP-IDF build fails without IDF; the tree is complete before that step
    [ -d "$TREE/firmware/main/hal" ] || { echo "firmware replay failed: read $WORK/fw-rebuild.log, fix the network or the patch order, run again."; exit 1; }
  fi
  FW="$TREE/firmware"
  [ -d "$WORK/lvgl" ] || git clone -q --depth 1 --branch v9.5.0 https://github.com/lvgl/lvgl "$WORK/lvgl"
  [ -d "$WORK/fonts" ] || git clone -q --depth 1 https://github.com/78/xiaozhi-fonts "$WORK/fonts"
  [ -d "$WORK/zlib" ] || git clone -q --depth 1 --branch "$ZLIB_TAG" https://github.com/madler/zlib "$WORK/zlib"
  python3 -I "$HERE/gen_sdkconfig.py" "$FW" "$WORK/inc/sdkconfig.h" >/dev/null
  # the tree layout cover_gen.py and the native build scripts expect (managed_components as the IDF would leave them), made of links
  local C="$WORK/compat/firmware"
  rm -rf "$WORK/compat"; mkdir -p "$C/managed_components" "$C/build-bench/config"
  ln -s "$FW/main" "$C/main"; ln -s "$FW/components" "$C/components"; ln -s "$WORK/lvgl" "$C/managed_components/lvgl__lvgl"; ln -s "$WORK/fonts" "$C/managed_components/78__xiaozhi-fonts"
  cp "$WORK/inc/sdkconfig.h" "$C/build-bench/config/sdkconfig.h"
}

# One program: shim_main.py makes the browser copy of the native source, then it links with LVGL and zlib into $OUT/wasm/NAME.{js,wasm}.
build_program() {   # NAME NATIVE_SRC EXTRA_CXX_FILES(space list) EXTRA_C_FILES(space list) EXTRA_DEFS EXTRA_INC
  local name="$1" src="$2" cxx="$3" cfiles="$4" defs="$5" inc="$6"
  local L="$WORK/lvgl" H="$FW/main/hal" S="$FW/main/stackchan/avatar/skins/default" U="$FW/components/smooth_ui_toolkit/src"
  local CF=(-O2 -w -I"$WORK/inc" -I"$R/stub" -I"$L" -I"$L/src" -DESP_PLATFORM=1 -DLV_CONF_SKIP=1)
  local CXXF=(-std=gnu++20 -O2 -w -I"$WORK/inc" -I"$R" -I"$R/stub" -I"$L" -I"$L/src" -I"$WORK/zlib" -DESP_PLATFORM=1 -DMAIPAI_HOST_RENDER=1 -DMD_HOST_SWITCH=1 -DLV_CONF_SKIP=1 -I"$U" -I"$U/lvgl" -I"$U/.." -I"$FW/main" -I"$H" $inc $defs)
  mkdir -p "$WORK/shim" "$WORK/obj-wasm/$name" "$WORK/obj-wasm/lv" "$WORK/obj-wasm/zlib"
  python3 -I "$HERE/shim_main.py" "$src" "$WORK/shim/$(basename "$src")" >/dev/null
  # LVGL and zlib objects: built once, kept, shared by every program
  find "$L/src" -name '*.c' | while read -r f; do o="$WORK/obj-wasm/lv/$(echo "${f#$L/}" | tr '/' '_').o"; [ -f "$o" ] || echo "$f $o"; done \
    | xargs -r -P "$(nproc)" -L1 bash -c 'emcc '"${CF[*]}"' -c "$0" -o "$1"'
  for z in adler32 compress crc32 deflate trees zutil; do [ -f "$WORK/obj-wasm/zlib/$z.o" ] || emcc -O2 -w -I"$WORK/zlib" -c "$WORK/zlib/$z.c" -o "$WORK/obj-wasm/zlib/$z.o"; done
  local OBJS=() f o
  for f in "$WORK/shim/$(basename "$src")" $cxx; do o="$WORK/obj-wasm/$name/$(basename "$f").o"; emcc "${CXXF[@]}" -c "$f" -o "$o"; OBJS+=("$o"); done
  for f in $cfiles; do o="$WORK/obj-wasm/$name/$(basename "$f").o"; emcc "${CF[@]}" -c "$f" -o "$o"; OBJS+=("$o"); done
  local mod; mod="$(echo "${name:0:1}" | tr a-z A-Z)${name:1}Module"
  emcc -O2 "${OBJS[@]}" "$WORK"/obj-wasm/lv/*.o "$WORK"/obj-wasm/zlib/*.o -o "$OUT/wasm/$name.js" \
    -sMODULARIZE=1 -sEXPORT_NAME="$mod" -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=16MB -sENVIRONMENT=web,node -sSTACK_SIZE=1MB \
    -sEXPORTED_FUNCTIONS=_vu_init,_vu_cmd,_vu_fb,_malloc,_free -sEXPORTED_RUNTIME_METHODS=ccall,cwrap,HEAPU8,FS -sFORCE_FILESYSTEM=1
  printf '%s: %s bytes wasm, %s bytes js\n' "$name" "$(stat -c %s "$OUT/wasm/$name.wasm")" "$(stat -c %s "$OUT/wasm/$name.js")"
}

build_screens() {
  fetch_tree
  local H="$FW/main/hal" S="$FW/main/stackchan/avatar/skins/default" F="$FW/managed_components/78__xiaozhi-fonts/src"
  local FONTS="$WORK/fonts/src"
  mkdir -p "$WORK/more"
  # the whole HAL header is not needed by the More screen: the native build does the same cut (build-screens.sh)
  sed 's|#include "hal.h"|// hal.h left out in the host build|' "$H/maipai_more.cc" > "$WORK/more/maipai_more.cc"
  local EXTRA="$WORK/more/maipai_more.cc $R/more_host.cc $R/hooks_banner.cc $H/maipai_banner.cc $H/maipai_subtitles.cc $H/maipai_pages.cc $H/maipai_apps.cc $H/maipai_firstrun.cc $S/eyes.cpp $S/mouth.cpp $S/default.cpp $S/speech_bubble.cpp $H/maipai_facefx.cc"
  build_program screens "$R/render.cc" "$EXTRA" "$FONTS/font_noto_sans_basic_20_4.c $FONTS/font_noto_sans_basic_16_4.c $S/assets/default_bubble_arrow.c" "-DBUILTIN_TEXT_FONT=font_noto_sans_basic_20_4 -DMAIPAI_PAGES_RENDER=1" ""
  # the passcode lock screen and keypad, and the link covers: separate native programs, separate small modules the page loads on demand
  build_program lock "$R/lock_render.cc" "" "" "" ""
  mkdir -p "$WORK/cover"; python3 -I "$VU/cover_gen.py" "$WORK/compat" "$WORK/cover" >/dev/null
  build_program cover "$VU/cover_render.cc" "" "$FONTS/font_noto_sans_basic_20_4.c" "" "-I$WORK/cover"
}

# The C cores as one module: the Python virtual unit's own wrappers (dance ladder, host reconnect: scripts/virtual-unit/dance/*.c, included not copied), the spike's lock and movement
# limiter wrappers, and a generated wrapper (gen_cores.py) over the core headers the rest of the rig and its tests ask: lock, limiter, listen guard, update trial, signed update header,
# link quiet, remote safety rules, sounds (the quiet schedule) and hourly chime, touch.
CORE_NAMES="lock motion_limit listen_guard update updatehdr link_quiet remote sounds hourly touch reconnect"
build_cores() {
  fetch_tree
  local H="$FW/main/hal"
  mkdir -p "$WORK/cores"
  python3 -I "$HERE/gen_cores.py" "$H" "$WORK/cores/cores_gen.c" "$OUT/wasm/cores.sigs.json" $CORE_NAMES
  emcc -O2 -std=c99 -w -I"$H" -I"$HERE" -c "$HERE/cores_all.c" -o "$WORK/cores/cores_all.o"
  emcc -O2 -std=c99 -w -I"$H" -c "$WORK/cores/cores_gen.c" -o "$WORK/cores/cores_gen.o"
  local EXPORTS
  EXPORTS=$(python3 -I - "$HERE/cores_api.c" "$HERE/cores_all.c" "$VU/dance/ladder_sim.c" "$VU/dance/reconnect_sim.c" "$WORK/cores/cores_gen.c" <<'PY'
import re, sys
names = ["_malloc", "_free"]
for f in sys.argv[1:]:
    for m in re.finditer(r"^(?!static)[a-z_][\w\s\*]*?[\s\*](\w+)\([^;{]*\)\s*\{", open(f).read(), re.M):
        if m.group(1) not in ("main", "if", "for", "while"):
            names.append("_" + m.group(1))
print(",".join(sorted(set(names))))
PY
)
  emcc -O2 "$WORK/cores/cores_all.o" "$WORK/cores/cores_gen.o" -o "$OUT/wasm/cores.js" \
    -sMODULARIZE=1 -sEXPORT_NAME=CoresModule -sENVIRONMENT=web,node -sFILESYSTEM=0 -sALLOW_MEMORY_GROWTH=0 -sINITIAL_MEMORY=2MB -sSTACK_SIZE=256KB \
    -sEXPORTED_FUNCTIONS="$EXPORTS" -sEXPORTED_RUNTIME_METHODS=ccall,cwrap,UTF8ToString,HEAPU8,HEAP32
  printf 'cores: %s bytes wasm, %s bytes js, %s functions exported\n' "$(stat -c %s "$OUT/wasm/cores.wasm")" "$(stat -c %s "$OUT/wasm/cores.js")" "$(echo "$EXPORTS" | tr ',' '\n' | wc -l)"
}
