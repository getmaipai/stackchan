#!/usr/bin/env python3
"""The cross-review bug table: every test in host/tests/test_cross_review_open_bugs*.py, its owner, and whether the bug is still open.

Each bug is a test whose docstring starts "owner: <who> (<file>)". Open: the test is marked strict xfail and still fails. Fixed: it passes (the marker was removed: a regression test now) or it
"unexpectedly passes" under the strict marker (the fix landed; the marker is still there and the run fails until it is deleted). Run after pulling origin/main:
  python3 scripts/review-status.py            write docs/dev/cross-review-status.md
  python3 scripts/review-status.py --check    exit 1 when the committed table is out of date
Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "dev" / "cross-review-status.md"
FILES = sorted((ROOT / "host" / "tests").glob("test_cross_review_open_bugs*.py"))


def bugs() -> list[dict]:
    rows = []
    for path in FILES:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                doc = ast.get_docstring(node) or ""
                m = re.match(r"(?i)owner: ([^(.,\n]+?)(?: \(([^)]*)\))?[.,]\s*(.*)", doc, re.S)
                if not m:
                    continue
                rows.append({"file": path.name, "test": node.name, "owner": m.group(1).strip().lower().replace(" track", ""), "where": m.group(2) or "", "what": " ".join(m.group(3).split())[:200]})
    return rows


def results() -> dict[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        xml = Path(tmp) / "r.xml"
        subprocess.run(["uv", "run", "--project", "host", "python", "-m", "pytest", *[str(f) for f in FILES], "-q", "-p", "no:cacheprovider", f"--junitxml={xml}"], cwd=ROOT, capture_output=True, text=True)
        out: dict[str, str] = {}
        for case in ET.parse(xml).getroot().iter("testcase"):
            name = case.get("name", "").split("[")[0]
            if case.find("skipped") is not None:
                state = "open"
            elif case.find("failure") is not None:
                state = "fixed (remove the xfail marker)" if "XPASS" in (case.find("failure").get("message") or "") else "FAILING"
            else:
                state = "fixed"
            if out.get(name) in (None, "fixed", "fixed (remove the xfail marker)") or state == "open":
                out[name] = state if out.get(name) != "open" else "open"
        return out


def render() -> str:
    res = results()
    rows = bugs()
    lines = ["# Cross-review bugs: fixed and still open", "", "Made by `python3 scripts/review-status.py` from `host/tests/test_cross_review_open_bugs*.py` (each bug is a test; run it after pulling `origin/main`). "
             "`open` is a strict xfail that still fails. `fixed` passes now; `fixed (remove the xfail marker)` means the fix landed and the marker must go.", "",
             "| Status | Owner | Where | What | Test |", "|---|---|---|---|---|"]
    counts: dict[tuple[str, str], int] = {}
    for r in rows:
        st = res.get(r["test"], "not run")
        counts[(r["owner"], "open" if st == "open" else "fixed" if st.startswith("fixed") else st)] = counts.get((r["owner"], "open" if st == "open" else "fixed" if st.startswith("fixed") else st), 0) + 1
        lines.append(f"| {st} | {r['owner']} | {r['where']} | {r['what']} | `{r['file']}::{r['test']}` |")
    lines += ["", "## Count by owner", "", "| Owner | Open | Fixed |", "|---|---|---|"]
    for owner in sorted({o for o, _ in counts}):
        lines.append(f"| {owner} | {counts.get((owner, 'open'), 0)} | {counts.get((owner, 'fixed'), 0)} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    page = render()
    if "--check" in sys.argv:
        if not OUT.is_file() or OUT.read_text() != page:
            print("review-status: docs/dev/cross-review-status.md is out of date. Run python3 scripts/review-status.py.")
            return 1
        print("review-status: ok")
        return 0
    OUT.write_text(page)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
