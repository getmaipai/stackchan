# MaiPai StackChan

Custom firmware and a host program for the StackChan desktop robot. Talk to it, and it answers with AI that runs on your own
computer. Private by design, quick to react, and packed with things to do: timers, games, a camera, a clock, a coding companion and more.

> **Draft notice.** These docs are written as if v1.0.0 is finished, so the owner can review the full product. Remove this notice
> when v1.0.0 ships. Until then, treat every feature as unconfirmed on a unit.

![The robot on a desk with the big-eyes face, next to a laptop showing the web settings page.](docs/images/hero.svg)

## Why use it

- **Your voice stays home.** The robot talks only to a host program on your network, and the host calls only the addresses you list in one settings file.
  There is no vendor account, no telemetry and no cloud service in the loop. It keeps working with the internet off.
- **It reacts at once.** The wake tone and listening cue play in under 150 ms. "Stop" and touch commands act in under 300 ms with no model involved.
  Replies start speaking on the first finished sentence, not the last.
- **It does far more.** Faces and a clock, timers and alarms, pickup and petting reactions, a camera that can say who it sees, two games,
  a build light for your coding agent, and a local API for your own tools. All in one firmware.
- **You stay in charge.** Features are off until you turn them on. Updates are checked but never installed unless you say so, images are signed, and a failed update rolls back.
  The source is AGPL-3.0 and you can build it yourself.

## What you get

| Area | What it does |
|---|---|
| [Faces and look](docs/user/face-and-look.md) | Two face styles, any colour or none, a clock face, night mode, optional captions, quick sliders on the head strip. |
| [Voice](docs/user/voice.md) | Wake word, follow-up questions without it, interrupting, ten voice commands, personas, offline phrases. |
| [Timers and alarms](docs/user/timers-and-alarms.md) | A ring that empties as time runs out, named timers, snooze, an hourly chime, quiet hours. |
| [Moves and moods](docs/user/moves-and-moods.md) | Reactions to pickup, shake, tilt and petting. Breathing idle, quiet mode, privacy sleep, a low-battery ladder. |
| [Camera](docs/user/camera.md) | Opt-in. Snapshots, "what is this", face follow, "take my picture", a local name list. Frames stay on the host. |
| [Games and pet](docs/user/games-and-pet.md) | Colour memory, an action game, a pet mood that depends on care, music dance. |
| [Coding companion](docs/user/coding-companion.md) | Agent status on the face and ring, a green or red build light, dictation, approvals by touch. |
| [Home tools](docs/user/home-tools.md) | Local REST and WebSocket API, event stream, MQTT, a home-automation bridge and metrics. All off by default. |
| [Languages](docs/user/languages.md) | English and Spanish, switched at run time with no reflash. |
| [Updates](docs/user/updates.md) | Signed images, a health check after every install, automatic rollback. |

![The web app's feature list with each feature switched on or off.](docs/images/web-features.svg)

## Quick start

You need a StackChan robot, a USB cable, and a Mac, Linux machine or Raspberry Pi 5 to run the host.

```
pipx install git+https://github.com/getmaipai/stackchan
stackchan pair
stackchan check
```

Flash the firmware from the web flasher over USB (or build it with `stackchan firmware build`), type the 6 digit code the robot shows,
set `llm_url` in `robot.toml` to your model, and say the wake word. About 20 minutes the first time.
Full steps: [Getting started](docs/user/getting-started.md).

![The robot screen showing a 6 digit pairing code.](docs/images/pairing-code.svg)

## Run it alone, or with MaiPai Home

**Standalone (default).** The host uses a language model you run yourself, reached over a chat-completions style web address.
Speech to text and text to speech use the addresses you set, or a built-in local engine when you leave them blank.
You need nothing else.

**With MaiPai Home (optional, faster and smarter).** [MaiPai Home](docs/user/with-maipai-home.md) is a private AI hub for your household.
Set `brain = "home"` and the robot gets:

- **Faster answers.** Home keeps its speech and chat models loaded and warm on one machine built for them, so the first word arrives sooner.
  It can run bigger, better models than a small always-on host. A 4B class model answers in under 400 ms warm. A 27B class model on a weak host does not.
- **Memory.** It remembers across days and knows each person by voice and by name.
- **The household.** Calendars, briefings, announcements, song naming, and rules for children and teens.

The robot is complete without Home. Switching is one line in `robot.toml`, and the robot is not reflashed.

## Safety note

In standalone mode this repo adds no content filter of its own. Content safety is the job of the language model you connect and
your persona prompt. The family-friendly persona is a prompt, not a guarantee.

## Documentation

- Users: [Getting started](docs/user/getting-started.md), [Features](docs/user/features.md), [Settings](docs/user/settings.md),
  [Languages](docs/user/languages.md), [Privacy](docs/user/privacy.md), [Troubleshooting](docs/user/troubleshooting.md).
- Developers: `docs/dev/` (build from source, host and brains, contributing).
- Writing rules: `docs/STYLE.md`. Names still to confirm: `docs/dev/draft-names.md`. Design record: `docs/design/`.

## Contributing

Read `docs/dev/contributing.md` first. Run `bash scripts/check.sh` before you send a change.

## License

AGPL-3.0. See `LICENSE`, `NOTICE` and `THIRD-PARTY.md`. This is an independent project, not made or endorsed by the robot's maker.
