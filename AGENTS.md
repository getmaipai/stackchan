# MaiPai StackChan

Firmware (`firmware/`) and host program (`host/`) for the StackChan robot. Standalone with a local LLM, or paired with MaiPai Home.
Org standards (writing style, privacy, PII) apply; see `getmaipai/.github`.

## Hard rules
- No dependency on any other MaiPai repo (no import, no submodule, no runtime call). Shared shapes are vendored snapshots with a drift check.
- Nothing in code, docs, comments or commit text mentions, compares to or credits other projects. Required license notices go only in LICENSE, NOTICE, THIRD-PARTY.md and `# Upstream:` patch lines. `scripts/hygiene-check.sh` enforces this.
- No em dashes, no filler vocabulary. Every error message says what went wrong and what to do.
- An optional feature that is off costs no memory. Every firmware step runs the memory gate.
- Every feature has a body half (unit and host, always here) and a brain half (standalone or Home adapter). A missing brain half hides the feature.

## Commands
- `bash scripts/check.sh` runs the hygiene check on all tracked files.
- `bash scripts/run-bg.sh NAME -- cmd...` runs a long command with output in `.runs/NAME.log`.
- `bash scripts/repo-map.sh` regenerates `docs/design/INDEX.md`.
- `bash scripts/install-hooks.sh` sets the repo-local hooks path (once per clone).

## Working economically (every lane, every session)

- Read `docs/design/INDEX.md` and the one spec file for your slice; do not grep or read the whole tree.
- Long commands go through `scripts/run-bg.sh`; read the status line and the summary, never the log. Do not paste build output, test logs or diffs into a message; give the path.
- Write results to `.runs/<slice>.result.md` (15 lines) and reply with one line.
- Stop after three failed attempts at the same step and report; do not widen scope.
- Use scripts for anything deterministic (hygiene check, repo map, memory summary, link check, golden diff); use a model only for judgement.
- Use the smallest model and effort that fits: Codex Luna low by default, Sonnet for bulk edits, Haiku for scans, the strongest model for one bounded design or review question.
- Prefer a follow-up message to the same agent over a new brief while its context is useful; start fresh when it is large or stale.
- Never run two writers on the same files; own your directory.
- Keep this file under 100 lines; move detail to `docs/design/`.
