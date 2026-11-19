#!/usr/bin/env bash
# Intent: render every game sound of the unit to a WAV file with the unit's own sound core, so the owner can listen to the real sounds on a computer.
# Usage: bash scripts/sfx-wav.sh OUTDIR [TREE]   TREE is a replayed firmware tree (default: main's reference tree, scripts/ref-tree.py).
# Placement: host-side development tool; no firmware change. Upstream: none.
set -euo pipefail
OUT=${1:?Usage: sfx-wav.sh OUTDIR [TREE]. Give the folder the WAV files go to.}
TREE=${2:-$(python3 "$(dirname "$0")/ref-tree.py")}
HDR="$TREE/firmware/main/hal"
[ -f "$HDR/maipai_games_sfx_core.h" ] || { echo "No sound core in $HDR. Pass a replayed firmware tree as the second argument." >&2; exit 1; }
mkdir -p "$OUT"
cc -std=c99 -Wall -Wextra -O1 -I"$HDR" "$(dirname "$0")/sfx-wav.c" -o "$OUT/.sfx-wav"
"$OUT/.sfx-wav" "$OUT"
rm -f "$OUT/.sfx-wav"
