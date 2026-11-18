"""Decisions and scrapped features for the feature ledger (scripts/feature-ledger.py). Reads docs/design/decisions.md and the dropped lists; nothing here is a verdict about code
except DECISION_EVIDENCE, which names the files whose existence moves a decision from "not started" to "in progress" or "built".
Placement: docs tooling. Upstream: none."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISIONS_MD = ROOT / "docs" / "design" / "decisions.md"
SECTION = "## Owner decisions of 2026-11-18"
DECISION_STATUSES = ["built", "in progress", "not started"]

BABY_PAGE = "docs/user/baby-and-pet-monitor.md"
BABY_REASON = ("scrapped (decision 10, 2026-11-18): the camera is small, low resolution, about three frames a second, with no night vision, so it cannot meet what a person expects of a "
               "baby monitor, and a wrong promise could do harm. We do not build, document or advertise monitoring of a child or a person who needs care.")

# decision number -> (files whose existence is the evidence, one line of evidence in plain words). All present = built, some = in progress, none = not started; DECISION_FORCED overrides where files cannot say it.
DECISION_EVIDENCE: dict[int, tuple[list[str], str]] = {
    1: (["scripts/boundary-check.sh", "docs/design/core-extras-modules.md"], "the four tests are written down and scripts/boundary-check.sh enforces them in check.sh"),
    2: (["docs/user/which-setup.md", "docs/user/getting-started.md"], "the docs describe a setup with no Home; the friend test that gates the first release has not been run end to end"),
    3: (["host/maipai_packages/memory_notes", "host/maipai_packages/home_assistant", "host/maipai_packages/coding_companion"], "the memory notes, Home Assistant and coding companion packages exist, off by default"),
    4: (["host/maipai_packages/wake_word_maker"], "the wake word maker exists; talking over the robot is built, a family-chosen wake word is built but not flashed"),
    5: (["schema/tools.json", "scripts/spec-drift-check.sh"], "vendored spec snapshots with a drift check; the shared movement limiter, memory admission and indicators are still being moved into the spec"),
    6: ([], "the four users shape the docs and the first run; the child and teen rule (Home required) is stated, and not yet enforced in the host"),
    7: (["scripts/virtual-unit/view3d.js", "scripts/virtual-unit/physics/physics.js"], "the 3D view draws the real renderer on the rigged model, with physics for the head and an IMU"),
    8: (["firmware/patches/ORDER"], "the patch series is the plan; nothing replaces it"),
    9: (["docs/dev/bench.md"], "one bench page and one unit; the unit ends each window on the released image (the bench page holds the routine)"),
    10: ([], "the baby monitor pages, rows and promises are removed from the user docs and the product"),
    11: (["docs/dev/memory-budget.md"], "firmware writes one budget table of what fits at once, what is on by default and what excludes what"),
    12: (["firmware/patches/UX12-first-run-skip-brain-question-and-next-steps.patch", "docs/plan/first-run-brain-choice.md"], "the first run asks the three questions (Home, my own servers, set one up for me); the minimal local stack installer is not built"),
    13: (["docs/dev/memory-budget.md", "docs/design/encrypted-link.md"], "the encrypted link exists; making it the default waits on the memory table"),
    14: (["scripts/efuse-check.py"], "scripts/efuse-check.py refuses any eFuse write in firmware, builds, scripts and updates"),
    15: (["schema/memory-budget.json", "scripts/virtual-unit/memory_model.py"], "the virtual unit enforces the declared budget and a leak canary; the firmware numbers are partly placeholders"),
    17: ([], "the installed set with slots is not built: the unit holds everything compiled in; the memory model (schema/memory-budget.json) now states each item's cost for the slot sizes"),
    18: ([], "the language tiers and the first screen anyone can read are not built: the first run shows six languages in their own names; no font packs yet"),
    19: ([], "one image for everyone is the plan; profiles wait for the memory budget (decision 11) to show they are needed; none are built"),
    20: ([], "the first run now asks three questions and offers Skip on each; the rule that every other choice is automatic or under Advanced is not yet checked across the settings page"),
    21: (["scripts/virtual-unit/view.py"], "the simulation backend exists (the virtual unit and its 3D view); the Live backend (a registered robot through the person's host, one control session at a time) is not built"),
    16: ([], "the host serves several units today; the managed service, per-unit supervision and no-silent-death parts are not built"),
}

# explicit status, by number, where files alone cannot say it
DECISION_FORCED: dict[int, str] = {
    2: "in progress", 4: "in progress", 5: "in progress", 6: "in progress", 9: "in progress", 12: "in progress", 13: "not started", 15: "in progress", 16: "in progress", 17: "not started", 18: "not started", 19: "not started", 20: "in progress", 21: "in progress",
}


def decisions() -> list[dict]:
    """Every numbered owner decision of 2026-11-18, with its title (the bold lead), the full text, a status and one line of evidence."""
    text = DECISIONS_MD.read_text(errors="ignore") if DECISIONS_MD.is_file() else ""
    if SECTION not in text:
        return []
    body = text.split(SECTION, 1)[1]
    out = []
    for m in re.finditer(r"^(\d+)\. \*\*(.+?)\*\*\s*(.*)$", body, re.M):
        n = int(m.group(1))
        title = m.group(2).strip().rstrip(".:")
        title = re.sub(r"\s*\((?:owner, )?2026-11-18\)\s*$", "", title)
        files, note = DECISION_EVIDENCE.get(n, ([], "a new decision: the ledger has no files to check for it yet (add it to DECISION_EVIDENCE in scripts/ledger_decisions.py), so it counts as not started"))
        have = [f for f in files if (ROOT / f).exists()]
        if n == 10:
            status = "built" if not (ROOT / BABY_PAGE).exists() else "in progress"
            note = note if status == "built" else "the pages, rows and promises are being removed from the user docs; the ledger already lists every baby monitor row as scrapped"
        elif n in DECISION_FORCED and (n != 13 or not (ROOT / "docs/dev/memory-budget.md").exists()):
            status = DECISION_FORCED[n]
        elif files and len(have) == len(files):
            status = "built"
        elif have:
            status = "in progress"
        else:
            status = "not started"
        out.append({"n": n, "title": title, "text": " ".join((m.group(3)).split()), "status": status, "evidence": note, "files": have})
    return out


# ---- scrapped rows ---------------------------------------------------------------------------------------------------

REASONS = {
    "sound direction": "dropped on the design list (docs/design/features.md, Dropped or rejected)",
    "bluetooth": "off in v1 (decided 2026-11-15); reviewed after the memory gate shows what it costs",
    "phone-pickup nudge": "dropped on the design list (docs/design/features.md, Dropped or rejected)",
    "native phone app": "dropped on the design list: the settings page and web app are the phone's side",
    "a phone app": "dropped: the settings page and web app are the phone's side",
    "anything that calls an outside service by itself": "the host calls no address the owner did not configure (decision 12 of the scope list)",
}


def dropped_items() -> list[dict]:
    """The features the plan says are not included: the 'Dropped or rejected' list of docs/design/features.md and the 'Not included' paragraph of docs/user/features.md.
    A parenthesis after an item is its reason."""
    seen: dict[str, dict] = {}

    def add(name: str, reason: str, source: str) -> None:
        name = name.strip(" .").strip()
        if not name:
            return
        key = re.sub(r"[^a-z]", "", name.lower())
        alias = {"aphoneapp": "nativephoneapp", "nativephoneapp": "nativephoneapp"}.get(key, key)
        if alias in seen:
            return
        seen[alias] = {"name": name[0].upper() + name[1:], "reason": reason or REASONS.get(name.lower(), "listed as not included"), "source": source}

    user = (ROOT / "docs" / "user" / "features.md").read_text(errors="ignore") if (ROOT / "docs" / "user" / "features.md").is_file() else ""
    m = re.search(r"^## Not included\s*\n+(.+?)(?:\n\n|\Z)", user, re.S | re.M)
    if m:
        para = m.group(1).split(". ", 1)[0] if ". " in m.group(1) else m.group(1)
        flat = re.sub(r"\(([^)]*)\)", lambda mm: "\u0001" + mm.group(1).replace(",", "\u0002") + "\u0003", para)
        for part in re.split(r",\s*(?:and\s+)?", flat):
            reason = ""
            mm = re.search(r"\u0001(.*?)\u0003", part)
            if mm:
                reason = mm.group(1).replace("\u0002", ",")
                part = re.sub(r"\u0001.*?\u0003", "", part)
            add(re.sub(r"^and\s+", "", part.strip()), reason, "docs/user/features.md (Not included)")
    design = (ROOT / "docs" / "design" / "features.md").read_text(errors="ignore") if (ROOT / "docs" / "design" / "features.md").is_file() else ""
    m = re.search(r"^## Dropped or rejected\s*\n+(.+?)(?:\n\n|\Z)", design, re.S | re.M)
    if m:
        for item in m.group(1).split(". "):
            add(item, "", "docs/design/features.md (Dropped or rejected)")
    return list(seen.values())
