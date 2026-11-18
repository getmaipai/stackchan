#!/usr/bin/env python3
"""Keep docs/user/index.md and docs/dev/index.md: a hand-written start, then every page of the folder listed by its title (generated, so none is lost).

Usage: python3 scripts/make-doc-indexes.py [--check]    (--check fails when an index is out of date; run by scripts/check.sh)"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- pages:start -->", "<!-- pages:end -->"

USER_START = """# MaiPai for StackChan: user guide

For people who own a robot. Each page answers one question. Not sure where to begin? Read [Getting started](getting-started.md), then [Choose a brain](choose-a-brain.md).

**First:** [Getting started](getting-started.md) · [Install the host](install-the-host.md) · [Choose a brain](choose-a-brain.md) · [Keep the host running](run-as-a-service.md) · [Troubleshooting](troubleshooting.md)

**Other sections:** [Playground](../playground/index.md) (the virtual robot) · [Developers](../dev/index.md) · [About and legal](about.md)

## All pages
"""
DEV_START = """# MaiPai for StackChan: developer guide

For people who build, fix or extend it. Users should read the [user guide](../user/index.md) instead.

**Start here:** [How it fits together](overview.md) · [Contributing](contributing.md) · [Build from source](build-from-source.md) · [Host and brains](host-and-brains.md) · [The choices rule](choices-rule.md) · [Memory budget](memory-budget.md)

**Find by question:**
- *How do I run the robot without hardware?* [Virtual unit](virtual-unit.md), [End to end check](e2e-virtual-unit.md), [Test speed](test-speed.md)
- *How is memory spent?* [Memory budget](memory-budget.md), [Internal RAM](internal-ram-tasks.md), [Cost of features that are off](off-cost.md)
- *What keeps the host alive?* [Service](stackchan-service.md), [Watchdog inventory](watchdog-inventory.md), [Updater](updater.md)
- *What leaves my home?* [Egress table](egress-table.md), [Software-only protection](software-only-protection.md)
- *Which numbers did we measure?* [Gate numbers](gate-numbers.md), [Unit measurements](stackchan-unit-measurements.md), [Voice measurements](stackchan-voice-measurements-2026-10-20.md), [Battery](battery-and-power.md)
- *What is the robot's screen, face or head doing?* [Screens](screens-contact-sheets.md), [Faces](stackchan-faces-2026-11-14.md), [Head recording](head-recording.md), [Dance](dance-entry-points.md)
- *What is wrong or open?* [Cross-review bugs](cross-review-status.md), [Fuzzing](fuzzing-and-hostile-peer.md), [Choices audits](host-choices-audit.md)

**Plans and decisions:** [Decisions](../design/decisions.md) · [Plans](../plan/) · [Readiness](../plan/release-readiness.md) · [Feature ledger](feature-ledger.md)

**Other sections:** [User guide](../user/index.md) · [Playground](../playground/index.md)

## All pages
"""


def title(path: Path) -> str:
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ")


def listing(folder: Path, skip: set[str]) -> str:
    rows = sorted((p for p in folder.glob("*.md") if p.name not in skip), key=lambda p: p.name)
    return "\n".join(f"- [{title(p)}]({p.name})" for p in rows)


def build(folder: str, start: str) -> str:
    base = ROOT / "docs" / folder
    return start + START + "\n" + listing(base, {"index.md"}) + "\n" + END + "\n"


def main(argv: list[str]) -> int:
    stale = []
    for folder, start in (("user", USER_START), ("dev", DEV_START)):
        target = ROOT / "docs" / folder / "index.md"
        text = build(folder, start)
        if "--check" in argv:
            if not target.exists() or target.read_text() != text:
                stale.append(str(target.relative_to(ROOT)))
        else:
            target.write_text(text)
    if stale:
        print("doc indexes out of date: " + ", ".join(stale) + ". Run python3 scripts/make-doc-indexes.py.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
