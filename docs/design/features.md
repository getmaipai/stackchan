# Feature map and build order

Costs are estimates. Every firmware item passes the memory gate (firmware-memory.md).
Status: design. Nothing here is confirmed on a unit unless stated.

## Core and Home (owner, 2026-11-15; `docs/dev/scope-core-vs-home.md`)

The core is a private voice robot: voice, faces and clock, timers and alarms, reactions, dance, privacy switches and the always-on cues, lights and sounds, travel with the private network, pairing and security, signed updates, reset, English and Spanish. Sections tagged [Home] below ship with the Home adapter or as Home packages, not in the core install. The unit keeps the body half of each (cues, camera and mic switches, indicators) so the privacy rules hold whatever runs on top, and `monitor_cue_begin` stays in the core.
Build rule: one source, two firmware presets with the same signing: `core` (small, no camera streaming, no monitor audio, no remote path) and `home` (adds the body halves Home features need, compiled in only if the memory gate holds). The hub's flash flow picks the preset. Feature logic for the [Home] sections is not kept in this public repo (it would invite hacks and copies for other bots); it lives in Home against a capability API that this repo exposes and every bot implements. See `core-extras-modules.md`.
First setup offers one optional screen: "Do you run MaiPai Home? Enter its address", skippable; pairing then uses `home_url`.

## Scope rule

Test for any feature:

- Local (built here): needs only the unit and the owner's own local servers, uses no outside service, needs no household-wide data or policy.
- Hub (MaiPai Home or the owner's own tools): needs an outside service, household records, other rooms, or policy.
- Grey zone: keep only a basic the robot must do alone, such as a local timer or alarm. Identity and routines belong in Home.

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

## [Home] Camera (host, opt-in)

Photo capture and cue only. The bundled detector runs in Home compute.
Wave and mirror mode. "Take my picture" with a countdown, shutter cue and local folder.
Frames stay on the host or Home hub.
The camera snapshot is low resolution, so the docs call them snapshots.


Live view and capture cues (owner request, 2026-11-15). The unit must always show, in a way no setting can hide, when it is listening, taking a picture or streaming live:
- Listening: green steady ring plus a mic icon on the face.
- Picture: pink, two flashes then steady, a camera icon and a double click.
- Live view: pink steady for the whole time, camera icon with a LIVE dot (new, needs design), and a double click on start.
The cue is driven by the same code path that opens the camera or mic, so a capture without the cue is impossible (hardware-truth rule, as for hard mute).
Live view in the web app: the avatar socket already carries JPEG frames up (type 0x02; 0x05 and 0x06 start and stop). First check why camera streaming never worked in AI-agent mode (`docs/dev/stackchan-vision-channel-2026-10-21.md`), then measure a low-resolution live view: frame rate, free internal RAM, Wi-Fi load, heat over 10 minutes, and the latency cost to voice. Ship only if the memory gate holds; send results to the docs session (camera page, tagged Planned).

## Ideas added after a market audit (core, small; owner request 2026-11-15)

Time-of-day faces and clock variants. Several named timers with live countdowns on the face. A cooking helper prompt pack (spoken "next step", per-step timers) that uses the own LLM and the unit timers with no new code path. A speech speed and pitch setting. For Home to build against the capability API: sound-alarm recognition alerts, intercom, per-person context with a guest mode, phone handoff. Photo-frame face stays deferred until the memory gate has headroom.

## Touch and play

Colour-memory game and an action game, as signed data packs on one built-in game engine. Reaction and whack-a-mole variants.
Mood that depends on care, saved across days. Music dance and mood faces. ESP-NOW pose mirroring between units.

## [Home] Coding companion (host plus unit)

Agent status on face and ring. Spoken and captioned updates. Build light (green pass, red fail) from a `stackchan notify` hook.
Dictation by push to talk. Approvals by touch only by default, never by voice alone. An MCP endpoint lets an agent drive the robot.

## Reset the device (firmware, small; owner request 2026-11-15)

Settings > Reset on the robot clears saved Wi-Fi networks, the private-network key, pairing and settings. The host keeps its own files.
Two-step confirm on purpose: press Reset, then hold the button for 3 seconds. Cancel changes nothing. An interrupted reset still lands on the setup page (the clear is one atomic step that ends in setup, never half-cleared).
Rules to build against: clearing runs only on the unit (no host command can trigger it), nothing is cleared until the hold completes, the confirm screen says what will be erased in plain words, and it logs one local line. Memory: a screen and a handler, no resident cost; run the memory gate. Order: with step 7 (always-on behaviours), after saved-settings identity (step 1).

## [Home] Find my robot and remote control (owner request, 2026-11-15; web app on the host)

Hardware reality: Wi-Fi, BLE 5, IR and three Grove ports; no GPS and no UWB, so no map and no arrow. A Grove GPS module stays an idea.
Find my robot: the web app shows last seen (time, Wi-Fi network name, battery), from a heartbeat the unit already sends the host. "Make it beep" plays a loud repeating tone with flashing light bars. It overrides quiet hours and mute (owner-initiated, authenticated), and one tap on the robot stops it. A warmer or colder meter only if Bluetooth stays after its review.
Remote control: off by default (`remote_control` setting plus a token), reachable only from the home network or the private network, never through an outside relay. Actions: beep with a chosen tone, lights in a chosen colour, one-way talk (typed text or push to talk), head move.
Rules (confirmed, with additions):
- No remote listening, ever: there is no host-to-mic path, and the build has no such message type.
- A Remote icon shows on the screen the whole time anyone is controlling. It cannot be hidden by a setting.
- A short tone plays before any remote speech.
- Remote lights never use the meaning colours (green listening, pink camera, and the warning colours); they use a separate palette.
- Remote talk is blocked while muted or in full quiet. Find keeps working when muted.
- Added: a remote head move obeys the same servo limits, wear counter and stall guard as local moves, is refused while the unit is carried or the arm is blocked, and is rate limited. Added: every remote action writes one line to the local activity log the household can read, and a lost token is replaced from the robot's own settings, not from the web app.
Remote icon design: monochrome glyph in the face's icon strip (same size and row as the mic and camera icons), a small screen with two signal arcs, always steady (no blink; blinking is reserved for the camera cue), drawn in the theme's neutral icon colour so it never reads as a meaning colour. When live view and remote control are both active both icons show. Needs a screen mockup before build; it must pass the memory gate (a 1-bit glyph, a few hundred bytes).

## [Home] Monitoring modes (owner request, 2026-11-15)

Watch mode and alerts, baby and pet monitor, remote pan and tilt, and the rule that no monitoring is stealth: every cue comes from the one code path that opens the mic or camera. Full design, the cue table and the decisions: `docs/design/monitoring.md`. Build after the memory gate holds on the new base.

## [Home] Integrations host

All in Home. This host exposes only the capability API and the settings page.
The self-hoster status light, a busy light and a smart-home dimmer on the strip are small ideas on top of these.

## Dropped or rejected

Sound direction. Bluetooth. Phone-pickup nudge. Native phone app. Anything that calls an outside service by itself.

## Build order

0. Fix swipe up. Baseline memory and latency on the unit.
1. Rebase onto the new base (firmware-base.md). Re-measure. Free internal RAM. Identity into saved settings and the clock fix.
2. Schema and brain interface. Simulator and virtual unit protocol. Behaviour core.
3. Host tab, discovery, pairing code.
4. Own-LLM adapter and the first full local turn.
5. Flasher, settings panel, updater.
6. Faces, colour, night mode, clock, big-eyes pack.
7. Always-on behaviours.
8. Timers, tools hook and thinking cue.
9. Home backlog: integrations host, photo and camera alert.
10. Home backlog: games and pet.
11. Optional: private-network enrolment, host wake words.

The memory gate and a language check (English and Spanish) run after every step.

## Open

- Experiment: an iPhone as hotspot and model server for the travelling robot (plan, risks and what to record: `docs/dev/experiment-iphone-llm-2026-11-15.md`). Needs the unit, an iPhone, a laptop host and a trip test with Jesse. Send the numbers to the docs session for a Planned page.
- Measured speed and quality for named machines (small model warm, large model on a weak host) before release; the user docs only quote design figures until then.
- Experiment, after the laptop-host test: a phone-only setup with no computer. Options: a small always-on host (Pi 5) with the model on the phone (works today), or a native iPhone app that is the host (robot link, pairing, on-device speech, on-device model). By the scope rule it is a separate client, not core. Feasibility notes: `docs/design/ios-host.md`.
- After StackChan ships: plan the Reachy Mini migration like this one and retire the old `bot` repo (see `decisions.md`, "Migration order").
- Review and decide on Bluetooth (owner request, 2026-11-15). Measure the real cost first: flash and heap with the stack compiled in but off, heap while running, and the latency effect on voice streaming from the shared radio. Candidate uses, best first: phone Wi-Fi setup from a browser (no hotspot page), a clicker for push to talk and coding approvals, find my robot, a phone or watch as a remote, room sensors on the face. Presence by Bluetooth stays dropped unless reversed. Decide: keep compiled in and off by default, or cut.

- Servo position readback when torque is released (decides record and replay of posed moves).
- Whether a storage card slot is usable.
- Which wake words the new base ships, and whether a trainable engine fits.
- Strip slide reliability across three zones.
