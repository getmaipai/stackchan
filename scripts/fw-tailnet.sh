#!/usr/bin/env bash
# Intent: download the pinned private-network client (firmware/tailnet/PIN) into a folder outside the firmware tree,
# reset it to the pinned commit and apply the library patch (firmware/tailnet/microlink.patch).
# Usage: bash scripts/fw-tailnet.sh   then   source scripts/fw-env.sh   (fw-env.sh names the folder to the build).
# MAIPAI_DEPS sets the parent folder (default ~/esp/maipai-deps). MAIPAI_MICROLINK_REPO overrides the address to fetch from
# (a local clone, for an offline build); the commit check still applies.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
pin() { sed -n "s/^$1=//p" "$ROOT/firmware/tailnet/PIN"; }
REPO=${MAIPAI_MICROLINK_REPO:-$(pin repository)}
COMMIT=$(pin commit)
DEST=${MAIPAI_DEPS:-$HOME/esp/maipai-deps}/microlink
[[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || { echo "firmware/tailnet/PIN has no 40-character commit. Fix the file and retry." >&2; exit 1; }
mkdir -p "$(dirname "$DEST")"
[[ -d "$DEST/.git" ]] || git clone --no-checkout "$REPO" "$DEST"
git -C "$DEST" fetch --no-tags "$REPO" "$COMMIT"
git -C "$DEST" checkout --detach --force "$COMMIT"
git -C "$DEST" clean -fdq
[[ "$(git -C "$DEST" rev-parse HEAD)" == "$COMMIT" ]] || { echo "The download does not match the pinned commit. Check the repository address and retry." >&2; exit 1; }
sed -n '/^diff --git/,$p' "$ROOT/firmware/tailnet/microlink.patch" > "$DEST/.maipai-lib.patch"
git -C "$DEST" apply --check .maipai-lib.patch || { echo "The library patch does not apply to $COMMIT. Update firmware/tailnet/ together with the pin." >&2; exit 1; }
git -C "$DEST" apply .maipai-lib.patch
rm -f "$DEST/.maipai-lib.patch"
echo "Private-network client ready at $DEST (commit $COMMIT, library patch applied)."
echo "Next: source scripts/fw-env.sh"
