#!/usr/bin/env bash
# Intent: repo gate. Hygiene check over every tracked file; add tests here as they exist.
set -eu
cd "$(dirname "$0")/.."
# The last line always says the outcome, so a caller that filters the output for words still sees a failure (a filtered run once missed the choices check and left main red).
trap 'rc=$?; if [ "$rc" -eq 0 ]; then echo "check: ALL PASSED"; else echo "check: FAILED (exit $rc), read the lines above"; fi' EXIT
bash scripts/hygiene-check.sh $(git ls-files -co --exclude-standard)

bash scripts/boundary-check.sh
python3 scripts/efuse-check.py || exit 1  # owner decision 14: nothing burns an eFuse

bash scripts/spec-drift-check.sh
python3 scripts/golden-stamp.py || exit 1  # the renderer goldens are for this ORDER (regenerate them in the landing that changes it)
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
python3 scripts/captions-check.py || exit 1
python3 scripts/funding-check.py || exit 1
python3 scripts/docs-grade.py --max 7 >/dev/null || { python3 scripts/docs-grade.py --max 7 | grep -B1 "long:"; echo "docs-grade: a user page reads above grade 7; shorten its long sentences"; exit 1; }
echo "docs-grade: ok"
"$PY" scripts/choices-check.py || exit 1
python3 scripts/make-doc-indexes.py --check || exit 1
if git grep -nI -E '^(<<<<<<< |>>>>>>> )' -- . ':!host/tests/fixtures' ':!*.patch' >/tmp/conflict-markers.$$ 2>/dev/null; then cat /tmp/conflict-markers.$$; rm -f /tmp/conflict-markers.$$; echo "conflict markers: a tracked file still holds merge conflict markers. Resolve them (keep one coherent text) and commit."; exit 1; fi
rm -f /tmp/conflict-markers.$$
echo "conflict markers: none"
python3 scripts/virtual-unit/tools_extract.py --check

python3 scripts/make-vu-screenshots.py --check
python3 scripts/readiness.py --check
"$PY" scripts/dashboard-words-check.py
"$PY" scripts/feature-ledger.py --check   # the host environment is the one source for the ledger (python3 on the Mac is 3.9 and can render it differently); regenerate with: cd host && uv run python ../scripts/feature-ledger.py
