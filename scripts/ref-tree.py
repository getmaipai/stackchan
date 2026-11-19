#!/usr/bin/env python3
"""Prints the firmware tree the renderer goldens and the unit checks run against. MAIPAI_FW_TREE_ROOT wins when it is set. Otherwise the tree is the canonical reference tree of main
(~/esp/stackchan-rebuild/main-ref, or MAIPAI_FW_REF_TREE), made by scripts/fw-ref-tree.sh: it must exist with its bench configuration and must have been replayed from the same firmware/patches/ORDER
this checkout has (its .main-ref-commit holds the commit of main it was made from). If it is missing or older than ORDER this exits 1 with a plain message instead of picking some other tree.
Usage: python3 scripts/ref-tree.py   (prints the path). Placement: host-side development tool. Upstream: scripts/fw-ref-tree.sh."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def resolve():
    """Returns (path, None) or (None, the message to show the person)."""
    env = os.environ.get("MAIPAI_FW_TREE_ROOT")
    if env:
        return Path(env), None
    tree = Path(os.environ.get("MAIPAI_FW_REF_TREE", str(Path.home() / "esp" / "stackchan-rebuild" / "main-ref")))
    fix = "Run bash scripts/fw-ref-tree.sh (it replays main's patch order and prints the tree), then run this again; or set MAIPAI_FW_TREE_ROOT to a tree replayed from this checkout's firmware/patches/ORDER."
    if not (tree / "firmware" / "build-bench" / "config" / "sdkconfig.h").exists():
        return None, f"The reference firmware tree is missing or not built ({tree}). {fix}"
    stamp = tree / ".main-ref-commit"
    if not stamp.exists():
        return None, f"The reference firmware tree {tree} has no .main-ref-commit, so its age cannot be checked. {fix}"
    commit = stamp.read_text().strip()
    shown = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:firmware/patches/ORDER"], capture_output=True, text=True)
    order = ROOT / "firmware" / "patches" / "ORDER"
    if shown.returncode != 0:
        return None, f"The reference firmware tree was made from {commit[:10]}, a commit this checkout does not have (git fetch first). {fix}"
    if shown.stdout != order.read_text():
        return None, f"The reference firmware tree {tree} is older than firmware/patches/ORDER: its patch order is the one of {commit[:10]}, this checkout's differs. {fix}"
    return tree, None


def main() -> int:
    tree, why = resolve()
    if why:
        print(why, file=sys.stderr)
        return 1
    print(tree)
    return 0


if __name__ == "__main__":
    sys.exit(main())
