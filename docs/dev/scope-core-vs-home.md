# Scope: the core robot and MaiPai Home

Owner direction, 2026-11-15: the core MaiPai for StackChan app should be simple and single purpose, not stretched to hold the kitchen sink. Anything bigger runs with MaiPai Home.

## The rule

Owner, 2026-11-15: the firmware and the local app bring the basics working well, private and local. Extras are not force-fitted by extending the local app.
The test is a rule: **we do not duplicate integrations, connectivity or features that MaiPai Home already has.** We connect to Home instead.

The carve-out: a basic the robot must do with no brain at all stays in the core, even if Home has its own version. Example: an on-robot timer that still rings when the host and Home are off. The robot's own link (Wi-Fi, pairing, Tailscale so it can reach its host from anywhere) is also core, because the robot needs it before any brain is reached.

How to use the rule on a new idea:

1. Does it work with only the LLM and the robot? If not, it is a Home feature.
2. Does Home already do it, or is it an integration or a connection? If yes, connect to Home. Do not build it here.
3. Is it a basic the robot must do alone? Then build it here, small, and keep it private and local.

## The core purpose

A private voice robot. It listens, answers with your own LLM, shows a face, keeps time, reacts to touch and motion, dances, protects your privacy and travels with you. It needs no brain beyond the LLM.

## In the core

Voice (wake word, follow-ups, interrupt, stop, ten commands), faces and clock, timers and alarms, reactions and idle life, dance on request and to music, mute, camera off and full quiet, the always-on cues, lights and sounds, on the go with Tailscale, pairing and security, signed updates with rollback, reset, English and Spanish, switch and go back.

## With MaiPai Home (not in the core)

| Feature | Why it goes to Home |
|---|---|
| Camera: snapshots, face follow, wave and mirror, take my picture, name list, what is this | Needs vision, identity and storage that Home already owns |
| Watch mode, security alarm, alerts | Alerts, recipients and quiet hours are household features |
| Baby and pet monitor | Listening in and alerts need Home's recipients and rules |
| Find my robot, remote beep, lights, talk, pan and tilt, live view | Needs accounts, a safe remote path and an activity log |
| Games and a pet mood | Persistent state and content, a Home package |
| Coding companion | An integration with an agent, a Home package |
| Home tools: local API, events, MQTT, home-automation bridge, metrics, MCP | Integrations belong in one place, Home |
| Memory, people, calendars, announcements, naming songs, child and teen rules | Household data and policy |

## What this means for the code

Final rule (owner reason: feature logic in the public repo invites hacks and copies for other bots): this repo keeps only what is native to the robot.

- The unit protocol, and a thin capability API: camera frame, microphone stream, lights, moves, display and cues, heartbeat and sensors.
- Cue enforcement on the unit, from one code path that opens the microphone or camera and draws the cue first.
- The core host keeps the voice turn, timers, reactions, dance, privacy switches, pairing and updates.
- Feature logic for watch, monitor, identity, alerts, recognition, games, the coding companion and integrations is **not** kept here. It lives in MaiPai Home against that capability API, so it is robot-agnostic and any robot gets it.
- The firmware has two presets with the same signing key. The Home preset adds the body halves Home features need, each behind its own Kconfig switch.
- Nothing in the core pages may say this app can do those features.

## Confirmed by the build session (2026-11-15)

- Superseded: an earlier plan kept moved host modules here under `extras/`. The final rule is that feature logic lives in MaiPai Home, not in this repo. See "What this means for the code".
- Firmware: one source and two presets with the same signing key. **Core** is small: no camera streaming, no monitor audio, no remote path. **Home** adds the body halves Home features need, each behind its own Kconfig switch, compiled in only if the memory gate holds. The hub's flash flow picks the preset. A user never chooses.
- First setup offers one optional, skippable screen: "Do you run MaiPai Home? Enter its address."
- The cue code path (`monitor_cue_begin`) is in the core and in both presets.
- The heartbeat that gives "last seen" stays in the core unit protocol, because Home's find-my-robot reads it.
- Doc line to keep: the core robot never streams a camera or a microphone to anything but the paired host's voice turn. The cue table in `docs/design/monitoring.md` is the Home-feature cue spec.

## Open

- The firmware already includes some body halves for the moved features (camera capture, streaming, the music detector). Decide which stay compiled in and which become optional builds, to keep the core small and inside the memory gate.
- Whether `home_url` pairing should be offered during first setup, so the extras are one step away.
- The docs mark moved features with the `Needs MaiPai Home` tag. Moving one back to the core is a tag change plus a design decision.

## The App Store test (owner, 2026-11-17; supersedes the camera and remote rows above where they differ)

Owner: the stock robot has an App Store, so "any feature that can come through the App Store can go local." The working test is now:

1. **Stock parity.** If the stock firmware or its App Center delivers a feature (photo, live view, monitoring, gallery, dance, games, data display, remote control), we may build it locally, as long as it needs no outside service and no household-wide data. We never ship less than stock, except what stock does through the vendor's cloud, which we replace with the owner's own model or Home.
2. **Local means on the owner's own host.** Frames, photos and audio stay on the owner's host (or the hub), never on a third party. Camera and remote features are opt-in, off by default, and always show their cue.
3. **Apps are packages, not firmware forks.** Optional features ship as host-side packages and unit data packs (games, scenes, voice games, translator, photo booth). One firmware image carries the capabilities; the owner turns them on. A smaller `core` image stays an option if the memory gate ever needs it, with the same signing.
4. **Home stays the owner of** outside services (weather, news, calendars, email), household records and other rooms, per-person identity and memory, policy, and the child and teen gates. In local mode those are off or answered from the model's own knowledge; in Home mode the hub supplies them.

What changed: the camera and remote rows in the table above (take my picture, face follow, find my robot, remote control) may now be built locally. Recognition, names and storage across the household still go to Home.
