#!/usr/bin/env bash
# Intent: fuzz the unit's own parsers (firmware *_core.h headers) on this computer with the address and undefined behavior sanitizers. Replays the patch ORDER into an empty
# folder (host/tests/firmware_order_cores.py), builds one program per parser from scripts/fuzz/core_fuzz.c into .runs/fuzz, and runs each with a seed and an iteration count.
# Usage: bash scripts/fuzz-cores.sh [iterations, default 20000] [seed, default 1] [target ...]   targets: FACE FILLER GAMES LANG REACT PACKCACHE TIMERS UPDATEHDR MOOD TAILNET REMOTE LISTEN LOCK
# A failure prints the sanitizer report and the line to repeat it. Placement: host-side development tool; no firmware change. Upstream: none.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ITER="${1:-20000}"; SEED="${2:-1}"; shift 2 2>/dev/null || shift $# 2>/dev/null
TARGETS=("$@"); [ ${#TARGETS[@]} -eq 0 ] && TARGETS=(FACE FILLER GAMES LANG REACT PACKCACHE TIMERS UPDATEHDR MOOD TAILNET REMOTE LISTEN LOCK)
OUT="$ROOT/.runs/fuzz"; mkdir -p "$OUT"
CORES="$(mktemp -d)"; trap 'rm -rf "$CORES"' EXIT
git init -q "$CORES"
HAL="$(cd "$ROOT/host" && uv run python -c "
import sys
sys.path.insert(0, 'tests')
from pathlib import Path
import firmware_order_cores as f
print(f.build_cores(Path('$CORES')))
")" || { echo "fuzz: could not replay the patches into $CORES"; exit 2; }
status=0
for t in "${TARGETS[@]}"; do
  exe="$OUT/fuzz_$t"
  if ! cc -std=gnu99 -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer -w -DTARGET_$t -I"$HAL" "$ROOT/scripts/fuzz/core_fuzz.c" -o "$exe" 2>"$OUT/build_$t.log"; then
    echo "fuzz $t: did not build (see $OUT/build_$t.log)"; status=1; continue
  fi
  if ! ASAN_OPTIONS=detect_leaks=0:abort_on_error=0 "$exe" "$ITER" "$SEED" 2>"$OUT/run_$t.log"; then
    echo "fuzz $t: FAILED; repeat with: bash scripts/fuzz-cores.sh $ITER $SEED $t   (report in $OUT/run_$t.log)"; head -12 "$OUT/run_$t.log"; status=1
  fi
done
exit $status
