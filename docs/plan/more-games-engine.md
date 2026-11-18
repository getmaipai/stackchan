# More games: what the unit's engine can and cannot do (firmware track)

Firmware track, 2026-11-18. Companion to the playground's `docs/plan/more-games.md` (the games list and screens); this file holds the engine capacity, the gaps for the twelve requested games, the tool shapes and the pack and memory rules. Numbers are read from the code in the b49 tree (**read**), from the budget file (**declared**) or are **estimates** to measure on the unit.

## 1. The engine today (read from `maipai_games_core.h`)

A game is a data pack run by a small declarative player: states, touch regions, drawn shapes, texts, transitions with guards, actions. No scripts, no code in a pack.

| Limit | Value | Meaning for new games |
|---|---:|---|
| Pack ceiling | 16,384 B (signature included) | the 7 shipped packs are 1,058 to 3,968 B (read) |
| States | 16 | |
| Touch regions | 12 | a board with more than 12 tappable cells does not fit |
| Shapes drawn | 64 | each is an LVGL object while the game runs |
| Texts | 32, 48 characters, English and Spanish | `%0` to `%7` print a counter |
| Transitions | 96, actions 255 | one event may run 64 steps at most (the step budget) |
| Counters | 8 (16-bit) | a counter per piece of state: a board does not fit in them |
| Board | one board of 9 cells (Tic-Tac-Toe), with its own AI (random, blocks wins, perfect) | the only board logic; nothing for 16, 42, 64 or 81 cells |
| Sequence | 32 steps (Color Memory) | |
| Timer per state | 80 ms to 30 s, random in a range, or the time in a counter | the fastest tick is 80 ms |
| Sounds | 5 tones, plus clips in groups of 4, played through the sound policy; ring light 6 colors; celebration (confetti, fireworks) | hooks exist |
| Inputs | tap, swipe left, swipe right, shake, pet (head touch strip), tilt (4 ways), "easy" (a too-hard shake) | see table below |
| Scores | top five per game in the unit's NVS; "lower is better" flag | |

Inputs, as seen by a pack:

| Input | Exposed to packs | Engine work needed |
|---|---|---|
| Tap on a region | yes (on touch, or on release for Bop-It style games) | none |
| Swipe left or right | yes | none |
| Swipe up or down | **no** (the bottom edge swipe stops a game, the top edge is reserved) | new events inside the play area; 2048 and Snake want them |
| Long press | **no** | new event (Mine Finder flag) |
| Drag, continuous touch position | **no** (the player sees taps and swipes on release) | new input path; the Paddle game wants it |
| Shake, pet, tilt in four directions | yes | none |
| Analog tilt angle | **no** (tilt is four discrete events) | new input, for a rolling-ball maze |

Edge rule: regions stay inside x 20 to 300 and y 28 to 224 (the unit reserves the edges for its swipes); buttons are at least 44 px high.

Rules that hold for every game (read from `maipai_games.cc`): a game never starts in full quiet, during an update, or while the lock is on; the sound policy and mute decide every tone; the ring light is skipped in full quiet; **no game code moves the head** (the file has no motion call) and none may be added.

## 2. Memory and CPU

| Item | Cost | Source |
|---|---|---|
| Nothing exists while no game runs (no task, timer, object or PSRAM) | 0 | header of `maipai_games.h` (read) |
| A running game: the `Game` struct (pack, run state, 64 object pointers and points) | about 1.8 KB, in PSRAM | estimate from the struct, `calloc` in PSRAM (read) |
| LVGL objects: at most 64 shapes plus the root | `screen.game` declared 4,000 B internal | placeholder in `schema/memory-budget.json`: to measure with two `self.bench.heap_info` calls |
| Pack download or write (`task.game_pack`) | 12,288 B internal, 6,144 B largest block, transient | estimate in the budget file |
| Tone and clip buffers | PSRAM, allocated on first use | read |
| Frame budget | the game timer runs about every 30 ms (a stop request ends a game "within 30 ms", read); the display strip rate is measured by `self.game.bench_gaps` (p50, p99, worst) | no numbers yet: run it during a game |

**AI opponent budget (estimate, to measure):** a search must never stall the face or the touch path. Run it in slices on the game timer, at most 5 ms per 30 ms tick, with a node counter as the limit (for example 20,000 nodes a slice), and show the unit "thinking" with a face. A C search with bit boards on the S3 at 240 MHz reaches an estimated 5 to 15 million simple nodes a second, so depth 6 alpha-beta on Four in a Row (about 117,000 nodes without pruning) is tens of milliseconds, sliced over a few ticks. These are estimates; the first bench run decides the depth per level.

## 3. The twelve games against the engine

All twelve fail on the board size, the region count or an input. The shipped player is the right engine for button-style games and the wrong one for board games.

| Game | Fits today | Gap | Estimated pack data |
|---|---|---|---|
| Four in a Row (7 by 6) | no: 42 cells, one 9-cell board | grid board, drop rule, win check, AI depth 4 to 6; 7 column regions would fit | about 1 KB |
| Reversi (8 by 8) | no: 64 cells and 64 regions | grid board, flip rule, legal-move marks, AI depth 3 to 4 | about 1 KB |
| Checkers | no: 32 squares, selection then move, forced jumps | grid board, piece selection state, jump rules, AI depth 4 to 6 | about 1.5 KB |
| Dots and Boxes (5 by 5 boxes) | no: 60 edges to tap | grid with edge hit-testing, box capture, greedy AI (take boxes, avoid the third side) | about 1 KB |
| Memory Match (4 by 4) | no: 16 cards, regions are 12 at most; a 3 by 4 deck (12 cards) needs 12 regions and per-card state that 8 counters cannot hold | a cell array, flip and compare rule | about 1 KB |
| 2048-style slider | no | swipe up and down; a 4 by 4 value array; slide and merge rule; a tile drawn from a value | about 1 KB |
| Mine Finder (8 by 8) | no | cell array, long press (flag), flood reveal | about 1 KB |
| Sudoku (9 by 9) | no: 81 cells; cells are about 21 px, under the 44 px button rule | cell array, number pad, puzzle table (81 bytes a puzzle: 100 puzzles are 8 KB), a zoom or an exception to the size rule | 8 KB for 100 puzzles |
| Snake | no: body longer than 32, tick every 80 ms at the fastest | grid tick, a body ring buffer, direction from swipe up and down or from tilt (tilt exists) | about 1 KB |
| Paddle (pong or breakout) | no | a drag input, ball physics per tick (30 ms), brick array | about 1 KB |
| Tilt Maze | partly: tilt events exist; a maze grid does not | maze cells (15 by 10 bytes per maze), tilt-to-step rule; a rolling ball needs analog tilt | 150 B per maze |
| Hangman | no: 26 letters, regions are 12 at most | a letter keyboard (two taps or a small keyboard primitive), a word list (about 10 bytes a word, 32 texts today) | 2 KB for 200 words |

## 4. The proposal: a grid engine beside the data-pack player

Do not stretch the declarative player: counters and 12 regions cannot hold a board. Add a second pack kind, **grid game**, played by a small native engine:

- The pack names a **rule set** by id (connect-four, reversi, checkers, dots-and-boxes, match, slider, mines, sudoku, snake, maze, hangman, paddle) and carries its **theme and data**: colors, texts in English and Spanish, sounds, puzzle and word and maze tables, the AI level names. A pack is still data; the rules are small pure C cores with host tests, signed with the image like the rest of the firmware.
- The engine owns a cell array (up to 100 cells, one byte each), computes the tapped cell from geometry (so no region limit), draws a cell from its value through a glyph and color table (one LVGL object per cell: up to about 100 objects, about 16 KB in the LVGL pool, estimate; cheaper: one canvas or a drawn strip, to decide at measurement time), and runs the rule set's move and win logic and its sliced AI.
- Cost (estimate): 2 to 4 KB of app flash per rule set, so about 30 to 50 KB for twelve (the app image has about 395 KB under the 20 percent rule); no RAM while no game runs; a running game adds the cell array (100 B), the object pool and the search state (a few KB, PSRAM).
- New inputs: swipe up and down, long press, drag (each its own small change in the touch path, tested in `maipai_touch_core.h`'s host test), analog tilt only if the maze wants a ball.
- The memory gate applies per rule set: a row in `schema/memory-budget.json` per game with its internal bytes, PSRAM bytes and largest block, filled by a measurement, in the same commit as the patch (decision 15).

## 5. Tool shapes (for the app track)

Exist today (read): `self.game.list {}` answers `{ok, playing, games:[{id, title, lower_is_better, scores}]}`; `self.game.start {name, source, token}` starts a built-in game by id (`memory`, `whack`, `tictactoe`, `bopit`, `rps`, `eightball`, `dice`) and refuses in full quiet, during an update and while locked; `self.game.stop {}` answers `{ok, was}`; `self.game.scores {name}` answers the top five. The tools are `self.game.*` (singular), not `self.games.*`.

Gaps to build:

- `self.game.start` and `self.game.list` also know **installed packs** (today the start table is the built-in list): the id of an installed game is its pack name (40 characters at most, the pack core's limit), and `list` marks each entry `builtin` or `installed`.
- **Random lives on the host**: the host picks the name from its history and calls `self.game.start {name}`. The unit never picks, and has no `random` value. A host that asks for a game by voice ("play a game") sends one start call; "play X" maps X to an id on the host from the list.
- `self.game.list` answers the best score per game (it already does, up to five).

## 6. Packs as installed-set assets

- A game pack is one installed-set item of the `game` kind: a signed asset with the 128-byte header, a slot in the assets partition, a size at most the engine ceiling (16 KB today; the grid kind needs its own ceiling, 24 KB with a puzzle table is enough), loaded on demand and read in place from flash. **Never copy a pack into PSRAM wholesale** (the PSRAM finding of the audit): only the running game's working set lives in PSRAM.
- **Capacity:** the assets partition has 1,762,694 bytes free after SF47 (measured), plus 1,287,460 if the stock font is reclaimed (see `docs/plan/optimization.md`): at the 16 KB ceiling that is about 110 packs now and about 190 after the font; at the real 1 to 4 KB per pack, several hundred. The slot granularity of the installed-set design decides the exact count (read the slot size from `docs/plan/installed-set.md` before counting).
- **Memory cost per pack:** zero while installed (flash only), plus the running-game cost above while it plays; each pack states `internal`, `psram`, `largest_block` in the budget file with a status (measured or estimate), and the budget file changes with the pack.
- Signature: the pack format already allows a 64-byte Ed25519 signature; an installed pack from the catalog must carry one, a pack made at home is flagged as such on the games page.

## 7. What to build, in order

1. Measure: `self.game.bench_gaps` during Color Memory and Whack-a-mole (the frame numbers), two `heap_info` calls around a game (the real `screen.game` row).
2. Inputs: swipe up and down, long press (small, tested).
3. The grid engine with the cell array, geometry hit test, drawing and the sliced AI loop, and the first rule set: Four in a Row (shortest rules, a clear AI), then Memory Match, 2048, Hangman, Snake, Mine Finder, Reversi, Dots and Boxes, Checkers, Sudoku, Tilt Maze, Paddle (the last two need new inputs).
4. The installed-pack start path in `self.game.start` and `self.game.list`.

Each rule set is one SF patch with a host test and a budget row. Nothing here changes the quiet, mute, lock and limiter rules: a game that needs one of those exceptions is not built.

## 8. Accelerometer games (tilt maze, marble, steering, balance, hot potato, shake)

Added 2026-11-18 at the owner's request. **Read** means read from the b49 tree; **estimate** means to measure.

### 8.1 What the unit's motion sensor gives a game today

| Item | Value | Source |
|---|---|---|
| Sensor | BMI270 (accelerometer and gyroscope) on the controller. No magnetometer is read: the tree has no code for one | read (`hal_imu.cpp`, `drivers/bmi270`) |
| Accelerometer | 100 Hz output rate, range plus or minus 2 g, normal mode with 4-sample averaging | read |
| Gyroscope | 100 Hz, range plus or minus 2000 degrees a second; it is read by the driver but nothing feeds it to a feature | read |
| Task rhythm | the IMU task wakes every 20 ms; a fresh sample goes to the pickup detector, the movement limiter and the games (`maipai_games_imu_feed`), so a game sees up to 50 samples a second; shake, orientation and the stall of the main loop run every fifth pass (100 ms) | read |
| Calibration | none: no offset or scale is stored; the rest pose of a game's tilt is the pose the unit held for 0.8 s (`MGI_SETTLE_SAMPLES` 8 at the 100 ms tilt rate) | read |
| Filtering | tilt: one-pole low pass, alpha 0.6; orientation: alpha 0.5; both reject a total pull outside 0.8 to 1.2 g as "moving" | read |
| Orientation bands | which axis is down (six poses) with a 5-sample hold; the limiter maps them to upright, tilted, side, inverted, unknown (older than 2 s) | read (`maipai_orient_core.h`, `maipai_motion_limit_core.h`) |
| Shake and tilt for games | shake: sum of axis change over 100 ms above 9.0 m/s squared; a harder one is "easy" (no points); tilt: 0.38 g (about 22 degrees) in four directions, must return within 0.15 g to re-arm, no tilt for 700 ms after a shake | read |

**Exposed to packs today:** only the events (shake, easy, tilt left, right, forward, back, and pet). A pack never sees a number. A tilt maze that steps one cell per tilt event works now; a rolling marble, a steering wheel, a balance game and hot potato do not.

### 8.2 Engine work

1. **An IMU input kind: "motion frame".** The engine receives a filtered tilt vector at a fixed 30 ms tick (the game timer): roll and pitch in tenths of a degree (computed from the accelerometer, low pass alpha about 0.3), plus a shake energy and, optionally, the gyro rate on one axis for a "turn" game. It replaces no existing event. A rolling marble and a steering wheel read roll; balance reads pitch and roll; hot potato reads shake energy and "still". One small pure core (`maipai_games_tilt_core.h`) with a host test over recorded sample sequences; no allocation.
2. **Counters or a cell array cannot hold physics.** Marble roll, racing and flying need a position and velocity per tick: they belong to the rule sets of the grid engine in section 4 (a physics rule set with fixed-point positions), not to the declarative player.
3. **Orientation-aware screen rotation for held play.** Steering by holding the unit like a wheel turns the screen sideways. LVGL can rotate the display (a software rotation costs time and a full-frame buffer; a transform on the game's own root object is cheaper). Rotation only inside a game, locked to the pose at the start, restored when the game ends. Cost: to measure (the flush path is the tight one: strip rate is 44.7 fps on the face today).
4. **Calibration:** store no offsets; use the held rest pose at the start of every game ("hold it the way you like, then start"), which removes the need for a factory calibration.
5. **Cost (estimate):** the tilt core is under 1 KB of flash, a few floats of state, no task, no allocation; a physics rule set 2 to 3 KB of flash each; CPU per 30 ms tick under 0.2 ms; the display, not the logic, is the limit.

### 8.3 Safety rules for held games

| Rule | How |
|---|---|
| **Free-fall pause.** A drop pauses the game and the head holds | a free-fall detector: total pull under about 0.3 g for 100 ms or more (two samples at 50 Hz; at plus or minus 2 g the impact saturates, so the detector uses only the fall), then the game pauses with a "Dropped: tap to resume" screen, the ring light shows amber, and the game stops after 10 s. A new small core (`mff_*`) next to the pickup core, host-tested with falling and shaking sequences (a hard shake is not a fall: it alternates; a fall is sustained) |
| **Carried rule** | the head stays still as today (the limiter's carried flag): games never move the head, and this stays true |
| **Hold with both hands** | before a held-motion game starts the screen asks for two taps at once (two regions held for 0.5 s, so both hands are on the unit) or one tap on "I am holding it"; a person who sets the unit down gets the tabletop variant (a tilt maze runs on the table as step events) |
| **Session cap** | a held-motion game ends after 3 minutes without a person's tap and always after 10 minutes, with a rest screen (arm fatigue and drops); the cap is a constant in the core, never a setting a pack can raise |
| **Not startable when** | full quiet, update, lock (as now); battery under 20 percent and not charging; the servo temperature reading hot (SF48 telemetry, hot means 55 degrees and over: to confirm against the servo's data sheet); the limiter on a long unreliable cable is irrelevant because games never move the head |
| **No head, no torque** | a game never calls a motion function; the host test for each rule set checks the file has none |
| **Gentle** | no cue or sound louder than the sound policy allows; a shake game counts only the "gentle" band (the existing easy threshold) so the unit is not thrown about |

### 8.4 Head as a joystick: feasibility (research only, no test run)

**What the code allows (read):**
- The servo layer can switch torque per servo (`EnableTorque`), read torque state, read the position (`ReadPos`: a raw count, one count is 0.3125 degrees (read from the servo layer's angle mapping), valid range 0 to 4095, valid-checked) and bus telemetry (voltage, load 0 to 1000, current, temperature) with one `FeedBack` call, which SF48 uses already.
- **The head is already free at rest.** The servo layer has "auto release torque on rest" on (`_auto_torque_release_enabled = true`): after a move finishes it checks every 200 ms and turns torque off. So today a person can already turn the head by hand when it is idle; the stall guard and the limiter act only when the unit drives the servo.
- Reading the position with torque off works (a read is a bus read; it does not need torque).

**What the joystick needs:** hold torque off for the game, poll `ReadPos` of both servos at 20 to 30 Hz under the servo bus lock, map the angles to the game input with a dead zone, and never send a position command.

**Risks:**
1. **Gears and end stops.** A person can push the head past the soft limits; with torque off nothing resists. The gear train of the servo is not rated for back-driving force that this repo documents (to read in the servo's data sheet before any test; do not assume the maker's numbers). Mitigation: a hard soft-limit watch in the game (at 70 percent of the travel the game shows a warning; at 90 percent it ends the game and re-enables torque, which holds the head where it is: a hold, not a move), and the on-screen text "turn gently".
2. **Re-enabling torque at a pushed pose** makes the servo hold the angle it has at that moment: it commands its present position, so it does not jump (the unit already does this: `stop_motion_at_angle`). To verify on the unit before any game uses it.
3. **The limiter and the stall guard.** The stall guard watches load and current rises while a target is set; with no target (torque off) it does not run. The limiter's carried and quiet rules do not apply to a head the unit is not driving, but the carried rule must also end the game (a held unit makes the head swing).
4. **Overload:** a person pushing hard shows as load in the telemetry only while torque is on; with torque off the load reads near zero, so **there is no overload signal while free**. The only safety is the travel watch above and the speed of the angle change (a change faster than about 300 degrees a second is a shove: end the game).
5. **Bus time:** two reads every 30 ms is about 2 of every 30 ms on a shared bus, with the servo supply telemetry task of SF48 and the face's own pitch writes also using it; the games must use the same servo bus lock and a lower rate when the face is moving. To measure (the bench's `power_probe` reads both servos in one pass).
6. **Wear and trust:** the owner and a child will push it; a head that ends a game on a hard shove teaches the right push.

**Recommendation: do the test, as a read-only bench probe first; do not build the game yet.** The head is already free at rest, the position reading exists, and the feature costs nothing in flash or RAM while off. The risk is the push, not the code. The head joystick is worth building only if the test shows a clean, low-noise reading and the owner finds a gentle push natural; otherwise the head pads (the touch strip already gives "pet") and the IMU cover the same games.

**Test plan (silent bench test, with the owner's OK, nobody pushes hard):**
1. Bench tool `self.bench.head_read {seconds 1-30, hz 5-30}` (patch SF65, bench only; it ends at once and holds the head on a shove over 300 degrees a second or a turn over 20 degrees; the owner must be present): torque off for both servos, logs `ReadPos` and the load at the rate, returns min, max, noise (standard deviation at rest), the read rate achieved and the bus errors; torque back on at the end at the present angle; aborts and holds on any angle change faster than 300 degrees a second or past 70 percent of travel.
2. Rest: torque off, nobody touching, 10 s: noise and drift of the position (expected a few counts).
3. Gentle push by the owner within 30 percent of the travel, 10 s each axis: does the reading follow without steps; the latency of one read.
4. Re-enable torque after a pushed pose: the head must hold the pose, not jump (the one result that decides whether it is safe).
5. Bus load: the achieved read rate with the face moving, with `self.bench.power_probe` running at the same time.
6. Pass: noise under 3 counts, no jump on torque enable, reads at 20 Hz or better; fail on any jump or an error rate above 1 percent. Quiet rules apply: volume 0 and hard mute before the test; no motion command is sent in any step.

## 9. The engine as built so far (patch SF62, 2026-11-18): shapes for the virtual unit

Pure cores, compiled into the host test only (not yet in the image); the device layer (drawing, start tool, installed-pack ids) follows. Source: `maipai_grid_core.h`, `maipai_grid_c4_core.h`, `maipai_grid_mem_core.h` (in the firmware tree after replay); test: `host/tests/firmware/grid_core_test.c`.

- **Cells:** up to 100, one byte each, row-major (`row * cols + col`); 0 is empty or face down.
- **Geometry:** play area x 20 to 300, y 28 to 224 (the unit's reserved edges). `gr_layout(cols, rows, square)` gives the cell size and origin (a board that does not fit, or cells under 12 px, is refused); `gr_cell_at(x, y)` gives the cell or -1; `gr_col_at(x, y)` gives a column for a tap anywhere in the column's full height. Four in a Row uses 40 by 32 px cells (a column is 40 px wide); Memory 4 by 4 uses 49 px squares.
- **Results and cues (common):** `GR_PLAYING`, `GR_PERSON_WON`, `GR_UNIT_WON`, `GR_DRAW`; cues `tap`, `unit_move`, `match`, `miss`, `win`, `lose`, `draw`, `bad` (the device layer maps them to the five tones, the ring light and the celebration).
- **Four in a Row:** 7 by 6, row 0 on top, 1 the person, 2 the unit; a tap in a column drops a disc to the lowest empty cell; four in a line wins. The unit's move is a **sliced search**: `start(board, level, seed)` then `step(budget)` once per game tick until it says the move is ready. Levels: 0 random legal, 1 takes a win and blocks a loss, 2 four plies, 3 six plies. One root move per tick, each capped at 1,000 nodes (cut moves fall back to the evaluation).
- **Memory Match:** 12 or 16 cards in pairs, shuffled from a seed (a test or a replay gets the same deck); a cell byte holds the symbol (1 to 8) in the low 5 bits, bit 5 face up, bit 6 matched; a mismatch turns back after 900 ms (`tick(now)`); the score is the number of turns (lower is better).
- **Measured on a laptop (host test):** a search node costs about 194 ns; level 3 from an open position is about 6,800 nodes over 7 ticks, level 2 about 1,000 nodes, level 1 about 56. **Estimate for the unit:** 3 to 5 microseconds a node, so a 1,000-node tick is 3 to 5 ms (the plan's budget); to be measured on the unit with the bench's frame-gap tool before the levels are final.
- **Lint:** `host/tests/test_games_no_head_motion.py` fails when any patch adds a call to the head's motion, a servo or the torque in a game or grid file.
