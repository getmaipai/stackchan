---
name: lane-brief
description: Write a short, complete brief for a Codex, cloud, or local-lane task from the template, so the lane reads one spec file instead of rediscovering the design. Use before dispatching any slice of work.
---

1. Pick the lane by the rule: Codex first for decided and verifiable work that needs the local firmware tree; cloud Claude for pure-software slices with tests and no hardware; local lane for one to six files with a failing test; local Claude only for design, review and unit gates.
2. Copy `templates/lane-brief.md` to `.runs/briefs/<slice>.md` and fill every field. The brief names: one spec file, the files the lane may change, the test that must pass and its expected result, the stop rule (3 failing attempts), and the result file.
3. The brief is at most 40 lines. Do not paste logs, diffs or design history; link the spec file instead.
4. Run `scripts/hygiene-check.sh .runs/briefs/<slice>.md` before sending (no mention of other projects, no em dashes).
5. Dispatch (use the dispatch skill for Codex or the local lane; a cloud session gets the brief text and the branch name). Start it in the background and move to the next slice at once.
6. When it ends, read only `.runs/<slice>.result.md`, run the named test, and read the diff; do not re-read the whole lane transcript unless the result is missing.
