# Battleship-lite

Rank 7 of `docs/plan/more-games.md`. Status: on branch `ux/unproven-games`, unproven (patch `firmware/patches/UX23-battleship-lite.patch` waits for a bench plain-boot proof). Core, screen, goldens and tests are done here; registering the game, the touches, the sounds, the best score and the game-over call are the firmware track's.

## How it plays

A 6 by 6 sea. The unit hides three ships (a 3, a 2 and another 2, straight, never touching one another, corners included). The person has 22 shots and taps a cell to fire. The screen says Miss, Hit or Sunk (a sunk ship shows as dark red bars); firing at a cell twice costs nothing. All three sunk is **You won**; 22 shots without it is **You lost**; the shared game-over screen shows the shots left. A game with a real winner.

Why 22: a sensible search (the neighbors of a hit first, otherwise a checkerboard) won 104 of 200 courses with 22 shots, 22 of 200 with 18 and 169 of 200 with 24. About half is a fair game for a person who plays a little better than a plain search.

## The screen

The sea is 6 by 6 cells of 30 px with 2 px between (190 by 190 px at x 8, y 34), drawn by one object and one draw callback. Cells are above the 24 px floor of the board rule in `docs/design/screen-style.md`; the number column starts 8 px right of the sea. On the right: Shots left, Ships left, and the word for the last shot. English and Spanish. A miss is a pale dot, a hit an amber spark, the last shot has a white top edge.

## Checks

`host/tests/firmware/battleship_core_test.c`: 2,000 seeds all give the same fleet shape (3, 2, 2), straight, whole and apart; the same seed gives the same sea; miss, hit, sunk, a repeat ignored, the last cell wins; a full set of misses loses; a plain search wins about half; every cell's box maps back to itself and the sea is 8 px clear of the side column. Four frames and an es frame in `host/tests/golden/screens/game-battleship-*.png`.
