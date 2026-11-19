# Higher or Lower

Rank 1 of `docs/plan/more-games.md`. Status: on branch `ux/unproven-games`, unproven (patch `firmware/patches/UX21-higher-or-lower.patch` waits for a bench plain-boot proof). Core, screen, goldens and tests are done here; registering the game, the touches, the sounds, the best score and the game-over call are the firmware track's.

## How it plays

A shuffled deck of 52 cards, one face up. The player taps Higher or Lower; the next card is turned over. Aces are low.

| The next card is | Result | Streak |
|---|---|---|
| on the side the player chose | Right | +1, the new card becomes the current one |
| the same rank | Same (a push) | no change, the next card is drawn |
| on the other side | Wrong | the game ends |

A score-only game: it ends on **Game over** with the streak and the new-best mark (owner decision 33), never "You won!". If the deck runs out (51 turns without a wrong answer) the game also ends with the streak it has. A hint line counts the cards left that are higher and lower than the current one, so the odds are honest.

## The screen

A header line (the streak on the left, the odds hint on the right; after an answer the word Right, Wrong or Same), two cards of 84 by 104 px (the current one and the next, face down, or after an answer the dimmed old one and the new one), and two buttons of 148 by 56 px, 8 px apart, 8 px from the glass edge (Higher in green, Lower in blue). A card shows the rank large, a colored shape (circle for clubs and hearts, a turned square for diamonds and spades; red for hearts and diamonds) and the suit's name in 14 px, so color is never the only signal. English and Spanish.

## Memory and sounds

Nothing is stored except the best score the firmware keeps for every game. The state is 60 bytes. Sounds from the table: a tick on a turn, the good clip on Right, the bad clip on Wrong.

## Checks

`host/tests/firmware/hilo_core_test.c`: every seed gives all 52 cards once, a made deck plays right, push, right, wrong as the table says, the hint counts add up, a sorted deck ends the game at the last card, 300 random games never read outside the deck, a sensible strategy beats always-higher over 1,000 games, and the buttons meet the finger-size standard. Six frames in `host/tests/golden/screens/game-hilo-*.png`.
