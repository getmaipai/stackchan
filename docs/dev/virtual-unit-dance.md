# The dance in the virtual unit


> Part of the [playground docs](../playground/index.md). This page is the full reference; the playground pages are the guide.

The virtual unit plays both kinds of dance the firmware has, and runs the music dance on a simulated song. Nothing here ran on a unit.

## What each dance is in the firmware

| Dance | What the firmware does | In the virtual unit |
|---|---|---|
| Happy, robot, panic, look around (the four buttons, `self.robot.dance`) | A fixed table of keyframes (`DanceModifier` in `stackchan/modifiers/dance.h`): the head goes to each keyframe's angles, the eyes and mouth change. No lights, no overlays. | The same table (`KEYFRAMES` in `scripts/virtual-unit/hw.py`): head path, eye position per keyframe, a happy, surprised or plain face per keyframe. The four have real lengths (4.2, 2.7, 1.1 and 7.5 s). |
| Bob (`self.robot.dance bob`) | Step 2 of the ladder, the nod on the beat, until the dance is stopped (patch MD01). | The same: `u.dance.bob()`. With no song the beat is a steady 600 ms, as on the unit. |
| Music dance (`self.music.stage`, or the unit's own session) | `BeatDanceModifier` plays the step: eyes, head, and the ring at the peak. Home's director adds notes, ring, disco ball, confetti and faces around it. | `scripts/virtual-unit/dance_sim.py`, below. |

The light show the owner expects (ring colors, disco ball, confetti, notes) belongs to the music dance with Home reachable, or to the host's own dance plans (`dance.py`). The four buttons never show it on the unit either.

## The music dance simulation

- **The unit's half is the real core.** `maipai_dance_ladder_core.h` is cut out of patch MD01, compiled with a small C interface (`scripts/virtual-unit/dance/ladder_sim.c`) and loaded with ctypes (`dance_core.py`). The step rule, the pose of each step, the head budget (90 moves a minute) and the ring swell are the C ones. `BeatDanceModifier::_update` and the unit's own cycle (`ladder_tick` in `maipai_music.cc`) are ported line by line.
- **Home's half is the real host code.** `LadderDirector` from `host/maipai_body/bodies/stackchan/dance_ladder.py` runs as the host runs it (a step four times a second, the feed once a second) and makes the same tool calls: `self.music.stage`, `self.face.music_notes`, `self.overlay.set`, `self.overlay.clear`, the face, and the ring.
- **Two modes.** `home` is the unit with Home reachable (the whole show, one cycle). `unit` is the unit alone: eyes, head and the ring at the peak only, and its own cycle repeats while the music goes on.
- **The song** is a fake tempo and level curve: `slow`, `fast`, `very_fast` (a 428 ms beat, so the head moves every second beat), `loud_peak` (builds, holds, fades), `quiet`, `fades`.
- **Control** (virtual only, not a firmware tool): `u.call("sim.music", {"action": "start", "song": "loud_peak", "mode": "home"})`, then `stop`, `song`, `status`. `status` has the step, the beat, the eye offsets, the head, the 12 ring pixels, the overlays, the notes and the face.
- **Goldens:** `dance-1-eyes` to `dance-5-down` in `host/tests/golden/screens`, taken on `loud_peak` in `home` mode. Tests: `host/tests/test_virtual_unit_dance.py`.

## Drawn, and not drawn

Drawn by the unit's own code on the screen: the overlay engine (disco ball and light spots, confetti), the face and its dance faces, the eyes' gaze. The music notes are drawn from the decor core's own parts, without the slant. The ring is state (12 pixels in `status` and in the 3D view's lights), not a picture.

Not drawn: the slant of the notes; the mouth weight of the keyframe dances (a happy or surprised face stands in for it); the servo's real speed (assumed 0.4 degrees a second per speed unit; the bench has not measured it).

## What differs from the design note (`docs/design/dance-ladder-2026-11-17.md`)

Found by running it, for the firmware track:

1. **The note describes one show; the unit plays half of it.** The firmware paints the ring only at step 4 (`BeatDanceModifier`). The breath (nod), the chase (sway), the notes, the overlays and the face changes are the host's, so a unit with no Home shows the eyes, the head and the peak ring only. The note's table does not say which half is which.
2. **The peak shows for one dwell longer than the note says.** The core starts the way down at the dwell (12 s at 120 BPM) but the step stays 4 until the first down dwell (2 to 4 s) has passed, so the full dance is on screen 14 to 16 s, not 12.
3. **The four buttons are not the ladder.** Happy, robot, panic and look around have no lights or overlays on the unit. If the settings page or the 3D view should offer a light-show dance without Home, that is a new unit feature.
4. **`bob` is not in the tool's dance list** the host reads (`BUILTIN_DANCES`), though the unit accepts it.

## After patch SF51: the hand-chosen dance (2026-11-18)

The virtual unit mirrors SF51. `self.robot.dance` happy, robot, panic and look around (and the screen Dance button, which calls it) start a ladder session on a synthetic beat at 90, 120, 140 and 80 BPM for 45 s, then the way down; `self.dance.session {name or bpm, seconds, max_stage}` starts one on purpose; `self.robot.stop_dance` ends it; a muted or full-quiet unit keeps the keyframe dance; `bob` is still step 2 until stopped; the limiter's tilted band allows dances up to step 2. The unit paints the nod's breath and the sway's chase itself while a session runs or no host runs the show (`mode` "unit" and "session"); with the host's director (`home`) the host paints them. The core (`mdl_synth_*`, `mdl_show_for_step`, `mdl_face_next`, `mdl_ring_breath`, `mdl_ring_chase`) is the series' header, built by `dance_core.py` from MD01 plus every later patch that changes it. Goldens: `dance-session-1-eyes` to `dance-session-5-down`. Vectors for the host director: `docs/plan/dance-vectors.md`. Step 4 lasts one down-dwell longer than the note says: the firmware track agrees (the core is right, the note was loose).
