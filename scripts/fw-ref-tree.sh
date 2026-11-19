#!/usr/bin/env bash
# Intent: ONE canonical firmware reference tree for main: ~/esp/stackchan-rebuild/main-ref is a clean replay of origin/main's firmware/patches/ORDER, with build-bench/config present
# (the renderer goldens and the unit checks run against it: MAIPAI_FW_TREE_ROOT). It is rebuilt only when main's ORDER (or its patches) changed since the last run, and only the bench
# image is built so the configuration exists. Prints the path. Other trees are never touched. Usage: bash scripts/fw-ref-tree.sh [--force]
# Placement: the machine that builds firmware (development only). Upstream: none.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TREE="${MAIPAI_FW_REF_TREE:-$HOME/esp/stackchan-rebuild/main-ref}"
git -C "$ROOT" fetch -q origin main
# A detached checkout of origin/main of its own (the build reads the repo's other files too: the phrase clips, the game packs, the overlays).
SRC="${MAIPAI_FW_REF_SRC:-$HOME/esp/stackchan-rebuild/.main-ref-src}"
if [ ! -d "$SRC" ]; then
    git -C "$ROOT" worktree add --detach "$SRC" origin/main >/dev/null
else
    git -C "$SRC" checkout -q --detach origin/main
fi
STAMP=$(cat "$SRC/firmware/patches/ORDER" "$SRC"/firmware/patches/*.patch "$SRC"/firmware/configs/* "$SRC/scripts/fw-build.sh" "$SRC/scripts/fw-rebuild.sh" | shasum -a 256 | cut -d' ' -f1)
if [ "${1:-}" != "--force" ] && [ -f "$TREE/.main-ref-stamp" ] && [ "$(cat "$TREE/.main-ref-stamp")" = "$STAMP" ] && [ -f "$TREE/firmware/build-bench/config/sdkconfig.h" ]; then
    echo "$TREE"
    exit 0
fi
rm -rf "$TREE"
bash "$SRC/scripts/fw-rebuild.sh" "$TREE" >"$TREE.log" 2>&1 || { echo "The replay of main's ORDER failed. Read $TREE.log, fix the patch it names, then run this again." >&2; exit 1; }
bash "$SRC/scripts/fw-build.sh" "$TREE" bench 4 >>"$TREE.log" 2>&1 || { echo "The bench build of the reference tree failed. Read $TREE.log." >&2; exit 1; }
echo "$STAMP" > "$TREE/.main-ref-stamp"
git -C "$ROOT" rev-parse origin/main > "$TREE/.main-ref-commit"
echo "$TREE"
