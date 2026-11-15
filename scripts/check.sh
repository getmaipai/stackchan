#!/usr/bin/env bash
# Intent: repo gate. Hygiene check over every tracked file; add tests here as they exist.
set -eu
cd "$(dirname "$0")/.."
bash scripts/hygiene-check.sh $(git ls-files -co --exclude-standard)

bash scripts/boundary-check.sh
