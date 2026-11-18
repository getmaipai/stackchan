# MaiPai for StackChan

### Faster, steadier, private and portable firmware for your StackChan desk robot. Your own LLM or MaiPai Home, on any network.

[Documentation](docs/user/features.md) · [Getting started](docs/user/getting-started.md) · [Which setup?](docs/user/which-setup.md) · [Compare](docs/user/compare.md) · [Questions](docs/user/faq.md) · [Troubleshooting](docs/user/troubleshooting.md)

> **Draft.** These docs are written as if v1.0.0 is finished, so the owner can review the full product. Remove this note when v1.0.0 ships.
>
> **Some pictures are placeholders.** Pictures named `unit-` are real screenshots from the flashed robot. The other drawings (47 of them) are placeholders and will be replaced before release.

MaiPai for StackChan is open-source firmware and a host program for the [StackChan](https://github.com/m5stack/StackChan) desk robot. It replaces the factory firmware with something quicker, steadier and yours.

![The robot on a desk showing the big-eyes face, with the settings page open on a laptop beside it.](docs/images/hero.svg)

## Why you would want it

**Fast and steady.** Wake cue in under 150 ms. "Stop" and touch commands in under 300 ms. Replies start on the first finished sentence, so you do not wait for the whole answer. The robot also stays calm and keeps running: a restart guard, a signed update that rolls itself back if the new version fails, and fewer false wake-ups from fan noise. [Voice](docs/user/voice.md), [updates](docs/user/updates.md).

**Private by design.** What you say stays in your home. AI on your own computer answers, with no cloud service, no vendor account and no telemetry, and the host calls only the addresses you list in one settings file. Mute, camera off and full quiet take one tap, and [nothing is ever monitored in secret](docs/user/no-stealth.md). [Privacy](docs/user/privacy.md), [security](docs/user/security.md).

**New things it can do.** Five faces and your own pictures as a face, 26 screen effects, swipe pages and a control sheet, games with saved best scores, voice timers and alarms that work with no model, dances to your music, six languages, remote controls and a camera you switch on yourself, with a cue that cannot be hidden. [Everything it does](docs/user/features.md).

**Take it with you.** Away from home the robot joins your private network by itself and reaches your host from any Wi-Fi: a friend's house, a hotel, the office. Setup takes a phone and a setup code on the robot's screen. [Use it away from home](docs/user/use-it-anywhere.md).

**Go further with MaiPai Home** (free, open source). Connect the robot to [MaiPai Home](docs/user/with-maipai-home.md) for memories, companions and personalities, cloned voices, recognizing people, naming songs, live lookups, watching and monitoring, find and remote control, and rules for children and teens. [See how it compares](docs/user/compare.md) with the factory firmware, and with MaiPai Home, side by side.

## Get started

You need a StackChan robot ([store page](https://shop.m5stack.com/products/stackchan-kawaii-co-created-open-source-ai-desktop-robot)), a USB cable, and a Mac, Linux machine or Raspberry Pi 5 for the host.

### With your own LLM

```
pipx install "git+https://github.com/getmaipai/stackchan#subdirectory=host"
```

Flash the robot from the web flasher (the build is trimmed: Bluetooth is off and the factory cloud links are removed), run `stackchan run`, then `stackchan pair`, set `url` under `[llm]` in `robot.toml` to your local LLM, and say the wake word. How fast and how well it answers depends on your model and hardware: [Pick hardware and a model](docs/user/hardware-and-models.md). It takes about 20 minutes: [Getting started](docs/user/getting-started.md).

### With MaiPai Home

[MaiPai Home](docs/user/with-maipai-home.md) adds the full feature set: memories, companions and personalities, cloned voices, recognizing people, naming songs, live lookups across rooms and household rules.
Set `brain = "home"` and run `stackchan check`.


With your own LLM we add no content filter. The model you connect decides what the robot says.

## Status

MaiPai for StackChan is pre-1.0, so expect rough edges. Tell us what you find on the Issues tab.

Sound, screen looks, the smoother eyes and your own picture faces, head petting, the setup page, the reset screen and a signed update with a real key and travel over your private network are built but not yet checked on a robot. The new face extras, word reactions, time zone, network test and version screens have not been seen on a robot screen, no one has played the games by touch, no one has heard the offline phrases or seen the dances, the six languages are not native-reviewed, and a per-person wake phrase is stored but not matched yet.

### Known gaps

- After the wake word, one owner reported hearing no reply. The robot's audio reaches the host loud, but the speech engine returned no words. This is open and we are looking at it.
- A real wake by voice and how finger swipes feel have not been tested by a person.
- The eye animation runs at 28 to 33 frames a second with some gaps over 50 ms.
- The robot's screen shows no accented letters.
- A face style changed on the robot shows on the host only after the settings page reloads.
- Quick settings shows 3 saved Wi-Fi networks.
- Planned, not built: brighter dim level, new games, scenes and data cards, Wi-Fi roaming.

## Get help

- Start with [Troubleshooting](docs/user/troubleshooting.md), and run `stackchan check`.
- Report bugs and request features on the Issues tab.
- The robot itself: [official project](https://github.com/m5stack/StackChan), [official docs](https://docs.m5stack.com/en/StackChan).

MaiPai for StackChan is a hobby project. We read everything (eventually), but may be slow and can't promise to build it. Please don't take silence personally.

## Support the project

MaiPai for StackChan is free and open source. If it helps you, [sponsoring on GitHub](https://github.com/sponsors/JesseWebDotCom) pays for test hardware, such as more robots, a computer for bigger models and a phone for travel tests. We test on that hardware ourselves and publish what we measure.

## What is in this repository

Source code, patches to the StackChan firmware and a build recipe. No model or library binaries are stored here. The build downloads Espressif's speech library, which provides the wake word "Hi, Stack Chan", the English stop word and the audio front end, under its own license. [THIRD-PARTY.md](THIRD-PARTY.md) and `NOTICE` list every download and license. Ready-made images on GitHub Releases may come later.

## Development

Start with [the developer overview](docs/dev/overview.md), read `docs/dev/contributing.md`, then run `bash scripts/check.sh` before you send a change. Build from source and the host design are under `docs/dev/`.

## Disclaimer

MaiPai is open-source software for personal, self-hosted, non-commercial use by you and your household; it is not affiliated with, endorsed by, or sponsored by any platform it can connect to; all product names and trademarks belong to their respective owners; you are responsible for complying with the terms and laws that apply to you and the services you access. StackChan is M5Stack's robot, and this project is not made or endorsed by M5Stack.

The language models are third-party and chosen by you. Their outputs can be wrong, offensive or harmful, and are not medical, legal or professional advice. You are responsible for how you use them, and parents decide what children can reach.

AGPL-3.0. See `LICENSE`, `NOTICE` and `THIRD-PARTY.md`.
