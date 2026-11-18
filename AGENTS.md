# MaiPai StackChan

Firmware (`firmware/`) and host program (`host/`) for the StackChan robot. With your own LLM, or paired with MaiPai Home.
Org standards (writing style, privacy, PII) apply; see `getmaipai/.github`.

## Hard rules
- No shared robot code repo: vendored copies from commons/spec are definitions and fixtures, never host code. See docs/design/repo-boundaries.md.
- No dependency on any other MaiPai repo (no import, no submodule, no runtime call). Shared shapes are vendored snapshots with a drift check.
- Names and credits (owner, 2026-11-18, `docs/plan/trademark-and-affiliation.md`): accurate credits, source names, URLs and provenance records may appear wherever they are useful, and the 3D model shows the real robot with its own name and marks. Required license notices stay in LICENSE, NOTICE, THIRD-PARTY.md and with the redistributed assets. The maker's marks are never used as this project's branding, and the affiliation wording comes from `docs/legal/affiliation.json`. `scripts/hygiene-check.sh` still blocks the names on the owner's private word list.
- No em dashes, no filler vocabulary. Every error message says what went wrong and what to do.
- An optional feature that is off costs no memory. Every firmware step runs the memory gate.
- Every feature has a body half (unit and host, always here) and a brain half (own-LLM or Home adapter). A missing brain half hides the feature.

## Commands
- `bash scripts/check.sh` runs the hygiene check on all tracked files.
- `bash scripts/test-all.sh` runs the complete host suite in 4 processes (builds the virtual unit renderers first); run it before landing. `bash scripts/test-fast.sh` leaves out the slow tests.
- `bash scripts/run-bg.sh NAME -- cmd...` runs a long command with output in `.runs/NAME.log`.
- `bash scripts/repo-map.sh` regenerates `docs/design/INDEX.md`.
- `bash scripts/install-hooks.sh` sets the repo-local hooks path (once per clone).

## Who does the work (owner rule, 2026-11-15; binds every session here, parent and child)

Order, no exceptions: (1) Claude cloud; (2) Codex, launched in an owned tmux session Jesse can attach to; (3) our local coder (`local-lane dispatch`, small decided tasks); (4) Claude agents on this machine.
A Claude agent here (Sonnet, Haiku or Opus) is never the first choice for edits, test fixing, builds or flashing. Using one needs a reason, written before launch, why steps 1 to 3 could not do it. A parent never reports local Claude agents as "running" for work that belonged to steps 1 to 3.
This rule binds the session that dispatches work. A Codex run started by the dispatcher in an owned tmux session (`stackchan-<slug>-codex`) already is step 2: it does its brief and must not refuse, re-route or hand work back.
If this repo has no launcher for a step, fix the launcher first instead of falling back to a local agent.

## Scope (owner rules 2026-11-15, replaced in part by decisions 1 and 3 of 2026-11-18)

Our firmware and local app bring the basics working well, private and local. A feature belongs here when it passes any of four tests: (a) body: the unit's own hardware or cue path; (b) standalone parity: what the stock robot or a leading community project does without a hub, we deliver locally as an optional package; (c) household: Home owns several-person policy, child and teen rules, recognition by name, outside services and other rooms; (d) thin connector with one owner: when paired, Home's version takes over. Optional local packages allowed without Home (decision 3): Home Assistant voice and camera snapshots, agent tools, the coding companion, and local memory for several adults as plain per-person notes files. Packages live in `host/maipai_packages/<name>/`, are off by default, cost nothing while off (imported only when switched on in `robot.toml`), import no Home code and hold no identity or household code beyond their own files. Module split: `docs/design/core-extras-modules.md`.

Enforced: `scripts/boundary-check.sh` runs in `scripts/check.sh` and fails on new Home-feature code under `host/maipai_body`, on a package under `host/maipai_packages` that imports Home code or identity modules, on the own-LLM brain importing Home code, and on a new firmware patch without a `# Placement:` line. The old modules still waiting to leave sit on `docs/design/boundary-debt.txt`, which may only shrink. Every lane brief starts with a Placement line (template: `docs/templates/lane-brief.md`).

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
