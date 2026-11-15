#!/usr/bin/env bash
# Intent: point this clone at the tracked hooks (repo-local config only, never global).
set -eu
cd "$(dirname "$0")/.."
git config --local core.hooksPath .githooks
echo "hooks: .githooks active"
