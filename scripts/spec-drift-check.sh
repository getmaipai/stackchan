#!/usr/bin/env bash
# Intent: the vendored spec (host/spec-vendor/spec) is a snapshot, never edited by hand. Fails when a vendored file differs from the manifest
# (a local edit) or, when the source tag is on this Mac, from the tag itself (a wrong or stale copy). Files the trimmed snapshot leaves out are fine.
# Usage: bash scripts/spec-drift-check.sh [--update]   --update rewrites the manifest: run it only right after a deliberate re-vendor and say so in the commit.
# Source tag folder: MAIPAI_COMMONS_TAGS (default ~/Developer/github.com/getmaipai/commons-tags), path taken from the "Source:" line of host/spec-vendor/STAMP.md.
# Placement: repo gate. Upstream: none.
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
V="$ROOT/host/spec-vendor"
M="$V/MANIFEST.sha256"
cd "$V"
now="$(find spec -type f | LC_ALL=C sort | while read -r f; do shasum -a 256 "$f"; done)"
if [ "${1:-}" = "--update" ]; then printf '%s\n' "$now" > "$M"; echo "spec manifest updated ($(wc -l < "$M" | tr -d ' ') files)"; exit 0; fi
[ -f "$M" ] || { echo "spec drift: host/spec-vendor/MANIFEST.sha256 is missing: run bash scripts/spec-drift-check.sh --update after checking the snapshot is the tagged one"; exit 1; }
if [ "$now" != "$(cat "$M")" ]; then
  echo "spec drift: the vendored spec no longer matches its manifest. Changed or extra files:"
  diff <(cat "$M") <(printf '%s\n' "$now") | grep '^[<>]' | awk '{print "  " $3}' | sort -u | head -10
  echo "Fix: restore the files from the source tag (never edit the vendored spec by hand); after a deliberate re-vendor run --update."
  exit 1
fi
src="$(sed -n 's/^Source: *//p' STAMP.md | head -1)"
tags="${MAIPAI_COMMONS_TAGS:-$HOME/Developer/github.com/getmaipai/commons-tags}"
if [ -n "$src" ] && [ -d "$tags/${src#commons-tags/}" ]; then
  bad=0
  while read -r f; do
    cmp -s "$f" "$tags/${src#commons-tags/}/${f#spec/}" || { echo "spec drift: $f differs from the source tag"; bad=1; }
  done < <(find spec -type f)
  [ "$bad" = 0 ] || { echo "Fix: re-vendor from the tag named in host/spec-vendor/STAMP.md."; exit 1; }
  echo "spec drift: ok (manifest and source tag agree)"
else
  echo "spec drift: ok (manifest only: the source tag is not on this Mac)"
fi
