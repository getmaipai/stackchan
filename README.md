# MaiPai for StackChan

### StackChan firmware, rewritten: private, secure, faster, more abilities. Your own LLM or MaiPai Home, on any network.

[Documentation](docs/user/features.md) · [Getting started](docs/user/getting-started.md) · [Which setup?](docs/user/which-setup.md) · [Compare](docs/user/compare.md) · [Questions](docs/user/faq.md) · [Troubleshooting](docs/user/troubleshooting.md)

> **Draft.** These docs are written as if v1.0.0 is finished, so the owner can review the full product. Remove this note when v1.0.0 ships.

MaiPai for StackChan is open-source firmware and a host program for the [StackChan](https://github.com/m5stack/StackChan) desk robot.
What you say to it stays in your home. AI on your own computer answers, with no cloud service, no vendor account and no telemetry, and the host calls only the addresses you list in one settings file.

It is faster and smoother than the factory firmware, and it adds timers, a camera that can name the people you enrol, games, a coding companion and a local API. Take it on the go: it joins your phone's hotspot and reaches your host over Tailscale, so it works at a friend's house, a hotel or the office.

Connect it to [MaiPai Home](docs/user/with-maipai-home.md) (free, open source) for more: faster answers from bigger models, memory across days, people, calendars and household rules.

[See how it compares](docs/user/compare.md) with the factory firmware, and with MaiPai Home, side by side.

![The robot on a desk showing the big-eyes face, with the settings page open on a laptop beside it.](docs/images/hero.svg)

## What it does

- **[Voice](docs/user/voice.md):** Say the wake word and talk. Follow-up questions need no wake word, you can interrupt, and ten voice commands work with no model involved.
- **[Faces and clock](docs/user/face-and-look.md):** Two face styles, any colour or none, a clock face, night mode and optional captions.
- **[Timers and alarms](docs/user/timers-and-alarms.md):** A ring that empties as time runs out, named timers, snooze and quiet hours.
- **[Reactions](docs/user/moves-and-moods.md):** Pickup, shake, tilt and petting, a breathing idle, tap-the-face mute and privacy sleep, and low-battery steps.
- **[Baby and pet monitor](docs/user/baby-and-pet-monitor.md):** Hear and see a nursery from your phone and get alerts, started on the robot, with a clear sign on its screen. Planned.
- **[No stealth](docs/user/no-stealth.md):** Every listening, looking or watching mode shows on the robot's screen.
- **[Watch and alerts](docs/user/watch-and-alerts.md):** Notices motion and loud sounds, alerts you with a snapshot, and can flash red and blue with a siren. Planned.
- **[Music and dance](docs/user/music-and-dance.md):** It hears music and dances to the beat, dances on request, and with MaiPai Home names the song.
- **[Camera](docs/user/camera.md):** Off until you turn it on. Snapshots, face follow and a local name list, and "what is this" with MaiPai Home. Frames stay on your host.
- **[Games and a pet mood](docs/user/games-and-pet.md):** Colour memory, an action game, and a mood that depends on how you care for the robot.
- **[Coding companion](docs/user/coding-companion.md):** A green or red build light and your agent's status on the face.
- **[Home tools](docs/user/home-tools.md):** A local API, an event stream, MQTT and metrics, all off by default.
- **[On the go](docs/user/use-it-anywhere.md):** Join your phone's hotspot or any Wi-Fi, and reach your host or hub over Tailscale on an encrypted link.
- **[Security](docs/user/security.md):** Pairing with a code, revocable tokens, signed updates, and an encrypted link over Tailscale.
- **[Lights and sounds](docs/user/lights-and-sounds.md):** One light colour per meaning, and soft tones that rise for good news and fall for bad.
- **[Languages](docs/user/languages.md):** English and Spanish, switched at run time with no reflash.
- **[Updates](docs/user/updates.md):** Signed images, a health check after install and automatic rollback. Nothing installs unless you say so.

Wake cue in under 150 ms. "Stop" and touch commands in under 300 ms. Replies start on the first finished sentence.

## Get started

You need a StackChan robot ([store page](https://shop.m5stack.com/products/stackchan-kawaii-co-created-open-source-ai-desktop-robot)), a USB cable, and a Mac, Linux machine or Raspberry Pi 5 for the host.

### With your own LLM

```
pipx install git+https://github.com/getmaipai/stackchan
```

Flash the robot from the web flasher, run `stackchan pair`, point `llm_url` at your local LLM, and say the wake word. How fast and how well it answers depends on your model and hardware: [Pick hardware and a model](docs/user/hardware-and-models.md). It takes about 20 minutes: [Getting started](docs/user/getting-started.md).

### With MaiPai Home

[MaiPai Home](docs/user/with-maipai-home.md) keeps its speech and chat models loaded on one machine built for them, so the first word arrives sooner, and it adds memory across days, people, calendars and household rules.
Set `brain = "home"` and run `stackchan check`.

### On the go with Tailscale

Paste a Tailscale key on the Network page and add your phone's hotspot as a saved Wi-Fi. The robot reaches your host or hub from anywhere: [Use the robot anywhere](docs/user/use-it-anywhere.md).

With your own LLM we add no content filter. The model you connect decides what the robot says.

## Status

MaiPai for StackChan is pre-1.0, so expect rough edges. Tell us what you find on the Issues tab.

## Get help

- Start with [Troubleshooting](docs/user/troubleshooting.md), and run `stackchan check`.
- Report bugs and request features on the Issues tab.
- The robot itself: [official project](https://github.com/m5stack/StackChan), [official docs](https://docs.m5stack.com/en/StackChan).

MaiPai for StackChan is a hobby project. We read everything (eventually), but may be slow and can't promise to build it. Please don't take silence personally.

## Support the project

MaiPai for StackChan is free and open source. If it helps you, [sponsoring on GitHub](https://github.com/sponsors/JesseWebDotCom) pays for test hardware, such as more robots, a computer for bigger models and a phone for travel tests. We test on that hardware ourselves and publish what we measure.

## Development

Start with [the developer overview](docs/dev/overview.md), read `docs/dev/contributing.md`, then run `bash scripts/check.sh` before you send a change. Build from source and the host design are under `docs/dev/`.

## Disclaimer

MaiPai is open-source software for personal, self-hosted, non-commercial use by you and your household; it is not affiliated with, endorsed by, or sponsored by any platform it can connect to; all product names and trademarks belong to their respective owners; you are responsible for complying with the terms and laws that apply to you and the services you access. StackChan is M5Stack's robot, and this project is not made or endorsed by M5Stack.

The language models are third-party and chosen by you. Their outputs can be wrong, offensive or harmful, and are not medical, legal or professional advice. You are responsible for how you use them, and parents decide what children can reach.

AGPL-3.0. See `LICENSE`, `NOTICE` and `THIRD-PARTY.md`.
