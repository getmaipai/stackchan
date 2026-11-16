# Reachy Mini migration and retiring `bot`

Status: plan, written 2026-11-16 for the owner to decide. Nothing here is built or run. It follows "Migration order" in
`decisions.md` (owner, 2026-11-15) and decisions 1, 2, 3 and 10. The commands in section 3 are an outline and were not run.
Facts below were read from the local `bot` checkout (572 commits, version 0.2.105), Home's pin files and this repo.

## Bottom line

- Move the Reachy Mini work into its own repo, `getmaipai/reachy`, with its history, and archive `bot` once Home pins the new repos.
- `bot` today is mostly StackChan code and a copy of the shared voice layer. Reachy is about 2,200 lines of body code plus
  its tests, scripts and docs. The extraction is small; the real work is the trim, Home's pins and the spec copy.
- The shared voice layer is about 17,700 lines identical in `bot` and in this repo. That trips the duplication check in
  `repo-boundaries.md` (limit about 3,000). It needs one owner answer (question 2).

## 1. What is in `bot`, and where each piece goes

Line counts are Python lines under `body/maipai_body/` in `bot` (2026-11-16), compared with `host/maipai_body/` here.

| Piece in `bot` | Lines | What it is | Goes to |
|---|---:|---|---|
| `bodies/stackchan/` (host side, firmware patches, assets, avatar, xiaozhi server) | 17,584 | StackChan | Already moved to `stackchan`. Leave behind; nothing to copy. |
| `bodies/reachy_mini/` (`client.py`, `profile.py`, `motors.py`, `envelope.py`, `eyes_client.py`, `audio_config.py`, `fake.py`, `fixtures/`) | 2,168 | Reachy daemon client and body profile | `reachy`, as its body package |
| `bodies/fake/` | 191 | Test double behind the HAL seam | `reachy` (it is the CI fake) |
| `hal/`, `robot/` | 1,211 | The seam and the robot object | `reachy`, own copy |
| `speech/`, `vision/`, `presence/`, `expression/`, `indicator/`, `initiative/`, `selftest/`, `moves/` | 13,067 | Voice loop, wake word, face and presence, expression, dance | `reachy`, own copy, trimmed to what Reachy uses |
| `link/` (pairing, hub link, offline ladder) | 3,389 | Connection to Home | `reachy`, own copy. The offline ladder was scoped to Reachy first. |
| `measure/`, `dashboard/` | 4,893 | Bench tools and the local page | `reachy`; the StackChan-only measures stay out |
| `hub_host.py`, `scripts/build-hub-bundle.sh` | about 400 | Hub sidecar that Home downloads and runs for connected bodies | Open check (section 6, step 3): which body needs it |
| `app.py` (the `reachy_mini_apps` entry point `maipai_bot`) | part of 6,479 top-level | The app the Reachy daemon launches | `reachy` |
| `body/tests/` (272 entries; 91 named `stackchan`) | | Tests | Reachy keeps the shared and Reachy tests (`test_profile`, `test_envelope`, `test_eyes_client`, `test_motor_*`, link, speech, expression); StackChan tests stay behind |
| `scripts/install-reachy.sh`, `probe_eyes.py`, `udev/`, `robot-conf/`, `measure_rm07_egress.py` | | Reachy install and network scripts | `reachy` |
| `scripts/cut-release.sh`, `sign-release-sums.sh`, `signing-key.sh`, `publish-release.sh`, `build-wheelhouse.sh`, `prepare-bot-release.sh` | | Release tooling | `reachy`, rewritten for one wheel and no firmware |
| `docs/dev/design-reachy-mini-*`, `reachy-mini-gap-audit-*`, `reachy-mini-media-stack-*`, `research-minicpm5-reachy-mini-*`, `what-we-take-from-pollen-*`, `eyes-wire-protocol.md`, `led-standard-*` | | Reachy design record | `reachy/docs/design/` |
| `docs/user/reachy-mini-setup.md`, `reachy-mini-privacy.md` | | User docs | `reachy/docs/user/` |
| `docs/BACKLOG.md` ("Reachy Mini body" area and the Reachy rows of EXPR, LINK and MR items) | 3,067 total | Build status | Split: Reachy rows move; StackChan rows were handled by that move; `bot`'s file gets a tombstone |
| `docs/dev/stackchan-*`, `design-stackchan-*`, `xiaozhi-protocol.md` | | StackChan design record | Already in `stackchan`; confirm, then leave behind |
| `docs/dev/hal-seam.md`, `design-robot-api-2026-10-14.md` | | The one-seam and robot-API ideas | `reachy/docs/design/` as history. The robot API now lives in `commons/spec` (decision 10); mark these superseded. |
| `dist/` (42 GB), `data-scratch/`, `bot-release/` | | Git-ignored build output and notes | Never copied. Not in history. |

Found while reading: this repo's `host/maipai_body/bodies/reachy_mini/` is a leftover copy of the Reachy code. It should be
deleted from `stackchan` when `reachy` is verified (step 4 of the work list), so each body exists in one place.

## 2. Own repo or Home package

The rule (org principle 5, restated in `decisions.md` 1 and `repo-boundaries.md`): a repo exists only for a different release
cadence, committer audience or visibility; otherwise the code belongs in a shared home. Home features are packages from
`getmaipai/catalog`; a body driver is not a feature.

Recommendation: own repo, `getmaipai/reachy`, same visibility rules as this repo.

1. Different release cadence. The Reachy app is a Python wheel the Reachy daemon installs and runs on the robot's own
   computer. It ships when the body code changes, not when Home ships. Home only pins a release.
2. Different committer audience. People who work on a Reachy Mini body and people who work on Home do not overlap.
3. A Home package fails the existing test. The 2026-09-27 design (section 2) rejected a package because a 50 Hz control loop,
   the motion arbitration and the stop path cannot live inside a catalog package's sandbox. That still holds.
4. Keeping it in Home fails decision 11: it is body code (needs this robot's body or the loop to talk through it), not a
   feature that is the same for every bot.
5. The September decision said "no new repo, it ships with Bot's release". That reason is gone: `bot` is no longer the
   framework (decision 1), and a Reachy-only `bot` is the same thing as a new repo with a worse name.

Name: the brief and this note use `getmaipai/reachy`; `repo-boundaries.md` says `reachy-mini`. Pick one before step 3 (question 1).
Package `maipai-reachy`, command `reachy`, mirroring decision 6. The product name needs the same trademark register search
that `decisions.md` ("Name check") requires for StackChan.

## 3. History-preserving extraction (script outline, not run)

Goal: `reachy` keeps the real commit history of every Reachy file, with authors and dates, and contains no StackChan files.
Nothing is written to `bot`; all work is on a fresh clone in the scratch area.

Tool: `git filter-repo`. It is not installed on this Mac (checked 2026-11-16). Install it by pinned version with `uv tool install`
before step 1 and write the version in the script header. Fallback is `git filter-branch`, slower and riskier, only if the install fails.

```bash
#!/usr/bin/env bash
# Outline only. Intent: build getmaipai/reachy from a fresh clone of bot with Reachy history only.
set -euo pipefail
SRC=/Users/jessetorres/Developer/github.com/getmaipai/bot        # read only
WORK=$SCRATCH/reachy-extract                                      # empty directory
source /Users/jessetorres/Developer/github.com/getmaipai/home/data-scratch/bin/https-git.env

# 0. Mirror first: a full backup of bot as it is today (rollback point, section 6).
git clone --mirror "$SRC" "$WORK/bot-before.git"
git -C "$WORK/bot-before.git" bundle create "$WORK/bot-before.bundle" --all

# 1. Fresh non-local clone (filter-repo refuses a dirty or reused clone).
git clone --no-local "$WORK/bot-before.git" "$WORK/reachy"
cd "$WORK/reachy"

# 2. Keep only Reachy and shared paths. Renames put the Python package at the new root.
git filter-repo \
  --path body/maipai_body/bodies/reachy_mini  --path body/maipai_body/bodies/fake \
  --path body/maipai_body/hal --path body/maipai_body/robot --path body/maipai_body/speech \
  --path body/maipai_body/vision --path body/maipai_body/presence --path body/maipai_body/expression \
  --path body/maipai_body/indicator --path body/maipai_body/initiative --path body/maipai_body/selftest \
  --path body/maipai_body/moves --path body/maipai_body/link --path body/maipai_body/measure \
  --path body/maipai_body/dashboard --path body/maipai_body/static \
  --path body/maipai_body/app.py --path body/maipai_body/__init__.py \
  --path body/tests --path body/scripts --path body/pyproject.toml --path body/uv.lock \
  --path scripts/install-reachy.sh --path scripts/probe_eyes.py --path scripts/udev --path scripts/robot-conf \
  --path-glob 'docs/dev/*reachy*' --path docs/dev/eyes-wire-protocol.md --path docs/dev/hal-seam.md \
  --path-glob 'docs/user/reachy-mini-*.md' \
  --path LICENSE --path NOTICE \
  --path-rename body/maipai_body/:host/maipai_body/ --path-rename body/tests/:host/tests/ \
  --path-rename body/pyproject.toml:host/pyproject.toml --path-rename body/uv.lock:host/uv.lock \
  --path-rename body/scripts/:host/scripts/
# A filter list this long is a first guess. Step 3 compares it with `git ls-files` of bot's last commit.

# 3. Remove StackChan-only files that rode along in shared directories (tests, measures, fixtures).
git filter-repo --invert-paths --path-glob '*stackchan*' --path-glob '*xiaozhi*' --path-glob '*firmware*'

# 4. Rewrite the author mail to the GitHub noreply address if any commit carries another (check with git shortlog -sne).
# 5. Scan the whole new history: gitleaks, the private PII word list, scripts/hygiene-check.sh on every blob.
# 6. Push to a local bare origin first (decision 7 pattern); create the GitHub repo only when the first cloud lane starts.
```

What to verify before the new repo counts as real (each is a command with an expected result):

1. Commit count: `git rev-list --count HEAD` is about 43 Reachy-path commits plus shared-layer commits, never more than 572.
   `git log --follow` on `profile.py` and `client.py` reaches the original RM-01 commit (`531cf59`).
2. `git ls-files | grep -i -E 'stackchan|xiaozhi|firmware'` prints nothing.
3. `git diff --stat bot-before..reachy -- host/maipai_body/bodies/reachy_mini` shows rename-only differences.
4. `uv sync` and `uv run pytest` pass in `host/`; `ruff check` and `ruff format --check` pass.
5. The simulator run passes: `reachy-mini-daemon --sim` on port 8000, then the suite with `MAIPAI_BODY_LIVE=1` (the same
   switch `bot` uses today).
6. `git count-objects -vH` is small (the 42 GB `dist/` is ignored and never entered history; confirm).
7. Secrets scan and the hygiene scan of the whole history are clean. A public repo needs this before the first push
   (`release-and-updates.md`, "the repo goes public at that moment, after the hygiene scan of the whole history passes").

## 4. Vendored spec copy and drift check (decision 10)

Today `bot` reads the spec from a sibling checkout (`../commons-tags/spec-spec-v0.1.208/spec`, `spec_pin.py`, `scripts/spec-dir.sh`).
That makes the repo depend on a neighbour, which decision 2 forbids. Reachy copies the mechanism this repo uses.

- Vendor to `host/spec-vendor/spec/` (data only: records, fixtures, `gen`, assets) plus `STAMP.md` naming the source tag
  (now `spec-v0.1.208`). `scripts/spec-dir.sh` prints that path; `MAIPAI_SPEC_DIR` points there.
- Vendor only what Reachy reads: the body capability vocabulary with the Reachy Mini and the Eyes board entries, the hello
  shape, the brain interface, the record shapes the link uses, and the Reachy fixtures (`Device.capabilities`).
  Never vendor host code.
- Drift check, in `scripts/check.sh`: (a) `STAMP.md` lists a SHA-256 per vendored file; the check recomputes them and fails on
  any change, so nobody edits a copy by hand; (b) when a `commons` tag checkout is present, the check compares the stamped tag with
  the newest `spec-v*` tag and prints "behind by N" without failing, and fails only on a file difference at the same tag;
  (c) an ad-hoc capability string in code that is not in the vendored vocabulary fails the build.
- Finding: this repo's `STAMP.md` is two lines and a grep found no script that reads it. Build the real check once in `reachy`,
  then port it back to `stackchan`. Both repos then run the same check. Spec first, then Home, then robots (org rule).

## 5. Rules carried over, and what differs without an ESP32

Carried over unchanged in meaning:

- No stealth. Anything that opens the camera or microphone shows a cue, and the cue comes from the same code path that opens
  it. On the unit that path is firmware `monitor_cue_begin`. On Reachy the equivalent is one Python function in the body
  profile (name it `cue_begin(mode)`); the only code that may call the daemon's camera and microphone start is that
  function. A test fails the build if `grep` finds another caller. The cue table in `monitoring.md` stays the spec, with
  Reachy's surfaces: antennas, the Eyes LED board and the head pose instead of a screen and a light ring.
- Body safety stays: servo limits, volume cap, wear limits, mute, pairing security. Age and surface gates are Home's and are
  never reimplemented in the robot repo (`AGENTS.md`, hard rules). The robot adds no content filter of its own (decision 13).
- An optional feature that is off costs nothing, and a gate proves it (decision 30).
- Public text never mentions other projects (decision 29); only notices in `LICENSE`, `NOTICE` and `THIRD-PARTY.md`.
- Errors say what went wrong and what to do next.

What differs for a robot with no ESP32:

| Topic | StackChan unit | Reachy Mini |
|---|---|---|
| Where the app runs | A host program on a Mac or Pi; the unit only runs firmware | The app runs on the robot's own computer (a Linux Compute Module, 4 GB per the 2026-09-27 design) as the daemon's one app |
| Memory gate | About 76 KB of internal RAM free; gate in `firmware-memory.md` (25 KB steady, 15 KB lowest, 16 KB largest block) | No KB gate. Gate is process memory (RSS) and CPU: measure the idle and one-turn peak with `measure_mr1_budget.py`, write the numbers in a table with build id and date, fail a step that adds more than an agreed share. The numbers do not exist yet; step 6 measures them. |
| Cue enforcement | Firmware refuses to open the mic or camera without the cue; a modified host cannot bypass it | The daemon owns the hardware and accepts any installed app, so a modified app can open the camera. The single code path plus a test is the guarantee, plus the physical cuts the profile can prove (mute, shutter). Say this limit plainly in the user docs, as `reachy-mini-setup.md` already does for other limits. |
| Servo limits | Firmware | The daemon clamps; the profile adds its own tighter limits and the e-stop recovery path |
| Updates | Firmware OTA and flasher | A wheel from a `reachy` release, installed by `install-reachy.sh`, hash and signature checked |
| Hub dependence | Own-LLM brain makes it complete with no Home | Connected body in v0.1: the hub runs turns; with no hub it says so once and keeps wake, stop and idle life (design section 3). Whether Reachy gets an own-LLM brain is a later decision. |

## 6. Retiring `bot`

Order matters; each step is reversible until the archive.

1. Finish StackChan v1 (the stated precondition). Do not start extraction before the first StackChan release tag exists,
   except steps 1 and 2 of the work list, which are read-only or spec-only.
2. Build and verify `reachy` (sections 3 to 5) against the simulator. Cut `reachy`'s first release.
3. Home's pins (Home repo, its own session; pin and release logic is a risky surface, so full `check.sh` and `code-review`):
   - Today one file, `backend/src/lib/botReleasePin.json`, pins one `getmaipai/bot` release: hub bundles for darwin-arm64,
     linux-x64, linux-arm64 and the StackChan firmware set, with the signing key. `scripts/pin.sh` has one `bot <version>` kind;
     `backend/src/lib/botRelease.ts` downloads and verifies it; `backend/src/lib/updates.ts` has `BOT_TARGET` for
     `getmaipai/bot` and checks for updates only when a robot is paired; tests are `botRelease.test.ts`, `stackchanInstall.test.ts`,
     `updates.test.ts`, `privacy.test.ts`, `scripts/pin.test.ts`; docs are `docs/PINNING.md` and `docs/dev/delivery-pipeline.md`.
   - Target: two pin files and two `pin.sh` kinds, `stackchan <version>` (hub sidecar if it stays, firmware set) and
     `reachy <version>`; two update targets; each repo has its own signing key entry; the "Home calls only configured
     addresses" test lists both repos.
   - Check first which body still needs the hub bundle (`hub_host.py`, the voice and avatar ports). If only StackChan does, it
     moves to `stackchan`'s release and Reachy ships a wheel only.
   - Ship to the live hub only when Jesse says so in that turn (`ship.sh`).
4. Wait one release cycle with both pins live and `bot` untouched, so a hub that has not updated can still fetch the old
   `bot` release. Archiving does not delete releases; the old assets stay downloadable.
5. Final `bot` commit (on its own main, by name): replace `AGENTS.md` with a short tombstone (what moved where, links to
   `stackchan` and `reachy`, "archived"), delete the "framework every robot plugs into" text, mark `BODY-STACKCHAN-01` as
   done and moved to `stackchan` with its one-line outcome, and mark the Reachy rows as moved to `reachy`. Update `README.md` the same way.
6. Org files, in their own repos: `getmaipai/CLAUDE.md` product table (`bot` row replaced by `reachy`), `.github` standards,
   `repo-boundaries.md` item 14 here (done), Home docs that name `bot` (`docs/dev.md`, `docs/BACKLOG.md`).
7. Archive `getmaipai/bot` on GitHub (read only). Keep the mirror from section 3 step 0 as
   `legacy-backups/bot-final.git` next to the existing `bot-legacy.git`.

Rollback:

- Before step 7: revert Home's pin commits (`pin.sh bot <last version>` restores the old file); `bot` is untouched.
- After step 7: un-archive is one setting on GitHub; the mirror and bundle from step 0 restore everything else.
- If `reachy` is found wrong after Home pins it: pin Home back to the last `bot` release and keep both repos alive. No history is deleted anywhere.

## 7. Ranked work list

Lanes follow `AGENTS.md` routing: Claude cloud, then Codex, then the local lane (`local-lane`), then Claude agents on this
machine (needs a written reason). Sizes are working hours for one session.

| # | Item | Size | Lane |
|---:|---|---:|---|
| 1 | File-by-file move/leave/drop list from `git ls-files` of `bot`, settle name and visibility | 2 h | Claude cloud (judgment) |
| 2 | Spec: confirm the body vocabulary has Reachy and Eyes entries; write the drift check and the vendored copy layout in `commons` terms | 3 h | Codex |
| 3 | Extraction script, dry run in scratch, verification list (section 3) | 3 h | Codex; Claude cloud reads the diff |
| 4 | Trim `reachy` to what Reachy uses; delete the leftover Reachy copy from `stackchan` | 5 h | Codex; local lane for single-file edits |
| 5 | Scaffold: `AGENTS.md`, README, `check.sh`, hygiene hook, architecture test (no hub import, one cue path) | 3 h | Codex |
| 6 | Cue path, RSS and CPU budget gate, regression tests, measured numbers | 4 h | Claude cloud designs; Codex writes tests |
| 7 | Simulator run of the moved repo end to end | 2 h | Claude agent on the Studio (the simulator needs this machine; reason: steps 1 to 3 cannot run MuJoCo) |
| 8 | Release tooling: one wheel, hashes, signature, `install-reachy.sh` check | 4 h | Codex |
| 9 | Home pins, update targets, tests, docs (section 6 step 3) | 6 h | Codex; Claude cloud review at medium |
| 10 | Tombstone commit, org docs, archive, mirror | 2 h | Claude cloud, archive after Jesse's yes (question 5) |

Total about 34 hours, roughly six sessions. Items 1 to 3 can start before StackChan ships; 4 and later wait for the release tag.
Physical Reachy rows (real motors, real microphones) stay marked unproven until a unit is on the bench (question 4).

## 8. Questions only the owner can answer

1. Repo name and visibility. Default: `getmaipai/reachy`, public like `stackchan`, after the history hygiene scan, with a trademark
   register search on the product name before the first public release.
2. The shared voice layer is about 17,700 identical lines in two repos, far over the 3,000 line check. Default: keep two
   copies now (decision 10), trim Reachy's copy, re-count at Reachy's first release, and bring the number back to you then.
   The alternative is one pip package, which needs an amendment to the no-dependency rule.
3. Start time. Default: steps 1 to 3 now (read only and spec work), the rest after the first StackChan release tag.
4. Is a Reachy Mini unit on the bench? Default: assume no; verify on the simulator only and label every physical row unproven.
5. Archive `bot` on GitHub after one release cycle with both pins live. Default: yes, since it is reversible and the
   mirror is kept.
