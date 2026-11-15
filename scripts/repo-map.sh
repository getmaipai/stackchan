#!/usr/bin/env bash
# Intent: generate docs/design/INDEX.md, a one-line-per-file map (path, size, first comment or heading line),
# so a lane reads one short index instead of grepping the tree. Regenerate on every landing (zero model tokens).
# Usage: repo-map.sh [root=.] [out=docs/design/INDEX.md]
set -u
ROOT="${1:-.}"; OUT="${2:-docs/design/INDEX.md}"
cd "$ROOT" || exit 2
mkdir -p "$(dirname "$OUT")"
{
  echo "# Repo index (generated, do not edit)"; echo
  echo "One line per file: path, lines, purpose (first comment or heading)."; echo
  git ls-files 2>/dev/null | grep -v -E '(^|/)(node_modules|\.runs|data-)|\.(png|jpg|webp|mp4|bin|gz|lock|woff2?)$|INDEX\.md$' | while IFS= read -r f; do
    [ -f "$f" ] || continue
    n=$(wc -l < "$f" | tr -d ' ')
    p=$(grep -m1 -E '^[[:space:]]*(#|//|/\*+|\*|"""|--)[[:space:]]*[A-Za-z]' "$f" 2>/dev/null | sed -E 's/^[[:space:]]*(#+|\/\/+|\/\*+|\*|"""|--)[[:space:]]*//; s/^(Intent|Purpose):[[:space:]]*//' | cut -c1-110)
    echo "- \`$f\` ($n): ${p:-no header}"
  done
} > "$OUT"
echo "repo-map: wrote $OUT ($(wc -l < "$OUT" | tr -d ' ') lines)"
