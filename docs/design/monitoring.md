# Monitoring modes and cues

Status: design, decided 2026-11-15 (owner rule: no stealth monitoring; any monitoring is clear on the screen). Nothing here is built.

## The one rule

Every mode that opens the microphone or the camera gets its cue from the same code path that opens it. A function `monitor_cue_begin(mode)` is the only caller allowed to open the mic or camera in firmware; it draws the cue first, and the open call fails if the cue could not be drawn. No setting, host message or quiet mode hides a cue. Tests: a build check lists every caller of the mic and camera open calls and fails if one bypasses `monitor_cue_begin`.

## Cue table

| Mode | Screen | Light ring | Sound |
|---|---|---|---|
| Listening | mic icon | green, steady | none |
| Picture | camera icon | pink, two flashes then steady | double click |
| Live view | camera icon with a LIVE dot | pink, steady the whole time | double click on start |
| Watching (armed) | camera icon, the word "Watching", mic icon if sound watching is on | off at night, dim steady amber by day (setting) | none |
| Alert warning and alarm | big ALERT, flashing red and blue | red and blue sides swap at 2 Hz | rising and falling siren (alarm only), stops after 60 s or on disarm |
| Baby or Pet monitor | "Baby monitor" or "Pet monitor" (paw), mic icon, camera icon, "Listening in" mark while a phone is connected | off at night, dim steady amber by day | none |
| Remote control | Remote icon (screen with two arcs) | none | short tone before remote speech |
| Soothe (remote talk in monitor) | "Talking" | none | no tone (a tone would wake the child); the "Talking" mark replaces it |

Decisions inside the table:
- Watching: an all-night pink ring is unbearable and the camera icon with the word on the screen is the cue. While watching, each snapshot shows a one-second dot beside the camera icon. The pink ring is used only for a picture taken for an alert or by request, and for live view. The screen never turns fully off while armed (lowest brightness floor).
- Night: the ring never shows green, pink or amber at night in monitor modes; the screen floor brightness carries the cue. The screen, not the ring, is the unhideable part.
- Red and blue are reserved for alerts only. Remote lights use a separate palette. Flash rate stays at or below 2 Hz (photosensitive limit is 3 Hz).
- Own-LLM and Home setups use the same cues; Home only adds descriptions, who, quiet hours and recipients.

## Watch mode and alerts

- Detectors: motion (host snapshot differencing with ignore areas and sensitivity), loud sound (level measured on the unit; nothing recorded or sent unless an alert fires), robot lifted or moved (the unit's motion sensor). Home adds person versus pet, who, a description.
- Arm and disarm by voice, web app or a tap; 30 s arm delay with a countdown on screen.
- Responses: quiet alert (snapshot plus notice), warning (spoken line, lights, screen), alarm (adds siren).
- Alert channels, own-LLM: web app notice, local API, event stream, MQTT, phone push through the web app over the private network.
- Rate limit between alerts (default 60 s, setting). The detectors ignore the robot's own voice, moves and siren (a short blanking window after each).
- Memory: detectors on the host cost the unit nothing; the sound level meter on the unit is a few hundred bytes and runs only while armed with sound watching on.

## Baby and Pet monitor

- Starts ONLY on the robot (voice or touch). A phone connects afterwards; the robot shows "Listening in" while one is connected and stops streaming the moment the last phone leaves or the owner touches the robot.
- Listening exception (the only one): audio goes to the connected phone through a separate message type `monitor_audio`, compiled in only with `CONFIG_STACKCHAN_MONITOR`, accepted only while the unit's own monitor state is on (the unit sets it, the host cannot). The remote-control feature still has no host-to-mic path. The audio is not recorded unless an alert clip is switched on, off by default.
- Alerts on loud sound and motion; soothe by playing a sound or talking (no tone, "Talking" shown).
- Songs: built-in soft sounds, the owner's own files from a host music folder, or Home library songs. Auto-lullaby on a cry alert is off by default, always shows "Playing", stops after 30 minutes, with a low volume cap. No outside music service.
- Pet profile: loudness first for barking, howling and meowing; comfort with the owner's voice or calming sounds; label "Pet monitor" with a paw icon.
- Cry and bark detection: loudness and duration first (host side). A small classifier is optional, runs on the host only, is trained or checked on real samples before it is claimed, and stays off the unit. Until measured, the docs promise "loud sound", not "cry".
- Not promised: night vision.

## Remote pan and tilt

Arrows or a joystick, a Home button, saved spots, and live view looking around. Tilt limited to about 5 to 85 degrees (the servo maker's guidance), same servo limits, wear counter, stall guard, carried check and rate limit as local moves. Each move is one line in the activity log.

## Legal note (for the docs, needs the owner's read)

Tell residents and visitors that the robot can watch and listen. Audio and video recording and monitoring laws differ by place (some require consent from everyone recorded). The robot records nothing by default and is not a replacement for a real alarm or a medical baby monitor. This is not legal advice; the docs say so.

## Build order and checks

After the rebase and the memory gate: 1 the cue function and its bypass check (small, firmware); 2 live view; 3 watch mode (host detectors, then the unit's sound meter and the lifted sensor); 4 alerts and the alert look; 5 baby and pet monitor and `monitor_audio`; 6 remote pan and tilt. Each step runs the memory gate and the English and Spanish language check; the cue table is checked against screenshots and the real unit.
