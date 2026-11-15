# Host and brains

Status: design. Nothing here is built.

## Three layers

1. **Unit (firmware).** Face, touch, IMU, servos, camera capture, mics, speaker, wake word, clock, timer ring, settings, Wi-Fi and pairing.
   It speaks one protocol to one host. Its hello reports `contract_version`, firmware version, face packs, sensors and capabilities.
   It has roughly 76 KB of free internal RAM (estimate), so it never talks to a language model.
2. **Host (`stackchan`).** Protocol server, pairing, mDNS discovery (`_maipai-stackchan._tcp`), feature modules, config, local API and web app.
   Runs on a Mac, Linux or a Pi 5.
3. **Brain.** Everything that thinks or remembers sits behind interfaces the host calls: speech to text, language model, text to speech, voice match, memory, vision, tools and notifications.

## Body half and brain half

Every feature has both. The body half (trigger, face, sound, light, cue) always lives here and is the same everywhere.
The brain half needs knowledge or judgement. A missing brain half hides the feature. It never shows a raw error.

## Two brain adapters

- **Standalone (default).** Chat-completions style HTTP for the model, `stt_url` and `tts_url` for speech (each falls back to a built-in local engine when blank), vision when a vision model URL is set.
- **MaiPai Home (optional).** Turns, identity, memory and household policy over the hub's published HTTP API. It does nothing unless configured.

Both use the same record shapes. The seam is `transcribe_stream`, `run_turn`, `speak` and `cancel`.

## Capabilities

At connect the host publishes a list from the active adapter: `stt`, `llm`, `tts`, `vision.describe`, `face.recognize`, `speaker.id`, `memory`, `calendar`, `lists`, `announce`,
`notify.phone`, `music.id`, `home.control`, `schedule`. A feature turns on only when all it needs are present.

## No cross-repo dependency

Host code never imports a hub. Tests fail the build if standalone code imports hub code. The body-half suite runs with the standalone adapter alone.
One conformance suite runs against both adapters. The protocol schema lives in `schema/` as a stamped snapshot with a drift check.
Compatibility is additive. Unknown fields are ignored. A `contract_version` mismatch is refused politely and names the side to update first.

## Transport

One WebSocket between unit and host. Pairing: `stackchan pair` opens 2 minutes, the unit shows 6 digits, the host stores a hashed, revocable token.
Errors return as an object with `code` and `stage` in a normal reply. The link is plaintext on the LAN until TLS is built.

## Config

`robot.toml` holds one commented set of keys, shared by the web page and the unit. `stackchan check` tests each URL. The host calls no address you did not configure.
