#!/usr/bin/env bash
# Intent: run the repo security scan (see scripts/security-scan.py). Usage: bash scripts/security-scan.sh [--write]
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 scripts/security-scan.py "$@"
