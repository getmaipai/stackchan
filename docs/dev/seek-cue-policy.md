# The face-turning seeker and the camera-on cue: why the cue is lit most of the time, and a quieter policy

Firmware track, 2026-11-18. Owner decision 22: face turning is one on or off switch, on by default; the camera-on cue always shows; mute, the lock and vision-off stop it. Until the camera path to the host is finished the switch drives the unit's own seeker (`maipai_seek.cc`, cores `maipai_seek_core.h` and `maipai_seek_wire_core.h`). This note records a finding and proposes a quieter policy that keeps the cue honest. Nothing is changed by this note.

## The finding

- In the `always` mode the seeker takes **one camera frame a second at rest** (`MS_IDLE_PERIOD_MS` 1000, `maipai_seek_core.h:55`) to notice somebody walking in.
- Every grab asks for the camera-on cue first (`MW_CUE_FRAME_MS` 700 ms before each frame, `maipai_seek_wire_core.h:34`, `:433`, `:602`), and the capture path itself draws the cue for the stream hold (`stackchan_camera.cc:14`, `:24`). With a frame every second and a cue held for more than a second, **the cue is lit nearly all the time while the setting is on.** That is honest (the camera really is reading all the time) but it makes the cue useless as a signal: a person learns to ignore a glyph that never goes out, and the honest signal for the moments that matter (a photo, a stream to the host) is lost in it.
- The `talk` mode is quieter: it looks only for a window after the wake word (30 s) and during a talk.
- Owner decision 22 makes the switch plain on or off with default on, which maps to `always` unless we choose otherwise.

## The rule that cannot change

A frame is never read without the cue. Any quieter policy must read fewer frames, not hide the cue. The cue code path (`monitor_cue_begin` in the capture path) stays as it is: nothing in this proposal can capture without it, and no setting can turn it off.

## Proposed policy: look when something happened, not on a clock

1. **No frame on a timer at rest.** Replace the one-a-second idle watch by a frame **only when a cheap sensor says something changed**: a rise in the room's sound level (the microphone path already measures it for the music features), a touch or a head-bar touch, the motion sensor (the unit was bumped or the table shook), or a door-like step in the ambient light seen by the screen's light reading if the unit has one. The camera is the confirming sensor, not the watching one.
2. **A sparse safety net:** one frame every 30 seconds at rest (the cue lit for under 3 s in 30, about 10 percent) so a person who walks in silently is still noticed within half a minute. This is a setting of the same switch, not a new choice.
3. **After a wake word or during a talk** (the `talk` rule) the seeker looks as it does today: it is wanted, and the cue shows for the burst.
4. **After a sighting** it may look a little more often for a short time (a frame every 2 s for 20 s) to follow a person, then falls back to the sparse rate.
5. **Mute, the lock, vision-off, full quiet and night mode** keep stopping it, as the doc says (night mode already skips the idle watch, patch NX06).

Effect on the cue: lit about 10 percent of the time at rest instead of about 100 percent; lit for the whole burst when it looks for a reason. A person sees the cue mean "the camera just looked".

## Cost and tests

- Firmware: a change of the idle period and a trigger input in the seek core (`ms_*` state machine), about 1 KB of flash, no RAM. The cheap triggers already exist as signals (`maipai_music_level`, `maipai_pickup`, the touch events).
- Host C tests on `seek_core_test.c`: no idle frame inside 30 s without a trigger; a trigger starts one burst within 500 ms; the cue request precedes every grab in every state; muted, locked, vision-off and full quiet never grab; after a sighting the rate steps up and falls back.
- The owner decides whether 30 seconds is the right net; the cue and the limits stay as listed.

## Open

Whether the owner wants the cue lit to mean "looking now" (this proposal) or "the setting is on" (today). The proposal is the honest one for a camera cue; the second is a status light and belongs on the settings page, not on the face.

## Status (SF55, 2026-11-18)

Approved by the coordinator as proposed; the 30 s net is the default and is not a recorded owner decision (the owner can change `MS_IDLE_PERIOD_MS`). Built as patch SF55: triggers are the head touch and any pickup event except a lift or carry (bump, shake, set-down), plus a sound rise read once a second from the music level (`ms_sound_rise`: 400 above the slow average and 2.5 times it, one per 5 s). The sound trigger works only while the music features run (the level comes from that path); without them the touch, the bump and the 30 s net remain. Each look is two frames, because at 30 s the previous frame is too old to compare. Host tests: `seek_core_test.c` (net, trigger, gates drop a trigger, 2 s follow window, sound rise) and `seek_wire_test.c`. Not yet on a unit.
