# Pong

Rank 11 of `docs/plan/more-games.md`. Status: on branch `ux/unproven-games`, unproven (patch `firmware/patches/UX24-pong.patch` waits for a bench plain-boot proof). Core, screen, goldens and tests are done here; registering the game, the drag, the 33 ms tick, the sounds, the best score and the game-over call are the firmware track's.

## How it plays

The person's paddle (amber, left) follows a finger dragged up and down; the unit's (pale blue, right) follows the ball. First to 5 points wins: **You won** or **You lost** with the score on the shared screen. The ball leaves a paddle faster each hit (up to 10 px a tick) and steeper the nearer the edge it hit, so the way to win a point is to hit near an edge: the unit's paddle moves 2.5 px a tick and cannot follow a steep ball. After a point the ball is served toward the side that lost it. A long rally (more than 6 hits) gets a wilder return from the unit, so no game goes on for ever.

## The numbers

Court 304 by 192 px at x 8, y 36; paddles 40 by 6; ball 8; 30 ticks a second; positions in 1/16 pixel, no floating point. Measured by the host test over 20 games each: a person who never moves lost all 20; a person who aims for the paddle's edge won 19 of 20; the longest game took 2,509 ticks (82 s).

## The screen

One object, one draw callback (frame, net, paddles, ball) redrawn on every step, with the score above the court (You and Unit, English and Spanish). The firmware redraws only the strip the ball and paddles moved through (SF78). Frames: `host/tests/golden/screens/game-pong-*.png`.

## Checks

`host/tests/firmware/pong_core_test.c`: drag clamps to the court; the same seed gives the same game; a wall bounce flips the ball; a paddle hit speeds it up and a miss scores for the unit and puts the ball back in the middle going toward the loser; an edge hit is steeper than a center hit; the ball and paddles never leave the court in 40 games; standing still loses, aiming wins, every game ends within five minutes.
