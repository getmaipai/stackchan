#!/usr/bin/env bash
# Intent: the complete host suite, with the virtual unit renderers built first when a firmware tree is on this Mac. Run before landing.
# Usage: bash scripts/test-all.sh [pytest args]        runs everything, including the tests marked slow, in 4 pytest processes at once (scripts/test-sharded.py; about 6 minutes)
#        JOBS=1 bash scripts/test-all.sh               one process, the old way (about 25 minutes)
#        bash scripts/test-fast.sh [pytest args]       the same without the slow tests (the end to end and the sanitizer fuzz): the quick check while working
# Prints one line per group and a total; exit 1 on any failure.
# The end to end on the virtual unit (tests/test_e2e_virtual_unit.py, docs/dev/e2e-virtual-unit.md) is part of the suite; MAIPAI_E2E=0 skips it.
# Env: MAIPAI_FW_TREE_ROOT (default ~/esp/stackchan-rebase/final15). Without a tree the virtual unit tests skip with one clear message.
# Placement: repo gate. Upstream: none.
set -eu
JOBS="${JOBS:-4}"
if [ "$JOBS" = 1 ]; then
  cd "$(dirname "$0")/../host"
  MAIPAI_BUILD_RENDERER=1 uv run pytest -q "$@" 2>&1 | tail -15
  exit "${PIPESTATUS[0]}"
fi
exec python3 "$(dirname "$0")/test-sharded.py" -j "$JOBS" --slow "$@"
