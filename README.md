# MaiPai for StackChan

### StackChan firmware, rewritten: private, faster, more abilities using your own local LLM or MaiPai Home, over Tailscale.

[Documentation](docs/user/features.md) · [Getting started](docs/user/getting-started.md) · [Compare](docs/user/compare.md) · [Troubleshooting](docs/user/troubleshooting.md)

> **Draft.** These docs are written as if v1.0.0 is finished, so the owner can review the full product. Remove this note when v1.0.0 ships.

MaiPai for StackChan is open-source firmware and a host program for the [StackChan](https://github.com/m5stack/StackChan) desk robot. You talk to the robot,
and it answers with AI that runs on your own computer or on your MaiPai Home hub. It is faster and smoother than the factory firmware and more capable: it adds timers, a camera that can name the people you enrol, games, a coding companion and a local API, and it works from any Wi-Fi over Tailscale.

Your voice stays in your home. The robot talks only to your host or your hub, and the host calls only the addresses you list in one settings file.
There is no vendor account, no telemetry and no cloud service.

[See how it compares](docs/user/compare.md) with the factory firmware, and standalone with MaiPai Home, side by side.

![The robot on a desk showing the big-eyes face, with the settings page open on a laptop beside it.](docs/images/hero.svg)

## What it does

- **[Voice](docs/user/voice.md):** Say the wake word and talk. Follow-up questions need no wake word, you can interrupt, and ten voice commands work with no model involved.
- **[Faces and clock](docs/user/face-and-look.md):** Two face styles, any colour or none, a clock face, night mode and optional captions.
- **[Timers and alarms](docs/user/timers-and-alarms.md):** A ring that empties as time runs out, named timers, snooze and quiet hours.
- **[Reactions](docs/user/moves-and-moods.md):** Pickup, shake, tilt and petting, a breathing idle, privacy sleep and low-battery steps.
- **[Camera](docs/user/camera.md):** Off until you turn it on. Snapshots, "what is this", face follow and a local name list. Frames stay on your host.
- **[Games and a pet mood](docs/user/games-and-pet.md):** Colour memory, an action game, and a mood that depends on how you care for the robot.
- **[Coding companion](docs/user/coding-companion.md):** A green or red build light and your agent's status on the face.
- **[Home tools](docs/user/home-tools.md):** A local API, an event stream, MQTT and metrics, all off by default.
- **[Anywhere](docs/user/use-it-anywhere.md):** Join your Tailscale network and reach your host from any Wi-Fi over an encrypted link.
- **[Languages](docs/user/languages.md):** English and Spanish, switched at run time with no reflash.
- **[Updates](docs/user/updates.md):** Signed images, a health check after install and automatic rollback. Nothing installs unless you say so.

Wake cue in under 150 ms. "Stop" and touch commands in under 300 ms. Replies start on the first finished sentence.

## Get started

You need a StackChan robot ([store page](https://shop.m5stack.com/products/stackchan-kawaii-co-created-open-source-ai-desktop-robot)), a USB cable, and a Mac, Linux machine or Raspberry Pi 5 for the host.

### Standalone

```
pipx install git+https://github.com/getmaipai/stackchan
```

Flash the robot from the web flasher, run `stackchan pair`, point `llm_url` at your local LLM, and say the wake word. It takes about 20 minutes: [Getting started](docs/user/getting-started.md).

### With MaiPai Home

[MaiPai Home](docs/user/with-maipai-home.md) keeps its speech and chat models loaded on one machine built for them, so the first word arrives sooner, and it adds memory across days, people, calendars and household rules.
Set `brain = "home"` and run `stackchan check`.

### Anywhere with Tailscale

Paste a Tailscale key on the Network page and the robot reaches your host or hub from any Wi-Fi: [Use the robot anywhere](docs/user/use-it-anywhere.md).

In standalone mode we add no content filter. The model you connect decides what the robot says.

## Status

MaiPai for StackChan is pre-1.0, so expect rough edges. Tell us what you find on the Issues tab.

## Get help

- Start with [Troubleshooting](docs/user/troubleshooting.md), and run `stackchan check`.
- Report bugs and request features on the Issues tab.
- The robot itself: [official project](https://github.com/m5stack/StackChan), [official docs](https://docs.m5stack.com/en/StackChan).

MaiPai for StackChan is a hobby project. We read everything (eventually), but may be slow and can't promise to build it. Please don't take silence personally.

## Development

Read `docs/dev/contributing.md`, then run `bash scripts/check.sh` before you send a change. Build from source and the host design are under `docs/dev/`.

## Disclaimer

MaiPai is open-source software for personal, self-hosted, non-commercial use by you and your household; it is not affiliated with, endorsed by, or sponsored by any platform it can connect to; all product names and trademarks belong to their respective owners; you are responsible for complying with the terms and laws that apply to you and the services you access. StackChan is M5Stack's robot, and this project is not made or endorsed by M5Stack.

The language models are third-party and chosen by you. Their outputs can be wrong, offensive or harmful, and are not medical, legal or professional advice. You are responsible for how you use them, and parents decide what children can reach.

AGPL-3.0. See `LICENSE`, `NOTICE` and `THIRD-PARTY.md`.
