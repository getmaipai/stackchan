# Maze

Rank 6 of `docs/plan/more-games.md`; input design in `docs/design/accelerometer-games.md`. Status: on branch `ux/unproven-games`, unproven (patch `firmware/patches/UX28-maze.patch` waits for a bench plain-boot proof and for SF107, the analog tilt). Core, screen, goldens and tests are done here; the firmware track registers the game, reads the lean (`maipai_games_tilt_analog`), runs the 33 ms tick, plays the sounds and calls the game-over screen.

## How it plays

An 8 by 8 maze made from a seed (a depth first search, so exactly one way between any two cells). A pale marble starts in the top left cell and rolls toward the lean of the unit; walls stop it, it never passes through one (it moves one axis at a time in pieces of at most one pixel). The goal is the amber disc in the bottom right cell. Reaching it ends the game on **You won** with the seconds; each game is a new maze. The only target on the screen is the grabber every game has, so there is no button to hit.

## The numbers (measured)

| What | Value |
|---|---|
| Flash (the unit's compiler on the b68 flags, core and screen) | 2.7 KB |
| State | 92 bytes (the 64 cell openings, the marble, a seed), in PSRAM in the grid pattern |
| LVGL objects | 2 (the root and one draw object), with the grabber 3 |
| Dirty area per tick | mean 242 px, 0.1 ms of flush; worst frame 2.2 ms |
| Changed pixels outside the rectangles it invalidates | 0 over 700 frames |

Cells are 24 px (the board rule's floor), walls 4 px, the marble 10 px across in 20 px passages. The solver (a search outward from the goal) and the autopilot are in the core: the autopilot solved all 100 test mazes, 18 s on average and 37 s at the slowest, so a person with a steady lean can too.

## The screen

A frame, a dark floor with a faint checker, the closed sides as light bars, the goal (a pulsing amber disc with a dark center), the marble (shadow, body, highlight) and the time chip at the right, in one draw callback. Frames: `host/tests/golden/screens/game-maze-*.png`.

## Checks

`host/tests/firmware/maze_core_test.c`: on 300 seeds every maze is perfect (126 openings, each matched from the other side, none through the border, all 64 cells reachable); the same seed gives the same maze; flat does not move the marble, a lean rolls it and the border stops it; for 40 mazes under a pseudo-random lean for a minute the marble is never inside a wall and never outside the maze; the autopilot solves every maze; a won game stays won; the dirty rectangles cover the marble's old and new place.
