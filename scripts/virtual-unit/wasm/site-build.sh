#!/usr/bin/env bash
# Intent: build the static playground (docs-site/playground/): the unit's screens renderer, the lock keypad and the link covers as WebAssembly (the same C++ the native renderers
# build, with main() split by shim_main.py), the C cores as one module with a generated wrapper, the pinned Pyodide runtime (downloaded here, never committed), the virtual unit's
# Python (copied, with the documented shim layer), the viewer files, and the page.
# Needs: emcc 3.1.74 on PATH (emsdk), git, python3, node; network on the first run (firmware replay, LVGL, fonts, zlib, Pyodide). Nothing is fetched when the page runs.
# Usage: bash scripts/virtual-unit/wasm/site-build.sh [screens|cores|pyodide|physics|site|all]   (default all)
#   WASM_WORK        work folder for the replayed tree and fetched sources (default .runs/wasm, shared with build.sh)
#   MAIPAI_FW_TREE   an existing replayed tree root (default: replay into $WORK/fwtree with scripts/fw-rebuild.sh)
#   PLAYGROUND_OUT   output folder (default docs-site/playground)
# Placement: host-side development tool. Upstream: none.
set -euo pipefail
# macOS portability: nproc, stat -c and sha256sum are GNU tools; use what the machine has
ncpu() { nproc 2>/dev/null || sysctl -n hw.ncpu; }
fsize() { stat -c %s "$1" 2>/dev/null || stat -f %z "$1"; }
sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi; }
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
WORK="${WASM_WORK:-$ROOT/.runs/wasm}"
OUT="${PLAYGROUND_OUT:-$ROOT/docs-site/playground}"
VU="$ROOT/scripts/virtual-unit"
R="$ROOT/scripts/fw-face-render"
WHAT="${1:-all}"
PYODIDE_VERSION="0.27.7"
ZLIB_TAG="v1.3.1"
need_emcc() { command -v emcc >/dev/null || { echo "emcc is not on PATH. Install Emscripten (git clone https://github.com/emscripten-core/emsdk, ./emsdk install 3.1.74, ./emsdk activate 3.1.74), source emsdk_env.sh, run this again."; exit 1; }; }
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
    | xargs -P "$(ncpu)" -L1 bash -c 'emcc '"${CF[*]}"' -c "$0" -o "$1"'
  for z in adler32 compress crc32 deflate trees zutil; do [ -f "$WORK/obj-wasm/zlib/$z.o" ] || emcc -O2 -w -I"$WORK/zlib" -c "$WORK/zlib/$z.c" -o "$WORK/obj-wasm/zlib/$z.o"; done
  local OBJS=() f o
  for f in "$WORK/shim/$(basename "$src")" $cxx; do o="$WORK/obj-wasm/$name/$(basename "$f").o"; emcc "${CXXF[@]}" -c "$f" -o "$o"; OBJS+=("$o"); done
  for f in $cfiles; do o="$WORK/obj-wasm/$name/$(basename "$f").o"; emcc "${CF[@]}" -c "$f" -o "$o"; OBJS+=("$o"); done
  local mod; mod="$(echo "${name:0:1}" | tr a-z A-Z)${name:1}Module"
  emcc -O2 "${OBJS[@]}" "$WORK"/obj-wasm/lv/*.o "$WORK"/obj-wasm/zlib/*.o -o "$OUT/wasm/$name.js" \
    -sMODULARIZE=1 -sEXPORT_NAME="$mod" -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=16MB -sENVIRONMENT=web,node -sSTACK_SIZE=1MB \
    -sEXPORTED_FUNCTIONS=_vu_init,_vu_cmd,_vu_fb,_malloc,_free -sEXPORTED_RUNTIME_METHODS=ccall,cwrap,HEAPU8,FS -sFORCE_FILESYSTEM=1
  printf '%s: %s bytes wasm, %s bytes js\n' "$name" "$(fsize "$OUT/wasm/$name.wasm")" "$(fsize "$OUT/wasm/$name.js")"
}

build_screens() {
  need_emcc; fetch_tree
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
  need_emcc; fetch_tree
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
  printf 'cores: %s bytes wasm, %s bytes js, %s functions exported\n' "$(fsize "$OUT/wasm/cores.wasm")" "$(fsize "$OUT/wasm/cores.js")" "$(echo "$EXPORTS" | tr ',' '\n' | wc -l)"
}

# The pinned Pyodide runtime (core build: Python 3.12 and its standard library, no packages): downloaded here, checked against the pinned hash, never committed.
PYODIDE_SHA256="9bc8f127db6c590b191b9aee754022cb41b1a36c7bac233776c11c5ecb541be8"
build_pyodide() {
  local tar="$WORK/downloads/pyodide-core-$PYODIDE_VERSION.tar.bz2"
  mkdir -p "$WORK/downloads" "$OUT/pyodide"
  if [ ! -f "$tar" ]; then curl -fsSL -o "$tar" "https://github.com/pyodide/pyodide/releases/download/$PYODIDE_VERSION/pyodide-core-$PYODIDE_VERSION.tar.bz2" || { echo "could not download Pyodide $PYODIDE_VERSION. Check the network, or copy pyodide-core-$PYODIDE_VERSION.tar.bz2 into $WORK/downloads and run again."; exit 1; }; fi
  [ "$(sha256 "$tar" | cut -d' ' -f1)" = "$PYODIDE_SHA256" ] || { echo "the Pyodide download does not match the pinned hash. Delete $tar and run again; if it still differs, check the release before changing PYODIDE_SHA256 in site-build.sh."; exit 1; }
  rm -rf "$WORK/pyodide-x"; mkdir -p "$WORK/pyodide-x"; tar xjf "$tar" -C "$WORK/pyodide-x"
  for f in pyodide.js pyodide.asm.js pyodide.asm.wasm python_stdlib.zip pyodide-lock.json; do cp "$WORK/pyodide-x/pyodide/$f" "$OUT/pyodide/$f"; done
  printf 'pyodide %s: %s bytes of wasm\n' "$PYODIDE_VERSION" "$(fsize "$OUT/pyodide/pyodide.asm.wasm")"
}

# The physics engine (MuJoCo 4.0.1, Apache-2.0): the WebAssembly build from the npm registry, pinned by the package's published SHA-512, put in the site's vendor folder so the page never asks an
# outside address (the native viewer loads the same file from a CDN; see scripts/virtual-unit/physics/THIRD-PARTY-physics-engine.json). Downloaded here, checked, never committed.
MUJOCO_VERSION="4.0.1"
MUJOCO_INTEGRITY="vLuwD6biiyo2D2LG1fwpwJUfWSDZhBIr6aUd3AuPJR8P7FAIeSHgofGC+0XgIpZ0vYi0EOyju+Kv7zPJepX7wA=="
build_physics() {
  local tgz="$WORK/downloads/mujoco-$MUJOCO_VERSION.tgz"
  mkdir -p "$WORK/downloads" "$OUT/vendor/mujoco-$MUJOCO_VERSION"
  if [ ! -f "$tgz" ]; then curl -fsSL -o "$tgz" "https://registry.npmjs.org/@mujoco/mujoco/-/mujoco-$MUJOCO_VERSION.tgz" || { echo "could not download MuJoCo $MUJOCO_VERSION from the npm registry. Check the network and run again."; exit 1; }; fi
  [ "$(openssl dgst -sha512 -binary "$tgz" | base64 | tr -d '\n')" = "$MUJOCO_INTEGRITY" ] || { echo "the MuJoCo download does not match the pinned SHA-512. Delete $tgz and run again; if it still differs, check the package before changing the pin."; exit 1; }
  rm -rf "$WORK/mujoco-x"; mkdir -p "$WORK/mujoco-x"; tar xzf "$tgz" -C "$WORK/mujoco-x"
  cp "$WORK/mujoco-x/package/mujoco.js" "$WORK/mujoco-x/package/mujoco.wasm" "$OUT/vendor/mujoco-$MUJOCO_VERSION/"
  cp "$ROOT/docs-site/vendor/mujoco/LICENSE-Apache-2.0.txt" "$OUT/vendor/mujoco-$MUJOCO_VERSION/LICENSE-Apache-2.0.txt"
  printf 'mujoco %s: %s bytes of wasm (the page does not load it yet: the physics switch stays off until the page swaps the engine address)\n' "$MUJOCO_VERSION" "$(fsize "$OUT/vendor/mujoco-$MUJOCO_VERSION/mujoco.wasm")"
}

# The page: the viewer copied from view.html with the documented changes (make_page.py), the viewer's own scripts and model, three.js from the site's vendor folder, the adapter layer.
build_site() {
  local P="$HERE/page"
  mkdir -p "$OUT/vendor" "$OUT/model"
  python3 -I "$HERE/make_page.py" "$VU/view.html" "$ROOT/docs/legal/affiliation.json" "$OUT"
  cp "$VU/view3d.js" "$VU/talk.js" "$OUT/"
  cp "$P/engine.js" "$P/bridge.js" "$P/boot.js" "$P/app.js" "$P/test.js" "$P/test.html" "$OUT/"
  rm -rf "$OUT/vendor/three-r128"; cp -R "$ROOT/docs-site/vendor/three-r128" "$OUT/vendor/three-r128"
  cp "$VU/model/stackchan.web.glb" "$OUT/model/stackchan.web.glb"
  python3 -I "$HERE/bundle.py" "$ROOT" "$OUT/vu-py.zip"
  du -sk "$OUT" | awk '{print "playground folder: " $1 " KB"}'
}

case "$WHAT" in
  screens) build_screens ;;
  cores) build_cores ;;
  pyodide) build_pyodide ;;
  physics) build_physics ;;
  site) build_site ;;
  all) build_screens; build_cores; build_pyodide; build_physics; build_site ;;
  *) echo "Unknown target $WHAT. Use screens, cores, pyodide, physics, site or all."; exit 1 ;;
esac
