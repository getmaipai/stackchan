# MaiPai StackChan

Firmware and a host program for the StackChan desktop robot. The robot talks, shows a face, sets timers and keeps you company,
using AI models that run in your own home.

## The promise

Private, local AI that is yours. Nothing leaves your home. The robot talks only to the host program and the Wi-Fi you gave it.
The host calls only the addresses you put in its settings file. There is no telemetry, no vendor account and no cloud.

## Status

Today only a repo skeleton exists: design notes in `docs/design/`, hygiene scripts, and empty `firmware/`, `host/` and `schema/`
folders. Nothing below is built yet. Every feature on this page is planned. These docs are a first draft for the owner to review.

## Two ways to run it

- **Standalone (planned, default).** The host program uses a language model you run yourself, reached over a chat-completions
  style web address. Speech to text and text to speech use the addresses you set, or a built-in local engine when you leave them blank.
- **With MaiPai Home (planned, optional).** MaiPai Home can act as the robot's brain and add household memory, people and policy.
  It is one optional brain. The robot is complete without it, and you never need to install anything else to run this repo.

Switching is one line in `robot.toml`. The robot is not reflashed.

## Planned highlights

- Faces as data: face style and colour are settings, and colour can be none. Captions are optional and off by default.
- Clock face, night mode, a thinking cue (animated dots and a quiet tone) and a quick-slider overlay.
- Wake word, voice commands (stop, mute, quiet, don't move), timers and alarms, and personas.
- Pickup, shake, tilt and petting reactions, privacy sleep, quiet mode and a low-battery ladder.
- Camera features, opt-in: snapshots, "what is this", face follow and a local name list. Frames stay on the host.
- Touch games, a mood that depends on care, and a coding companion with build lights.
- A local API, an event stream, MQTT and a metrics endpoint, all off by default.
- English and Spanish, chosen at run time with no reflash.
- An optional updater: checking is on, installing is off until you turn it on. Images are signed, and a failed update rolls back.

## Roadmap

The build runs in ordered steps: schema and a simulated unit, host and pairing, the first full local turn, flasher and settings,
faces, always-on behaviours, integrations, host features, then games. Firmware first moves to a newer base (see
`docs/dev/build-from-source.md`). There is one first release, v1.0.0, with everything in scope. No tags come before it.
Detail: `docs/design/`.

## Planned install

1. Install the host: `pipx install git+https://github.com/getmaipai/stackchan`. No Docker. A package index listing comes later.
2. Run `stackchan pair`, then type the 6 digit code the robot shows.
3. Get the firmware from a web flasher over USB, or build it from source with `stackchan firmware build`.
4. Autostart is opt-in: `stackchan install-service`. Nothing runs as a silent service.

Windows service support is not in v1.

## Safety note

In standalone mode this repo adds no content filter of its own. Content safety is the job of the language model you connect and
your persona prompt. An optional family-friendly persona may ship, labelled as a prompt and not a guarantee.

## Docs

- Users: `docs/user/` (getting started, features, settings, languages, troubleshooting, privacy).
- Developers: `docs/dev/` (build from source, host and brains, contributing).
- Writing rules: `docs/STYLE.md`. Design record: `docs/design/`.

## License

AGPL-3.0. See `LICENSE`, `NOTICE` and `THIRD-PARTY.md`.

## Contributing

Read `docs/dev/contributing.md` first. Run `bash scripts/check.sh` before you send a change.
