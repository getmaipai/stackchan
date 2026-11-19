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
PAT = re.compile(r'Add(?:UserOnly)?Tool\(\s*"(self\.[A-Za-z0-9_.]+)"')
USER_ONLY = re.compile(r'AddUserOnlyTool\(\s*"(self\.[A-Za-z0-9_.]+)"')
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


# Patch TC01 widens the Property list of six tools in place (the AddTool line is not in the hunk), so the line reader above never sees the new arguments.
# These are the tools host/maipai_body/remote_trust.py stamps (gated_kind), with the arguments TC01 adds. The virtual unit then accepts the host's token and source.
REMOTE_GATE_ARGS = {"source": "string", "token": "integer"}
REMOTE_GATED = {"self.robot.set_head_angles": {"cue_kind": "string"}, "self.robot.dance": {}, "self.game.start": {}, "self.audio.play_sound": {}, "self.listen.test": {}, "self.camera.take_photo": {}}


def extract_args() -> dict[str, dict[str, str]]:
    extract()
    return _ARGS


_ARGS: dict[str, dict[str, str]] = {}
_USER: set[str] = set()


def extract() -> dict[str, str]:
    _ARGS.clear()
    found: dict[str, str] = {}
    args: dict[str, dict[str, str]] = {}
    removed: set[str] = set()
    _USER.clear()
    pdir = ROOT / "firmware" / "patches"
    order = [pdir / n for n in (pdir / "ORDER").read_text().split() if (pdir / n).exists()]  # the order the patches apply in: later wins
    for patch in order + [p for p in sorted(pdir.glob("*.patch")) if p not in order]:
        added, gone = [], []
        for line in patch.read_text(errors="replace").splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                gone.append(line[1:])
        _USER.update(USER_ONLY.findall("\n".join(added)))
        _USER.difference_update(n for n in PAT.findall("\n".join(added)) if n not in USER_ONLY.findall("\n".join(added)))
        for name, props in properties("\n".join(added)).items():
            args.setdefault(name, props)
            _ARGS.setdefault(name, props)
        for name in PAT.findall("\n".join(added)):
            found.setdefault(name, patch.name)
            removed.discard(name)
        for name in PAT.findall("\n".join(gone)):
            if name not in PAT.findall("\n".join(added)):
                removed.add(name)
    result = {k: v for k, v in found.items() if k not in removed}
    base = json.loads((ROOT / "schema" / "base-tools.json").read_text())["tools"]
    for name, props in base.items():
        result[name] = "base firmware (schema/base-tools.json)"
        _ARGS[name] = props
    for name, extra in REMOTE_GATED.items():
        if name in result:
            _ARGS[name] = {**_ARGS.get(name, {}), **REMOTE_GATE_ARGS, **extra}
    return dict(sorted(result.items()))


def main() -> int:
    tools = extract()
    text = json.dumps({"source": "firmware/patches (AddTool lines)", "count": len(tools), "tools": tools,
                       "user_only": sorted(n for n in _USER if n in tools),
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
