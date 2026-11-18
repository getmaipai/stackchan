#!/usr/bin/env python3
"""Reading level of the user docs (Flesch-Kincaid grade), worst pages first, with their longest sentences.

Usage: python3 scripts/docs-grade.py [--max GRADE] [--sentences N] [files...]   (default: docs/user/*.md, max 8)
Code blocks, tables, links' targets and headings are skipped. Exit 1 when a page is above --max."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def syllables(word: str) -> int:
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and not word.endswith(("le", "ee")) and count > 1:
        count -= 1
    return max(1, count)


def prose(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " thing ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith(("|", "#", ">", "---"))]
    return re.sub(r"[*_]", "", "\n".join(lines))


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n\s*\n|\n[-*]\s+|\n\d+\.\s+", text)
    return [p.strip() for p in parts if re.search(r"[A-Za-z]{2}", p)]


def grade(text: str) -> tuple[float, list[str]]:
    found = sentences(prose(text))
    words = [w for s in found for w in re.findall(r"[A-Za-z']+", s)]
    if not found or not words:
        return 0.0, []
    syl = sum(syllables(w) for w in words)
    value = 0.39 * len(words) / len(found) + 11.8 * syl / len(words) - 15.59
    longest = sorted(found, key=lambda s: -len(s.split()))
    return value, longest


def main(argv: list[str]) -> int:
    maximum, top = 8.0, 2
    files: list[Path] = []
    args = iter(argv)
    for arg in args:
        if arg == "--max":
            maximum = float(next(args))
        elif arg == "--sentences":
            top = int(next(args))
        else:
            files.append(Path(arg))
    files = files or sorted((ROOT / "docs" / "user").glob("*.md"))
    rows = sorted(((grade(p.read_text())[0], p) for p in files), reverse=True)
    bad = 0
    for value, path in rows:
        flag = "  <-- above" if value > maximum else ""
        print(f"{value:5.1f}  {path.name}{flag}")
        if value > maximum:
            bad += 1
            for sentence in grade(path.read_text())[1][:top]:
                print(f"         long: {sentence[:160]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
