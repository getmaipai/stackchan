#!/usr/bin/env bash
# Intent: block any mention of projects we studied (private word list), em dashes and filler words in
# staged files and in a commit message, with a one-line verdict. Zero model tokens.
# Usage: hygiene-check.sh [--msg FILE] [paths...]   (no paths: staged files)
# Word list: $NO_MENTION_WORDS or ~/.config/maipai/no-mention-words.txt (one word or phrase per line, never committed).
# Allowed places for factual notices: LICENSE, NOTICE, THIRD-PARTY*, and lines starting "# Upstream:" in patches.
set -u
WORDS="${NO_MENTION_WORDS:-$HOME/.config/maipai/no-mention-words.txt}"
MSG=""; PATHS=()
while [ $# -gt 0 ]; do
  case "$1" in --msg) MSG="$2"; shift 2;; *) PATHS+=("$1"); shift;; esac
done
if [ ${#PATHS[@]} -eq 0 ]; then
  while IFS= read -r f; do PATHS+=("$f"); done < <(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null)
fi
bad=0; out=""
[ -f "$WORDS" ] || { echo "hygiene: FAIL word list missing ($WORDS); create it (one name per line, outside the repo)"; exit 2; }
scan() { # $1 label, stdin text
  local label="$1" text hits
  text="$(cat)"
  hits="$(printf '%s\n' "$text" | grep -n -i -F -f "$WORDS" | head -5)"
  [ -n "$hits" ] && { bad=1; out+="  mention in $label:"$'\n'"$(printf '%s\n' "$hits" | sed 's/^/    /')"$'\n'; }
  if printf '%s' "$text" | grep -q $'\xe2\x80\x94'; then bad=1; out+="  em dash in $label"$'\n'; fi
  hits="$(printf '%s\n' "$text" | grep -n -i -E '\b(delve|seamless(ly)?|robust|leverage|empower|streamline|game-changer)\b' | head -3)"
  [ -n "$hits" ] && { bad=1; out+="  filler word in $label:"$'\n'"$(printf '%s\n' "$hits" | sed 's/^/    /')"$'\n'; }
}
for f in ${PATHS[@]+"${PATHS[@]}"}; do
  [ -f "$f" ] || continue
  case "$(basename "$f")" in LICENSE*|NOTICE*|THIRD-PARTY*|hygiene-check.sh) continue;; esac
  case "$f" in *.png|*.jpg|*.webp|*.mp4|*.bin|*.gz|*.woff*|*.ico) continue;; esac
  scan "$f" < <(grep -v -E '^[+ ]?# Upstream:' "$f")
done
[ -n "$MSG" ] && [ -f "$MSG" ] && scan "commit message" < "$MSG"
if [ $bad -eq 0 ]; then echo "hygiene: ok (${#PATHS[@]} files)"; exit 0; fi
echo "hygiene: FAIL"; printf '%s' "$out"; exit 1
