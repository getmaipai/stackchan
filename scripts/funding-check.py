#!/usr/bin/env python3
"""Intent: fail when the README or the docs point to a funding page that .github/FUNDING.yml does not list.

Zero model tokens. A sponsor link in prose must always match a listed account, so no page can promote
a funding page the owner did not register. Usage: funding-check.py [--root DIR]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# FUNDING.yml key -> URL template. "custom" entries are full URLs and need no template.
TEMPLATES = {
    "github": "github.com/sponsors/{h}",
    "ko_fi": "ko-fi.com/{h}",
    "open_collective": "opencollective.com/{h}",
    "patreon": "patreon.com/{h}",
    "liberapay": "liberapay.com/{h}",
    "buy_me_a_coffee": "buymeacoffee.com/{h}",
}
# Hosts that count as a funding link when they appear in prose. The handle must be a real name, so a
# placeholder such as <handle> does not match.
LINK = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"(github\.com/sponsors|ko-fi\.com|opencollective\.com|patreon\.com|liberapay\.com|buymeacoffee\.com)"
    r"/([A-Za-z0-9][A-Za-z0-9_.-]*)",
    re.IGNORECASE,
)
SCAN_DIRS = ("docs", "docs-site")
SCAN_SUFFIXES = {".md", ".html", ".txt", ".json", ".toml"}


def norm(url: str) -> str:
    url = re.sub(r"^https?://", "", url.strip().lower())
    url = re.sub(r"^www\.", "", url)
    return url.rstrip("/.")


def listed_links(funding: Path) -> set[str]:
    """Return the normalized links FUNDING.yml lists. Reads the simple `key: value` form GitHub accepts."""
    out: set[str] = set()
    if not funding.is_file():
        return out
    for raw in funding.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line or line.startswith("-"):
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        items = [v.strip().strip("'\"") for v in value.strip().strip("[]").split(",")]
        for item in filter(None, items):
            if key == "custom":
                out.add(norm(item))
            elif key in TEMPLATES:
                out.add(norm(TEMPLATES[key].format(h=item)))
    return out


def scan_files(root: Path) -> list[Path]:
    files = [root / "README.md"]
    for d in SCAN_DIRS:
        base = root / d
        if base.is_dir():
            files += [p for p in sorted(base.rglob("*")) if p.is_file() and p.suffix in SCAN_SUFFIXES]
    return [p for p in files if p.is_file()]


def find_problems(root: Path) -> list[str]:
    listed = listed_links(root / ".github" / "FUNDING.yml")
    problems = []
    for path in scan_files(root):
        for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in LINK.finditer(line):
                link = norm(f"{m.group(1)}/{m.group(2)}")
                if link not in listed:
                    problems.append(
                        f"funding: {path.relative_to(root)}:{n} links to {link}, which .github/FUNDING.yml does not list. "
                        "Add the account to FUNDING.yml or remove the link."
                    )
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = ap.parse_args(argv)
    problems = find_problems(args.root)
    for p in problems:
        print(p, file=sys.stderr)
    if not problems:
        print("funding: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
