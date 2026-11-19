# Games visual budget: what the unit can afford

Playground track, 2026-11-18, recalibrated 2026-11-19 with the box times the bench measured on the unit (a flat 100 by 100 box draws and flushes in 8.49 ms, so a full 320 by 240 redraw is about 65 ms, not the 30 ms this page first assumed; the earlier verdicts were written on that wrong number and are replaced here). Everything here is measured or marked as an assumption; nothing is guessed silently. The renderer picture alone proves nothing about fit, so this page comes before any art direction. Method scripts: `scripts/virtual-unit/games_cost.py` (frame cost), the `technique`, `objcount` and `diffbegin` commands of `scripts/fw-face-render/grid_render.cc`, and the unit's own compiler on the unit's own flags for flash.

## 1. The budget

| Resource | Gate | b68 bench (reported by the firmware track) | Headroom | Source |
|---|---|---|---|---|
| Internal RAM free, median | at least 40,000 B | 86,000 B | 46,000 B | `docs/dev/gate-numbers.md`, bench b68 |
| Internal RAM free, lowest seen | at least 24,000 B | 39,800 B | 15,800 B | same |
| Largest free internal block | at least 24,000 B median, 16,000 B lowest | 38,900 B | 14,900 B | same |
| PSRAM free | above 6,000,000 B | about 7.8 MB (baseline of `schema/memory-budget.json`) | about 1.8 MB | memory model |
| A full 320 by 240 redraw (draw and flush) | a one-off at screen entry only, at most 100 ms; never during play or motion (section 4) | about 65 ms: a flat 100 by 100 box takes 8.49 ms and the display flush runs about 2.4 MB/s | | bench 2026-11-19, `self.game.bench_box` |
| Face refresh, 3,200 px | at most 8 ms (3 to 7 measured) | | | same |
| Game tick gap (Four in a Row) | worst gap at most 60 ms, median at most 40 ms | worst 81 ms and median 40 to 44 ms at look 0, the plain look (spikes to 92 ms seen): **the plain game already fails the worst-gap rule** | -21 ms | bench 2026-11-19 |
| Flash for assets | | lean and nofont images free 1.29 to 1.99 MB; the installed-set pool is 382 sectors of 4 KB (1.53 MB) shared by every kind | | `docs/plan/installed-set.md`, firmware track |

What decides the RAM numbers (read from the b68 build, `sdkconfig`): LVGL allocates with the C library's malloc; `CONFIG_SPIRAM_MALLOC_ALWAYSINTERNAL` is 256, so every allocation of 256 bytes or less goes to internal RAM. An LVGL object (48 bytes measured with the unit's compiler: `sizeof(lv_obj_t)`, a label 108) and its styles are all that size, so **every LVGL object of a game screen is internal RAM**, the scarce kind. Big buffers (the game's state in the grid pattern, pictures) go to PSRAM. Drawing is software only (`LV_USE_DRAW_SW`, no assembler blends: `LV_USE_DRAW_SW_ASM` is off), gradients and shadows are enabled (`LV_DRAW_SW_COMPLEX`), and the shadow cache is **0** (`LV_DRAW_SW_SHADOW_CACHE_SIZE`): a shadow is recomputed on every redraw of the area it touches.

The cost of a redraw is the pixels of the dirty area: the draw time of those pixels plus their flush, measured on the unit as 0.85 ms per 1,000 pixels of a flat box (8.49 ms for 10,000; 65 ms for the whole 76,800). A static decoration costs nothing per frame while it stays outside the dirty rectangles; it costs a full draw when it is under something that moves.

## 2. Visual techniques

A 100 by 100 pixel box drawn and flushed on the unit (`self.game.bench_box`, 2026-11-19; the bench result). The second column is the measured time in milliseconds; the third is the cost against a flat box. Eight techniques are measured; the others are an **estimate**: the host renderer's ratio against flat (`technique NAME N`, best of three runs) times the measured 8.49 ms. A host ratio is not a measurement, so those rows say so.

| Technique | LVGL objects | Unit ms, 100 by 100 box | Against flat | Source | Verdict |
|---|---:|---:|---:|---|---|
| Flat rectangle | 1 | 8.49 | 1.00 | measured | fits as a moving part at 10,000 px or less |
| Rounded corners (radius 14) | 1 | 9.08 | 1.07 | measured | fits |
| Circle | 1 | 9.88 | 1.16 | measured | fits |
| Border (3 px) | 1 | 11.0 | 1.3 | estimate | fits |
| Outline (4 px, amber) | 1 | 10.1 | 1.19 | measured | fits |
| Vertical gradient | 1 | 9.32 | 1.10 | measured | fits: a backdrop is drawn once, at entry; inside a dirty rectangle it costs a flat fill |
| Highlight strip (20 percent white) | 2 | 11.0 | 1.3 | estimate | fits |
| Alpha 50 percent fill | 1 | 9.80 | 1.15 | measured | fits, at most 3 per dirty area |
| Soft shadow, blur 6 | 1 | 13.2 | 1.55 | measured | static and drawn once only, at most 3 on a screen, never under anything that moves |
| Soft shadow, blur 14 | 1 | 20.9 | 2.46 | measured | only tiny (60 by 60 px at most), static, drawn once; never in a motion frame |
| 8 particles (rectangles in one callback) | 0 | about 12 for 10,000 px; a particle is 50 px | 1.4 | estimate | fits as tiny dirty rectangles (one per piece), never as a band |
| 24 particles (rectangles in one callback) | 0 | about 18 for 10,000 px | 2.1 | estimate | fits only as tiny dirty rectangles, about 100 px each |
| Text 20 px | 2 | 10.2 | 1.2 | estimate | fits |
| Text scaled 2x (card rank, a pop) | 2 | 23.8 | 2.8 | estimate | one-off only (an event frame), one at a time |
| Rotated tile (30 degrees) | 1 | 34 | 4.0 | estimate | fits only small (40 by 40 px at most, about 5 ms) and for 200 ms |
| Squash and stretch (scale x 300, y 200) | 1 | 44 | 5.2 | estimate | fits only small (40 by 40 px at most, about 7 ms) and for 200 ms |
| Per-game bitmaps |  |  |  | flash and RAM: 8 KB for a 64 by 64 picture at 16 bits | does not fit as per-game assets; fits with a limit from the shared bank (decision 17): 20 shared parts is 160 KB, 10 percent of the 1.53 MB pool |

Rules that fall out of it:

1. **Count objects, not only pixels.** Each object is about 110 bytes of internal RAM with its styles (assumption: 48 bytes measured plus an assumed 60 for styles) and a label about 200. The headroom in the worst case is 15,800 bytes for the whole unit, so a game screen should stay under 2,000 bytes: about 15 objects. The board games already do this with one object and a draw callback (3 objects with the root and the drag bar).
2. **Move only what moves.** A full-board invalidation every tick flushes 76,800 pixels (about 65 ms) before any drawing: that is two whole ticks. Every animated game must invalidate the dirty rectangles (SF78 pattern).
3. **Decorate the static parts, once.** Shadows, gradients and highlights belong to the board, the tiles and the background, drawn when the screen appears, and never to something that moves. A blur 14 shadow is 20.9 ms for a 100 by 100 box: tiny and static only.
4. **No per-game bitmaps.** A shared bank of small parts (a disc, a card corner, a pip, a spark) is the only picture cost, and each part is paid once for all games.

## 3. Cost per game

Frame cost from the run of each game in `games_cost.py` (a disc falling, two cards flipping, a game played by a fixed policy): the pixels that change from one frame to the next, and the pixels of the 16 by 16 tiles that hold a change (the flush of several small dirty rectangles; the one-rectangle column is the flush of a single rectangle round everything). The ms columns use the unit's measured 0.849 ms per 1,000 pixels of a flat box, draw and flush together (a full screen is 65 ms); a shadow or alpha part costs its multiple from section 2 on top.

| Game | Frames | Pixels changed per frame | Tiles flushed per frame (px) | Flush ms (mean) | Flush ms (worst frame) | One rectangle, ms (mean) | The game's own dirty rectangles, ms (mean / worst) | Pixels changed outside them |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Four in a Row (a disc falls) | 48 | 629 | 2,181 | 1.9 | 3.0 | 0.9 | none yet | - |
| Match (two cards flip) | 58 | 398 | 1,231 | 1.0 | 4.6 | 1.2 | none yet | - |
| Hangman (a letter) | 20 | 128 | 640 | 0.5 | 3.0 | 1.2 | none yet | - |
| Mine Finder (a reveal) | 20 | 1,107 | 2,073 | 1.8 | 17.2 | 1.4 | none yet | - |
| Snake (it moves) | 100 | 54 | 143 | 0.1 | 3.5 | 0.1 | none yet | - |
| 2048 (two swipes) | 28 | 449 | 1,188 | 1.0 | 7.2 | 1.1 | none yet | - |
| Higher or Lower (a turn) | 4 | 27,999 | 37,184 | 31.6 | 56.9 | 34.9 | none yet | - |
| Reversi (a game) | 61 | 3,014 | 11,272 | 9.6 | 56.7 | 34.8 | none yet | - |
| Battleship-lite (shots) | 13 | 4,916 | 7,345 | 6.2 | 53.5 | 19.3 | none yet | - |
| Pong (a rally) | 401 | 329 | 2,975 | 2.5 | 62.8 | 13.2 | 0.8 / 1.1 | 0 |
| Balance (a lean) | 901 | 125 | 481 | 0.4 | 51.3 | 0.5 | 1.1 / 28.7 | 0 |
| Maze (a roll) | 438 | 242 | 883 | 0.7 | 56.3 | 1.2 | 0.4 / 4.8 | 0 |
| Game over, today's (won) | 60 | 82 | 435 | 0.4 | 3.9 | 0.3 | none yet | - |
| Game over, new look (won, confetti) | 60 | 1,493 | 7,530 | 6.4 | 10.0 | 11.3 | 4.3 / 11.2 | 0 |
| Game over, new look (lost, rain) | 60 | 419 | 2,218 | 1.9 | 4.8 | 2.0 | 3.3 / 11.0 | 0 |
| Game over, new look (draw) | 60 | 438 | 1,702 | 1.4 | 6.5 | 1.5 | 3.5 / 12.1 | 0 |
| Game over, new look (new best) | 60 | 1,521 | 8,256 | 7.0 | 11.1 | 11.3 | 5.2 / 12.9 | 0 |
| Game over, new look (time's up) | 60 | 300 | 1,442 | 1.2 | 4.3 | 1.5 | 3.5 / 10.9 | 0 |
| Flappy-style flyer (flying) | 601 | 1,417 | 11,552 | 9.8 | 62.2 | 36.2 | 4.8 / 8.5 | 0 |

The first frame of a run is the reference, so a game's start screen is not in the means; the worst-frame column shows the largest single change (a whole-board shake, a pop, a first draw). A run is judged by two rules (section 4): a stream of frames (animation, Pong, the flyer, Balance, Maze, the game-over motion) by its mean and worst frame, an event (a turn, a move, a shot) by its one frame.

One table, per game. Flash is the measured size of the code and constants (text and read-only data, `xtensa-esp32s3-elf-size`) of the game's own core and screen compiled with the unit's flags from the b68 bench build (`maipai_*` units for the new games); for the six grid games the unit is one object file, so the figure is shared. State is `sizeof` of the game's struct on the chip. Objects are counted on the renderer (the top layer after the game screen is built; the new games' counts exclude the 3 objects of the grid root and board that the renderer keeps under them). Internal RAM is objects times 110 bytes (labels 200), an assumption flagged above.

| Game | Flash KB | State, bytes | LVGL objects | Internal RAM at peak, KB | Flush ms per frame (mean, tiles) | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Four in a Row, Match, Hangman, Mine Finder, Snake, 2048 (one unit, `maipai_grid.cc`) | 27.6 together (estimates 1.9 to 4.0 each in `schema/memory-budget.json`) | in PSRAM (grid pattern) | 3 each | 0.4 each | 0.1 to 1.9 | fits (a stream of small frames) |
| Data-pack games (Tic-Tac-Toe, Whack-a-Mole, Do It, Color Memory, Rock Paper Scissors, Dice and Coin, Magic 8 Ball) | 61.0 (the pack engine and the games unit, `maipai_games.cc`, shared) | 12,288 task (estimate) | per pack 10 to 20 (not counted here) | 2 to 4 (estimate) | not measured in the renderer | fits; measure on the bench |
| Question games (riddle, trivia, 20 Questions) | 26.1 (`maipai_qa_game.cc`) | | 2,400 B estimated | 2.4 | static screens | fits |
| Shared game-over screen | 0.6 (estimate) | | 15 (5 labels), or 5 with the new look (UX15d) | 2.1, or 0.3 | an event: one full-screen frame at entry (about 65 ms), then the motion at look 2 of 4.3 ms mean and 11.2 worst (section 4) | fits as an event; the new look meets the motion rule on the host (`docs/design/game-over-look.md`) |
| Dice Poker (UX18, then UX18b) | 2.2 (UX18b changes the screen only) | 16 | 36 (7 labels), 2 after UX18b | 4.6, 0.3 after UX18b | not measured (static turns) | fits after UX18b (one draw callback, 2 objects with the root); fits with a limit before it (36 objects is 30 percent of the worst-case headroom) |
| Higher or Lower (UX21) | 2.5 | 64 | 15 (8 labels) | 2.4 | 31.6 per turn (four frames, worst 56.9: a turn is an event, not a stream) | fits as an event (one slow frame per tap, under 100 ms) |
| Reversi (UX22) | 2.2 | 76 | 5 (3 labels) | 0.8 | 9.6 mean, worst 56.7 (one frame per move) | fits as an event (the search is 262 nodes at most per move, measured on the host) |
| Battleship-lite (UX23) | 1.7 | 92 | 5 (3 labels) | 0.8 | 6.2 mean, worst 53.5 (one frame per shot) | fits as an event |
| Balance (UX27) | 2.5 | 68 | 2 with the root, 3 with the grabber | 0.4 | 1.1 mean with its own dirty rectangles (worst frame 28.7 ms: the plate's one-pixel shrink, once in two seconds) | fits the stream rule (mean 1.1 ms, 0 changed pixels outside its rectangles over 900 frames); the shrink is one event frame |
| Maze (UX28) | 2.7 | 92 | 2 with the root, 3 with the grabber | 0.4 | 0.4 mean (worst 4.8) | fits (0 outside its rectangles over 700 frames) |
| Pong (UX24) | 1.7 | 36 | 6 (4 labels) | 1.0 | 2.5 by tiles; 0.8 with its own dirty rectangles (worst 1.1) | fits with its dirty rectangles (pg_dirty, checked: 0 pixels outside); invalidating the whole court is 65 ms a tick |
| Flappy-style flyer (UX25) | 1.3 | 48 | 3 (1 label) | 0.4 | 4.8 with its own dirty rectangles (worst 8.5); 11.9 by tiles before the revision | meets the stream rule since the 2026-11-19 revision (mean 4.8 ms against 5.5, worst 8.5 against 13.6; 0 pixels outside the rectangles over 600 frames): the strips of a pipe skip the rows of its gap, the pipes are 160 px apart (two on the glass at most), the score rectangle is 120 px wide; a full invalidation is 65 ms a tick |

Totals: the six new unproven games add 11.6 KB of flash (0.9 percent of the 1.29 MB the lean images free) and at most 5 KB of internal RAM when one is on screen (never two at once: one game runs at a time on the game task). Flash is not the constraint; **internal RAM and the flush per frame are**.

## 4. What a richer look can spend

The rules, in the numbers of the 2026-11-19 bench (0.85 ms per 1,000 pixels, draw and flush, a flat box):

1. **Objects:** at most about 15 LVGL objects (2,000 bytes internal) plus the one draw callback.
2. **A motion frame** (a frame of an animation or of a game that ticks): the dirty area of one frame at most **16,000 px** worst (about 13.6 ms) and **6,500 px** on average over the motion (about 5.5 ms). The flat box time is multiplied by the technique's factor in section 2.
3. **An event frame** (one frame after a tap: a turn, a move, a shot, a pressed button): at most about 60 ms once per tap.
4. **A one-off full-screen frame** (the screen appears: a game over, a menu, a pack's first state): up to **100 ms** (65 ms of flush and the draw of a gradient backdrop), allowed **only at screen entry, never during play and never during a motion**. It is the one place a full-screen backdrop gradient is drawn.
5. **Shadows:** blur 6 only static, drawn once (in the entry frame), at most 3 on a screen, never under anything that moves; blur 14 only tiny (60 by 60 px at most) and static. Alpha at most 3 fills per dirty area.
6. **Particles and sparkles:** tiny dirty rectangles, one per piece (about 100 px each), never a band that covers the area they cross. Slow parts (rain, a hand, a glint) move in 60 ms steps.
7. **Scale and rotation** only on small tiles (40 by 40 px at most) for 200 ms; every picture from the shared bank, none per game.
8. **The baseline is already over the gap rule:** Four in a Row at its plain look has a worst tick gap of 81 ms against the limit of 60 ms (median 40 to 44), so a game that ticks has nothing to spare. A richer look on a ticking game waits for a faster flush (the firmware track is investigating the SPI clock and DMA), and is a patch that activates only when a measured flush ceiling allows it (`docs/design/games-look.md`).

The old Four in a Row and Match flush 1 to 2 ms a frame; a screen with no tick of its own (a game over, a menu) can spend a motion budget of about 6,500 px a frame for as long as its motion plays, and nothing after.

## 4b. The revisions the budget asked for (done, 2026-11-18)

- **Dice Poker** (patch UX18b): the whole screen in one draw callback: 36 LVGL objects (4.6 KB of internal RAM) became 2 with the root (about 0.3 KB); the frames are the same to the pixel but for a one pixel shift of the button words.
- **Pong** (UX24) and the **flyer** (UX25): each core has `pg_dirty` and `fl_dirty`, the rectangles that differ between two states, and each screen an `invalidate_dirty` that invalidates only those. The renderer checks the claim pixel by pixel: over 400 and 600 frames **0 changed pixels lay outside the rectangles**. Cost per frame with them (draw and flush at 0.85 ms per 1,000 pixels): Pong 0.8 ms mean and 1.1 ms worst (about 1,000 pixels a tick, worst 1,300), the flyer 4.8 ms mean and 8.5 ms worst (the pipes' edge columns only, and only the rows a pipe fills: a flat pipe that shifts 2.5 pixels changes only where it starts and ends; 5,700 pixels a tick, worst 10,000; the first version, with full-height columns, 130 px between pipes and a full-width score line, was 8.8 and 18.1 ms and failed the rule). Without them both would redraw the whole court or sky, 65 ms a tick. Both meet the motion rule (mean 5.5 ms, worst 13.6 ms allowed).
- The four-in-a-row richer look (UX26) is the bench prototype: `docs/plan/games-richer-look-bench.md`.

## 5. What the bench measured, and what is still open

Measured on the unit (2026-11-19): the box times in section 2 (the K calibration is now eight points, not one), and the Four in a Row tick gaps (81 ms worst at the plain look, about 170 and 200 at the richer looks 1 and 2: the richer look failed). Still open:

1. Internal heap before and during each game screen (`heap_info`): the object and style bytes here are sizeof plus an assumed 60 bytes of styles.
2. The data-pack games' frame cost, which the grid renderer does not draw.
3. The new games' real ticks: the firmware track wires them; the budget above only says what dirty area they may flush.
4. The game-over look's motion frames on the unit (`self.game.bench_over`, `docs/design/game-over-look.md`).
5. The flush itself: if the SPI clock and DMA work makes it faster, K shrinks and every number in sections 2 to 4 is re-derived from the new `bench_box` times (change `UNIT_BOX_US` in `games_cost.py`).
