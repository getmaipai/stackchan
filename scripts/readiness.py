#!/usr/bin/env python3
"""First-release readiness: the friend test as a checklist, made from the state of the repository.

Each row is one thing a friend must be able to do on their own. A row shows done, partly or blocked, with the evidence found in the repo (files, tests, golden
frames, patches) and what is still missing (a release key, a unit hands-on check, a native-language review). The evidence is looked up here, not typed, so the
page changes when the repository does; the missing parts are written here once, in plain words, because no file can prove an absence of hands.

Usage: python3 scripts/readiness.py            write docs/plan/release-readiness.md
       python3 scripts/readiness.py --check    exit 1 when the committed page is out of date (run by scripts/check.sh)
Rules: a row is done only when it has evidence and nothing missing; blocked when something it needs does not exist yet (a key, a published flasher, a signed image);
partly otherwise. Nothing in a row is marked done on the strength of host tests alone when the feature has to work on the robot: the missing line says so.
Placement: docs tooling. Upstream: none.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "plan" / "release-readiness.md"


def tracked() -> list[str]:
    return subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")


FILES = tracked()


def has(pattern: str) -> list[str]:
    rx = re.compile(pattern)
    return [f for f in FILES if rx.search(f)]


def text(path: str) -> str:
    return (ROOT / path).read_text() if (ROOT / path).is_file() else ""


def patches(prefix: str) -> list[str]:
    return [Path(f).name for f in has(rf"^firmware/patches/{prefix}")]


def count_xfail(path: str) -> int:
    return text(path).count("xfail")


# (name, [(label, files found)], [missing], blocked?)
def rows() -> list[dict]:
    flasher = has(r"^flasher/(index\.html|flasher\.js|flasher-core\.js)$")
    key_missing = "no release key exists yet" in text("docs/user/security.md") or "release key" in text("docs/user/updates.md")
    firstrun = has(r"^host/tests/golden/screens/first-run-\d-en\.png$")
    lock_goldens = has(r"^host/tests/golden/screens/lock-")
    lock_xfail = count_xfail("host/tests/test_cross_review_open_bugs.py")
    docs_pages = has(r"^docs/user/[^/]+\.md$")
    placeholders = re.search(r"\((\d+) of them\)", text("README.md"))
    not_reviewed = "not native-reviewed" in text("README.md") or "not yet reviewed by native" in text("docs/user/compare.md").lower()
    return [
        {
            "row": "Install the robot from a web page",
            "evidence": [("flasher page and scripts", flasher), ("flasher tests", has(r"^flasher/test/"))],
            "missing": ["a flasher published at an address a friend can open", "a signed release image to flash (no release key yet)" if key_missing else ""],
            "blocked": True,
            "unblock": [("owner", "create the release key and decide where the flasher page is published (an address a friend can open)"), ("firmware", "build the first release image signed with that key and publish it with its signature file"), ("app", "host the flasher page and the image, and point the page's manifest at them")],
        },
        {
            "row": "Install the host program without a terminal",
            "evidence": [("install page", has(r"^docs/user/install-the-host\.md$")), ("host packaging", has(r"^host/pyproject\.toml$"))],
            "missing": ["an installer a friend can double click (today: pipx from a terminal)"],
            "blocked": True,
            "unblock": [("owner", "choose the systems to support first (Mac, Windows, a Raspberry Pi) and whether a bundled app is wanted"), ("app", "build that installer, with the first-run page that opens the settings page and the pairing card, and test it on a clean machine")],
        },
        {
            "row": "Pair the robot with a code, no terminal",
            "evidence": [("six-digit pairing card on the settings page", has(r"^host/maipai_body/settings_ui_family\.py$")), ("pairing tests", has(r"test_.*pairing"))],
            "missing": ["a person pairing a real robot from a phone, start to end, with nobody helping"],
            "blocked": False,
        },
        {
            "row": "First run: language, name, mode, privacy sentence",
            "evidence": [("first-run screens as golden frames (English)", firstrun), ("first-run patches", patches("UX05|UX06|UX08|SF09"))],
            "missing": ["a person doing the first run on a real robot with a finger (bench 2026-11-18 ran it once with test touches: it shows once after Wi-Fi and never again)", "the five other languages read by native speakers" if not_reviewed else ""],
            "blocked": False,
        },
        {
            "row": "A voice reply after the wake word",
            "evidence": [("host turn tests", has(r"^host/tests/test_turn")), ("voice page", has(r"^docs/user/voice\.md$"))],
            "missing": ["the wake cue and the first spoken sentence timed on a robot (bench 2026-11-18: five of five short test clips answered with no reset; the 150 ms and 300 ms figures are still targets, not measurements)"],
            "blocked": False,
        },
        {
            "row": "Update the robot",
            "evidence": [("signed update patches", patches("155|159")), ("update cover frames", has(r"^host/tests/golden/screens/cover-update-"))],
            "missing": ["a release key and a signed image installed on a robot", "a first update from one real release to the next"],
            "blocked": True,
            "unblock": [("owner", "create the release key (the same one as the flasher row) and say when a first release is cut"), ("firmware", "sign two releases and prove the update path with the real key: accepted, refused on a wrong signature, and rolled back when the new image fails to start"), ("bench", "run that on a robot and record it")],
        },
        {
            "row": "Privacy switches: mute, camera off, always-on cues",
            "evidence": [("privacy page", has(r"^docs/user/mute-and-camera-off\.md$")), ("camera on and muted frames", has(r"^host/tests/golden/screens/screen-(camera-on|muted)\.png$"))],
            "missing": ["the cues seen and heard on a robot with a real finger (bench 2026-11-18 proved tap on, hold off and no toggle while muted with a test touch)"],
            "blocked": False,
        },
        {
            "row": "Lock the robot with a passcode",
            "evidence": [("lock patches", patches("LK0|SF13")), ("lock screen and keypad frames", lock_goldens), ("lock page", has(r"^docs/user/lock\.md$"))],
            "missing": ["a person locking and unlocking on a robot (bench 2026-11-18: five wrong codes lock it out and the lockout survives a restart)", f"{lock_xfail} known lock bug(s) still open as expected-fail tests" if lock_xfail else ""],
            "blocked": False,
        },
        {
            "row": "Parent view: what the robot is doing, in plain words",
            "evidence": [("parent view code", has(r"^host/maipai_body/settings_ui_family\.py$")), ("plan", has(r"^docs/plan/parent-view\.md$"))],
            "missing": ["the page's buttons measured at phone width (48 px)", "a parent using it on a phone"],
            "blocked": False,
        },
        {
            "row": "Docs a friend can follow",
            "evidence": [("user pages", docs_pages), ("claims check", has(r"^scripts/docs-claims-check\.py$")), ("screens from the virtual unit", has(r"^docs/images/vu-"))],
            "missing": [f"{placeholders.group(1)} placeholder drawings still to replace with real pictures" if placeholders else "", "the pages read aloud to someone who has never seen the robot"],
            "blocked": False,
        },
    ]


def status(row: dict) -> str:
    evidence = any(files for _, files in row["evidence"])
    missing = [m for m in row["missing"] if m]
    if missing and row["blocked"]:
        return "blocked"
    if evidence and not missing:
        return "done"
    return "partly"


def render() -> str:
    lines = [
        "# First release readiness: the friend test",
        "",
        "Made by `python3 scripts/readiness.py` from the repository; do not edit by hand. A friend should be able to do each row alone. `done` needs evidence and nothing missing; `blocked` means something it needs does not exist yet; `partly` is the rest. Host tests alone never make a robot feature `done`: the missing line names the hands-on check.",
        "",
        "| Row | Status | Evidence in the repo | Still missing |",
        "|---|---|---|---|",
    ]
    counts = {"done": 0, "partly": 0, "blocked": 0}
    for row in rows():
        st = status(row)
        counts[st] += 1
        evidence = "; ".join(f"{label}: {len(files)} file(s), e.g. `{files[0]}`" for label, files in row["evidence"] if files) or "none found"
        missing = "; ".join(m for m in row["missing"] if m) or "nothing"
        lines.append(f"| {row['row']} | **{st}** | {evidence} | {missing} |")
    lines += ["", "## The blocked rows and what unblocks each", ""]
    for row in rows():
        if status(row) == "blocked":
            lines.append(f"**{row['row']}**")
            lines += [f"- {who}: {what}" for who, what in row.get("unblock", [])]
            lines.append("")
    lines += [
        f"Totals: {counts['done']} done, {counts['partly']} partly, {counts['blocked']} blocked.",
        "",
        "## What gates the first release, in one list",
        "- A release key and a signed image (blocks install and update).",
        "- A published web flasher and a host installer that needs no terminal.",
        "- Hands-on checks on a robot: first run, pairing from a phone, lock, privacy cues, the first spoken reply, the head's own timings.",
        "- Finger test on the glass (owner, 2026-11-18): press Skip and Back on every first-run step, the keypad keys, every control sheet tile, both sliders, the four settings tabs, the timer delete button, the games wall tiles and the Quiet now and Vision off tiles; note any press that misses, hits the next target or needs a second try (the audit that lists them is docs/dev/screen-audit.md).",
        "- Native-speaker review of the five languages after English and Spanish.",
        "",
        "Related: `docs/plan/friend-test-path-2026-11-18.md` (the path written as steps), `docs/dev/head-recording.md` (the servo calibration the bench still owes).",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    page = render()
    if "--check" in sys.argv:
        if not OUT.is_file() or OUT.read_text() != page:
            print("readiness: docs/plan/release-readiness.md is out of date. Run python3 scripts/readiness.py.")
            return 1
        print("readiness: ok")
        return 0
    OUT.write_text(page)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
