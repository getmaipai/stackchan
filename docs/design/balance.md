# Balance

Rank 5 of `docs/plan/more-games.md`; input design in `docs/design/accelerometer-games.md`. Status: on branch `ux/unproven-games`, unproven (patch `firmware/patches/UX27-balance.patch` waits for a bench plain-boot proof and for SF107, the analog tilt). Core, screen, goldens and tests are done here; the firmware track registers the game, reads the lean (`maipai_games_tilt_analog`), runs the 33 ms tick, plays the sounds and calls the game-over screen.

## How it plays

A ball on a round plate rolls toward the lean of the unit (roll right and pitch forward, in permille of a full lean; forward rolls the ball up the screen). The plate starts 88 px in radius and shrinks a pixel every two seconds (down to 34). Every four seconds a hole opens, first as an amber ring (about one second, harmless), then as a black hole that takes the ball; at most six. The ball off the plate or in a hole ends the game on **Game over** with the seconds survived and the new-best mark (a score-only game, owner decision 33). The ball starts 40 to 55 px from the middle, so a unit standing flat does not last: the plate shrinks past the ball (longest 99 s in the test).

## The numbers (measured)

| What | Value |
|---|---|
| Flash (code and constants, the unit's compiler on the b68 flags, core and screen) | 2.5 KB |
| State | 68 bytes, in PSRAM in the grid pattern |
| LVGL objects | 2 (the root and one draw object), with the grabber 3 |
| Dirty area per tick | mean 481 px, 0.2 ms of flush; worst frame 13.2 ms (the plate's one-pixel shrink redraws its box once every two seconds, inside the 40 ms picture gate) |
| Changed pixels outside the rectangles it invalidates | 0 over 900 frames |

The core takes the two lean values as arguments, so the host test and the renderer drive it with made-up values: its own autopilot (a position and velocity controller that steers away from holes) lasted 150 s on all 20 courses, standing still ended all 20.

## The screen

The plate (a shadow, a rim, the plate, a lighter dome), the holes (a ring, then black), the ball (a shadow, the ball, a highlight, red after the fall) and the time chip (Time and the seconds, Tiempo in Spanish) at the right, all in one draw callback. Frames: `host/tests/golden/screens/game-balance-*.png`.

## Checks

`host/tests/firmware/balance_core_test.c`: a flat lean does not move the ball; right, left and forward roll it the right way; a small lean (60 permille) still moves it (the speeds are in 1/256 px, so nothing is lost to rounding); the speed is capped and friction brings a ball to rest; rolling off ends the game; the plate shrinks and holes open and arm on their schedule; a ring is safe and an armed hole is not; no hole opens on the ball or beside another; the same seed gives the same course; the autopilot plays on and standing still ends; the dirty rectangles cover the ball's old and new place.
