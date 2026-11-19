#!/usr/bin/env python3
"""The renderer goldens (host/tests/golden) are made for one firmware/patches/ORDER, and host/tests/golden/golden-order.sha1 holds that ORDER's hash. This check fails when ORDER has changed and the goldens were not
regenerated in the same landing: a patch that joins ORDER changes screens, and a golden from before it silently describes a unit that no longer exists. scenarios.py writes the stamp itself at the end of a clean
full run, so the fix is always the same: bash scripts/fw-ref-tree.sh, then MAIPAI_FW_TREE_ROOT=<its tree> python3 scripts/virtual-unit/scenarios.py --update (look at what changed), then scenarios.py once more
without --update (it must print "clean"), and commit the goldens and the stamp. Usage: python3 scripts/golden-stamp.py [--check]. Placement: repo gate. Upstream: scripts/virtual-unit/scenarios.py."""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAMP = ROOT / "host" / "tests" / "golden" / "golden-order.sha1"


def main() -> int:
    want = hashlib.sha1((ROOT / "firmware" / "patches" / "ORDER").read_bytes()).hexdigest()
    have = STAMP.read_text().strip() if STAMP.exists() else ""
    if have == want:
        print("golden stamp: ok (the goldens are for this firmware/patches/ORDER)")
        return 0
    print("golden stamp: FAIL. firmware/patches/ORDER changed since the renderer goldens were made" + ("" if have else " (there is no stamp yet)") + ". Regenerate them in this landing: "
          "bash scripts/fw-ref-tree.sh, then MAIPAI_FW_TREE_ROOT=<that tree> python3 scripts/virtual-unit/scenarios.py --update, look at what changed, run scenarios.py again without --update until it says clean, "
          "and commit the goldens and host/tests/golden/golden-order.sha1.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
