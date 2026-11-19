#!/usr/bin/env python3
# Intent: the dashboard's front pages stay calm (owner request 2026-11-19): at most 6 controls, at most 60 words, labels of 1 to 3 words, one help sentence of 12 words or fewer, and no jargon. The text is read from FRONT in host/maipai_body/settings_ui_shell.py, which the page itself uses.
# Usage: python3 scripts/dashboard-words-check.py   exit 1 when a page is over budget (run by scripts/check.sh)
# Placement: docs tooling. Upstream: none.
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "host"))
from maipai_body.settings_ui_shell import BANNED, FRONT  # noqa: E402

MAX_CONTROLS, MAX_WORDS, MAX_LABEL, MAX_HELP = 6, 60, 3, 12


def words(text: str) -> list[str]:
    return re.findall(r"[\w'-]+", text)


def main() -> int:
    problems = []
    for page, spec in FRONT.items():
        controls = spec["controls"]
        if len(controls) > MAX_CONTROLS:
            problems.append(f"{page}: {len(controls)} controls on the front page, at most {MAX_CONTROLS}. Move the rest behind More settings.")
        for label in controls:
            if not 1 <= len(words(label)) <= MAX_LABEL:
                problems.append(f"{page}: the label '{label}' has {len(words(label))} words, use 1 to {MAX_LABEL}.")
        if len(words(spec["help"])) > MAX_HELP:
            problems.append(f"{page}: the help line has {len(words(spec['help']))} words, at most {MAX_HELP}.")
        shown = [spec["title"], spec["help"], *controls, *spec["text"]]
        total = sum(len(words(t)) for t in shown)
        if total > MAX_WORDS:
            problems.append(f"{page}: {total} words on the front page, at most {MAX_WORDS}. Cut words or move text behind More settings.")
        for t in shown:
            for bad in BANNED:
                if re.search(rf"\b{bad}\b", t, re.I):
                    problems.append(f"{page}: the word '{bad}' is jargon on a front page ('{t}'). Say it in plain words or move it behind More settings.")
    for line in problems:
        print(line)
    print("dashboard-words: ok" if not problems else f"dashboard-words: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
