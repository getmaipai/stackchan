#!/usr/bin/env bash
# Intent: keep Home-grade feature code out of this repo (docs/design/repo-boundaries.md). Zero model tokens.
# Fails when (1) a tracked file under host/maipai_body matches a Home-feature pattern and is not on the debt list,
# (2) the own-LLM brain imports Home code, (3) a firmware patch outside the debt list has no "# Placement:" line.
# The debt list (docs/design/boundary-debt.txt) holds the old modules still waiting to leave; it may only shrink.
set -eu
cd "$(dirname "$0")/.."
DEBT=docs/design/boundary-debt.txt
bad=0
say() { echo "$1" >&2; bad=1; }
QUESTIONS="Ask three questions: does it need this robot's body or the loop to talk through it (stay here)? is it the same for every bot (definition: commons/spec; logic: Home)? is it about the household, other devices or policy (Home)? See docs/design/repo-boundaries.md."
PATTERN='(/vision/|presence_watch|companion|announce|routines|speaker_evidence|speaker_fusion|voiceprint|owner_levels|music_identify|ambient_vision|person_tracker|meeting_faces|/dashboard/|watch_mode|monitor_mode|alert|recogni|identity|mqtt|homeassistant|home_assistant)'
while IFS= read -r f; do
  case "$f" in host/maipai_body/brain/home.py|host/tests/*) continue;; esac
  grep -qxF "$f" "$DEBT" 2>/dev/null && continue
  say "boundary: $f looks like Home feature logic and is not on the debt list. $QUESTIONS"
done < <(git ls-files -co --exclude-standard host/maipai_body | grep -E "$PATTERN" || true)
if git ls-files -co --exclude-standard host/maipai_body/brain | grep -q own_llm; then
  if grep -nE '^\s*(from|import)\s+(maipai_body\.(hub_host|link)|maipai_body\.brain\.home)' host/maipai_body/brain/own_llm*.py >/dev/null 2>&1; then
    say "boundary: the own-LLM brain imports Home code; it must work with no Home present."
  fi
fi
for p in $(git ls-files -co --exclude-standard firmware/patches 2>/dev/null | grep '\.patch$' || true); do
  grep -qxF "$p" "$DEBT" 2>/dev/null && continue
  grep -q '^# Placement:' "$p" || say "boundary: $p has no '# Placement: unit | host | home-preset (reason)' line. $QUESTIONS"
done
[ $bad -eq 0 ] && echo "boundary: ok"
exit $bad
