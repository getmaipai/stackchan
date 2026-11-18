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
