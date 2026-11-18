#!/usr/bin/env python3
"""Turn a plain `diff -u` patch into the git style the repo's replay and tests read: a `diff --git` line before every file diff, and `new file mode`
for a file made from /dev/null. Usage: gitify.py FILE.patch...   (safe to run again)
Placement: host-side development tool. Upstream: none."""
import re
import sys
from pathlib import Path

for name in sys.argv[1:]:
    lines = Path(name).read_text().splitlines(True)
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ ") and not (out and out[-1].startswith(("new file", "index"))):
            old = ln[4:].split("\t")[0].strip()
            new = lines[i + 1][4:].split("\t")[0].strip()
            path = new[2:] if new.startswith("b/") else new
            prev = "".join(out[-3:])
            if f"diff --git a/{path} b/{path}" not in prev:
                out.append(f"diff --git a/{path} b/{path}\n")
                if old == "/dev/null":
                    out.append("new file mode 100644\n")
            out.append(f"--- {old}\n")
            out.append(f"+++ {new}\n")
            i += 2
            continue
        out.append(ln)
        i += 1
    Path(name).write_text("".join(out))
