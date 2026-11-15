# Repo boundaries: what lives where

Status: design review, 2026-11-15. Written for the owner to decide. Nothing here is built. Rules it leans on: `AGENTS.md`
(Scope, hard rules), `docs/dev/scope-core-vs-home.md`, `core-extras-modules.md`, `decisions.md` 1 to 3 and 10 to 11, and the
org rule that a repo exists only for a different release cadence, committer audience or visibility.

## Recommendation

Three homes, not four. (1) The public `stackchan` repo holds everything native to this robot: the firmware, the flasher and
updater, the unit protocol, the capability driver, the cue enforcement, the voice loop with its own-LLM brain, the body halves
(face, clock, reactions, dance, timers), and one small local settings page. It is a complete private voice robot with no Home.
(2) MaiPai Home holds every feature that is the same for every bot: vision and identity, watch and monitor, find my robot and
remote control, games and pet, the coding companion, MQTT and home automation. Home writes each once against the capability API.
(3) `commons/spec` owns the capability API and the record shapes; each robot repo and Home carry a stamped vendored copy with a
drift check. There is no shared robot code repo. The current `bot` repo stops being "the framework every robot plugs into"; it
becomes the Reachy Mini repo when that work resumes, or is archived. Reachy Mini reuses the shared part by implementing the same
spec, not by importing StackChan code.

## Where the owner's loose rule is wrong

- "If it can run on the robot it goes in the stackchan repo." The robot has about 76 KB of free RAM; almost nothing runs on it.
  The host program on a Mac or Pi is where features live, and "runs on the robot" says nothing about the host. The real test is
  the one already in `AGENTS.md`: does it need this robot's body, or the loop to talk through it?
- "If it is generic to both bots it goes in the bot repo." Generic code is two kinds. Definitions (capability names, shapes,
  fixtures) go to `commons/spec` as data. Generic feature logic (watch, identity, games) goes to Home, because it is about the
  household or Home already has it. What is left, the plain voice-loop glue, is small and each robot needs it to be complete
  alone. A third repo for it would have the same cadence, audience and visibility as the robot repos, so the org rule says no.
- "Home keeps household logic." Too narrow. Home also keeps robot-agnostic logic that is not about the household (games, the
  coding companion), by the owner's own reason: feature logic in a public robot repo invites hacks and copies for other bots.

## Decision table

Tests: T1 body (needs this robot's body or the talk loop), T2 same for every bot, T3 about the household or Home has it.

| Code | Lives in | Why | Test |
|---|---|---|---|
| Unit firmware body halves | `stackchan` firmware; Home-only halves behind Kconfig in the `home` preset | Native to this unit; off costs no memory | T1 |
| Unit protocol | `stackchan`, `schema/` | The wire to this unit only | T1 |
| Capability API and record shapes | `commons/spec`; vendored stamped copy in `stackchan` and Home | One definition for every bot and for Home | T2 |
| Cue enforcement (camera and mic) | Firmware, one code path (`monitor_cue_begin`); cue table stays in `monitoring.md` | Hardware truth; a modified host cannot bypass it | T1 |
| Voice turn and local speech | `stackchan` host | Needed to be complete with no Home | T1 |
| Own-LLM brain | `stackchan` host, behind the brain seam | The standalone brain; Home is another adapter | T1 |
| Face, clock, reactions, dance | Firmware for face, clock, timer ring, IMU reactions; host for dance clips and the move files | Body behaviour, same with or without Home | T1 |
| Vision and identity compute | Home (a Home package or sidecar); `stackchan` keeps camera frame and cue only | Same for every bot; people and consent are Home's | T2, T3 |
| Watch, monitor and alert logic | Home; unit keeps the sound meter, lifted sensor, `monitor_audio` message and cues | Recipients, quiet hours and history are household | T2, T3 |
| Find my robot and remote control | Home; unit keeps heartbeat, beep, Remote icon, servo limits, activity log line | Needs accounts and a safe remote path | T3 |
| Games and pet | Home package for packs, state and scores; game-engine primitives in the `home` preset firmware | Content and saved state; copies invited if public | T2 |
| Coding companion | Home package; unit keeps the status cue, build light and touch-only approval | An agent integration | T2, T3 |
| MQTT and home automation | Home | Integrations live in one place | T3 |
| Settings page | `stackchan` host, new small page (status, `robot.toml`, pairing code, mute, update, persona) | Needs no Home, shows no household data | T1 |
| Flasher and updater | `stackchan`; Home's flash flow calls it by pin and picks the preset | Native to this unit's chips and images | T1 |
| Reachy Mini equivalents | Its own repo (today's `bot` repo): daemon client, body profile, its own cue surfaces, settings page; same spec copy; same Home features | Different committer audience and robot | T1 |

## Three questions for new code

1. Does it need this robot's body, or the loop to talk through it? Yes: the robot repo (firmware if it must work with the host
   off or is a hardware truth, else the host).
2. Is it the same for every bot? Yes and it is a definition: `commons/spec`. Yes and it is logic: Home.
3. Is it about the household, other devices, services or policy? Yes: Home.

When the answers disagree: split at the capability API. The body half (capture, cue, move, light, ring) goes to the robot repo;
the thinking half goes to Home. A camera alert with a name is the example: frame and pink cue here, detector and recipient in
Home. Code that is body-free, household-free and the same for every bot (a face detector) is Home compute, never a robot repo.
Only one carve-out stays in the robot repo even when Home has it: a basic the robot must do with the host off (the timer ring).

## How Reachy Mini reuses the shared part

- `commons/spec` owns the capability API: the body capability vocabulary already there, the hello shape, the brain interface,
  the record shapes. Spec first, then Home, then each robot (org rule).
- Each robot repo vendors a stamped copy with a drift check (decision 10). The copy is data: schemas and fixtures, not code.
- Home holds one robot client against that spec. It does not know which robot is paired beyond the capability list.
- Voice-loop glue (pairing, link, brain seam, timers) is written in each robot repo. Reachy Mini runs on its own computer and
  Home runs its turns today, so its copy is a thin daemon client, not a second StackChan host.
- Plainly: no shared robot repo. Not a new one, and not `bot` as a framework. `bot` becomes `reachy-mini` or is archived.

## Changes to the current plan

1. `decisions.md` 10: narrow to "vendored copies are definitions and fixtures, never host code"; add "no shared robot code repo".
2. `decisions.md` 1 and 2: name what happens to `bot` (becomes the Reachy Mini repo or is archived; stops being a framework).
3. `decisions.md` 11: the grey zone is only "a basic the robot must do alone" (timer, alarm); drop "simple local version" for
   identity and routines, which conflicts with `scope-core-vs-home.md`.
4. `architecture.md`, "One schema": `schema/` here owns the unit protocol only; the capability API and brain interface are
   owned by `commons/spec`, otherwise Reachy Mini must copy from StackChan.
5. `architecture.md`, capability list: say there are two lists, brain-to-host and body-to-Home, both in the spec; never a third.
6. `features.md`, "Scope rule": delete local face enrolment and the named camera alert from the grey zone; they are Home.
7. `features.md`, "[Home] Camera": the bundled detector runs in Home compute, not this host; keep only capture and cue here.
8. `features.md`, "[Home] Integrations host": "All host-side" becomes "All in Home"; this host exposes only the capability API
   and the settings page.
9. `features.md`, build order 8 to 10: move "integrations host", "photo, camera alert" and "games, pet" to Home's backlog;
   keep timers, tools hook and the thinking cue here.
10. `monitoring.md`, "Alert channels, own-LLM": remove; the own-LLM robot has no watch mode. The cue table stays as the unit spec.
11. `core-extras-modules.md`: `moves/` stays in core (dance needs it); Home's pin moves on firmware releases too, not only
    on capability API changes, because Home's flash flow uses this repo's flasher and assets.
12. `safety-and-privacy.md`: "frames stay on the host" becomes "frames stay in the home, on the host or the Home hub".
13. The plan's "Who provides what" table (standalone: local enrol, simple detector, toml routines, MQTT) is superseded; mark it.
14. Follow-up outside this repo: `bot/AGENTS.md` and `BODY-STACKCHAN-01` describe the old framework plan; retire them.

## Risks, each with the one check that decides it

- Two copies of the voice-loop glue drift apart. Check: at Reachy Mini's first release, count identical lines between the two
  host loops; above about 3000, publish one pip package and ask the owner to amend the no-dependency rule.
- Face follow lags when the detector runs in Home compute instead of this host. Check: measure frame-to-head-move latency
  with the detector in a Home sidecar on the host machine; it must stay under 150 ms, or face follow moves back here as a body half.
- Capability sprawl or a third list. Check: the drift check passes in `stackchan` and Home against one spec file each, and an
  ad-hoc capability string fails CI.
- A core feature quietly needs Home. Check: CI runs the whole body-half suite with the own-LLM brain and no Home present.
- Home feature logic leaks into the public tree. Check: before the first GitHub push, `git ls-files` shows none of the moved
  modules (`vision/recognize.py`, `presence_watch.py`, `companion.py` and the rest of the leave list).
- The `home` preset breaks the memory gate. Check: the gate runs on the `home` preset with every Kconfig switch on.
- A modified host opens the camera without a cue. Check: a host test sends the open message with no cue and the unit refuses;
  `grep` shows `monitor_cue_begin` as the only caller of the open functions.
