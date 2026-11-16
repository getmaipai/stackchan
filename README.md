# MaiPai for StackChan

### StackChan firmware, rewritten: private, secure, faster, more abilities. Your own LLM or MaiPai Home, on any network.

[Documentation](docs/user/features.md) · [Getting started](docs/user/getting-started.md) · [Which setup?](docs/user/which-setup.md) · [Compare](docs/user/compare.md) · [Questions](docs/user/faq.md) · [Troubleshooting](docs/user/troubleshooting.md)

> **Draft.** These docs are written as if v1.0.0 is finished, so the owner can review the full product. Remove this note when v1.0.0 ships.

MaiPai for StackChan is open-source firmware and a host program for the [StackChan](https://github.com/m5stack/StackChan) desk robot.
What you say to it stays in your home. AI on your own computer answers, with no cloud service, no vendor account and no telemetry, and the host calls only the addresses you list in one settings file.

It is faster and smoother than the factory firmware, and it works away from home, over your private network. It adds timers, a camera that can name the people you enrol, a coding companion and a local API.

Connect it to [MaiPai Home](docs/user/with-maipai-home.md) (free, open source) for the full feature set: memory across days, recognising people, naming songs, the camera, watching and monitoring, find and remote control, and more.

[See how it compares](docs/user/compare.md) with the factory firmware, and with MaiPai Home, side by side.

![The robot on a desk showing the big-eyes face, with the settings page open on a laptop beside it.](docs/images/hero.svg)

## What it does

MaiPai for StackChan is one thing: a private voice robot. It does a small set of things well, and everything bigger runs with MaiPai Home.

**The robot, with your own LLM**

- **[Voice](docs/user/voice.md):** Say the wake word and talk. Follow-up questions need no wake word, you can interrupt, ten voice commands work with no model involved, and you can set the speech speed and pitch.
- **[Faces and clock](docs/user/face-and-look.md):** Two face styles, any colour or none, time-of-day and clock faces, night mode and optional captions.
- **[Timers and alarms](docs/user/timers-and-alarms.md):** A ring that empties as time runs out, named timers, snooze and quiet hours.
- **[Reactions](docs/user/moves-and-moods.md):** Pickup, shake, tilt and petting, a breathing idle, tap-the-face mute, a mood that grows with care, an hourly chime and low-battery steps.
- **[Privacy controls](docs/user/mute-and-camera-off.md):** Mute, camera off and full quiet, one tap each. [Nothing is ever monitored in secret](docs/user/no-stealth.md).
- **[Away from home](docs/user/use-it-anywhere.md):** Reach your host from any Wi-Fi: the robot joins your private network by itself when it cannot reach your host.
- **[Security](docs/user/security.md), [updates](docs/user/updates.md), [lights and sounds](docs/user/lights-and-sounds.md) and [languages](docs/user/languages.md):** Pairing with a code, a Wi-Fi setup page with an on-screen code, a reset on the robot, signed updates with rollback, soft tones and one light colour per meaning, English and Spanish.

**More, with [MaiPai Home](docs/user/with-maipai-home.md)** (free, open source)

- **Seeing:** [snapshots, face follow, a name list and "what is this"](docs/user/camera.md).
- **Security:** [motion and sound alerts and an alarm](docs/user/watch-and-alerts.md), and a [baby and pet monitor](docs/user/baby-and-pet-monitor.md).
- **Find and control:** [find my robot, remote beep, lights, talk, pan and tilt, and live view](docs/user/find-and-remote.md).
- **Play and build:** [games and a pet mood](docs/user/games-and-pet.md), a [coding companion](docs/user/coding-companion.md), and [home tools](docs/user/home-tools.md) such as a local API and MQTT.
- **The household:** memory across days, people, calendars, announcements, naming songs, and rules for children and teens.

Wake cue in under 150 ms. "Stop" and touch commands in under 300 ms. Replies start on the first finished sentence.

## Get started

You need a StackChan robot ([store page](https://shop.m5stack.com/products/stackchan-kawaii-co-created-open-source-ai-desktop-robot)), a USB cable, and a Mac, Linux machine or Raspberry Pi 5 for the host.

### With your own LLM

```
pipx install git+https://github.com/getmaipai/stackchan
```

Flash the robot from the web flasher (the build is trimmed: Bluetooth is off and the factory cloud links are removed), run `stackchan pair`, point `llm_url` at your local LLM, and say the wake word. How fast and how well it answers depends on your model and hardware: [Pick hardware and a model](docs/user/hardware-and-models.md). It takes about 20 minutes: [Getting started](docs/user/getting-started.md).

### With MaiPai Home

[MaiPai Home](docs/user/with-maipai-home.md) adds the full feature set: memory across days, recognising people, naming songs, the camera, watching and monitoring, and household rules.
Set `brain = "home"` and run `stackchan check`.


With your own LLM we add no content filter. The model you connect decides what the robot says.

## Status

MaiPai for StackChan is pre-1.0, so expect rough edges. Tell us what you find on the Issues tab.

Sound, screen looks, head petting, the setup page, the reset screen and a signed update with a real key and travel over your private network are built but not yet checked on a robot.

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
