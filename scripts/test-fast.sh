#!/usr/bin/env bash
# Intent: the host suite without the slow tests (the end to end on the virtual unit and the sanitizer fuzz, marked `slow`), in 4 pytest processes at once, for quick feedback while
# working (about 3 minutes). scripts/test-all.sh runs everything and is the gate before landing. Usage: bash scripts/test-fast.sh [pytest args]; JOBS=N changes the process count.
# Placement: repo gate helper. Upstream: none.
set -eu
exec python3 "$(dirname "$0")/test-sharded.py" -j "${JOBS:-4}" "$@"
