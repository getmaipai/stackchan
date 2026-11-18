# Dance vectors for the host director (from the virtual unit's session, patch SF51)

Produced by running the unit's own core (compiled from `maipai_dance_ladder_core.h` as the series leaves it) on the virtual unit. A host director that mirrors the unit's show must give the same steps at the same seconds. Nothing here ran on a unit.

## Steps and seconds (a session of 45 s, up to step 4)

| Dance | BPM | Beat ms | Step changes: (second, step) |
|---|---|---|---|
| happy | 90 | 666 | (0, 1), (2.05, 2), (8.05, 3), (14.06, 4), (34.06, 3), (37.03, 2), (40.06, 1), (43.03, 0) |
| robot | 120 | 500 | (0, 1), (2.05, 2), (7.06, 3), (12.01, 4), (27.06, 3), (30.03, 2), (33, 1), (35.05, 0) |
| panic | 140 | 428 | (0, 1), (2.05, 2), (7.06, 3), (12.01, 4), (27.06, 3), (30.03, 2), (33, 1), (35.05, 0) |
| look_around | 80 | 750 | (0, 1), (3.04, 2), (9.04, 3), (15.05, 4), (38.02, 3), (41.05, 2), (45.01, 1), (48.05, 0) |

## Ring pixels the unit paints (12 pixels, RGB 0 to 168; half of full is 84)

| Step | Beat/time | Pixels 0..11 (R,G,B) |
|---|---|---|
| 2 breath | t=0 ms, beat 666 | 4,16,9 4,16,9 4,16,9 4,16,9 4,16,9 4,16,9 16,12,0 16,12,0 16,12,0 16,12,0 16,12,0 16,12,0 |
| 2 breath | t=500 ms, beat 666 | 6,20,12 6,20,12 6,20,12 6,20,12 6,20,12 6,20,12 20,16,0 20,16,0 20,16,0 20,16,0 20,16,0 20,16,0 |
| 2 breath | t=1000 ms, beat 666 | 7,26,15 7,26,15 7,26,15 7,26,15 7,26,15 7,26,15 26,20,0 26,20,0 26,20,0 26,20,0 26,20,0 26,20,0 |
| 2 breath | t=1500 ms, beat 666 | 8,28,16 8,28,16 8,28,16 8,28,16 8,28,16 8,28,16 28,22,0 28,22,0 28,22,0 28,22,0 28,22,0 28,22,0 |
| 3 chase | beat 0, level 57 | 40,32,0 3,13,7 3,13,7 3,13,7 3,13,7 3,13,7 3,10,6 3,10,6 3,10,6 3,10,6 3,10,6 18,30,0 |
| 3 chase | beat 1, level 57 | 18,30,0 30,24,0 3,10,6 3,10,6 3,10,6 3,10,6 3,13,7 3,13,7 3,13,7 3,13,7 3,13,7 3,13,7 |
| 3 chase | beat 2, level 57 | 3,13,7 24,40,0 40,32,0 3,13,7 3,13,7 3,13,7 3,10,6 3,10,6 3,10,6 3,10,6 3,10,6 3,10,6 |
| down chase | beat 0, level 57 | 26,20,0 2,8,4 2,8,4 2,8,4 2,8,4 2,8,4 1,5,3 1,5,3 1,5,3 1,5,3 1,5,3 12,20,0 |

## What the show adds at each step change

| Previous | Step | Notes | Disco | Confetti | Clear back layer |
|---|---|---|---|---|---|
| 0 | 1 | 0 | none | 0 | 0 |
| 1 | 2 | 1 | none | 0 | 0 |
| 2 | 3 | 2 | light | 0 | 0 |
| 3 | 4 | 3 | normal | 1 | 0 |
| 4 | 3 | 2 | light | 0 | 0 |
| 3 | 2 | 1 | none | 0 | 1 |
| 2 | 1 | 0 | none | 0 | 0 |
| 1 | 0 | 0 | none | 0 | 0 |

Faces: the unit picks the next from the step's list and never repeats one of the last two (`mdl_face_next`, a linear congruential generator seeded by the start time); a new face every 16 beats at step 2 and every 8 beats above. Notes refresh every 10 s, the disco ball every 20 s, confetti every 32 beats at step 4. Head moves follow the ladder doc (one a beat, every second beat above 133 BPM, at most 90 a minute).
