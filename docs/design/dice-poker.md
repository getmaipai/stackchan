# Dice Poker

The first new game from `docs/plan/more-games.md` (rank 2, after Higher or Lower which needs a card face). Patch: `firmware/patches/UX18-dice-poker.patch` (two header-only files: `maipai_dicepoker_core.h` for the rules, the hand ranking and the touch targets, `maipai_dicepoker.h` for the LVGL screen). Pictures: `host/tests/golden/screens/game-dicepoker-*.png` and `game-over-dicepoker-over-new-best.png`.

## How it plays

Five dice. Each round the player rolls all five, may hold any dice by tapping them, and re-rolls the rest, twice at most. Keep banks the hand's points. Five rounds; the score is the total. It has no opponent and no winner, so it is a score-only game and ends on **Game over** with the total and the new-best mark (decision 31, `docs/design/game-over-screen.md`).

| Hand | Points |
|---|---:|
| High dice | 0 |
| A pair | 10 |
| Two pair | 20 |
| Three of a kind | 30 |
| Straight (1 to 5 or 2 to 6) | 40 |
| Full house | 50 |
| Four of a kind | 70 |
| Five of a kind | 100 |

The most a game can score is 500. The ranking is checked on all 7,776 hands against the standard poker-dice counts (five of a kind 6, four 150, full house 300, three 1,200, two pair 1,800, pair 3,600, straight 240, high dice 480).

## The screen

A header line (the round, the score, 16 px), five 52 px dice 8 px apart with a 3 by 3 pip pattern and an amber border and the word HOLD under a held die, the hand's name in the 20 px text, and two 148 by 56 buttons at the bottom: **Roll again (n)**, with the re-rolls left on the button, and **Keep**. Before the first roll one 304 by 56 **Roll** button. Spanish (plain letters): Ronda, Puntos, FIJO, Lanzar, Quedarme, and the hand names (Nada, Una pareja, Dos parejas, Trio, Escalera, Full, Poker, Repoker). Every target is finger size (the dice are secondary targets at 52 px; the buttons are 56), 8 px apart, on the 8 px margin; the core test checks it.

## Sounds and memory

Nothing new is stored: the dice rattle (`MGS_C_RATTLE`, in the table), a soft thud when a die is held, the good clip for a pair or better, the fanfare for a straight or better, the ting for a new best. The state is 14 bytes plus the random seed, held in PSRAM while the game runs (the grid-game pattern); nothing at rest. The screen is about 40 small LVGL objects while it is up.

## What is the firmware track's

Registering the game in the unit's games list (`self.game.list`), routing touches with `dp_hit`, calling `dp_roll`, `dp_toggle_hold` and `dp_keep`, the sounds, the best score, and the memory row. Not proven on a unit.
