# The dance in the virtual unit

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
