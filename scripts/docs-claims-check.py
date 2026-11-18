#!/usr/bin/env python3
# Intent: check the claims in README.md, docs/user and docs/design/features.md that a script can test against the code: tool names in backticks exist in schema/tools.json, MAIPAI_ names exist in firmware or host, counts of styles, languages, games and overlays equal what the code defines, and relative links point at files that exist.
# Usage: python3 scripts/docs-claims-check.py   (exit 1 and one line per wrong claim). Run by scripts/check.sh.
# Placement: docs tooling. Upstream: none.
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "eighteen": 18}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def truth() -> dict[str, set[int]]:
    """What the code defines. A claim about a count must equal one of the numbers listed for its noun."""
    styles = len(json.loads((ROOT / "host/maipai_body/face_table.json").read_text())["styles"])
    languages = len(re.search(r"SUPPORTED = \(([^)]*)\)", (ROOT / "host/maipai_body/i18n.py").read_text()).group(1).split(","))
    o01 = (ROOT / "firmware/patches/O01-overlay-engine-bigger-shapes-and-combinations.patch").read_text()
    elements = len(re.findall(r'"([a-z]+)"', re.search(r"^\+static const char\* const MO_NAMES\[MO_COUNT\] = \{(.*?)\};", o01, re.S | re.M).group(1)))  # the empty "none" entry has no letters, so it is not counted
    presets = len(re.search(r"MOP_NAMES\[MOP_COUNT\] = \{(.*?)\};", o01, re.S).group(1).split(","))
    gm06 = (ROOT / "firmware/patches/GM06-remove-the-reaction-time-game.patch").read_text()
    games = len(re.findall(r'"[a-z0-9]+"', re.search(r"^\+// Starts a game by id (.*)$", gm06, re.M).group(1)))
    return {"styles": {styles}, "languages": {languages}, "games": {games}, "overlays": {elements, presets, elements + presets}, "screen effects": {elements + presets}}


def main() -> int:
    files = [f for f in git("ls-files", "README.md", "docs/user", "docs/design/features.md").split() if f.endswith(".md")]
    tools = set(json.loads((ROOT / "schema/tools.json").read_text())["tools"])
    known = set(git("grep", "-h", "-o", "-E", "MAIPAI_[A-Z0-9_]+", "--", "firmware", "host").split())
    facts = truth()
    bad: list[str] = []
    for name in files:
        text = (ROOT / name).read_text()
        for tool in re.findall(r"`(self\.[a-z0-9_.]+)`", text):
            if tool not in tools:
                bad.append(f"{name}: tool {tool} is not in schema/tools.json")
        for flag in set(re.findall(r"\b(MAIPAI_[A-Z0-9_]+)\b", text)):
            if flag not in known:
                bad.append(f"{name}: {flag} is not defined in firmware or host")
        for match in re.finditer(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve|eighteen) (screen effects|overlays|styles|languages|games)\b", text, re.I):
            number = int(match.group(1)) if match.group(1).isdigit() else NUMBERS[match.group(1).lower()]
            if number not in facts[match.group(2).lower()]:
                bad.append(f"{name}: says '{match.group(0)}', the code has {sorted(facts[match.group(2).lower()])}")
        for target in re.findall(r"\]\(([^)#\s]+\.(?:md|svg|png))[)#]", text):
            if not target.startswith("http") and not (ROOT / name).parent.joinpath(target).resolve().exists():
                bad.append(f"{name}: link to {target} points at no file")
    readme = (ROOT / "README.md").read_text()
    drawings = [f for f in git("ls-files", "docs/images").split() if not Path(f).name.startswith(("unit-", "vu-"))]
    claimed = re.search(r"\((\d+) of them\)", readme)
    if claimed is not None and int(claimed.group(1)) != len(drawings):  # the README no longer makes this claim; if it returns it must be right
        bad.append(f"README.md: the placeholder drawing count says {claimed.group(1) if claimed else 'nothing'}, docs/images holds {len(drawings)} files that are not unit- or vu- pictures")
    t01 = (ROOT / "firmware/patches/T01-low-battery-ladder.patch").read_text()
    ladder = tuple(int(re.search(rf"MB_LEVEL_{k} (\d+)", t01).group(1)) for k in ("CHIRP", "ASK", "SLEEP"))
    said = re.search(r"A chirp at (\d+) percent, a spoken ask at (\d+), sleep at (\d+)", (ROOT / "docs/user/features.md").read_text())
    if said is None or tuple(map(int, said.groups())) != ladder:
        bad.append(f"docs/user/features.md: the low-battery steps do not say {ladder} as patch T01 defines them")
    for line in bad:
        print(line)
    print("docs-claims: ok" if not bad else f"docs-claims: {len(bad)} wrong claim(s). Fix the page, or the code if the page is right.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
