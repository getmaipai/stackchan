# Hardware, and a proposed declarative dialog and object system (2026-11-17)

Placement: design note for an outside review. Facts are marked [measured], [from code] or [estimate]. Everything in section 4 onward is a proposal, not built, except where it says "exists".

## 1. What this is

A small desk robot with a face screen, a microphone, a speaker, a camera, a two-axis head and a ring of lights. It talks to a program on the owner's own computer (the host) over Wi-Fi. The host runs the speech engines and the language model (a model the owner runs, or the household hub, MaiPai Home). The product promise: private, local, nothing leaves the home. The robot is complete without the hub.

Two layers:
- **The unit:** firmware on the robot. It draws, listens, speaks, moves and senses. It holds almost no application logic.
- **The host:** a Python program. It runs speech to text, the model, text to speech, game and dialog logic, the settings page, and sends commands to the unit over one WebSocket.

## 2. The hardware (the unit)

| Part | What it is | Notes |
|---|---|---|
| Processor | ESP32-S3, dual core 240 MHz | no GPU |
| Flash | 16 MB | the app image is about 3.5 MB; one app slot with about 30 percent free; a 4.4 MB assets partition (fonts, sounds, face data) [from code] |
| Memory | about 320 KB internal RAM, 8 MB PSRAM | internal RAM is the scarce part: steady free internal RAM about 70 to 87 KB, lowest dip about 33 KB, largest free block about 25 to 41 KB; PSRAM free about 7.1 MB [measured, 12 minute soak] |
| Screen | 320 by 240 color touch screen | LVGL 9 draws it; 20 to 33 frames a second for the face; one frame is 150 KB so the unit draws strips, not full frames [measured] |
| Microphone | one usable channel for speech (the board reports stereo, we use channel 0) | no sound direction possible; wake word and stop word run on the unit |
| Speaker | mono, with a codec | speech arrives as Opus audio at 24 kHz, 60 ms frames |
| Camera | small color camera in the body | about 52 degree field of view [measured]; used only on request or for opt-in features, always with a cue |
| Head | two servos, pan and tilt | head moves are rate limited and have a stall guard |
| Motion sensor | 6 axis (tilt, shake, tap, pick up) | |
| Light ring | addressable LEDs | dark unless it tells a person something |
| Light sensor | ambient light (reads nothing on some units) | |
| Radio | Wi-Fi and Bluetooth LE | Bluetooth is off |
| Other | touch strip below the screen, three expansion ports, an infrared and an NFC part with no code | |

The software stack: ESP-IDF 6.1.1, LVGL 9, FreeRTOS. The firmware is a stock base plus about 200 small patches replayed in order; there is one signed image. Tasks whose stack is in PSRAM must never touch flash or NVS (a boot-loop lesson). The memory gate for any change: internal free at least 40 KB steady, lowest at least 24 KB, largest block at least 24 KB, PSRAM free above 6 MB.

The screen has fixed zones: a banner row (y 0 to 28), the face or content (y 28 to 184) and a subtitle strip (y 184 to 240). The remote-control cue, the camera and microphone cues and privacy states live in the banner row and can never be covered by a source.

## 3. What exists today (the starting point)

- **One command channel** from host to unit: tool calls (a name and JSON arguments) for faces, lights, sounds, screens, head moves, timers, games, camera, volume, privacy. Several sources drive it: the language model (through tags in its reply), the owner's settings page and remote controllers, Home, host routines (rest, night, alarms, music dance) and local voice commands. [from code]
- **Reply tags:** the model puts tags like `[happy]`, `[rain]...[/rain]`, `[scene bedtime]`, `[sound:name]` in its reply; the host strips them from speech and turns them into commands. The robot only does what it is told; nothing is guessed from the words. [from code]
- **Games** are small data packs (JSON compiled to a binary pack) read by a fixed engine in the firmware. [from code]
- **Faces** are data: shape tables shared between the unit and the host's preview. [from code]
- **Pages and tiles** are fixed layouts with data pushed from the host. [from code]
- Everything else (calendars, flash cards, alerts, images, dialogs) is hard coded or not built.

## 4. The proposal: describe things instead of coding them

Today every new screen or conversation flow needs firmware or host code. The proposal is a small declarative system with three kinds of description, all JSON, all validated, all versioned.

### 4.1 Objects

Everything the robot can show or do is an object:

```json
{ "id": "eightball", "type": "game", "version": 3,
  "permissions": ["touch", "imu.shake", "sound.play"],
  "cost": { "psram_kb": 40 },
  "ui": { ...display list... },
  "logic": { ...rules... } }
```

Object types: `face`, `overlay`, `scene`, `card`, `game`, `sound`, `light`, `routine`, `dialog`. Each has an id, a version, a content hash, the permissions it needs, and a cost estimate. Objects are packaged as signed packs (a pack is a few KB). The host serves packs; the unit caches a few in PSRAM. An "app store" is just a list of packs on the owner's host (or Home's catalog).

### 4.2 Display lists (what the unit draws)

The unit has one small drawing engine. A card, a game board, a calendar, an alert and a flash card are all display lists:

- Primitives: `rect`, `round`, `circle`, `line`, `arc`, `text` (four sizes), `icon` (by name), `image` (by id), `bar`, `ring`, `grid`.
- Properties: position, size, color tokens (theme names, not raw colors), `blink`, `pulse`, `ease_to` (move or resize over time with an easing curve), `fade`, `z`.
- Touch areas with an `action` and optional `value`. Local actions run on the unit with no network: `dismiss`, `flip`, `next`, `prev`, `toggle`. Other actions are sent to the source as an event.
- Limits: 64 elements, 4 KB, 6 animations at once, only inside the content zone, touch targets at least 44 by 44 pixels, no scripting. A list that breaks a rule is refused whole with a plain error.
- Safety: a list can never cover the banner row or change the face or the light ring. Every list gets a drag bar and a dismiss that a source cannot remove.

Example, a calendar card (the unit draws the grid itself from a month and marks):

```json
{ "type": "calendar", "month": "2026-11", "today": 17,
  "marks": [ { "d": 20, "blink": true }, { "d": 24 } ],
  "on_tap_day": { "action": "day" } }
```

Example, an alert with a dismiss:

```json
{ "type": "card", "priority": "alert", "elements": [
  { "t": "text", "size": 24, "x": 16, "y": 36, "text": "Oven is on" },
  { "t": "icon", "name": "warning", "x": 140, "y": 80, "pulse": true },
  { "t": "touch", "x": 100, "y": 130, "w": 120, "h": 48, "label": "Dismiss", "action": "dismiss" } ] }
```

### 4.3 Dialogs (what the robot says and asks)

A dialog is a small state machine that runs on the host. It is data, not code:

```json
{ "id": "bedtime", "type": "dialog", "version": 1, "max_turns": 12,
  "start": "greet",
  "nodes": {
    "greet":  { "say": "Time to wind down. Want a story or a quiet song?",
                "scene": "bedtime", "wait": { "intent": ["story", "song", "no"], "timeout_s": 20 },
                "next": { "story": "story", "song": "song", "no": "end", "timeout": "end" } },
    "story":  { "ask_model": { "rules": "Tell a calm short story in three parts. Use scene tags.",
                               "max_sentences": 8 }, "next": "end" },
    "song":   { "sound": "lullaby", "next": "end" },
    "end":    { "say": "Sleep well.", "scene": "off", "stop": true } } }
```

Node verbs (a fixed, small set): `say`, `ask_model` (with short rules and limits), `show` (a card or display list), `sound`, `light`, `scene`, `wait` (for a voice intent, a touch action, or a timeout), `branch` (on a simple condition over stored values), `set` (a small value), `stop`. Conditions are plain comparisons, no code. Every dialog has a turn limit, a time limit, an exit phrase ("stop the game") and a safety clause: it can never weaken the model's own safety rules or the child and teen gates.

Talk games, a daily mission, a bedtime routine and a quiz are all dialogs. The model is used only inside `ask_model` nodes, so a weak local model has a small, clear job per step, and the flow does not depend on the model following a long instruction.

### 4.4 The command catalog, sources and permissions

One catalog lists every command the unit accepts, with parameter limits and a cost. A matrix says which source may send which command: the model (a small safe subset), Home and the owner (everything the owner enabled), an installed pack (what its permissions declare), a local voice command. Priority and leases settle conflicts: privacy and the child gates first, then remote cues, then Home, then the owner, then packs, then the model. Camera, microphone and remote features are off by default and always show a cue that cannot be hidden.

### 4.5 Where things live (the placement test)

1. Local, on the owner's host: anything stock offered or that needs only the robot and the owner's own model and host.
2. Home: anything that needs an outside service (weather, news, calendars, email), household data, other rooms, a person's identity or memory, or policy.
3. Firmware: only what the robot must do alone (timers, alarms, faces, the drawing engine, wake and stop words).
4. A pack: everything else, as data.

## 5. Why this design

- A new game, card or flow costs a data file, not a firmware release.
- One drawing engine replaces many hand-written layouts, which should save flash over time [estimate; measured from the linker map after migration, not promised before].
- A weak model is safe: the structure lives in the dialog, and the model fills only small slots.
- Packs can be signed, reviewed and removed; permissions are explicit.
- The same display list can be drawn by the owner's web page, so the preview and the unit agree.

## 6. Risks and open problems

- **A bounded interpreter is still an attack surface.** Caps, validation, signed packs and refusing whole lists are the answer; is that enough?
- **Frame rate.** LVGL object creation is costly on this chip; the animation budget is about 6 simultaneous animations at 30 frames a second. A heavy list could drop frames.
- **Declarative dialogs get hard to read** once they branch a lot. Where do we stop and write code?
- **Versioning.** Packs outlive firmware. How do we keep a pack working across firmware changes (a capability list and a minimum version)?
- **Offline.** The unit caches 8 lists; the dialog runs on the host. If the host sleeps, only cached lists work.
- **Internal RAM** is the hard limit. Everything declarative must allocate in PSRAM and free on close.
- **Privacy review.** A pack that asks for the camera or microphone needs a visible permission and the usual cue.

## 7. Questions for the reviewer

1. Is a JSON display list with a fixed primitive set the right level, or should the unit instead render a small subset of an existing server-driven UI format? What are the pitfalls?
2. Is a declarative state machine for dialogs a good fit for weak local models, and what verbs are missing?
3. What would you cut to keep this small enough for a chip with 320 KB of internal RAM?
4. How should pack permissions, signing and revocation work for a household with children?
5. Where does declarative stop and code begin? Give a rule of thumb.
6. Anything here that adds avoidable latency to a spoken turn, or that could make the robot do something the owner did not ask for?
