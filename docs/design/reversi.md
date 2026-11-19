# Reversi

Rank 3 of `docs/plan/more-games.md`. Status: on branch `ux/unproven-games`, unproven (patch `firmware/patches/UX22-reversi.patch` waits for a bench plain-boot proof). Core, screen, goldens and tests are done here; registering the game, the touches, the pause before the unit's move, the sounds, the best score and the game-over call are the firmware track's.

## How it plays

8 by 8. The person plays black and moves first; the unit plays white. A move must flip at least one straight line of the other side's discs, in any of the eight directions. A side with no move passes (the screen says so). The game ends when neither side can move; the side with more discs wins. A game with a real winner: it ends on the shared screen with You won, You lost or Draw and the disc count.

## The unit's move

A two-ply search: for each of its moves it looks at the person's best reply and keeps the move whose worst case is best. The value of a position is a positional table (corners 100, the cells beside a corner -20, the diagonal one -50, edges 10, the inside 0 to 3) plus four times the difference in the number of moves each side has. One move searches at most 800 nodes; the host test measured 262 as the most over 120 full games (bound checked, not a clock time: at a few microseconds a node on the unit the slice is far under the 5 ms the plan allows, **assumed until the bench measures it**). Against a person who plays at random it won 115 of 120 games, lost 4 and drew 1.

## The screen

The board is 8 by 8 cells of 25 px (200 by 200 px) at x 8, y 30, drawn by one object and one draw callback (the grid-game pattern: one LVGL object, not 128). Cells are above the 24 px floor of the board rule in `docs/design/screen-style.md` and the score column starts 8 px right of the board (x 216). Black and white discs, two greens for the board, small amber dots on the cells the person may play, a colored center on the last move. On the right: the disc counts (You, Unit) and one line: Your move, Thinking, No move: pass, or Game over. English and Spanish.

## Checks

`host/tests/firmware/reversi_core_test.c`: the opening position and its four moves, illegal moves change nothing, flips in several directions at once, a pass for each side, the end and its result, 120 full games against random play (all end, counts add up, the unit wins at least 100, at most 800 nodes a move), and every cell's box maps back to itself under `rv_hit`. Six frames in `host/tests/golden/screens/game-reversi-*.png`.
