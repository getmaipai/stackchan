# MaiPai StackChan

Firmware (`firmware/`) and host program (`host/`) for the StackChan robot. With your own LLM, or paired with MaiPai Home.
Org standards (writing style, privacy, PII) apply; see `getmaipai/.github`.

## Hard rules
- No dependency on any other MaiPai repo (no import, no submodule, no runtime call). Shared shapes are vendored snapshots with a drift check.
- Nothing in code, docs, comments or commit text mentions, compares to or credits other projects. Required license notices go only in LICENSE, NOTICE, THIRD-PARTY.md and `# Upstream:` patch lines. `scripts/hygiene-check.sh` enforces this.
- No em dashes, no filler vocabulary. Every error message says what went wrong and what to do.
- An optional feature that is off costs no memory. Every firmware step runs the memory gate.
- Every feature has a body half (unit and host, always here) and a brain half (own-LLM or Home adapter). A missing brain half hides the feature.

## Commands
- `bash scripts/check.sh` runs the hygiene check on all tracked files.
- `bash scripts/run-bg.sh NAME -- cmd...` runs a long command with output in `.runs/NAME.log`.
- `bash scripts/repo-map.sh` regenerates `docs/design/INDEX.md`.
- `bash scripts/install-hooks.sh` sets the repo-local hooks path (once per clone).

## Who does the work (owner rule, 2026-11-15; binds every session here, parent and child)

Order, no exceptions: (1) Claude cloud; (2) Codex, launched in an owned tmux session Jesse can attach to; (3) our local coder (`local-lane dispatch`, small decided tasks); (4) Claude agents on this machine.
A Claude agent here (Sonnet, Haiku or Opus) is never the first choice for edits, test fixing, builds or flashing. Using one needs a reason, written before launch, why steps 1 to 3 could not do it. A parent never reports local Claude agents as "running" for work that belonged to steps 1 to 3.
This rule binds the session that dispatches work. A Codex run started by the dispatcher in an owned tmux session (`stackchan-<slug>-codex`) already is step 2: it does its brief and must not refuse, re-route or hand work back.
If this repo has no launcher for a step, fix the launcher first instead of falling back to a local agent.

## Scope (owner rule, 2026-11-15)

Our firmware and local app bring the basics working well, private and local. Extras are not force-fitted by growing the local app. We do not duplicate integrations, connectivity or features that MaiPai Home has; we connect to Home. Test for any new idea: (1) does it work with only the LLM and the robot? (2) does Home already do it, or is it an integration or a connection? Then connect to Home. (3) is it a basic the robot must do alone (an on-robot timer that rings with the host off; the robot's own Wi-Fi, pairing and private-network link)? Then build it small in the core. Module split: `docs/design/core-extras-modules.md`. The cue code path stays in the core.

## Fastest path (owner rule, 2026-11-15)

For every feature, pick the quickest route to a verified result and write a one-line verdict first (`PORT`, `REBUILD` or `SKIP`, with the reason) in the lane brief:
- PORT when the old patch or module applies clean or with at most about 3 conflict hunks, and the surrounding file was not rewritten upstream. Check with `git apply --check` or the patch map in `docs/design/firmware-base.md`.
- REBUILD (old code is the spec and the test, not the starting text) when the file was rewritten or moved upstream, the old code carries patches that exist only to dodge old limits, or the new base already offers the feature (see `docs/design/upstream-review.md`: HAVE and TAKE rows).
- SKIP when the feature is on the cut or dropped lists.
Never spend more than a few minutes choosing; when unsure, PORT the tests first and let them show what breaks. Run independent lanes in parallel, one owner per file set. Reuse old tests as the acceptance suite either way.

## Links Jesse can open (owner rule, 2026-11-15)

The desktop app previews a clicked file only when it sits inside one of the session's folders. At the start of a session that works in this repo from another folder, call `request_directory` for this repo's path, then link files as markdown links relative to that folder. A file outside every session folder (for example `~/esp/...`, `~/stackchan-backups/...`, `.runs/` of another checkout) is never linked as if it opens: copy a short result into this repo's `docs/` or say the full path in text and open it with `show_pane`.

## Working economically (every lane, every session)

- Read `docs/design/INDEX.md` and the one spec file for your slice; do not grep or read the whole tree.
- Long commands go through `scripts/run-bg.sh`; read the status line and the summary, never the log. Do not paste build output, test logs or diffs into a message; give the path.
- Write results to `.runs/<slice>.result.md` (15 lines) and reply with one line.
- Stop after three failed attempts at the same step and report; do not widen scope.
- Use scripts for anything deterministic (hygiene check, repo map, memory summary, link check, golden diff); use a model only for judgement.
- Use the smallest model and effort that fits: Codex Luna low when Codex does it; local Claude only as the routing rule above allows (Haiku for scans, the strongest model for one bounded design or review question).
- Prefer a follow-up message to the same agent over a new brief while its context is useful; start fresh when it is large or stale.
- Never run two writers on the same files; own your directory.
- Keep this file under 100 lines; move detail to `docs/design/`.
