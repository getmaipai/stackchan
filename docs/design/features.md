# Feature map and build order

Costs are estimates. Every firmware item passes the memory gate (firmware-memory.md).
Status: design. Nothing here is confirmed on a unit unless stated.

## Scope rule

Test for any feature:

- Local (built here): needs only the unit and the owner's own local servers, uses no outside service, needs no household-wide data or policy.
- Hub (MaiPai Home or the owner's own tools): needs an outside service, household records, other rooms, or policy.
- Grey zone: build the simple local version here (a local timer, a notes file, routines in the toml, local face enrolment, a camera alert with a name from that list).
  A hub supplies the household version on the same schema, with no migration.

Hub-only: song naming, calendar and briefings, email, weather, announcements, multi-room, per-person voice match,
cross-day memory, child and teen gates. This repo exposes events and hooks for them.

## Screen rule

The screen is 320x240. Default look: faces, icons, big numbers and short colour cues. Long text is spoken or goes to the web app.
Captions are the opt-in exception. Colour never carries meaning alone. Every state also has a shape or icon.

## Faces and look

- Face packs as data (`face.json`): geometry, palette, optional persona. One renderer shared by the unit and the web preview.
- `face_style`, `face_color` (none, named palette, custom), `captions`, `night_mode`. Switching never needs a reflash.
- Big-eyes pack and minimal pack. Preview stills approved by the owner before a pack is built.
- Clock face: big digits or ring, dimmed at night. Works with no host once the time is set.
- Thinking cue: animated dots on every face, plus a quiet tone by default.
- Quick-slider overlay opened from the head strip (volume, brightness, others from `quick_sliders`).

## Always-on behaviour (firmware, small each)

Pickup, shake and tilt reactions. Head-touch petting. Speech wobble and breathing idle. Free-roaming idle life.
Privacy sleep. Quiet mode with slow eased moves. Wake feedback cue. Hourly chime. Quiet hours.
Low-battery ladder: 20 percent chirp, 10 percent spoken request, 5 percent sleep before power loss.
Light and tone control per state. Camera-on cue that cannot be turned off.

## Voice and assistant (host)

Wake word on the unit. Local speech, model and voice. Follow-up without the wake word. Barge-in.
Voice commands: mute (quiet or hard), don't move, volume, brightness, sleep, stop, time, night mode.
Timers and alarms with snooze, escalation and per-category tones. Personas with a lock. Robot actions as model tools.
Offline phrases in the owner's voice. Language packs (see languages.md).

## Camera (host, opt-in)

Photo and "what is this" through the owner's vision model URL. Face follow with a bundled detector.
Wave and mirror mode. "Take my picture" with a countdown, shutter cue and local folder.
Local enrolment and a camera alert with a name from the local list. Frames stay on the host.
The camera snapshot is low resolution, so the docs call them snapshots.

## Touch and play

Colour-memory game and an action game, as signed data packs on one built-in game engine. Reaction and whack-a-mole variants.
Mood that depends on care, saved across days. Music dance and mood faces. ESP-NOW pose mirroring between units.

## Coding companion (host plus unit)

Agent status on face and ring. Spoken and captioned updates. Build light (green pass, red fail) from a `stackchan notify` hook.
Dictation by push to talk. Approvals by touch only by default, never by voice alone. An MCP endpoint lets an agent drive the robot.

## Reset the device (firmware, small; owner request 2026-11-15)

Settings > Reset on the robot clears saved Wi-Fi networks, the private-network key, pairing and settings. The host keeps its own files.
Two-step confirm on purpose: press Reset, then hold the button for 3 seconds. Cancel changes nothing. An interrupted reset still lands on the setup page (the clear is one atomic step that ends in setup, never half-cleared).
Rules to build against: clearing runs only on the unit (no host command can trigger it), nothing is cleared until the hold completes, the confirm screen says what will be erased in plain words, and it logs one local line. Memory: a screen and a handler, no resident cost; run the memory gate. Order: with step 7 (always-on behaviours), after saved-settings identity (step 1).

## Integrations host

REST and WebSocket API, event stream, MQTT, home-automation bridge, metrics, `stackchan check`. All host-side.
The self-hoster status light, a busy light and a smart-home dimmer on the strip are small ideas on top of these.

## Dropped or rejected

Sound direction. Bluetooth. Phone-pickup nudge. Native phone app. Anything that calls an outside service by itself.

## Build order

0. Fix swipe up. Baseline memory and latency on the unit.
1. Rebase onto the new base (firmware-base.md). Re-measure. Free internal RAM. Identity into saved settings and the clock fix.
2. Schema and brain interface. Simulator and virtual unit protocol. Behaviour core.
3. Host tab, discovery, pairing code.
4. Standalone adapter and the first full local turn.
5. Flasher, settings panel, updater.
6. Faces, colour, night mode, clock, big-eyes pack.
7. Always-on behaviours.
8. Integrations host.
9. Host features: timers, tools, photo, camera alert, thinking cue.
10. Games, pet, mirror, wave.
11. Optional: private-network enrolment, host wake words.

The memory gate and a language check (English and Spanish) run after every step.

## Open

- Review and decide on Bluetooth (owner request, 2026-11-15). Measure the real cost first: flash and heap with the stack compiled in but off, heap while running, and the latency effect on voice streaming from the shared radio. Candidate uses, best first: phone Wi-Fi setup from a browser (no hotspot page), a clicker for push to talk and coding approvals, find my robot, a phone or watch as a remote, room sensors on the face. Presence by Bluetooth stays dropped unless reversed. Decide: keep compiled in and off by default, or cut.

- Servo position readback when torque is released (decides record and replay of posed moves).
- Whether a storage card slot is usable.
- Which wake words the new base ships, and whether a trainable engine fits.
- Strip slide reliability across three zones.
