# Dance entry points on the real unit, and what each one runs

Bottom line: on the real unit code, only one path runs the ladder, and it needs real music. A dance chosen by hand (the screen's Dance button and tile, the `self.robot.dance` tool, a spoken word reaction, the Settings button, the voice ask) never runs the gradual loop on the unit. The unit plays a fixed keyframe dance (head, eyes and mouth only, no ring, no overlay, no notes). Only the host's "little dance" adds a ring show and a face change, and only while the host is paired. The ladder (eyes, nod, sway, full, way down) runs from two places: the host's `LadderDirector` when the host hears music (with the unit's `BeatDanceModifier` playing the motion), and the unit's own offline cycle when the host is away and its microphone hears music. Both need a measured beat and level. The sentence in `docs/design/dance-ladder-2026-11-17.md` that without Home and without music "the unit runs the same cycle by the judge's timeline" is refuted for a manual choice, and also only partly true for the offline music cycle: the unit alone paints no overlay, no notes, no breath or chase ring, and rotates no faces. The virtual robot showed no light show because the fake does what the real unit does for that tool: it moves the head only.

Paths: firmware paths (`main/...`) are in the replayed tree `~/esp/stackchan-rebuild/b47/firmware`; host and script paths are in this repo. Each claim is marked `[code]` (read in the file named) or `[inferred]` (derived from code, not run).

## The table

"Host" below means the StackChan host program (`host/maipai_body`) while it is paired with the unit.

| Entry point | What runs | Eyes | Head | Ring | Overlay | Faces | Beat source |
|---|---|---|---|---|---|---|---|
| Screen Dance button (quick action) and the Dance app tile | `maipai_dance_play("happy")`, a stock keyframe dance, 4.2 s | keyframe squint and `eye_x` (stock) | stock Happy keyframes, ML01 limited | none | none | none | none |
| `self.robot.dance` tool (names happy, robot, panic, look_around) | same function, stock keyframes | keyframe weights | keyframe yaw and pitch | none | none | none | none |
| `self.robot.dance` extras (sway, nod_yes, shake_no, wiggle, bow, groove) | the row in `maipai_dances_core.h` becomes keyframes, 1.4 to 4.5 s | keyframe `eye_x` and weights | keyframe | none | none | none | none |
| `self.robot.dance` name `bob` | `maipai_music_stage_set(2)`: the beat dance at step 2 until stopped | small shift, 4 px | nod on the beat | none | none | none | synthetic 600 ms (no beat held) |
| Spoken word reaction (the table in `maipai_react_core.h`, row "love" and the like) | `maipai_dance_play("happy")` after the face and decor | face from the row | Happy keyframes | none | decor from the row (heart) | face from the row | none |
| Host: spoken "dance" and the Settings button ("hub" command) | `DanceRunner` plays `LITTLE_PLAN`: happy, robot, happy (11.7 s) through `self.robot.dance` | keyframe | keyframes | host ring show: chase, pulse, sparkle at 0.5 | none | host: happy, wink, surprised, happy, neutral at the end | none |
| Host: music dance, ladder on (`ladder_on`) | `LadderDirector` inside `DanceRunner`; the unit plays `BeatDanceModifier` at the step the host sets | 10 px side to side, 4 px at the nod, 3 px lift at full | nod, sway, figure eight by step, 90 moves a minute budget | host: dark at step 1, breath at 2, chase at 3, unit swell at 4 | disco ball from step 3, confetti at entry to 4 and every 32 beats while loud | host: rotator, a face every 8 beats (16 at the nod) | the unit's measured grid (`maipai_beat_get`) |
| Host: music dance, ladder off (old plans `AUTO_PLAN`, `DANCE_PLAN`, `CALM_PLAN`) | fixed keyframe plans and phrases | keyframe | keyframes through `self.robot.dance` | host ring show | none | host faces | tempo only sets phrase length |
| Unit alone: offline music session (`offline_music_step`, patches V03, MD01, SF14) | `ladder_begin` then `ladder_tick` once a second; the unit plays `BeatDanceModifier` | 10 px side to side, 4 px at the nod, 3 px lift at full | nod, sway, figure eight by step | unit swell at step 4 only | none | `set_face` at the nod and the slow mood only (two or three mood faces) | the unit's measured grid; needs music |
| Host: `self.music.stage` called by hand | `maipai_music_stage_set`, same modifier | as the step | as the step | unit swell at step 4 only | none | none | last grid, else steady 600 ms; steps 3 and 4 fall to the nod after 3 s without a measured beat |

## Evidence, entry point by entry point

### 1. The unit's dance function (every manual path ends here)

- `maipai_dance_play(name)` is the one function behind the screen button, the tool and the word reactions: `main/hal/hal_mcp.cpp:136`. [code]
- It refuses when the limiter allows no dances: `main/hal/hal_mcp.cpp:139` (calls `maipai_motion_dances_ok`, `main/hal/maipai_motion_limit.cc:157`). [code]
- `bob` is the only name that reaches the beat dance: `main/hal/hal_mcp.cpp:142` to `143`, calling `maipai_music_stage_set(2)`. [code]
- happy, robot, panic and look_around pick a stock `DanceModifier` keyframe sequence: `main/hal/hal_mcp.cpp:145` to `153`; the sequences are in `main/stackchan/modifiers/dance.h:20` to `94`. Each row sets eye and mouth weights and yaw and pitch with a speed, and nothing else. [code]
- The data dances turn a row into the same keyframes: `main/hal/hal_mcp.cpp:155` to `171`, rows in `main/hal/maipai_dances_core.h:44` to `66`. [code]
- Playing one removes a running beat dance and zeroes the step: `main/hal/hal_mcp.cpp:177` to `184`. So a manual dance cancels an offline ladder cycle. [code]
- The tool is `self.robot.dance` (`main/hal/hal_mcp.cpp:800`); stop is `self.robot.stop_dance` (`main/hal/hal_mcp.cpp:836`), which also ends the beat dance. [code]
- Nothing in `DanceModifier` touches the ring, an overlay, the notes or a face change: `main/stackchan/modifiers/dance.h:96` to `107` (it only runs a timeline and destroys itself). [code]

### 2. Screen Dance button, quick action, Dance app, word reactions

- Quick action: `case MPG_A_DANCE: ... maipai_dance_play("happy")` at `main/hal/maipai_pages_unit.cc:284`. The action list is beep, dance, game, hello (`main/hal/maipai_pages_core.h:52`). [code]
- Dance app tile: `main/hal/maipai_apps.cc:469` to `476` calls the same host action after a quiet or mute check. [code]
- Word reactions: `play()` calls decor, a sound and `maipai_dance_play(MR_DANCES[e.dance])` at `main/hal/maipai_react.cc:132` to `148`; the four possible dances are `main/hal/maipai_react_core.h:46`. [code]
- Result: 4.2 s of Happy sway with a squint. The unit does not tell the host, so no ring show starts (no host event is consumed for it: `DanceRunner.on_events` handles only shake and touch, `host/maipai_body/bodies/stackchan/dance.py:330` to `345`). [code for the unit and the host handler; inferred that no other host hook watches it]

### 3. Host little dance (voice ask, Settings button)

- Voice: `head_commander.dance = lambda: runner.request("voice").line` at `host/maipai_body/bodies/stackchan/dance_wiring.py:140`; the Settings command: `host/maipai_body/bodies/stackchan/dance_wiring.py:133` to `135`. [code]
- The plan is `LITTLE_PLAN` (`host/maipai_body/bodies/stackchan/dance.py:156`): happy, robot, happy with wink and surprised faces between (`host/maipai_body/bodies/stackchan/dance.py:73` to `82`, 11.7 s). [code]
- The ring show is written by the host every 0.25 s at 0.5 of full while `show_ring` is on and it is not night: `host/maipai_body/bodies/stackchan/dance.py:455` to `491`, frames at `host/maipai_body/bodies/stackchan/dance.py:106` to `128`. [code]
- No overlay, no notes and no `self.music.stage` call anywhere in this plan. [code: no call in `dance.py` or `dance_wiring.py`]
- Gates: one dance at a time, 60 s between voice and hub dances (`host/maipai_body/bodies/stackchan/dance.py:61`, `:381`), refused when carried or `dance_max` is 0 (`:358`). [code]

### 4. Host music dance with the ladder

- Wired in `host/maipai_body/bodies/stackchan/music_dance_wiring.py:226` to `292`: `LadderDirector` is the plan's `on_tick`, `ring`, `finished` and `on_end`; the round is at most 120 s (`:54`). [code]
- The director sets the unit's step with `self.music.stage` (`music_dance_wiring.py:236`), the notes with `self.face.music_notes` (`:247`), overlays with `self.overlay.set` (`:231`). [code]
- Overlays: disco light at step 3 and normal at 4, confetti at entry to 4: `host/maipai_body/bodies/stackchan/dance_ladder.py:400` to `413`; confetti again every 32 beats while the level is high: `dance_ladder.py:424` to `432`. [code]
- Notes by step 0, 0, 1, 2, 3: `dance_ladder.py:162`. [code]
- Faces by step and a rotator that never repeats within the last two: `dance_ladder.py:169` to `197`; a face every 16 beats at the nod and every 8 otherwise: `dance_ladder.py:376` to `389` (`_phrase_s` and `_face`). [code]
- Ring: dark at step 1 (a fade on the way down), breath at 2, chase at 3, `None` at 4 so the unit's swell is the only light: `dance_ladder.py:436` to `456`. [code]
- Needs `overlays_enabled` on the unit: `main/hal/maipai_fx.cc:786` refuses with "overlays are turned off in the settings" and the host swallows the failure (`dance_ladder.py:412`). Default is on (`main/hal/maipai_prefs_core.h:80`, default value 1). [code]
- The unit's side: `BeatDanceModifier` reads the step with `maipai_music_stage_get()` (`main/stackchan/modifiers/beat_dance.h:44`), the beat with `maipai_beat_get` (`:51`), and moves eyes at every beat (`:74`) and the head at most once per beat (`:80` to `89`). [code]

### 5. Unit alone: the offline cycle

- Runs only when the host link is down (`main/hal/maipai_music.cc:256`), music features are on (`:262`), and no safety gate applies (`:278` to `284`). [code]
- The input is the microphone only: level, tempo and confidence come from `mm_feat_t` (`main/hal/maipai_music.cc:290` to `292`); `ladder_tick` passes the judge's verdict as the `music` flag and the measured period (`:221` to `223`). With no sound the flag is 0, and `mdl_step` starts the way down after 3 s (`main/hal/maipai_dance_ladder_core.h:53`, `:118`). [code]
- Start: a nod verdict begins a cycle capped at step 2 (`maipai_music.cc:294` to `302`); a dance verdict 15 s later lifts the cap to 4 (`:303` to `313`, delay `main/hal/maipai_music_judge.h:16`); a slow-mood break caps at 2 (`:314` to `323`). [code]
- Faces: `set_face` on the nod and from the mood function while music plays (`maipai_music.cc:298`, `:336` to `339`). There is no per-step face rotator on the unit. [code]
- No call to `ov_start`, the decor notes or a ring painter exists in `maipai_music.cc`. [code: file read in full]
- The ring is painted only by the modifier and only at step 4: `main/stackchan/modifiers/beat_dance.h:91` (`eff >= 4`), using `mdl_ring_frame` and `mdl_swell` (`main/hal/maipai_dance_ladder_core.h:279`, `:295`). The core has no breath or chase function. [code]
- Cap SF14: ten minutes of motion then three minutes of rest, enforced once a second in `ladder_tick` only (`main/hal/maipai_music.cc:204`; `main/hal/maipai_dance_cap_core.h:15` to `17`). It does not touch manual dances. [code]

### 6. Beat source for the modifier

- A measured beat is published only when the tempo is 60 to 187 BPM folded to 70 to 140 BPM, confidence is high and a grid is steady (`main/hal/maipai_music.cc:91` to `153`), so periods fall between about 428 and 857 ms. `maipai_beat_get` returns false after 3 s without a fresh one or below confidence 30 (`:435`). [code]
- With no beat ever seen, the modifier runs a steady 600 ms grid from its own start (`main/stackchan/modifiers/beat_dance.h:59` to `62`). So `bob` and a hand-set step 2 work without music. [code]
- But `mdl_effective_stage` drops steps 3 and 4 to the nod after 3 s without a measured beat (`beat_dance.h:63`; `main/hal/maipai_dance_ladder_core.h:243`), and the first 3 s count from the modifier's start (`_beat_seen(_t0)`, `beat_dance.h:29`). So a hand-set step 3 or 4 with no music shows the full dance for 3 s and then the nod. [code]

## Where the unit differs from the ladder doc, most important first

1. A manual dance is not the ladder. The screen button, the tile, the tool and word reactions play a stock keyframe dance (`main/hal/hal_mcp.cpp:145` to `153`). The doc's "a chosen dance builds gradually" is true only for music. [code]
2. The "no Home, no music" sentence has no code behind it. The unit's cycle takes `music` from the microphone judge (`main/hal/maipai_music.cc:221`); there is no synthetic beat or synthetic level anywhere. [code]
3. Overlays are host-only. The disco ball and the confetti exist only in `LadderDirector` (`dance_ladder.py:400` to `432`). On the unit alone nothing starts an overlay. [code]
4. The ring at steps 2 and 3 (breath, chase) is host-only (`dance_ladder.py:436` to `456`); the unit alone has the step 4 swell only (`beat_dance.h:91`). The doc's table lists breath and chase as part of steps 2 and 3. [code]
5. Notes and the face rotator are host-only. The doc lists notes 1 to 3 and a new face every 8 or 16 beats; the unit alone sets two or three mood faces and no notes (`maipai_music.cc:298`, `:336`). [code]
6. A hand-set step 3 or 4 falls to the nod after 3 s with no measured beat (`beat_dance.h:63`). The doc says the same for lost music, but a manual dance has no beat to lose. [code]
7. The host's voice and Settings dance is not the ladder either: `LITTLE_PLAN` plays happy, robot, happy and a ring show (`dance.py:73` to `82`, `:156`). It has the ring but no overlays and no gradual build. [code]
8. The head budget is per modifier, not per minute of dancing. `_budget` is reset in the constructor (`beat_dance.h:31`) and the modifier is destroyed at step 0 (`main/hal/hal_mcp.cpp:207` to `212`) and rebuilt for the next cycle, so the 90 a minute window restarts every cycle. A normal cycle at 100 BPM makes about 55 to 60 head moves, so the budget does not bite. It bites only in a long cycle or in `bob`, which has no end. [code for the reset; inferred for the move count]
9. The limiter's dance ceiling is checked in `maipai_music_stage_set` (`hal_mcp.cpp:239`) but the offline `Ladder` state still thinks it is at step 4 while the unit shows 3 on USB (`maipai_music.cc:303` to `306`). Harmless today (it only changes how long the unit "peaks"), so list it, do not fix it first. [inferred]
10. The orientation band "tilted" sets `dance_max` to 2 on the real unit (`main/hal/maipai_motion_limit_core.h:210`); the fake returns 1 (`scripts/virtual-unit/tools/motion.py:90`). A small fake bug. [code]
11. The doc says the unit "plays the motion from the beat it measures itself". True, and when the host is paired the host sets the step; the unit also needs `self.music.set` on before `self.music.stage` accepts a step above 0 (`main/hal/maipai_music.cc:564` to `566`), but `bob` and `maipai_music_stage_set` do not check it. [code]

## What a manual dance would need, and the smallest fix (design only)

Goal: a manual dance (button, tile, tool, word reaction, Settings, voice) builds as the ladder does, with a synthetic beat at the dance's own tempo, with or without the host.

### Smallest fix, unit only (covers the button, the tile, the tool and the reactions)

The ladder state and the pure rule already exist (`mdl_start`, `mdl_step`, `mdl_pose`, `mdl_budget_take`, `mdl_swell`, `mdl_ring_frame`). What is missing is a clock source that is not the microphone, and the show that the host adds. Add to `main/hal/maipai_dance_ladder_core.h` (plain C99, no clock, all inputs passed in):

```c
/* A synthetic beat and level for a dance chosen by hand: no microphone. */
typedef struct {
    uint32_t t0_ms;      /* when the dance began; the beat grid starts here */
    uint32_t period_ms;  /* the dance's own beat, 428 to 857 */
    uint32_t total_ms;   /* when to start the way down */
    uint8_t  max_stage;  /* 1..4 */
} mdl_synth_t;

void mdl_synth_start(mdl_synth_t* y, uint32_t now_ms, int bpm, uint32_t total_ms, int max_stage);
/* Always true while the dance runs; ref is the newest grid beat at or before now (so the modifier never sees "lost beat"). */
int  mdl_synth_beat(const mdl_synth_t* y, uint32_t now_ms, uint32_t* period_ms, uint32_t* ref_ms);
/* The step input for this second: music 1, level 1200, tc 60 until total_ms, then music 0. */
void mdl_synth_input(const mdl_synth_t* y, uint32_t now_ms, mdl_in_t* in);
/* Start the way down at total_ms instead of waiting 3 s for lost music. */
int  mdl_synth_step(const mdl_synth_t* y, mdl_t* s, uint32_t now_ms);   /* the stage, 0 when over */
/* The dance's own tempo: happy 75 (800 ms, its sway step), robot 120, groove 133, sway 75, wiggle 140. -1 for a name that is a gesture (panic, look_around, bow, nod_yes, shake_no): those stay keyframes. */
int  mdl_synth_bpm_for(const char* name);
```

Then the show that the host does today, as pure functions the unit can call (mirrors of `dance_ladder.py`, tested C against Python like the stage rule):

```c
typedef struct { uint8_t notes; uint8_t disco; uint8_t confetti; uint8_t clear_overlays; } mdl_show_t; /* disco 0 none, 1 light, 2 normal */
void mdl_show_for_step(int previous, int stage, mdl_show_t* out);               /* NOTES_FOR_STAGE and _overlays rules */
int  mdl_face_next(uint32_t* rng, int stage, uint8_t history[6]);               /* FACES_BY_STAGE, never the last 2 */
void mdl_ring_breath(uint8_t out[MDL_RING_PIXELS][3], uint32_t t_ms, uint32_t beat_ms, int full_depth);  /* 0.10 to 0.18 */
void mdl_ring_chase(uint8_t out[MDL_RING_PIXELS][3], uint32_t beat_index, int level_pct, int down);     /* 0.18 to 0.30 */
```

Firmware wiring (the one place to touch): in `maipai_dance_play` (`main/hal/hal_mcp.cpp:136`), for a name with `mdl_synth_bpm_for(name) > 0`, do not add `DanceModifier`; add a `BeatDanceModifier` constructed with an `mdl_synth_t`. In `main/stackchan/modifiers/beat_dance.h`:

- `_update` takes the beat from `mdl_synth_beat` (not `maipai_beat_get`) and the step from its own `mdl_t`, stepped once a second with `mdl_synth_step`, instead of `maipai_music_stage_get()` (`beat_dance.h:44`, `:51`).
- On a step change it calls one new function in `hal_mcp.cpp`, `maipai_dance_show_step(prev, stage)`, which applies `mdl_show_for_step` (notes through `maipai_decor_show_n`, disco and confetti through `ov_start`, clear through `ov_clear_all`) and one face through `hal_bridge::react_face`. Overlays and notes stay refused when `overlays_enabled` is off or a privacy cue shows, as the tools refuse today.
- The ring is painted for steps 2 and 3 with `mdl_ring_breath` and `mdl_ring_chase` next to the existing step 4 swell (`beat_dance.h:91`), gated by `maipai_dance_ring_allowed()` (`hal_mcp.cpp:197`).
- When `mdl_synth_step` returns 0 the modifier calls `requestDestroy()` (as `DanceModifier` does, `dance.h:104`), which darkens the ring in its destructor (`beat_dance.h:34`) and clears notes and overlays.
- Stage limits stay as they are: the limiter clamp (`hal_mcp.cpp:239`) applies, so on USB the manual dance tops out at step 3 and on a low battery or carried it does not start.
- Do not change the music paths. When the host is paired and the unit's music session is running, a manual dance replaces the cycle as it does now (`hal_mcp.cpp:177` to `184`).

Host tests that need no unit (`host/tests/firmware/dance_ladder_test.c`, extended): drive `mdl_synth_start` with 75 BPM and `max_stage` 4, call `mdl_synth_step` once a second for 60 s of fake time, and assert (1) the stage sequence 1, 2, 3, 4, 3, 2, 1, 0 with the dwell times from the table in the doc (at 800 ms: 2.4, 6.4, 6.4, 19.2, then 3.2 each); (2) `mdl_synth_beat` always returns true and `ref` is on the grid, so `mdl_effective_stage(stage, 0)` never drops a step; (3) `mdl_show_for_step` gives notes 1, 2, 3, disco 1 then 2, confetti once at the entry to 4 and `clear_overlays` below 3; (4) `mdl_budget_take` is never refused in a 60 s run at 75 BPM; (5) `mdl_ring_breath` and `mdl_ring_chase` stay under `MDL_RING_CAP_PCT` for every channel; (6) the Python mirror gives the same rows (`test_stackchan_dance_ladder.py` pattern).

Length: the doc's minimum cycle is 29.5 s, 47 s at 800 ms. Pass `total_ms` about 30 s for a button press so it does not feel long; this is a design choice for the owner.

### Cheaper first step, host paired only (covers voice and Settings)

Keep the unit as it is and give it one additive argument, `bpm`, on `self.music.stage` (`main/hal/maipai_music.cc:552` to `575`): when set, `BeatDanceModifier` uses a synthetic grid at that tempo and never treats the beat as lost. Then in `dance_wiring.py` build a plan like `music_dance_wiring.py:273` to `291` with a `LadderFeed` filled with that tempo, `tc` 60, `energy` 1200 and `music` true until the plan's `total_s`, instead of `LITTLE_PLAN`. This reuses the host's notes, overlays, faces and ring unchanged. It does not fix the unit-alone button, so it is a stopgap.

## Head caps against the new servo clock (patch SF28)

What changed: the animation now advances by the real time since the last step, between 10 and 50 ms (`main/hal/maipai_servo_clock_core.h:31` to `35`; `main/stackchan/motion/servo.cpp:111`), on its own 20 ms task, and a speed ceiling of 400 degrees a second times the limiter scale clips each written step (`maipai_servo_clock_core.h:21`, `:42` to `47`; `servo.cpp:116`). The ceiling is 400 at free (scale 100), 320 in the "mild" battery band (scale 80), and 200 at scale 50 (USB limited and the "limited" battery band). [code]

Method (inferred, not measured): a spring at `speed` has stiffness k = 10 + (speed/1000)^2 times 640 and critical damping (`servo.cpp:252` to `270`). A critically damped move of size D from rest peaks at D times sqrt(k) divided by e. Angles are tenths of a degree, so yaw 300 is 30 degrees and a side to side move is 60 degrees.

Peak head speed of the ladder's side to side move (`mdl_pose`, `maipai_dance_ladder_core.h:200` to `238`), free, unlimited:

| Beat (BPM) | Period | speed (`240000 / span`) | Swing | Peak, degrees a second |
|---|---|---|---|---|
| 70 | 857 ms | 280 | 60 degrees | about 171 |
| 100 | 600 ms | 400 | 60 degrees | about 234 |
| 100 to 133 (period 450 to 599) | 500 ms | 480 | 40 degrees | about 185 |
| 133 | 450 ms | 533 | 40 degrees | about 204 |
| above 133 (every second beat) | 428 ms, span 857 | 280 | 60 degrees | about 171 |

Reading (inferred): the worst ladder move is about 234 degrees a second, under the 400 ceiling with 1.7 times of room. On USB the swing halves (yaw 150) and the spring speed is capped at 600 (`maipai_motion_limit_core.h:51`), which gives about 100 to 120 degrees a second against a ceiling of 200: the ceiling never binds in the ladder. It binds for two stock keyframes: Robot (90 degree turns at speed 800, about 680 degrees a second asked) is clipped to 400 at scale 100 and to 200 at scale 50; Panic (40 degree shakes in 100 ms at speed 1000) comes close to 400 and is clipped at scale 50. Those two will look slower than the spring would have moved them, which is the intent of the ceiling. [inferred]

The 90 head moves a minute cap (`MDL_BUDGET_MOVES`, `main/hal/maipai_dance_ladder_core.h:252`; used at `beat_dance.h:85`):

- It counts moves issued, not distance traveled. Its number still means what the doc meant: at most 90 moves.
- What changed is the distance behind each move. On the old clock the head ran at about half speed and, at beats near 600 ms, often had not finished a swing before the next one reversed it. Now a 60 degree swing completes in about 0.44 s at 100 BPM (4.7 divided by sqrt(112) is the 95 percent settle time), so each move travels more. Travel per minute at 90 moves of 60 degrees is 5400 degrees. Before the clock change it was lower (inferred; the size of the drop is not measured).
- The cap only bites above 90 BPM. At 100 BPM it would freeze the head for about 6 s a minute; at 133 BPM for about 19 s (freeze fraction is 1 minus 90 over beats a minute, with the head in bursts). Inside a normal cycle it does not bite (item 8 above). [inferred]
- Stock `set_head_angles` has its own 40 a minute limit (`main/hal/hal_mcp.cpp:104`, `:348`); the beat dance does not pass through it. It is a different counter and stays.

What to retune:

1. Keep the 90 count. Add a travel cap beside it only if the servo's heat or the stall guard shows trouble in a long run: sum of absolute yaw and pitch change per 60 s, starting at 5400 degrees. Do it after a bench measure with the peak-speed record (patch SF39) at 100 and 133 BPM, not before. [inferred]
2. The speed formula `240000 / span` (clamp 220 to 600) was written so a move lands within a beat. On the real clock it does with room to spare above 70 BPM, so the clamp floor of 220 and the +10 percent "loud" boost at step 4 (`maipai_dance_ladder_core.h:228` to `231`) are where to trim first if the head now looks too snappy. Candidates: floor 180, ceiling 500. Judge on the real unit, not the fake. [inferred]
3. The 3 s "lost beat" rule and the dwell clamps are time based and are not affected by the clock change.
4. The fake's `speed_cap` and `dance_offset` (`scripts/virtual-unit/hw.py:249`) are simple sine shapes and do not use the real ceiling. Leave them, but do not read peak speed from the playground.

## Why the virtual robot showed no light show for "Dance happy"

The playground button calls `self.robot.dance` with the name (`scripts/virtual-unit/view.html:220`). The fake's handler only stores the name in `motion.dance` after the limiter check (`scripts/virtual-unit/tools/motion.py:153` to `161`), and the view turns that into a head path with `hw.dance_offset` (`scripts/virtual-unit/hw.py:249` to `270`, `view.py:118` to `152`). That matches the real unit, where the same tool also plays only the keyframe dance (section 1). The ring in the fake follows `self.robot.set_led_colors` (`view.py:6`), and nothing in the fake writes the ring, starts an overlay or sets notes for a dance. The ladder tools exist as stubs: `self.music.stage` only stores the number and returns `beat: false` (`scripts/virtual-unit/tools/audio.py:189` to `209`), and no file in `scripts/virtual-unit` renders a step (no `stage` use in `view.py`, `hw.py` or `view3d.js`). Two more differences to fix on the fake side: the fake lacks the `bob` name and the extra dances (`tools/motion.py:156` to `159` answers "unavailable"), and its preference default for `overlays_enabled` is false in `tools/audio.py:215` but true in `tools/page_overlay.py:21` (the real default is on). To see the show in the playground the fake must run the host's `LadderDirector` against a scripted `music_feat` stream (the host tests already do this), or implement the unit-side modifier once the fix above lands; the button alone cannot show it, because the real button does not either.

## After patch SF51 (written, built, not landed yet): the unit runs the ladder for a hand-chosen dance

What changes on the unit (decision of 2026-11-18: a friend without Home gets the whole show):

| Entry point | Now runs |
|---|---|
| Screen Dance button, Dance tile, `self.robot.dance` happy / robot / panic / look_around, word reactions | a ladder session on a steady synthetic beat at the dance's own tempo (90, 120, 140 and 80 BPM), 45 seconds of music, then the way down |
| `self.dance.session {name or bpm, seconds, max_stage}` (new tool) | the same session on purpose, with the length and the highest step chosen |
| `self.robot.stop_dance` | also ends a session (eyes ahead, head level, ring dark, overlays and notes cleared) |
| the gestures (bow, nod_yes, shake_no, data dances) and a muted or full-quiet unit | the keyframe dance as before |

A session shows, by step: 1 eyes only; 2 nod, ring breathes mint and gold (10 to 18 percent of full), one music note, a face every 16 beats; 3 sway, ring chases (18 to 30 percent), two notes, disco ball (light); 4 full dance, the gold swell on the beat, three notes, disco ball (normal) and a confetti burst on entering the step and every 32 beats; then 3, 2, 1 down, the back layer cleared below the sway. The faces come from the same lists as the host's director and never repeat the last two. The unit paints the nod and sway ring itself while a session runs or when no host is connected (when a host runs the show it paints them). The movement limiter still caps the step (USB: no full dance), and overlays that are off in the unit's settings, or a privacy look or a ringing timer, simply do not draw.

Memory: about 9 KB of flash, a state struct under 120 bytes, one one-second `esp_timer`; no task and no internal block while idle. The overlay and decor sprites are the ones the unit already has (`disco`, `confetti`, the notes decorator); nothing new is loaded.

Pure core and test: `mdl_synth_*`, `mdl_show_for_step`, `mdl_face_next`, `mdl_ring_breath`, `mdl_ring_chase` in `maipai_dance_ladder_core.h`, host test `dance_synth_test.c` (the sequence 1, 2, 3, 4, 3, 2, 1, 0 on a synthetic beat, the dwell table, the show rules, faces, ring bounds under the 50 percent cap).

### Step 4 lasts one down-dwell longer than the ladder doc says (the playground's finding)

The core is right and the doc is loose: `mdl_step` starts the way down at the end of the peak dwell (24 beats, 12 s at 120 BPM) by setting `down`; the stage then stays at 4 for one down-dwell (4 beats, 2 s at 120 BPM) before it drops to 3, so the full dance is on screen about 14 s at 120 BPM (up to 16 s at 80 BPM) and the host mirror `dance_ladder.py` does the same (a shared test feeds both). The doc's "12 s" should read "12 s of peak plus one down dwell"; the core is not changed (the host mirror and its vectors depend on it).

### For the host (app track)

A paired host may still run its own director through `self.music.stage`. Its "little dance" plan calls `self.robot.dance` three times in a row (happy, robot, happy): each call now starts a 45 second session, so the last one wins; the host should call `self.dance.session` once (or `self.music.stage` as for music) instead. `bob` is accepted by the unit (the nod on a steady beat) and missing from the host's built-in dance list.
