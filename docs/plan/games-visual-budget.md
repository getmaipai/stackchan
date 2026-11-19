# Games visual budget: what the unit can afford

Playground track, 2026-11-18. Everything here is measured or marked as an assumption; nothing is guessed silently. The renderer picture alone proves nothing about fit, so this page comes before any art direction. Method scripts: `scripts/virtual-unit/games_cost.py` (frame cost), the `technique`, `objcount` and `diffbegin` commands of `scripts/fw-face-render/grid_render.cc`, and the unit's own compiler on the unit's own flags for flash.

## 1. The budget

| Resource | Gate | b68 bench (reported by the firmware track) | Headroom | Source |
|---|---|---|---|---|
| Internal RAM free, median | at least 40,000 B | 86,000 B | 46,000 B | `docs/dev/gate-numbers.md`, bench b68 |
| Internal RAM free, lowest seen | at least 24,000 B | 39,800 B | 15,800 B | same |
| Largest free internal block | at least 24,000 B median, 16,000 B lowest | 38,900 B | 14,900 B | same |
| PSRAM free | above 6,000,000 B | about 7.8 MB (baseline of `schema/memory-budget.json`) | about 1.8 MB | memory model |
| One full-screen flush | at most 40 ms (26 to 35 measured) | 30 ms taken | | `docs/dev/gate-numbers.md` |
| Face refresh, 3,200 px | at most 8 ms (3 to 7 measured) | | | same |
| Game tick with SF78 | target 30 ms | 40 ms (firmware track's bench recorder) | -10 ms | firmware track |
| Flash for assets | | lean and nofont images free 1.29 to 1.99 MB; the installed-set pool is 382 sectors of 4 KB (1.53 MB) shared by every kind | | `docs/plan/installed-set.md`, firmware track |

What decides the RAM numbers (read from the b68 build, `sdkconfig`): LVGL allocates with the C library's malloc; `CONFIG_SPIRAM_MALLOC_ALWAYSINTERNAL` is 256, so every allocation of 256 bytes or less goes to internal RAM. An LVGL object (48 bytes measured with the unit's compiler: `sizeof(lv_obj_t)`, a label 108) and its styles are all that size, so **every LVGL object of a game screen is internal RAM**, the scarce kind. Big buffers (the game's state in the grid pattern, pictures) go to PSRAM. Drawing is software only (`LV_USE_DRAW_SW`, no assembler blends: `LV_USE_DRAW_SW_ASM` is off), gradients and shadows are enabled (`LV_DRAW_SW_COMPLEX`), and the shadow cache is **0** (`LV_DRAW_SW_SHADOW_CACHE_SIZE`): a shadow is recomputed on every redraw of the area it touches.

The cost of a redraw is the pixels of the dirty area: the draw time of those pixels plus their flush (0.39 ms per 1,000 pixels at 30 ms for 76,800). A static decoration costs nothing per frame while it stays outside the dirty rectangles; it costs a full draw when it is under something that moves.

## 2. Visual techniques

A 100 by 100 pixel box, redrawn 400 times in dirty-area mode on the host renderer (`technique NAME N`; best of three runs). Host microseconds are a **relative** measure: the first column is the cost against a flat rectangle. The chip estimate multiplies by K = 200 to 600, calibrated on the one unit number that has draw time in it (a face refresh of about 3,200 pixels measures 3 to 7 ms on the unit, 0.01 ms on the host; the flush share is 1.3 ms). That calibration is an **assumption** until the bench draws the same box.

| Technique | LVGL objects | Draw cost against flat | Pixels flushed (box 10,000) | Chip draw + flush estimate, ms | Verdict |
|---|---:|---:|---:|---|---|
| Flat rectangle | 1 | 1.0 | 10,000 | 6.5 to 11.7 | fits |
| Rounded corners (radius 14) | 1 | 1.1 | 10,000 | 6.7 to 12.4 | fits |
| Circle | 1 | 1.3 | 10,000 | 7.3 to 14.4 | fits |
| Border (3 px) | 1 | 1.3 | 10,000 | 7.3 to 14.4 | fits |
| Outline (4 px, amber) | 1 | 1.5 | 11,664 | 8.6 to 16.6 | fits |
| Vertical gradient | 1 | 1.2 | 10,000 | 7.1 to 13.5 | fits |
| Highlight strip (a second object, 20 percent white) | 2 | 1.3 | 10,000 | 7.4 to 14.4 | fits |
| Alpha 50 percent fill | 1 | 1.5 | 10,000 | 7.9 to 15.9 | fits with a limit: 3 per dirty area |
| Soft shadow, blur 6 | 1 | 2.2 | 12,544 | 10.5 to 21.7 | fits with a limit: static things only, 6 on screen |
| Soft shadow, blur 14 | 1 | 2.8 | 15,876 | 13.4 to 27.8 | does not fit anything that moves; static only, 3 on screen |
| 8 particles (one object each) | 9 | 1.4 | 10,000 | 7.6 to 14.5 | fits with a limit: pool them, 600 ms, about 1 KB internal while they live |
| 24 particles (one object each) | 25 | 2.1 | 10,000 | 9.1 to 19.5 | does not fit as objects (about 2.8 KB internal); one draw callback only |
| Text 20 px | 2 | 1.2 | 10,000 | 7.0 to 13.0 | fits |
| Text scaled 2x (card rank, a pop) | 2 | 2.8 | 10,000 | 10.9 to 24.9 | fits with a limit: one at a time |
| Rotated tile (30 degrees) | 1 | 4.0 | 11,236 | 14.4 to 34.4 | fits only small (40 by 40 px at most) and for 200 ms |
| Squash and stretch (scale x 300, y 200) | 1 | 5.2 | 11,392 | 17.4 to 43.4 | fits only small (40 by 40 px at most) and for 200 ms |
| Per-game bitmaps | | | | flash and RAM per picture: 8 KB for a 64 by 64 picture at 16 bits | does not fit as per-game assets; fits with a limit from the shared bank (decision 17): 20 shared parts is 160 KB, 10 percent of the 1.53 MB pool |

Rules that fall out of it:

1. **Count objects, not only pixels.** Each object is about 110 bytes of internal RAM with its styles (assumption: 48 bytes measured plus an assumed 60 for styles) and a label about 200. The headroom in the worst case is 15,800 bytes for the whole unit, so a game screen should stay under 2,000 bytes: about 15 objects. The board games already do this with one object and a draw callback (3 objects with the root and the drag bar).
2. **Move only what moves.** A full-board invalidation every tick flushes 76,800 pixels (30 ms) before any drawing: that alone is the whole frame budget. Every animated game must invalidate the dirty rectangles (SF78 pattern).
3. **Decorate the static parts.** Shadows, gradients and highlights belong to the board, the tiles and the background, drawn when the region is redrawn anyway, and never to something that moves every frame.
4. **No per-game bitmaps.** A shared bank of small parts (a disc, a card corner, a pip, a spark) is the only picture cost, and each part is paid once for all games.

## 3. Cost per game

Frame cost from the run of each game in `games_cost.py` (a disc falling, two cards flipping, a game played by a fixed policy): the pixels that change from one frame to the next, and the pixels of the 16 by 16 tiles that hold a change (the flush of several small dirty rectangles; the one-rectangle column is the flush of a single rectangle round everything). Flush ms uses the measured 30 ms for a full screen; draw time is not in it (see section 2).

| Game | Frames | Pixels changed per frame | Tiles flushed per frame (px) | Flush ms (mean) | Flush ms (worst frame) | One rectangle, ms (mean) |
|---|---:|---:|---:|---:|---:|---:|
| Four in a Row (a disc falls) | 48 | 629 | 2,181 | 0.9 | 1.4 | 0.4 |
| Match (two cards flip) | 58 | 398 | 1,231 | 0.5 | 2.1 | 0.6 |
| Hangman (a letter) | 20 | 128 | 640 | 0.2 | 1.4 | 0.6 |
| Mine Finder (a reveal) | 20 | 1,107 | 2,073 | 0.8 | 7.9 | 0.7 |
| Snake (it moves) | 100 | 54 | 143 | 0.1 | 1.6 | 0.0 |
| 2048 (two swipes) | 28 | 449 | 1,188 | 0.5 | 3.3 | 0.5 |
| Higher or Lower (a turn) | 4 | 27,999 | 37,184 | 14.5 | 26.2 | 16.0 |
| Reversi (a game) | 61 | 3,014 | 11,272 | 4.4 | 26.1 | 16.0 |
| Battleship-lite (shots) | 13 | 4,916 | 7,345 | 2.9 | 24.6 | 8.9 |
| Pong (a rally) | 401 | 329 | 2,975 | 1.2 | 28.9 | 6.1 |
| Flappy-style flyer (flying) | 601 | 1,674 | 13,982 | 5.5 | 28.6 | 18.2 |

The first frame of a run is the reference, so a game's start screen is not in the means; the worst-frame column shows the largest single change (a whole-board shake, a pop, a first draw).

One table, per game. Flash is the measured size of the code and constants (text and read-only data, `xtensa-esp32s3-elf-size`) of the game's own core and screen compiled with the unit's flags from the b68 bench build (`maipai_*` units for the new games); for the six grid games the unit is one object file, so the figure is shared. State is `sizeof` of the game's struct on the chip. Objects are counted on the renderer (the top layer after the game screen is built; the new games' counts exclude the 3 objects of the grid root and board that the renderer keeps under them). Internal RAM is objects times 110 bytes (labels 200), an assumption flagged above.

| Game | Flash KB | State, bytes | LVGL objects | Internal RAM at peak, KB | Flush ms per frame (mean, tiles) | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Four in a Row, Match, Hangman, Mine Finder, Snake, 2048 (one unit, `maipai_grid.cc`) | 27.6 together (estimates 1.9 to 4.0 each in `schema/memory-budget.json`) | in PSRAM (grid pattern) | 3 each | 0.4 each | 0.1 to 0.9 | fits |
| Data-pack games (Tic-Tac-Toe, Whack-a-Mole, Do It, Color Memory, Rock Paper Scissors, Dice and Coin, Magic 8 Ball) | 61.0 (the pack engine and the games unit, `maipai_games.cc`, shared) | 12,288 task (estimate) | per pack 10 to 20 (not counted here) | 2 to 4 (estimate) | not measured in the renderer | fits; measure on the bench |
| Question games (riddle, trivia, 20 Questions) | 26.1 (`maipai_qa_game.cc`) | | 2,400 B estimated | 2.4 | static screens | fits |
| Shared game-over screen | 0.6 (estimate) | | 15 (5 labels) | 2.1 | one draw | fits |
| Dice Poker (UX18) | 2.2 | 16 | 36 (7 labels) | 4.6 | not measured (static turns) | fits with a limit: 36 objects is 30 percent of the worst-case headroom; draw the pips in one callback like the boards (3 objects) |
| Higher or Lower (UX21) | 2.5 | 64 | 15 (8 labels) | 2.4 | 14.5 per turn (four frames: a turn is an event, not a stream) | fits |
| Reversi (UX22) | 2.2 | 76 | 5 (3 labels) | 0.8 | 4.4 | fits (the search is 262 nodes at most per move, measured on the host) |
| Battleship-lite (UX23) | 1.7 | 92 | 5 (3 labels) | 0.8 | 2.9 | fits |
| Pong (UX24) | 1.7 | 36 | 6 (4 labels) | 1.0 | 1.2 | fits with a limit: only if the court strip the ball and paddles moved through is invalidated each tick; invalidating the whole court is 30 ms of flush alone |
| Flappy-style flyer (UX25) | 1.3 | 48 | 3 (1 label) | 0.4 | 5.5 | fits with a limit: invalidate each pipe's strip, not the sky (a full invalidation is 30 ms of flush per tick) |

Totals: the six new unproven games add 11.6 KB of flash (0.9 percent of the 1.29 MB the lean images free) and at most 5 KB of internal RAM when one is on screen (never two at once: one game runs at a time on the game task). Flash is not the constraint; **internal RAM and the flush per frame are**.

## 4. What a richer look can spend

From the rules above, per game screen: at most about 15 LVGL objects (2,000 bytes internal) plus the one draw callback; dirty area per animated frame under 20,000 pixels (about 8 ms of flush, leaving 20 ms or more for drawing at the 30 ms target; the grid games run at 600 to 2,200); shadows, gradients and highlights on static parts only; particles at most 12 pooled objects or one callback for more, each burst under 700 ms; scale and rotation only on small tiles for 200 ms; every picture from the shared bank, none per game. The old Four in a Row and Match use 3 objects and flush 0.5 to 0.9 ms per frame, so a richer look has about 10 times its current flush and 5 times its current object count to spend before it touches the budget, **if** the bench confirms the K calibration.

## 5. What is not measured yet (the bench's list)

1. The drawing time of the box and the techniques on the chip (the K calibration is one point). `self.game.bench_record` and `bench_frames` on a Four in a Row with a prototype look would give the real gaps.
2. Internal heap before and during each game screen (`heap_info`): the object and style bytes here are sizeof plus an assumed 60 bytes of styles.
3. The data-pack games' frame cost, which the grid renderer does not draw.
4. The new games' real ticks: the firmware track wires them; the budget above only says what dirty area they may flush.
