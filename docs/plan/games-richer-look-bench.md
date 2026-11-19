# Four in a Row richer look: the bench

Playground track, 2026-11-18. A bench-only prototype, built only from what `docs/plan/games-visual-budget.md` says fits. It answers one question with measured numbers: can a richer look of a game board stay inside the memory gate and the 30 ms tick? The renderer picture alone proves nothing about fit.

## What the patch is

`firmware/patches/UX26-four-in-a-row-richer-look-bench.patch` changes only the Four in a Row branch of the grid game's one draw callback in `maipai_grid.cc`. No extra LVGL object, no bitmap. Three looks, switched at run time, so one image measures all of them:

| Level | What is drawn | Added draw calls per full board |
|---|---|---|
| 0 | the old look, unchanged | 0 |
| 1 | a vertical gradient backdrop and board (blue, light edge along the top), holes with a light rim and an inner floor, discs with a darker rim, the face and a pale highlight | about 3 per hole and 3 per disc (42 holes) |
| 2 | level 1 plus a soft shadow under the board (blur 8) and under each disc (blur 5) | the shadows |

Two bench tools in the existing bench tool block (they exist only on bench images): `self.game.bench_look {level}` and `self.game.bench_box {technique, n}`. The second draws and flushes one 100 by 100 pixel box of a technique `n` times and answers the unit's own microseconds per redraw: it replaces the K calibration of the budget (200 to 600, from one point) with a measurement for flat, radius, circle, gradient, shadow-small, shadow, alpha and outline.

## What the unit's compiler says (measured)

The patched `maipai_grid.cc` compiles with the unit's own compiler and flags (the b68 bench build): the grid unit grows from 27,630 to 33,192 bytes of code and constants (+5.6 KB: the look about 3.5 KB, the two bench tools the rest) and from 5,088 to 5,092 bytes of static RAM (+4: the level). No new heap object.

## What the renderer says (host, relative)

A full redraw of the board: level 0 44 microseconds, level 1 151 (3.4 times), level 2 193 (4.4 times) on the host. With the budget's K range that is 9 to 26 ms for level 0, 30 to 91 ms for level 1 and 39 to 116 ms for level 2 per full-board redraw, plus the flush. A falling disc redraws one column (about a seventh of the board), so the per-frame cost of a fall is one seventh of that: level 1 at 4 to 13 ms of drawing and about 1 ms of flush, inside the 30 ms tick **if the K range holds**. A full-board redraw (the start, a win flash of all four at once, a shake) is the case at risk: level 1 may pass 40 ms on one frame. That is what the bench decides. The before and after frames are `host/tests/golden/screens/game-c4-look-0.png`, `-1.png`, `-2.png` and `game-c4-look-2-win.png`.

## Build and run (the bench agent)

1. Replay the series with the patch at the end of `firmware/patches/ORDER` (it is the last line on the branch `ux/unproven-games`; the patch applies on the current main series, nothing else is needed): `bash scripts/fw-rebuild.sh TREE`.
2. Build the bench image: `bash scripts/fw-build.sh TREE bench`. The tools are in the bench block only, so `plain` and `gate` images do not carry the patch's tools (the draw branch is dead at level 0 and costs nothing).
3. Flash it and run the train: `python3 scripts/bench-train.py scripts/bench-trains/c4-richer-look.json` after setting `build_dir` in the manifest to the new tree (it says `NEWBUILD`). The train: heap before any game, the eight box times, start Four in a Row (it lifts the bench's quiet state for the game and puts it back), for each of the three looks it records ticks, drops three discs by touch, reads the frame gaps and the heap.
4. Read `result.json`: `us_per_redraw` per technique (the K calibration), `gaps_ms` per look (the largest gap between two ticks; the target is 30 ms, the baseline with SF78 is 40 ms), `internal_free` and `int_big` in the game against before.
5. Look at the screen for each level and say if a level flickers or tears when a disc falls (the `person` items of the manifest).

## The gate for the prototype

Level 1 or 2 passes if all of these hold on the unit: the worst tick gap is at most 120 ms (the plain look measured 81 ms on b80 and 109 ms on b85; the budget's own 60 ms rule is not met even by the plain look) and the median gap is at most 46 ms; internal free in the game is within 1,000 bytes of level 0 (the look adds no objects, so it should be equal); the box times show the budget's K within its range or better; no flicker. If level 1 passes and level 2 does not, the rule is: gradients, rims and highlights yes, shadows on the board only. If neither passes, the budget's verdicts are too generous and the art direction waits.

## Result and verdict (the bench, 2026-11-19)

The bench ran the train on a b-image with UX26. **The richer look failed.**

| | Measured |
|---|---|
| Box time on the unit, draw and flush of 100 by 100 px | flat 8,490 us, radius 9,075, circle 9,879, gradient 9,317, shadow blur 6 13,182, shadow blur 14 20,875, alpha 9,798, outline 10,133 |
| A full 320 by 240 redraw | about 65 ms (the display flush runs about 2.4 MB/s) |
| Worst tick gap, look 0 (plain) | 81 ms (limit 60), median 40 to 44, spikes to 92 |
| Worst tick gap, look 1 (gradients, rims, highlights) | about 170 ms |
| Worst tick gap, look 2 (adds shadows) | about 200 ms |

Why: the look repaints the board and 42 holes with gradients, rims and (look 2) shadows inside every dirty rectangle, and a shadow of blur 6 under each disc costs 1.55 times a flat box on a display that flushes 2.4 MB/s. The budget's estimates (a 30 ms full screen, K of 200 to 600) were too generous: `docs/plan/games-visual-budget.md` is recalibrated with the measured numbers.

**Verdict: the richer look for Four in a Row does not fit this display as it flushes now.** UX26 stays on the branch as a patch that does nothing at level 0. It activates only if a measured flush ceiling allows: the firmware track is investigating the SPI clock and DMA, and the rule for switching it on is: re-run `scripts/bench-trains/c4-richer-look.json`, and enable level 1 only when the flat 100 by 100 box is 4,500 us or less (a flush twice as fast) and level 1's worst gap is within 10 ms of level 0's. Level 2 (the shadows) additionally needs the shadow blur 6 box at 8,000 us or less. Until then the board stays plain; a richer look belongs to screens that do not tick (`docs/design/game-over-look.md`, the menus) and to nothing that flushes a board every frame.

### The b85 bench (2026-11-19)

The same train on the b85 image: Four in a Row frame gaps 109 ms at look 0, 177 at look 1 and 211 at look 2 (b80: 81, about 170, about 200), so the plain look's worst gap moved from 81 to 109 ms between the images while the richer looks stayed where they were. Box times (b85): flat 7.33 ms, radius 7.4, circle 9.3, gradient 9.0, shadow blur 6 14.3, blur 14 21.8, alpha 9.7, outline 10.5. The verdict stands. The gate is therefore 120 ms (it was 100); judge a look against the plain look measured in the same run (the richer looks are 68 to 102 ms worse).
