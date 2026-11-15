#!/usr/bin/env bash
# Intent: run the firmware batch brief repeatedly (one Codex run per batch) until a run writes ALL DONE or MAX runs pass.
# Usage: bash scripts/fw-lane.sh [MAX] ; logs in .runs/fw-lane-N.log ; run it inside an owned tmux session.
set -u
cd "$(dirname "$0")/.."
MAX="${1:-10}"
for n in $(seq 1 "$MAX"); do
  ~/.local/bin/codex-luna-high exec -s danger-full-access -C "$PWD" - < .runs/brief-fw-batch.md > ".runs/fw-lane-$n.log" 2>&1
  echo "run $n EXIT=$?" >> .runs/fw-lane.status
  head -1 .runs/fw-progress.md 2>/dev/null | grep -q "ALL DONE" && { echo "ALL DONE after $n runs" >> .runs/fw-lane.status; exit 0; }
done
echo "STOPPED after $MAX runs" >> .runs/fw-lane.status
