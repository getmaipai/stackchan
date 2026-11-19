#!/usr/bin/env bash
# Intent: make the clean host environment (.runs/e2e-venv, a fresh install of host/ as the README's pipx step does) that the security scan and the exposure suite run the real host in. The release gate calls it first, so a fresh checkout needs no earlier e2e run.
# Usage: bash scripts/build-clean-host-env.sh   (safe to run again: it reinstalls the current code)
# Placement: release tooling. Upstream: none.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.runs/e2e-venv"
mkdir -p "$ROOT/.runs"
[ -x "$VENV/bin/stackchan" ] || uv venv -q "$VENV" --python 3.13
uv pip install -q --python "$VENV/bin/python" "$ROOT/host"
echo "clean host environment ready: $VENV"
