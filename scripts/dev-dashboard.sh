#!/usr/bin/env bash
# Intent: run the host settings dashboard against seeded demo data (two stand-in units, no hardware, no real data) so it can be looked at.
# Usage: bash scripts/dev-dashboard.sh start|stop|status   (port 8801, 127.0.0.1 only; a fresh throwaway token is printed, never committed)
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
PORT="${DASHBOARD_PORT:-8801}"
RUN="$ROOT/.runs/dev-dashboard"
case "${1:-status}" in
  start)
    bash "$0" stop >/dev/null 2>&1 || true
    mkdir -p "$RUN"; rm -rf "$RUN/data"; mkdir -p "$RUN/data"
    PY=python3; [ -x "$ROOT/host/.venv/bin/python" ] && PY="$ROOT/host/.venv/bin/python"
    (cd "$ROOT/host" && nohup "$PY" -m maipai_body.settings_sim --port "$PORT" --data "$RUN/data" >"$RUN/log" 2>&1 &
     echo $! >"$RUN/pid")
    for _ in $(seq 1 40); do curl -fs "http://127.0.0.1:$PORT/settings" >/dev/null 2>&1 && break; sleep 0.5; done
    curl -fs "http://127.0.0.1:$PORT/settings" >/dev/null || { echo "dashboard did not start: see $RUN/log"; exit 1; }
    echo "dashboard: http://127.0.0.1:$PORT/settings (bound to this computer only; demo data, two stand-in units)"
    echo "settings token for another device (throwaway, this run only): $(cat "$RUN/data/settings-token")"
    ;;
  stop)
    [ -f "$RUN/pid" ] && kill "$(cat "$RUN/pid")" 2>/dev/null || true
    rm -f "$RUN/pid"
    for p in $(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null); do ps -o command= -p "$p" | grep -q settings_sim && kill "$p" || true; done
    echo "dashboard stopped" ;;
  status)
    if [ -f "$RUN/pid" ] && kill -0 "$(cat "$RUN/pid")" 2>/dev/null; then echo "dashboard running on http://127.0.0.1:$PORT/settings"; else echo "dashboard not running"; fi ;;
  *) echo "Usage: bash scripts/dev-dashboard.sh start|stop|status"; exit 2 ;;
esac
