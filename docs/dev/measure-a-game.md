# How to measure a game

For the firmware track and the bench. A game or a game's look is judged on numbers, not on the renderer's picture: the picture proves what it looks like, never that it fits. The same four steps gate every game, old or new. The numbers behind the rules are in `docs/plan/games-visual-budget.md`.

## 1. On the host, before any build

Run `python3 scripts/virtual-unit/games_cost.py`. It plays each game by script and prints, for every frame, the pixels that changed, the pixels of the 16 by 16 tiles that hold a change, the flush time that implies (a full screen flush is 30 ms, so 0.39 ms per 1,000 pixels), and, for a game that says which rectangles it changed, the cost of those rectangles and how many changed pixels fell outside them. Add a row for a new game to `RUNS` in that script.

Other tools, all commands of the grid renderer (`scripts/fw-face-render/grid_render.cc`):

| Command | What it answers |
|---|---|
| `diffbegin`, `diffend NAME` | the change per frame of everything drawn between them |
| `play GAME ...` | plays a game by itself, one step per frame, so `diffbegin` can measure it |
| `objcount` | how many LVGL objects the screen makes (each is internal RAM) |
| `technique NAME N` (with `PERF=1`) | the relative draw cost of one technique in a 100 by 100 pixel box |
| `timeit N` (with `PERF=1`) | the relative cost of redrawing the whole board |

The goldens match only the firmware tree whose patch set is the one in `firmware/patches/ORDER`. A newer tree can hold patches that are not on the list yet, so name the tree: `MAIPAI_FW_TREE_ROOT=~/esp/stackchan-rebuild/bNN bash scripts/virtual-unit/build-face.sh`, then `build-screens.sh`.

## 2. Flash, with the unit's compiler

Compile the game's header (or the unit file that holds it) with the compiler and flags of the bench build: take the `DEFINES`, `FLAGS` and `INCLUDES` of any `maipai_*.cc.obj` edge in `build-bench/build.ninja`, add the folder of the header, and run `xtensa-esp32s3-elf-size` on the object. Report the code and constants (text plus read-only data) and the static RAM (bss). The grid unit, for scale, is 27.6 KB.

## 3. On the unit (bench image)

1. Silent bench state is on; a game does not start in quiet, so the train lifts it for the game (`self.privacy.set` with `quiet` 0) and puts it back.
2. `self.bench.heap_info` before any game and again in the game: internal free, the lowest, the largest free block.
3. `self.game.start`, then `self.game.bench_record` with `on` 1, play (`self.game.bench_tap`, `bench_swipe`, `bench_event`), then `self.game.bench_frames`: the largest gap between two ticks is `gaps_ms`.
4. For a new look: `self.game.bench_look` switches levels so one image measures both, and `self.game.bench_box` gives the unit's own microseconds to draw and flush a 100 by 100 pixel box of a technique (flat, radius, circle, gradient, shadow-small, shadow, alpha, outline), which replaces the host's relative numbers with real ones.
5. A bench train runs the whole list with no one reading anything: `python3 scripts/bench-train.py scripts/bench-trains/<name>.json`. `c4-richer-look.json` is the model; copy it for a new game.

## 4. The pass rules

A game passes when all of these hold. Each says what to do if it fails.

| Rule | Number | If it fails |
|---|---|---|
| LVGL objects of the screen | at most 15 (about 2 KB of internal RAM) | draw in one callback, like the board games (3 objects) |
| Internal free in the game | at or above the gate (median 40,000 B, lowest 24,000 B, largest block 24,000 B median and 16,000 B lowest); for a new look, within 1,000 B of the plain look | remove objects, pool the particles |
| Dirty area per animated frame | mean at most 12,000 pixels, worst at most 22,000 (a full screen is 76,800) | invalidate rectangles (`lv_obj_invalidate_area`), never the whole object |
| Tick gap on the unit | median at most 40 ms, worst at most 60 ms (the target is 30 ms; the baseline with SF78 is 40) | fewer draw calls, smaller dirty area |
| One full-board redraw | at most 40 ms on the unit (the picture refresh gate) | no gradient or shadow under things that move |
| Flash | report it; it is not the limit (the lean images free 1.29 to 1.99 MB) | none, but no per-game bitmaps: use the shared bank |
| Changed pixels outside the rectangles the game invalidates | 0 | widen the rectangle (a rounded corner needs 3 to 4 pixels of margin) |

Techniques and their verdicts (flat, rounded, circle, border, outline, gradient and highlight fit; alpha, small shadows and particles fit with a limit; large shadows, 24 particle objects, and rotating or squashing anything but a small tile do not fit anything that moves) are in the budget's section 2.

## A checklist for a new game

1. A row in `games_cost.py`, the numbers in the game's spec, a verdict in the budget's table.
2. The screen draws in one callback; the game says its dirty rectangles; a test shows no changed pixel outside them.
3. The compiled size and the object count are in the spec.
4. A bench train (copy `c4-richer-look.json`) with the heap, the gaps and the pass rules above.
5. Only then a patch on the list, with `Check after a flash` naming the train.

Back: [index](index.md).
