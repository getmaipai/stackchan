#!/usr/bin/env bash
# Intent: before the repo goes public, no tracked file carries labels or wording from the private reviews.
# Fails (exit 1, one line per hit) when a tracked text file matches a pattern below and the line is not in scripts/leak-sweep-allow.txt.
# Usage: bash scripts/leak-sweep.sh            tree check (this is what check.sh runs)
#        bash scripts/leak-sweep.sh --history  also list commit messages on the current branch that match (a list for the owner, never fails)
# Patterns: finding ids (FP-3, HC-1, G-9 ...), "security finding", "review finding", "audit finding", "finding N", "findings table",
# "security audit outcomes", the review's name in labels, the private doc name. Placement: repo gate. Upstream: none.
set -u
cd "$(dirname "$0")/.."
B='(^|[^A-Za-z0-9_-])'
A='([^A-Za-z0-9_-]|$)'
ID="${B}(FP|HC|HS|FM)-[0-9]+${A}|${B}[FGQHTUB]-[0-9]{1,2}${A}"
WORDS='[Ss]ecurity finding|[Rr]eview finding|[Aa]udit finding|[Ff]inding [0-9]{1,2}([^0-9]|$)|findings table|[Ss]ecurity audit outcomes|Fable review|Fable fixes|Fable item|Fable memory|security-fixes-20'
PAT="($ID|$WORDS)"
ALLOW=scripts/leak-sweep-allow.txt
hits=$(git ls-files -z | xargs -0 git grep -n -I -E "$PAT" -- 2>/dev/null | grep -v -E '^(host/tests/golden/|host/spec-vendor/|scripts/leak-sweep)' || true)
if [ -f "$ALLOW" ]; then
  hits=$(printf '%s\n' "$hits" | while IFS= read -r line; do
    path=${line%%:*}
    grep -q -F -x -- "$path" "$ALLOW" 2>/dev/null && continue
    printf '%s\n' "$line"
  done)
fi
hits=$(printf '%s' "$hits" | sed '/^$/d')
if [ -n "$hits" ]; then
  echo "leak-sweep: $(printf '%s\n' "$hits" | wc -l | tr -d ' ') line(s) name a review finding or describe a flaw. Reword to a plain safety fix, or move the text to the private notes:"
  printf '%s\n' "$hits" | cut -c1-200 | head -40
  rc=1
else
  echo "leak-sweep: ok"
  rc=0
fi
if [ "${1:-}" = "--history" ]; then
  echo "--- commit messages on this branch that match (for the owner; history is not changed here)"
  git log --format='%h %s' -E --grep="$PAT" --grep='[Ss]ecurity|[Ff]law|[Vv]ulnerab|[Ee]xploit' | head -80
fi
exit $rc
