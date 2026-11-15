# Architecture

Status: design, decided 2026-11-15. Nothing here is built for the standalone path yet.

## Goal

One firmware, one host program, one feature set. A brain such as MaiPai Home makes features deeper.
It is never required. This repo has no dependency on any other repo.

## Three layers

1. Unit (firmware). Face, touch, IMU, servos, camera capture, mics, speaker, wake word, clock, timer ring,
   state cues, settings panel, Wi-Fi, pairing. It speaks one protocol to one host. Its hello reports
   `contract_version`, firmware version, face packs, sensors and a capability list.
2. Host (the `stackchan` program). Protocol server, pairing, discovery, feature modules, config, local API,
   web app. Runs on a small always-on machine (Mac, Linux, Pi 5). The unit has about 76 KB of internal RAM
   free (estimate), so it never talks to a language model itself.
3. Brain (the seam). Everything that thinks or remembers sits behind interfaces the host calls:
   speech-to-text, language model, text-to-speech, voice match, memory, vision, tools, notification delivery.

## Body half and brain half

Every feature is split in two.

- Body half: the trigger, the face and servo behaviour, the sound, the light, the UI cue. Always in this repo.
  Same in every setup. Example for a timer: the ring that empties, the chime, the stop touch.
- Brain half: the part that needs knowledge or judgement. Example: understanding "set a pasta timer for ten minutes".

A feature is standalone-complete when its body half works with the built-in brain half. A richer brain upgrades
the brain half and leaves the body half alone. If a brain half is missing, the feature hides itself. It never shows a raw error.

## Capability negotiation

At connect the host publishes a capability list built from the active brain adapter:
`stt`, `llm`, `tts`, `vision.describe`, `face.recognize`, `speaker.id`, `memory`, `calendar`, `lists`,
`announce`, `notify.phone`, `music.id`, `home.control`, `schedule`.

- The unit and the settings page show only what exists.
- Features declare the capabilities they need. The host turns a feature on only when all are present.
- The list stays short and every name is defined in the schema. No ad-hoc strings.

## Brain adapters

| Adapter | Provides |
|---|---|
| Standalone (default) | Chat-completions style HTTP for the language model, plus `stt_url` and `tts_url` for speech, each falling back to a built-in local engine when blank. Vision when a vision model URL is set. |
| MaiPai Home (optional) | Turns, identity, memory and household policy from a MaiPai Home hub, over its published API. Does nothing unless configured. |

Both adapters use the same record shapes (turns, events, face-pack manifest, persona). A persona or pack made for one works in the other.
The seam is: `transcribe_stream`, `run_turn` (yields the turn event stream), `speak`, `cancel`.

## No cross-repo dependency

- Host code never imports a hub. The hub adapter talks over HTTP and lives here as an optional module.
- A user never clones another MaiPai repo to run this one.
- Architecture tests fail the build if standalone code imports hub code.
- CI runs the whole body-half suite with the standalone adapter and no hub present.
- One conformance suite runs against both adapters, so they cannot drift apart.

## Vendored schema snapshot

- The unit protocol and brain interface live in `schema/` in this repo, versioned.
- The shared org spec holds the master copy. This repo vendors a stamped snapshot (a data copy, not a runtime dependency).
- A CI drift check compares the stamp to the tagged spec and fails on a difference.
- Compatibility is additive only. Unknown fields are ignored. Host and unit refuse politely when `contract_version`
  does not match and say which side to update first.

## robot.toml

- One commented file. `brain = "standalone"` (default) or `brain = "home"` with the hub address.
- Switching is one line. The unit is not reflashed.
- Keys: `llm_url`, `stt_url`, `tts_url`, `voice`, `language`, `face_style`, `face_color`, `captions`,
  `night_mode`, `thinking_cue`, `update_*`, privacy and presence keys, a `[body]` section for body-specific keys.
- The same keys appear in the web settings page and on the unit. Environment variables override secrets.
- `stackchan check` tests each URL and says in plain words what is wrong.
- The host calls no network address the owner did not put in the file.

## Transport

- One WebSocket between unit and host. The host fans out to speech, model and voice services.
- Pairing: `stackchan pair` opens a 2 minute window. The unit shows a 6 digit code. The owner types it on the host.
  The host issues a long random token, stored hashed and revocable with `stackchan forget`. Five wrong codes close the window.
- Discovery by mDNS (`_maipai-stackchan._tcp`). Fallback: a typed host address on the unit's Wi-Fi page.
- Camera frames use a credit scheme and one stream owner, so the unit never floods the host.
- Errors come back as an object with `code` and `stage` inside a normal reply, so the unit can always show a plain message.

## Local API and bridges (host side, off by default)

REST and WebSocket with a token on reads and writes, an event stream, an MCP endpoint, MQTT out, a home-automation bridge,
a metrics endpoint. All host-side, so none costs unit RAM. Binds to the LAN, token required.

## Open

- Whether the unit-to-host link gets TLS with a certificate the unit remembers at pairing. Plan: build it after the pairing token exists. Until then the link is plaintext on the LAN and the docs say so.
- Whether to add a Wyoming style speech adapter. Only if users ask.
