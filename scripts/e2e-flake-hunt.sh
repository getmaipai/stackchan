#!/usr/bin/env bash
# Intent: find a flaky e2e scenario by running the whole e2e in a loop while the CPU is oversubscribed. Each run's full output goes to .runs/flake/run-N.log (the host log tail of a
# failed scenario is in it, and E2E_LOG keeps the whole host log of the last run); the loop stops at the first failing run and prints the failing scenario lines.
# Usage: bash scripts/e2e-flake-hunt.sh [runs, default 5] [burners, default 2 x CPU count] [scenario ...]
# Placement: host-side development tool. Upstream: none.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNS="${1:-5}"; BURN="${2:-$(( $(sysctl -n hw.ncpu 2>/dev/null || nproc) * 2 ))}"; shift 2 2>/dev/null || shift $# 2>/dev/null
OUT="$ROOT/.runs/flake"; mkdir -p "$OUT"
pids=()
cleanup() { for p in "${pids[@]}"; do kill "$p" 2>/dev/null; done; }
trap cleanup EXIT
for _ in $(seq "$BURN"); do ( while :; do :; done ) & pids+=($!); done
echo "load: $BURN busy loops"
for n in $(seq "$RUNS"); do
  E2E_LOG="$OUT/host-$n.log" uv run --project "$ROOT/host" python "$ROOT/scripts/virtual-unit/e2e.py" "$@" > "$OUT/run-$n.log" 2>&1
  code=$?
  echo "run $n: exit $code, $(grep -c '^  took' "$OUT/run-$n.log") scenarios, slowest: $(grep -B0 '^  took' "$OUT/run-$n.log" | sort -k2 -n -r | head -1)"
  if [ $code -ne 0 ]; then grep -E "FAIL|^scenario" "$OUT/run-$n.log" | grep -B1 FAIL | cut -c1-300; echo "kept: $OUT/run-$n.log and $OUT/host-$n.log"; exit 1; fi
done
echo "no failure in $RUNS runs under load"
