#!/usr/bin/env bash
# Intent: rebuild the firmware tree from this repo alone: the pinned upstream bases (firmware/BASE), then every patch of
# firmware/patches/ORDER, in order, with git apply. Optionally compile while it goes. Nothing outside TREE is touched.
# Usage: bash scripts/fw-rebuild.sh TREE [--compile-every N] [--kind plain|bench|gate] [--stop-at PATCH] [--from-local DIR] [--list-misplaced]
#   --compile-every N  build after every Nth patch (1 = after every patch; 0 = only at the end; default 0). A build after a patch
#                      listed in firmware/patches/MISPLACED is skipped (it is known broken until its repair patch).
#   --from-local DIR   take the base from a local copy of the outer repo (with its nested tree) instead of downloading it.
#   --list-misplaced   print firmware/patches/MISPLACED and exit.
# Before any git command on the Mac Studio: source data-scratch/bin/https-git.env (the SSH alias hangs).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
P="$ROOT/firmware/patches"
TREE=""; EVERY=0; KIND=plain; STOP=""; LOCAL=""
while [ $# -gt 0 ]; do
    case "$1" in
        --compile-every) EVERY=$2; shift 2 ;;
        --kind) KIND=$2; shift 2 ;;
        --stop-at) STOP=$2; shift 2 ;;
        --from-local) LOCAL=$2; shift 2 ;;
        --list-misplaced) grep -v '^#' "$P/MISPLACED" | grep .; exit 0 ;;
        -*) echo "Unknown option $1. See the usage line at the top of scripts/fw-rebuild.sh." >&2; exit 1 ;;
        *) TREE=$1; shift ;;
    esac
done
[ -n "$TREE" ] || { echo "Usage: fw-rebuild.sh TREE [options]. TREE must not exist yet." >&2; exit 1; }
[ ! -e "$TREE" ] || { echo "$TREE already exists. Pass a new folder so no earlier work is overwritten." >&2; exit 1; }
base() { sed -n "s/^$1=//p" "$ROOT/firmware/BASE"; }
OUTER_URL=$(base outer_repository); OUTER=$(base outer_commit); NESTED=$(base nested_commit)
mkdir -p "$TREE"; TREE=$(cd "$TREE" && pwd)
if [ -n "$LOCAL" ]; then
    git clone -q --no-checkout "$LOCAL" "$TREE"
else
    git clone -q --no-checkout "$OUTER_URL" "$TREE"
fi
git -C "$TREE" checkout -q --detach "$OUTER"
if [ -n "$LOCAL" ] && [ -d "$LOCAL/firmware/xiaozhi-esp32/.git" ]; then
    # Local copy: take its nested tree at the pinned commit, without its uncommitted edits.
    git clone -q --no-checkout "$LOCAL/firmware/xiaozhi-esp32" "$TREE/firmware/xiaozhi-esp32"
    git -C "$TREE/firmware/xiaozhi-esp32" checkout -q --detach "$NESTED"
    [ -d "$LOCAL/firmware/components" ] && mkdir -p "$TREE/firmware/components" && cp -cR "$LOCAL/firmware/components/." "$TREE/firmware/components/"
else
    ( cd "$TREE/firmware" && python3 fetch_repos.py )
    git -C "$TREE/firmware/xiaozhi-esp32" checkout -q --detach "$NESTED"
    # fetch_repos.py applies the upstream vendor patch; the ORDER patches carry those edits themselves (B01), so start from the clean pinned commit.
    git -C "$TREE/firmware/xiaozhi-esp32" checkout -q -f --detach "$NESTED"
    git -C "$TREE/firmware/xiaozhi-esp32" clean -fdq
fi
[ "$(git -C "$TREE/firmware/xiaozhi-esp32" rev-parse HEAD)" = "$NESTED" ] || { echo "The nested tree is not at $NESTED. Check firmware/BASE and the download, then retry." >&2; exit 1; }
cd "$TREE"
n=0; total=$(grep -v '^#' "$P/ORDER" | grep -c .)
mkdir -p "$ROOT/.runs"; LOG="$ROOT/.runs/fw-rebuild.log"; : > "$LOG"
for f in $(grep -v '^#' "$P/ORDER" | grep .); do
    n=$((n+1))
    awk '/^diff --git|^--- /{p=1} p' "$P/$f" > "$TREE/.patch.diff"
    if ! git apply --whitespace=nowarn "$TREE/.patch.diff" 2>"$TREE/.apply.err"; then
        echo "FAIL apply $n/$total $f" | tee -a "$LOG"; head -8 "$TREE/.apply.err" | tee -a "$LOG"
        echo "Fix: the patch no longer applies after the patches before it. Rebase $f onto the tree in $TREE." >&2; exit 1
    fi
    echo "ok $n/$total $f" >> "$LOG"
    if [ "$EVERY" -gt 0 ] && [ $((n % EVERY)) -eq 0 ] && ! grep -q "^$f " "$P/MISPLACED"; then
        if bash "$ROOT/scripts/fw-build.sh" "$TREE" "$KIND" >"$ROOT/.runs/fw-rebuild-build.log" 2>&1; then
            echo "built after $n/$total $f" | tee -a "$LOG"
        else
            echo "FAIL build after $n/$total $f (log .runs/fw-rebuild-build.log)" | tee -a "$LOG"; exit 2
        fi
    fi
    [ -n "$STOP" ] && [ "$f" = "$STOP" ] && { echo "stopped at $f" | tee -a "$LOG"; exit 0; }
done
rm -f "$TREE/.patch.diff" "$TREE/.apply.err"
echo "applied $n/$total patches into $TREE" | tee -a "$LOG"
bash "$ROOT/scripts/fw-build.sh" "$TREE" "$KIND" >"$ROOT/.runs/fw-rebuild-build.log" 2>&1 && echo "final build OK ($KIND)" | tee -a "$LOG" || { echo "FAIL final build (log .runs/fw-rebuild-build.log)" | tee -a "$LOG"; exit 2; }
