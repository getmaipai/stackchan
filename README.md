# MaiPai StackChan

Firmware and a host program for the StackChan desktop robot. The robot talks, shows a face, sets timers, plays games and keeps you
company, using AI models that run in your own home.

> **Draft notice.** These docs are written as if v1.0.0 is finished, so the owner can review the full product. Remove this notice
> when v1.0.0 ships. Until then, treat every feature as unconfirmed on a unit.

> **Screenshot placeholder:** `hero.png`. The robot on a desk with the big-eyes face, next to a laptop showing the web settings page.

## The promise

Private, local AI that is yours. Nothing leaves your home. The robot talks only to the host program and the Wi-Fi you gave it.
The host calls only the addresses you put in its settings file. There is no telemetry, no vendor account and no cloud.

## What it does

- **Face and look.** Two face styles, any colour or none, a clock face, night mode and an optional caption line. [Details](docs/user/face-and-look.md)
- **Voice.** Say the wake word, then talk. Follow-up questions need no wake word, and you can interrupt. [Details](docs/user/voice.md)
- **Timers and alarms.** A ring on the screen empties as time runs out. Snooze, and tones for each kind of alarm. [Details](docs/user/timers-and-alarms.md)
- **Moves and moods.** It reacts when you pick it up, shake it or pet its head. It breathes, looks around and sleeps when you ask. [Details](docs/user/moves-and-moods.md)
- **Camera (opt-in).** Snapshots, "what is this", face follow, "take my picture" and a local name list. Frames stay on the host. [Details](docs/user/camera.md)
- **Games and a pet mood.** A colour-memory game, an action game, and a mood that depends on how you care for it. [Details](docs/user/games-and-pet.md)
- **Coding companion.** The face and ring show what your coding agent is doing. A build light turns green or red. [Details](docs/user/coding-companion.md)
- **Home tools (off by default).** A local API, an event stream, MQTT, a home-automation bridge and metrics. [Details](docs/user/home-tools.md)
- **Two languages.** English and Spanish, chosen at run time with no reflash. [Details](docs/user/languages.md)
- **Updates you control.** Checking is on, installing is off until you turn it on. Images are signed, and a failed update rolls back. [Details](docs/user/updates.md)

## Two ways to run it

- **Standalone (default).** The host program uses a language model you run yourself, reached over a chat-completions style web address.
  Speech to text and text to speech use the addresses you set, or a built-in local engine when you leave them blank.
- **With MaiPai Home (optional).** MaiPai Home can act as the robot's brain and add household memory, people and policy.
  It is one optional brain. The robot is complete without it, and you never need to install anything else to run this repo.
  [Details](docs/user/with-maipai-home.md)

Switching is one line in `robot.toml`. The robot is not reflashed.

## Install

1. Install the host: `pipx install git+https://github.com/getmaipai/stackchan`. No Docker.
2. Put the firmware on the robot with the web flasher over USB, or build it with `stackchan firmware build`.
3. Run `stackchan pair`, then type the 6 digit code the robot shows.
4. Set `llm_url` in `robot.toml`, run `stackchan check`, then say the wake word.
5. Optional: `stackchan install-service` starts the host when the computer starts. Nothing runs as a silent service.

Full steps: [Getting started](docs/user/getting-started.md). Windows service support is not in v1.

> **Screenshot placeholder:** `pairing-code.png`. The robot screen showing a 6 digit pairing code.

## Safety note

In standalone mode this repo adds no content filter of its own. Content safety is the job of the language model you connect and
your persona prompt. The family-friendly persona is a prompt, not a guarantee.

## Docs

- Users: [Getting started](docs/user/getting-started.md), [Features](docs/user/features.md), [Settings](docs/user/settings.md),
  [Languages](docs/user/languages.md), [Privacy](docs/user/privacy.md), [Troubleshooting](docs/user/troubleshooting.md).
- Developers: `docs/dev/` (build from source, host and brains, contributing).
- Writing rules: `docs/STYLE.md`. Design record: `docs/design/`.

## License

AGPL-3.0. See `LICENSE`, `NOTICE` and `THIRD-PARTY.md`.

## Contributing

Read `docs/dev/contributing.md` first. Run `bash scripts/check.sh` before you send a change.
