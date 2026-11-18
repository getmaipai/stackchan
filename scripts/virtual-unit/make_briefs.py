#!/usr/bin/env python3
"""Write lane briefs for the tools the virtual unit does not simulate yet, in chunks of at most 7 tools of one or two related namespaces.
Usage: make_briefs.py OUTDIR [namespace,namespace ...]   (default: every namespace with a gap); prints "chunkname tools" lines.
Each chunk is one Codex run; its files are tools/<chunk>.py and host/tests/test_vu_tools_<chunk>.py.
Placement: host-side development tool. Upstream: none."""
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vunit", Path(__file__).with_name("vunit.py"))
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)
d = json.loads((ROOT / "schema" / "tools.json").read_text())
tools, args = d["tools"], d["arguments"]
only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
by_ns = defaultdict(list)
for k, v in sorted(tools.items()):
    ns = k.split(".")[1]
    if k not in vunit.SIMULATED and (only is None or ns in only):
        by_ns[ns].append((k, v))
chunks, cur, cur_ns = [], [], []
for ns, rows in sorted(by_ns.items(), key=lambda kv: -len(kv[1])):
    while len(rows) > 7:
        chunks.append(([ns], rows[:7])); rows = rows[7:]
    if cur and len(cur) + len(rows) > 7:
        chunks.append((cur_ns, cur)); cur, cur_ns = [], []
    cur += rows; cur_ns.append(ns)
if cur:
    chunks.append((cur_ns, cur))
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
seen = defaultdict(int)
for ns_list, rows in chunks:
    base = "_".join(ns_list)[:24]
    seen[base] += 1
    name = base if seen[base] == 1 else f"{base}{seen[base]}"
    lst = "\n".join(f"- {k}  args {args.get(k) or '{}'}  patch {v}" for k, v in rows)
    (out / f"{name}.md").write_text(f"""# Lane brief: virtual unit tools, chunk {name}

Goal: the virtual unit answers these {len(rows)} firmware tools with the firmware's own behavior, so the parity gap list shrinks.
Lane: codex    Model and effort: Luna low
Placement: host (development tool under scripts/virtual-unit; no firmware change). Verdict: REBUILD (the patch text is the spec).
Read first and only: scripts/virtual-unit/tools/__init__.py (registry and rules), scripts/virtual-unit/vunit.py (fake clock u.now_ms, u.state, call, the existing handlers as examples), then for each tool below only the lines around its AddTool("name"...) in the patch named (use grep -n then sed -n to read about 60 lines). Do not read anything else.
Files you may change (nothing else): scripts/virtual-unit/tools/{name}.py (new), host/tests/test_vu_tools_{name}.py (new).
Must not touch: vunit.py, tools/__init__.py, other tools/*.py, schema/, firmware/, any other test.
Contract: register each tool with @tool("self.x.y") from tools; handler(u, args) -> dict with the keys and values the firmware's lambda returns (read its return statements; a bool true becomes {{"ok": true}}); use the firmware defaults and ranges from the Property(...) lines; keep state in u.state.setdefault("{name}", ...); time only from u.now_ms; no sleeping, network or files outside tempdirs. Hardware you cannot model (camera pixels, radio scans): return the firmware's shape with a fixed value and a comment saying so. A tool you truly cannot model stays unregistered and goes in the result file. A later patch that changed or removed a tool wins.
Tools:
{lst}
Done means: cd host && uv run pytest tests/test_vu_tools_{name}.py tests/test_virtual_unit_parity.py -q   Expected: pass, with at least one test per tool (a result shape, and one state change or refusal where the tool has any). Then bash scripts/check.sh prints no FAIL.
Work in this order: write the handlers file first with every tool you can, then the tests; do not stop to ask questions or summarize before both files exist. The task is big on purpose: write all {len(rows)} handlers.
Stop rule: after 3 failing attempts at one step stop and report the failing output; do not widen scope.
Output: .runs/vu-tools-{name}.result.md (registered count, unregistered tools with reason, test result; max 15 lines); reply with one line.
Rules: docs/STYLE.md writing rules (no em dashes; error text says what went wrong and what to do); no mention of other projects or products; commit nothing (the dispatcher commits by file name).
""")
    print(name, len(rows))
