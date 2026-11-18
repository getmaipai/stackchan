# Music dance ladder and the movement limiter, 2026-11-17

Owner request: the dance builds gradually. First only the eyes look side to side (about 1.5 s, before any head movement), then a
nod, then side to side, then all axes together, then the same in reverse as the music fades or after a peak, all on the beat.
Every step after the eyes shows dancing on screen. Firmware patches ML01, MD01, MD02 and MD03 (tree `final15`); host
`dance_ladder.py`, `music_dance.py`, `music_dance_wiring.py`, `motion_limit.py`.

## The steps

| Step | Eyes | Head | Notes | Ring | Overlay | Faces |
|---|---|---|---|---|---|---|
| 1 eyes | side to side every beat, 10 px (the widest the face zone allows) | still | none | dark | none | happy |
| 2 nod | small shift (4 px) | nod on the beat, pitch -170 and -40 | 1 | slow breath, mint and gold, 0.10 to 0.18 of full, breath = 4 beats (1.5 to 4 s) | none | happy, serene, laughing, love; a new one every 16 beats |
| 3 sway | 10 px toward the side | yaw plus or minus 200 (fast songs) or 300, pitch -100 | 2 | chase, one pixel per beat, 0.18 to 0.30 by level | disco ball, light | adds surprised, wink; every 8 beats |
| 4 full | 10 px and a 3 px lift | yaw and pitch together, the tilt turns over every two beats (a small figure eight) | 3 | the unit paints a soft swell on the beat, 0.30 to 0.50 of full, 40 percent rise and 60 percent fall | disco ball normal; confetti at entry and every 32 beats while loud | adds silly, excited; every 8 beats |
| down | steps 3, 2, 1 in reverse, each about 4 beats (2 to 4 s) | | 2, 1, 0 | 0.7 times the sway, then the nod glow fades to dark over 2 s | ball goes below the sway | no change on the way to the eyes |

Faces never repeat back to back and never repeat within the last two. Dwell: eyes 3 beats (1.5 to 3 s), nod and sway 8 beats
(4 to 8 s), peak 24 beats (12 to 20 s), way down 4 beats (2 to 4 s). A step up needs the music: nod needs tempo confidence 20; sway
needs level 800 and confidence 30; full needs level 1000 and confidence 35. A quiet or beatless song stays where it is. The peak ends
early when the level stays under 70 percent of its entry value for 6 s. No music for 3 s starts the way down at once. A cycle that
has not peaked in 75 s goes down anyway. Battery under 40 percent, or a slow-mood round, goes no higher than the nod.

The rule is `firmware/main/hal/maipai_dance_ladder_core.h` and its mirror `Ladder` in `dance_ladder.py`; a test feeds both the same
scripted seconds and compares every step. The unit plays the motion (`BeatDanceModifier`) from the beat it measures itself. With Home
reachable the host sets the step with `self.music.stage` (a call only on a change); without Home the unit runs the same cycle by the
judge's timeline. One head move per beat at most (every second beat above about 133 BPM, the eyes still step each beat), never more
than 90 head moves a minute (the dance then moves the eyes only for a beat). With no beat for 3 s the sway and the full dance drop
to the nod.

Safety unchanged: the gates (night, asleep, a camera or live cue, full quiet, muted, locked, carried, a low battery, the emergency
stop) are in `DanceRunner` and `MusicDance`; a camera cue or a touch ends the cycle and the unit is told step 0. The ring never goes
over half of full, never changes faster than a slow swell and uses gold, lime, mint, sky and lilac only.

## The movement limiter (ML01)

One chokepoint: `Servo::update_angle_anim_target` and the spring and speed setters in `stackchan/motion/servo.cpp`, plus the continuous
rotate in `hal_servo.cpp`. Carried, held, upside down or on its side (IMU: y below -3 or x beyond 6.5 m/s^2): no movement, the head
holds. On a USB cable and not carried: half the excursion around the rest pose, speed and spring stiffness at 60 percent, no full
dance. On battery: over 50 percent nothing; 30 to 50 80 percent; 15 to 30 50 percent and 60 percent speed; 8 to 15 25 percent and no
dances; under 8 a hold; 3 point hysteresis. A cable in is the USB rule, not the ladder. `self.motion.status` and `self.motion.set`
(`usb_limit` limited or off, saved; off never lifts the carried rule or the ladder). The host reads the state and does not ask: the
head gate, the dance gate and the ladder's top step. Words for the settings page are in the catalogs (`pol.motion.*`, English and
Spanish); the page card itself is not built.

Inverted reading: upright is +y; the head's pitch moves gravity between y and z only and a pan moves nothing on x, so only an
inverted or sideways body can trip the test.

## Tests

`host/tests/firmware/dance_ladder_test.c`, `motion_limit_core_test.c`, the notes in `decor_core_test.c`;
`test_stackchan_dance_ladder.py` (C against Python, scripted `music_feat` streams, faces, notes, overlays, ring caps, the whole chain),
`test_stackchan_motion_limit.py`.
