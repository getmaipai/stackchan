#!/usr/bin/env python3
"""Brings the face overlay tree (.runs/fixtree, made by build-face.sh from a replayed firmware tree) up to the whole patch series (firmware/patches/ORDER).

For each patch in ORDER that touches only firmware/main/hal and firmware/main/stackchan (the folders the overlay copies): already in the tree (it reverses cleanly) -> skipped; applies
cleanly -> applied; neither -> the build fails and says which patch and why. Patches that touch anything else are the tree's own business (the tree was replayed from the series). Writes
.runs/vu-build/tree-stamp.json (the tree, the ORDER hash, what was applied, skipped and left alone): host/tests/test_virtual_unit_tree_stamp.py fails when the renderer was not built from the
current series, so the goldens can never silently come from an old tree again.
Usage: overlay_patches.py <overlay root (.runs/fixtree)> <source tree root>. Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / "firmware" / "patches"


def order() -> list[str]:
    return [l.strip() for l in (PATCHES / "ORDER").read_text().splitlines() if l.strip() and not l.startswith("#")]


def files_of(patch: Path) -> list[str]:
    return re.findall(r"^diff --git a/(\S+) b/", patch.read_text(errors="ignore"), re.M)


def run(args: list[str], cwd: Path, stdin: bytes) -> bool:
    return subprocess.run(args, cwd=cwd, input=stdin, capture_output=True).returncode == 0


def main() -> int:
    overlay, source = Path(sys.argv[1]), Path(sys.argv[2])
    applied, skipped, alone, failed = [], [], [], []
    names = order()
    texts: dict[str, bytes] = {}
    mine: list[str] = []
    for name in names:
        p = PATCHES / name
        files = files_of(p)
        if not files or not all(f.startswith(("firmware/main/hal/", "firmware/main/stackchan/")) for f in files):
            alone.append(name)
        else:
            mine.append(name)
            texts[name] = p.read_bytes()
    # the newest patch of the series the tree already holds: from the end of the series, the first overlay patch that reverses cleanly (a patch that a later one changed cannot be
    # tested alone, but the newest one the tree has is always testable); everything after it is applied in order
    last = -1
    for i in range(len(mine) - 1, -1, -1):
        if run(["patch", "-p1", "-R", "--dry-run", "-s", "-f", "-N"], overlay, texts[mine[i]]):
            last = i
            break
    skipped = mine[: last + 1]
    for name in mine[last + 1 :]:
        if run(["patch", "-p1", "--dry-run", "-s", "-f"], overlay, texts[name]):
            run(["patch", "-p1", "-s", "-f"], overlay, texts[name])
            applied.append(name)
        else:
            failed.append(name)
            break
    stamp = {"tree": str(source), "order_sha": hashlib.sha1((PATCHES / "ORDER").read_bytes()).hexdigest(), "applied": applied, "already_in_tree": skipped, "not_in_overlay": alone, "failed": failed}
    out = ROOT / ".runs" / "vu-build"
    out.mkdir(parents=True, exist_ok=True)
    (out / "tree-stamp.json").write_text(json.dumps(stamp, indent=1) + "\n")
    print(f"overlay patches: {len(skipped)} already in the tree, {len(applied)} applied ({', '.join(applied[:6])}), {len(alone)} outside the overlay, {len(failed)} failed")
    if failed:
        print("FAILED: " + ", ".join(failed) + ". The tree and the series disagree: use a tree replayed from the current ORDER (MAIPAI_FW_TREE_ROOT).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
