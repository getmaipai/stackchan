#!/usr/bin/env bash
# Intent: build one firmware image from a patched tree. Usage: bash scripts/fw-build.sh TREE plain|bench|gate|talkover|linkpsk|aec|heap [JOBS]
#   plain = the shipped image; bench = serial tools and face bench plus the memory line; gate = the plain image plus the memory line;
#   talkover = bench plus the MIC3 reading (patch SF15); linkpsk = bench plus the link key calls (patch SF21); aec = bench plus the echo canceller and wake-word interruption (patch SF29).
# TREE is the folder scripts/fw-rebuild.sh made (it holds firmware/). Output: TREE/firmware/build-<kind>/ and a line "BUILD OK" or a failure.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TREE=${1:?Usage: fw-build.sh TREE plain|bench|gate|talkover|linkpsk|aec|heap [JOBS]}
KIND=${2:?Usage: fw-build.sh TREE plain|bench|gate|talkover|linkpsk|aec|heap [JOBS]}
JOBS=${3:-2}
FW="$TREE/firmware"
[ -d "$FW" ] || { echo "$FW is missing. Run scripts/fw-rebuild.sh first." >&2; exit 1; }
# The committed overlay files are copied in so the tree always builds from what the repo holds.
cp "$ROOT/firmware/configs/sdkconfig.bench.defaults" "$ROOT/firmware/configs/sdkconfig.gate.defaults" "$ROOT/firmware/configs/sdkconfig.talkover.defaults" "$ROOT/firmware/configs/sdkconfig.linkpsk.defaults" "$ROOT/firmware/configs/sdkconfig.aec.defaults" "$ROOT/firmware/configs/sdkconfig.heaptrace.defaults" "$FW/"
case "$KIND" in
    plain) OVERLAYS="" ;;
    bench) OVERLAYS="sdkconfig.bench.defaults;sdkconfig.gate.defaults" ;;
    gate)  OVERLAYS="sdkconfig.gate.defaults" ;;
    talkover) OVERLAYS="sdkconfig.bench.defaults;sdkconfig.gate.defaults;sdkconfig.talkover.defaults" ;;
    linkpsk) OVERLAYS="sdkconfig.bench.defaults;sdkconfig.gate.defaults;sdkconfig.linkpsk.defaults" ;;
    aec) OVERLAYS="sdkconfig.bench.defaults;sdkconfig.gate.defaults;sdkconfig.aec.defaults" ;;
    heap) OVERLAYS="sdkconfig.bench.defaults;sdkconfig.gate.defaults;sdkconfig.aec.defaults;sdkconfig.heaptrace.defaults" ;;
    *) echo "Unknown image kind $KIND. Use plain, bench or gate." >&2; exit 1 ;;
esac
# shellcheck disable=SC1091
. "$ROOT/scripts/fw-env.sh"
export MAIPAI_TAILNET=y
# The private-network client is downloaded into the tree (pinned commit plus both library patches), never the shared folder,
# so a build here cannot be changed by another session's copy.
if [ ! -d "$TREE/deps/microlink/.git" ]; then MAIPAI_DEPS="$TREE/deps" bash "$ROOT/scripts/fw-tailnet.sh"; fi
export MAIPAI_MICROLINK_DIR="$TREE/deps/microlink"
cd "$FW"
# Generated inputs (the CMake rule for the language header runs too late for the first build, and the bench clips need macOS say and ffmpeg).
python3 xiaozhi-esp32/scripts/gen_lang.py --language en-US --output xiaozhi-esp32/main/assets/lang_config.h
if { [ "$KIND" = bench ] || [ "$KIND" = talkover ] || [ "$KIND" = linkpsk ] || [ "$KIND" = aec ] || [ "$KIND" = heap ]; } && [ ! -f main/hal/maipai_bench_clips.c ]; then python3 "$ROOT/scripts/fw-bench-clips.py" "$FW"; fi
D="$PWD/sdkconfig.defaults"
if [ -n "$OVERLAYS" ]; then IFS=';' read -ra X <<< "$OVERLAYS"; for f in "${X[@]}"; do D="$D;$PWD/$f"; done; fi
if [ -n "${FW_BUILD:-}" ]; then printf 'CONFIG_MAIPAI_FW_BUILD=%s\n' "$FW_BUILD" > sdkconfig.build.defaults; D="$D;$PWD/sdkconfig.build.defaults"; fi  # the signed-update build number of this image
B="build-$KIND"
SDK="sdkconfig.f$KIND"
# A fresh sdkconfig the first time; later calls on the same tree rebuild incrementally.
if [ ! -f "$B/build.ninja" ]; then
    rm -f "$SDK"
    nice -n 15 idf.py -B "$B" -DSDKCONFIG="$SDK" -DSDKCONFIG_DEFAULTS="$D" reconfigure
fi
nice -n 15 ninja -j"$JOBS" -C "$B"
echo "BUILD OK $FW/$B"
