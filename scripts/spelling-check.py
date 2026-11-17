#!/usr/bin/env python3
"""Intent: fail on British spellings in text files (owner rule 2026-11-16: American spelling everywhere).

Usage: spelling-check.py [--allow FILE] [--root DIR] [paths...]   (no paths: every tracked file)
Allow-list (scripts/spelling-allow.txt), one rule per line, blank lines and '#' lines ignored:
    <path glob> :: <regex>     skip lines of matching files where the regex matches
    <path glob> :: *           skip the whole file
Allowed places: alias code that reads an old key, quoted legacy keys on a wire shared with another repo or
the flashed firmware, non-English text, vendored text. Exit 0 clean, 1 findings.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

# Each stem is a British form with its American spelling; matched inside identifiers too (CENTRE_PITCH, listen_colour).
BRITISH = re.compile(
    r"colour|behaviour|centre(?![a-z])|centred|centring|(?<![a-z])grey(?:s|ed|ing|ish|er|est|scale)?(?![a-z])|licence|favourite"
    r"|normalis|recognis|initialis|organis|customis|optimis|summaris|authoris|apologis"
    r"|analys(?:e|ed|er|ing)(?![a-z])|catalogue|(?:centi|kilo|milli)?metre|programme"
    r"|cancelled|cancelling|travell|labelled|labelling|modelling|honour|neighbour|defence|theatre|fibre",
    re.IGNORECASE,
)
SKIP_NAMES = ("LICENSE", "NOTICE", "THIRD-PARTY")
SKIP_SUFFIX = (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".bin", ".gz", ".woff", ".woff2", ".ico", ".wav", ".ogg", ".mp3", ".pdf", ".lock", ".npz", ".safetensors")
ALWAYS_ALLOWED = ("scripts/spelling-check.py", "scripts/spelling-allow.txt", "scripts/hygiene-check.sh", "host/tests/test_spelling_lint.py")


def load_allow(path: Path) -> list[tuple[str, str]]:
    rules: list[tuple[str, str]] = []
    if not path.is_file():
        return rules
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or " :: " not in line:
            continue
        glob, regex = line.split(" :: ", 1)
        rules.append((glob.strip(), regex.strip()))
    return rules


def scan_text(rel: str, text: str, rules: list[tuple[str, str]]) -> list[tuple[int, str, str]]:
    mine = [rx for glob, rx in rules if fnmatch.fnmatch(rel, glob)]
    if "*" in mine:
        return []
    compiled = [re.compile(rx) for rx in mine]
    found: list[tuple[int, str, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        hit = BRITISH.search(line)
        if hit and not any(rx.search(line) for rx in compiled):
            found.append((number, hit.group(0), line.strip()[:120]))
    return found


def scan_file(root: Path, rel: str, rules: list[tuple[str, str]]) -> list[tuple[int, str, str]]:
    if rel in ALWAYS_ALLOWED or Path(rel).name.startswith(SKIP_NAMES) or rel.endswith(SKIP_SUFFIX):
        return []
    try:
        text = (root / rel).read_text(encoding="utf-8")  # an absolute rel wins over root
    except (OSError, UnicodeDecodeError):
        return []
    return scan_text(rel, text, rules)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--allow", default=None)
    ap.add_argument("paths", nargs="*")
    args = ap.parse_args(argv)
    root = Path(args.root)
    rules = load_allow(Path(args.allow) if args.allow else root / "scripts" / "spelling-allow.txt")
    paths = args.paths or subprocess.check_output(["git", "-C", str(root), "ls-files"], text=True).splitlines()
    bad = 0
    for rel in paths:
        if Path(rel).is_absolute():
            try:
                rel = str(Path(rel).relative_to(root))
            except ValueError:
                pass  # outside the repo: scanned under its full path
        for number, word, line in scan_file(root, rel, rules):
            bad += 1
            print(f"spelling: {rel}:{number}: British spelling '{word}': {line}")
    if bad:
        print(f"spelling: FAIL {bad} line(s). Use the American spelling (color, behavior, center, gray, license, canceled), "
              "or add the file to scripts/spelling-allow.txt with a reason if it is an alias or a wire key.")
        return 1
    print(f"spelling: ok ({len(paths)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
