#!/usr/bin/env python3
"""Run the host suite in N pytest processes at once, one group of test files each (no plugin needed). Files are dealt out largest first by the time they took last run
(`.runs/test-times.json`, written by this script), so the groups finish together. Every group is a separate process with its own temp folders; tests that need a fixed port or a
shared folder belong in a file of their own marked `serial` and run alone after the groups.
Usage: python3 scripts/test-sharded.py [-j N, default 4] [--slow] [pytest args]    --slow includes the tests marked slow (the end to end and the fuzz); without it they are left out.
Prints one summary line per group and a total; exit 1 when any group fails. Placement: repo gate helper. Upstream: none."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "host"
TIMES = ROOT / ".runs" / "test-times.json"


def main(argv: list[str]) -> int:
    jobs, slow, extra = 4, False, []
    it = iter(argv)
    for a in it:
        if a == "-j":
            jobs = int(next(it))
        elif a == "--slow":
            slow = True
        else:
            extra.append(a)
    files = sorted(p.name for p in (HOST / "tests").glob("test_*.py"))
    times = json.loads(TIMES.read_text()) if TIMES.is_file() else {}
    order = sorted(files, key=lambda f: -times.get(f, 20.0))
    groups: list[list[str]] = [[] for _ in range(jobs)]
    load = [0.0] * jobs
    for f in order:   # largest first into the lightest group
        i = load.index(min(load))
        groups[i].append(f)
        load[i] += times.get(f, 20.0)
    env = {**os.environ, "MAIPAI_BUILD_RENDERER": "0"}
    # build the renderers once, before the groups start, so they do not race to build them
    subprocess.run(["uv", "run", "pytest", "-q", "-x", "-p", "no:cacheprovider", "tests/test_virtual_unit.py", "--co", "-q"], cwd=HOST, env={**os.environ, "MAIPAI_BUILD_RENDERER": "1"}, capture_output=True)
    began = time.time()
    procs = []
    for n, g in enumerate(groups):
        cmd = ["uv", "run", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={ROOT / '.runs' / f'shard-{n}.xml'}", "--durations=0", "--durations-min=2", *([] if slow else ["-m", "not slow"]), *extra, *[f"tests/{f}" for f in g]]
        procs.append((n, g, subprocess.Popen(cmd, cwd=HOST, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)))
    failed = 0
    new_times: dict[str, float] = {}
    for n, g, p in procs:
        out, _ = p.communicate()
        last = [l for l in out.strip().splitlines() if re.search(r"passed|failed|error", l)]
        print(f"group {n} ({len(g)} files): {last[-1] if last else out.strip().splitlines()[-1:]}")
        if p.returncode not in (0, 5):
            failed += 1
            print("\n".join(l for l in out.splitlines() if l.startswith(("FAILED", "ERROR")))[:2000])
        try:
            import xml.etree.ElementTree as ET

            for case in ET.parse(ROOT / ".runs" / f"shard-{n}.xml").getroot().iter("testcase"):
                f = (case.get("classname") or "").split(".")[1] + ".py" if (case.get("classname") or "").count(".") >= 1 else ""
                if f:
                    new_times[f] = new_times.get(f, 0.0) + float(case.get("time") or 0)
        except Exception:  # noqa: BLE001
            pass
    if new_times:
        TIMES.parent.mkdir(exist_ok=True)
        TIMES.write_text(json.dumps({k: round(v, 1) for k, v in new_times.items()}, indent=0))
    print(f"total {time.time() - began:.0f} s in {jobs} processes; {'FAILED' if failed else 'ok'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
