#!/usr/bin/env bash
# Intent: build the face renderer from a firmware tree plus the face patches written after that tree was built, without a firmware build.
# It makes an overlay tree of links, copies only main/hal and main/stackchan (the face code), applies the extra patches there, and builds into .runs/vu-build.
# Usage: bash scripts/virtual-unit/build-face.sh [firmware tree root; default MAIPAI_FW_TREE_ROOT, else the reference tree ~/esp/stackchan-rebuild/main-ref (bash scripts/fw-ref-tree.sh makes it)]
# Extra patches: FACE_PATCHES below (add a face patch here when it lands in firmware/patches and the tree is older than it).
# Placement: host-side development tool. Upstream: none.
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# the tree: the argument, else MAIPAI_FW_TREE_ROOT, else the canonical reference tree of main (scripts/ref-tree.py says plainly when it is missing or older than firmware/patches/ORDER)
B="${1:-$(python3 "$ROOT/scripts/ref-tree.py")}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FACE_PATCHES="UX01-style-mouth-widths.patch SF05-pairing-cover-line-break.patch UX02a-screen-palette.patch UX03a-eyes-only-mute-mark.patch UX03b-effects-on-the-face-only.patch UX04-update-cover.patch UX02b-screen-type-ladder.patch UX02c-sheet-icon-labels.patch UX09-update-refused-says-what-to-do.patch UX10-plain-words-home-link-original.patch SF01-time-helper-lock-and-remote-safety.patch UX02d-info-tab-plain-words.patch UX05a-first-run-core.patch UX05b-first-run-screens.patch UX06-face-rests-under-covers.patch UX07a-screen-fonts-with-accents.patch UX07b-screen-words-with-accents.patch UX07c-symbols-keep-their-font.patch UX08-first-run-is-a-screen.patch UX11-first-run-name-stackchan-first.patch UX12-first-run-skip-brain-question-and-next-steps.patch"
O="$ROOT/.runs/fixtree/firmware"
rm -rf "$ROOT/.runs/fixtree"; mkdir -p "$O/main"
for d in build-bench managed_components components; do ln -sfn "$B/firmware/$d" "$O/$d"; done
for e in "$B"/firmware/main/*; do n=$(basename "$e"); case "$n" in hal|stackchan) ;; *) ln -sfn "$e" "$O/main/$n";; esac; done
cp -R "$B/firmware/main/hal" "$O/main/hal"; cp -R "$B/firmware/main/stackchan" "$O/main/stackchan"
python3 "$ROOT/scripts/virtual-unit/overlay_patches.py" "$ROOT/.runs/fixtree" "$B"   # every patch of ORDER that touches the overlay, unless the tree has it already
mkdir -p "$ROOT/.runs/vu-build"
[ -f "$ROOT/.runs/vu-build/lvgl.a" ] || { echo "no .runs/vu-build/lvgl.a: run build.sh once from the tree (scripts/fw-face-render/build.sh)"; }
MAIPAI_FW_TREE="$O" bash "$ROOT/scripts/fw-face-render/build.sh" "$ROOT/.runs/vu-build"
