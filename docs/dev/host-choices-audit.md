# Host choices audit (owner decision 20, 2026-11-18)

Rule: offer a choice only when it is needed. We decide, with good defaults. Ask only when the answer changes something the person cares about, cannot be worked out, or has a real cost. Everything else is automatic or behind one collapsed Advanced section. Two close options: we pick one.

Dispositions: **keep** (needed, reason given), **automatic** (derive it), **merge**, **advanced** (stays, behind Advanced and out of the first-run path), **remove**.

## Counts before and after (this pass)

| Surface | Before | After | Change |
|---|---|---|---|
| `robot.toml` keys a person may have to write | 42 | 38 (the two `local_stack` lines are written by the Brain page, never by hand; `llm.tts_tokens` and `llm.tts_data_dir` are derived from `llm.tts_model`) | -4 |
| Keys the Brain page writes for the local stack | 9 | 6 | -3 |
| Questions at first run (Brain page, first-run) | 3 ways to choose, each with fields | 3 ways, and the only required fields are the ones with no default (Home's address; the three addresses of your own stack); the local stack asks one question (the size) with a recommended answer already selected | no new questions |
| Installed set page | per-kind picking | Automatic by default; Edit behind one button | choices hidden until wanted |
| CLI commands | 17 | 17 (`bench*` and `character` are maker tools, listed as advanced below) | 0 |

Counts of the unit settings registry (28 keys) and the CLI are reviewed below; no key was removed in this pass because a key a unit or Home already stores cannot vanish without a migration. The rule and the check below stop the number from growing, and each row says what to do next.

## `robot.toml`

| Key | Disposition | Reason |
|---|---|---|
| `brain` | keep | The one real choice: Home or your own stack. Set by the Brain page. |
| `units` | advanced | Per-unit overrides (model, persona, alarms); most homes never write it. |
| `llm.url`, `llm.model`, `llm.stt_url`, `llm.tts_url` | keep | The addresses of your own stack: no default exists. |
| `llm.api_key_env` | advanced | Only for a server that needs a key. |
| `llm.persona` | advanced | A default persona works; people who care edit it. |
| `llm.timeout_seconds`, `llm.history_messages` | advanced | Defaults are right for talking. |
| `llm.stt_model_dir`, `llm.tts_model` | automatic | Written by the local stack install. |
| `llm.tts_tokens`, `llm.tts_data_dir` | **automatic (done)** | Found beside `tts_model`. |
| `home.url` | keep | The address of Home. |
| `home.language` | automatic | Taken from the person's first choice. |
| `home.quiet_hours_from`, `home.quiet_hours_to` | keep | A household fact the robot cannot know. |
| `packages.*.enabled` | keep | A package is off until the person wants it (off costs nothing). |
| `packages.memory_notes.people`, `default_person` | keep | Names of people: cannot be derived. |
| `packages.memory_notes.folder`, `wake_word_maker.folder` | advanced | A good default folder exists. |
| `packages.home_assistant.url`, `token_env`, `cameras`, `speakers` | keep | Addresses and names that cannot be derived. |
| `packages.home_assistant.trigger` | advanced | The default phrase works. |
| `packages.home_assistant.allow_plain_http`, `allow_unidentified` | advanced | Safety relaxations; off by default and kept out of the main path on purpose. |
| `packages.coding_companion.show_request_text`, `port` | advanced | Defaults are the safe ones. |
| `settings.lan` | keep | Turns on a risk (the page reachable from the network): needs a decision. |
| `remote.enabled` | keep | Same: a risk the person must choose. |
| `update.source`, `update.trusted_key` | advanced | Only for people who run their own releases. |
| `update.preset` | merge | Follows the installed image; to be removed when there is one image. |
| `local_stack.enabled`, `local_stack.choice` | automatic | Written by the Brain page; never edited by hand. |

## Unit settings registry (the settings page, 28 keys)

Needed (a person cares about the result): `robot.muted`, `robot.vision_off`, `robot.quiet`, `robot.mute.local_unmute`, `robot.face.color`, `household.quiet_hours.from` and `.to`, `robot.timers.enabled`, `robot.camera.watch_level`.

Automatic where the host can decide (next): `robot.night.mode` (follow the light sensor), `robot.idle.level`, `robot.follow_up.seconds`, `robot.greetings.mode`, `robot.sleep.auto`, `robot.firmware.auto` (the update service already decides), `robot.power.warn_at`.

Advanced (collapsed): `robot.dance.*` (four keys), `robot.sounds.enabled`, `robot.sounds.night`, `robot.announce.enabled`, `robot.repeat.enabled`.

Remove or merge candidates (need Home and unit migration, listed for the owner): `robot.dance.auto_sensitivity` and `robot.dance.show_ring` (one "dance with the music" switch), `robot.sounds.night` (follows quiet hours).

## CLI

Keep: `run`, `status`, `pair`, `service`, `check`. Advanced: `units`, `name`, `face`, `forget`, `settings-token`, `coding-token`, `flash`, `update`. Maker tools, hidden from help for users: `bench`, `bench-run`, `bench-analyze`, `bench-frames`, `bench-compare`, `character`.

## Environment variables

25 `MAIPAI_*` variables are read. They are for tests and unusual installs, not settings; none is shown on any page. They stay documented only in `docs/dev`.

## First screen of the dashboard

The few things that matter first: is my robot OK (the health sentence), what is it doing (connected, in a turn, asleep), what do I need to do (the first failed part's advice, or a pairing code when no robot is paired). The health page already leads with that sentence; the settings home links it first.

## What was done in this pass

- `llm.tts_tokens` and `llm.tts_data_dir` are derived from `llm.tts_model`, and the local stack installer no longer writes them.
- The Brain page and the installed-set page have Automatic defaults and put manual editing behind one button.
- `docs/dev/choices-rule.md` and a check in `scripts/check.sh`: every key of `robot.toml` needs a row in `docs/dev/settings-justification.md`.

## Not done, and why

The unit settings registry reductions (merging the dance switches, deriving night mode and idle level) change what Home and units store: they need a migration plan with the owner. The first-run page of the unit is the firmware track's (UX12).
