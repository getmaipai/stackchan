# Flappy-style flyer

Rank 8 of `docs/plan/more-games.md`. Status: on branch `ux/unproven-games`, unproven (patch `firmware/patches/UX25-flyer.patch` waits for a bench plain-boot proof). Core, screen, goldens and tests are done here; registering the game, the tap, the 33 ms tick, the sounds, the best score and the game-over call are the firmware track's. The frame cost of a scrolling field is the plan's open risk: test it on the frame table before it ships.

## How it plays

A small bird falls; a tap anywhere hops it up about 30 px. Pipes with a 76 px gap scroll in from the right at 2.5 px a tick, one every 160 px. One point for every pipe passed. A pipe, the sky or the floor ends the game on **Game over** with the pipes passed and the new-best mark (a score-only game, owner decision 33). The gaps come from a seed, 24 px clear of the sky and the floor.

## The numbers

30 ticks a second, positions in 1/16 pixel. Gravity 0.5 px a tick every tick, a hop sets 5.5 px a tick upward, the fall is capped at 8 px a tick. A plain autopilot (hop when the bird sinks below the gap's middle) reached 12 pipes on all 40 courses it was tried on and 21 at best in 40 seconds, so the gaps are fair.

## The screen

One object, one draw callback: sky, floor, pipes with lips, the bird (amber; red-orange after the hit) with an eye; `Pipes N` (Tubos N in Spanish) at the top. The whole screen is the tap target. Frames: `host/tests/golden/screens/game-flyer-*.png`.

## Checks

`host/tests/firmware/flyer_core_test.c`: a bird that never hops dies in under 60 ticks with no points; a hop lifts it; the pipes scroll at the set speed and wrap with new gaps inside the sky; the same seed gives the same course; the autopilot flies through 12 pipes on 30 of 40 courses at least; a pipe at the bird's height ends the game and passing one scores exactly once.
