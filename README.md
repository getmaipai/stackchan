# MaiPai for StackChan

### StackChan firmware, rewritten: private, faster, more abilities using your own local LLM or MaiPai Home, over Tailscale.

[Documentation](docs/user/features.md) · [Getting started](docs/user/getting-started.md) · [Troubleshooting](docs/user/troubleshooting.md)

> **Draft.** These docs are written as if v1.0.0 is finished, so the owner can review the full product. Remove this note when v1.0.0 ships.

![The robot on a desk showing the big-eyes face, with the settings page open on a laptop beside it.](docs/images/hero.svg)

MaiPai for StackChan replaces the firmware on your [StackChan](https://github.com/m5stack/StackChan) desk robot and adds a small host program.
You talk to the robot, and it answers with AI that runs on your own computer or on your MaiPai Home hub.

Your voice stays in your home. The robot talks only to your host or your hub, and the host calls only the addresses you list in one settings file.
There is no vendor account, no telemetry and no cloud service.

## What you get

- **Fast.** The wake cue plays in under 150 ms, and "stop" and touch commands act in under 300 ms with no model involved. Replies start on the first finished sentence.
- **Your own brain.** Use any local LLM you run, or MaiPai Home. Switching is one line.
- **Anywhere.** The robot joins your Tailscale network and reaches your host from any Wi-Fi, over an encrypted link.
- **Faces and clock.** Two face styles, any colour or none, a clock face, night mode and optional captions.
- **Voice.** Wake word, follow-up questions without it, interrupting, voice commands, personas.
- **Timers and alarms.** A ring that empties as time runs out, snooze, quiet hours.
- **Reactions.** Pickup, shake, tilt and petting, breathing idle, privacy sleep, low-battery steps.
- **Camera.** Off until you turn it on. Snapshots, "what is this", face follow, a local name list. Frames stay on your host.
- **Games and a pet mood.** Colour memory, an action game, and a mood that depends on care.
- **Coding companion.** A green or red build light and agent status on the face.
- **Home tools.** A local API, MQTT and metrics, all off by default.
- **English and Spanish.** Switch at run time, no reflash.
- **Safe updates.** Signed images, a health check after install, automatic rollback. Nothing installs unless you say so.

Each feature has its own page in the [documentation](docs/user/features.md).

## Run it with MaiPai Home

On its own, the host uses a local LLM you run, and the robot is complete. With [MaiPai Home](docs/user/with-maipai-home.md), set `brain = "home"` and the robot also gets:

- **Faster answers.** Home keeps its speech and chat models loaded on one machine built for them, so the first word arrives sooner. It can run bigger models than a small always-on host. A 4B class model answers in under 400 ms warm. A 27B class model on a weak host does not.
- **Memory.** It remembers across days and knows each person by voice and name.
- **The household.** Calendars, briefings, announcements, and rules for children and teens.

## Getting started

You need a StackChan robot, a USB cable, and a Mac, Linux machine or Raspberry Pi 5 for the host.

```
pipx install git+https://github.com/getmaipai/stackchan
```

Then flash the robot from the web flasher, run `stackchan pair`, and say the wake word. The full steps take about 20 minutes: [Getting started](docs/user/getting-started.md).

In standalone mode we add no content filter. The model you connect decides what the robot says.

## Status

MaiPai for StackChan is pre-1.0, so expect rough edges. Tell us what you find on the Issues tab.

## Documentation

- Users: [Getting started](docs/user/getting-started.md), [Features](docs/user/features.md), [Settings](docs/user/settings.md), [Privacy](docs/user/privacy.md), [Troubleshooting](docs/user/troubleshooting.md).
- Developers: build from source, host and brains, contributing, all under `docs/dev/`.
- The robot itself: [official project](https://github.com/m5stack/StackChan), [official docs](https://docs.m5stack.com/en/StackChan), [store page](https://shop.m5stack.com/products/stackchan-kawaii-co-created-open-source-ai-desktop-robot).

MaiPai for StackChan is a hobby project. I read everything (eventually), but I may be slow and can't promise to build it. Please don't take silence personally.

## Development

Read `docs/dev/contributing.md`, then run `bash scripts/check.sh` before you send a change.

## Disclaimer

MaiPai is open-source software for personal, self-hosted, non-commercial use by you and your household; it is not affiliated with, endorsed by, or sponsored by any platform it can connect to; all product names and trademarks belong to their respective owners; you are responsible for complying with the terms and laws that apply to you and the services you access. StackChan is M5Stack's robot, and this project is not made or endorsed by M5Stack.

The language models are third-party and chosen by you. Their outputs can be wrong, offensive or harmful, and are not medical, legal or professional advice. You are responsible for how you use them, and parents decide what children can reach.

AGPL-3.0. See `LICENSE`, `NOTICE` and `THIRD-PARTY.md`.
