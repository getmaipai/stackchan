#!/usr/bin/env bash
# Intent: bring this checkout to origin/main and restart the virtual unit view on one port, then prove the page serves the model in the repo.
# Usage: bash scripts/virtual-unit/restart-preview.sh [port, default 8780]   Run it in the checkout the preview is served from.
# It only fast-forwards (a checkout with local changes or its own commits is refused), stops only a view.py that listens on that port, and
# prints one line: the commit and whether the served model matches. Exit 1 when it does not.
# Placement: host-side development tool. Upstream: none.
set -eu
PORT="${1:-8780}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "restart-preview: this checkout has local changes; commit or discard them, then run this again"; exit 1; }
git fetch -q origin
git merge -q --ff-only origin/main || { echo "restart-preview: this checkout cannot fast-forward to origin/main (it has its own commits); switch it to main and run this again"; exit 1; }
for pid in $(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null); do
  if ps -o command= -p "$pid" | grep -q "view.py"; then kill "$pid"; else echo "restart-preview: port $PORT is held by something that is not the view (pid $pid); free the port or pass another one"; exit 1; fi
done
for _ in 1 2 3 4 5 6 7 8 9 10; do lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1 || break; sleep 0.3; done
mkdir -p .runs
nohup python3 scripts/virtual-unit/view.py "$PORT" > ".runs/view$PORT.log" 2>&1 &
served=""
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  served="$(curl -s --max-time 2 "http://127.0.0.1:$PORT/model/stackchan.glb" | shasum | cut -c1-12 || true)"
  [ "$served" = "$(shasum scripts/virtual-unit/model/stackchan.glb | cut -c1-12)" ] && break
  sleep 0.5
done
want="$(shasum scripts/virtual-unit/model/stackchan.glb | cut -c1-12)"
if [ "$served" = "$want" ]; then echo "restart-preview: ok, port $PORT serves $(git rev-parse --short HEAD), model $want"; else echo "restart-preview: FAIL, port $PORT serves model $served but the repo has $want; read .runs/view$PORT.log"; exit 1; fi
