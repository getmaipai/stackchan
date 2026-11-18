#!/usr/bin/env python3
"""Write schema/tools.json: every MCP tool name the firmware patches register, with the patch that adds it.
Usage: tools_extract.py [--check]   (--check fails when schema/tools.json is stale)
Intent: one list of firmware tools that the virtual unit and the parity test both read.
Placement: host-side development tool; no firmware change. Upstream: none."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAT = re.compile(r'AddTool\(\s*"(self\.[A-Za-z0-9_.]+)"')
PROP = re.compile(r'Property\("([A-Za-z0-9_]+)",\s*kPropertyType(String|Integer|Boolean)')
KIND = {"String": "string", "Integer": "integer", "Boolean": "boolean"}


def properties(added_text: str) -> dict[str, dict[str, str]]:
    """For each tool, its declared arguments (name and type), read from the Property(...) list before the handler lambda."""
    out = {}
    for m in PAT.finditer(added_text):
        head = added_text[m.end():]
        cut = re.search(r"\[\s*(?:&|=|\])", head)
        block = head[: cut.start()] if cut else head[:600]
        out[m.group(1)] = {n: KIND[t] for n, t in PROP.findall(block)}
    return out


def extract_args() -> dict[str, dict[str, str]]:
    extract()
    return _ARGS


_ARGS: dict[str, dict[str, str]] = {}


def extract() -> dict[str, str]:
    _ARGS.clear()
    found: dict[str, str] = {}
    args: dict[str, dict[str, str]] = {}
    removed: set[str] = set()
    for patch in sorted((ROOT / "firmware" / "patches").glob("*.patch")):
        added, gone = [], []
        for line in patch.read_text(errors="replace").splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                gone.append(line[1:])
        for name, props in properties("\n".join(added)).items():
            args.setdefault(name, props)
            _ARGS.setdefault(name, props)
        for name in PAT.findall("\n".join(added)):
            found.setdefault(name, patch.name)
            removed.discard(name)
        for name in PAT.findall("\n".join(gone)):
            if name not in PAT.findall("\n".join(added)):
                removed.add(name)
    return {k: v for k, v in sorted(found.items()) if k not in removed}


def main() -> int:
    tools = extract()
    text = json.dumps({"source": "firmware/patches (AddTool lines)", "count": len(tools), "tools": tools,
                       "arguments": {k: _ARGS.get(k, {}) for k in tools}}, indent=1) + "\n"
    out = ROOT / "schema" / "tools.json"
    if "--check" in sys.argv:
        if not out.exists() or out.read_text() != text:
            print("schema/tools.json is stale: run python3 scripts/virtual-unit/tools_extract.py and commit it")
            return 1
        print(f"tools.json ok ({len(tools)} tools)")
        return 0
    out.write_text(text)
    print(f"wrote {out} ({len(tools)} tools)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
