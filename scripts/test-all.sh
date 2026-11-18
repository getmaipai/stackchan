#!/usr/bin/env bash
# Intent: the complete host suite, with the virtual unit renderers built first when a firmware tree is on this Mac. Run before landing.
# Usage: bash scripts/test-all.sh [pytest args]   Prints the pytest summary line; exit 1 on any failure.
# Env: MAIPAI_FW_TREE_ROOT (default ~/esp/stackchan-rebase/final15). Without a tree the virtual unit tests skip with one clear message.
# Placement: repo gate. Upstream: none.
set -eu
cd "$(dirname "$0")/../host"
MAIPAI_BUILD_RENDERER=1 uv run pytest -q "$@" 2>&1 | tail -15
exit "${PIPESTATUS[0]}"
