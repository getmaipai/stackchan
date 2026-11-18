#!/usr/bin/env bash
# Intent: repo gate. Hygiene check over every tracked file; add tests here as they exist.
set -eu
cd "$(dirname "$0")/.."
bash scripts/hygiene-check.sh $(git ls-files -co --exclude-standard)

bash scripts/boundary-check.sh

bash scripts/spec-drift-check.sh
# Secret scan: tracked files by the image-level scanner, tracked files and history by gitleaks when it is installed.
git ls-files -z | xargs -0 python3 scripts/check-no-keys.py >/dev/null || { echo "secrets: FAIL (check-no-keys.py found a key-shaped value)"; exit 1; }
if command -v gitleaks >/dev/null 2>&1; then
  gitleaks detect --no-git --source . -c .gitleaks.toml --redact --no-banner >/dev/null 2>&1 || { echo "secrets: FAIL (gitleaks, current files)"; exit 1; }
  # History is scanned on request (bash scripts/check.sh --history): early commits hold old test fakes (docs/plan/history-scan-2026-11-18.md).
  if [ "${1:-}" = "--history" ]; then
    gitleaks detect --source . -c .gitleaks.toml --redact --no-banner --log-opts="--all" >/dev/null 2>&1 || { echo "secrets: FAIL (gitleaks, history)"; exit 1; }
  fi
fi
echo "secrets: ok"
# Licenses: dependencies named in THIRD-PARTY.md, LICENSE is the AGPL, SPDX lines use a stated license.
PY=python3; [ -x host/.venv/bin/python ] && PY=host/.venv/bin/python
"$PY" scripts/license-check.py || exit 1

bash scripts/leak-sweep.sh
python3 scripts/docs-claims-check.py
python3 scripts/virtual-unit/tools_extract.py --check

python3 scripts/make-vu-screenshots.py --check
python3 scripts/readiness.py --check
