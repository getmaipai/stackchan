#!/usr/bin/env bash
# Intent: run the exposure suite (see scripts/exposure-test.py). Usage: bash scripts/exposure-test.sh [--write]
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 scripts/exposure-test.py "$@"
