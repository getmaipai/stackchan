# Public README draft (2026-11-18)

Status: draft for the owner. It follows the org README skeleton (`getmaipai/.github/docs/STYLE.md`). The org line is verbatim from `brand/COPY.md`; that file has no StackChan entry yet, so the product line below is a proposal to add there first, and the logos come from `brand/` (never redrawn). Screenshots are drawn by the robot's own screen code on a computer (the `vu-` pictures), not photos of a robot. Remove this block when the README replaces `README.md`.

Proposed `brand/COPY.md` entry, to add before this README ships:

> **stackchan (MaiPai for StackChan):**
> Private firmware and a host program for the StackChan desk robot: it talks, shows faces, keeps time and plays games with your own model on your own computer, and works with MaiPai Home when you have it.

---

<!-- README starts here -->

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/getmaipai/.github/main/brand/maipai-stackchan-logo-dark.png">
    <img alt="MaiPai for StackChan" src="https://raw.githubusercontent.com/getmaipai/.github/main/brand/maipai-stackchan-logo-light.png" width="360">
  </picture>
</p>

### A private voice for your StackChan desk robot, with your own model or MaiPai Home.

[Documentation](docs/user/features.md) · [Get started](docs/user/getting-started.md) · [Releases](https://github.com/getmaipai/stackchan/releases) · [Questions](docs/user/faq.md)

Private, local AI for your family, on your own hardware, never the cloud.

MaiPai for StackChan is firmware and a small host program for the [StackChan](https://github.com/m5stack/StackChan) desk robot. What you say goes to a computer in your home and nowhere else: no cloud service, no account, no telemetry. The robot calls only the addresses you list in one settings file.

![The robot's face, drawn by its own screen code.](docs/images/vu-clock.png)

## What it does

- **Talk.** Say the wake word and ask. The reply starts on the first finished sentence.
- **Faces.** Several faces, your own pictures as a face, screen effects, a clock face.
- **Timers and alarms.** Set them by voice. They work with no model running.
- **Privacy switches.** Mute, camera off and full quiet are three taps on the face, and the screen shows each state.
- **Passcode lock.** A code you set, an auto-lock time and a big keypad.
- **Games and dances.** Games with saved best scores, and dances to your music.
- **Six languages.** English, Spanish, French, German, Portuguese and Italian.
- **Updates you choose.** Signed updates that you install when you want, and a rollback if a new version does not start.
- **Parent view.** A plain page that says what the robot is doing.

![The robot's control sheet with volume, brightness and the quick switches.](docs/images/vu-control-sheet.png)

## Get started

You need a StackChan, a USB cable, and a Mac, a Linux machine or a Raspberry Pi 5 for the host.

```
pipx install "git+https://github.com/getmaipai/stackchan#subdirectory=host"
```

Flash the robot from the web flasher, run `stackchan run`, then `stackchan pair` and type the six digits on the robot. The full steps take about 20 minutes: [Get started](docs/user/getting-started.md). Before you flash, read [Switch from the factory firmware, or go back](docs/user/switch-from-the-factory-firmware.md); going back is supported.

> **Back up first.** Flashing replaces the factory firmware. Do not force the head or arms by hand.

## With MaiPai Home

Your own private AI at home, with chat, voice, pictures and videos, on your own hardware - for protection, privacy, and independence.

Connect the robot to [MaiPai Home](docs/user/with-maipai-home.md) (free, open source) for memories, recognizing people, household rules and child and teen protections. Set `brain = "home"` and run `stackchan check`. Without Home, the model you connect decides what the robot says, and we add no content filter.

## Status

Pre-1.0. We run it daily and it has rough edges. Some things are built and not yet tried on a real robot with a real person; the [readiness page](docs/plan/release-readiness.md) lists each one. Tell us what you find on the Issues tab.

## Documentation

- [What the robot can do](docs/user/features.md), [settings](docs/user/settings.md), [troubleshooting](docs/user/troubleshooting.md)
- [For developers](docs/dev/overview.md)
- Found a problem? Open an issue.

## Development

Start with [the developer overview](docs/dev/overview.md), then run `bash scripts/check.sh` before you send a change. `bash scripts/test-all.sh` runs the whole suite in about four minutes.

## Disclaimer

MaiPai is open-source software for personal, self-hosted, non-commercial use by you and your household; it is not affiliated with, endorsed by, or sponsored by any platform it can connect to; all product names and trademarks belong to their respective owners; you are responsible for complying with the terms and laws that apply to you and the services you access. StackChan is M5Stack's robot, and this project is not made or endorsed by M5Stack.

The language models are third-party and chosen by you. Their outputs can be wrong, offensive or harmful, and are not medical, legal or professional advice. You are responsible for how you use them, and parents decide what children can reach.

AGPL-3.0. See `LICENSE`, `NOTICE` and `THIRD-PARTY.md`.

<!-- README ends here -->

## Notes for the owner (not part of the README)

- Two pictures, as the skeleton allows. Both are `vu-` pictures from the virtual robot; the real flashed photos (`unit-` pictures) are better once the robot has been seen by a person with the final firmware.
- The release link and the web flasher need a published release and a release key. Until then the Get started step says "flash the robot from the web flasher", which does not exist publicly yet.
- "Several faces" replaces the exact count on purpose; the feature page holds the numbers.
- Claims left out because nobody has checked them on a robot with a person: the wake cue speed figures, face following, the encrypted link in travel.
