# The shared game-over screen

Owner idea of 2026-11-18, one standard for every game. When a game ends, the unit shows the same large screen: a face for the result, the result in words, the score, the best score (marked new best when it beat the old one) and two finger-size buttons, Play again and Quit. A game supplies only the result and the score text. Won and Lost are only for games with a real winner; a game that only counts a score ends on a neutral **Game over** or, when it is timed, **Time's up** (owner decision 31). Patch: `firmware/patches/UX15-shared-game-over-screen.patch` (two header-only files, `maipai_game_over_core.h` for the layout, texts and cues, `maipai_game_over.h` for the LVGL drawing). The renderer draws it with the unit's own code; the pictures are `host/tests/golden/screens/game-over-*.png`.

## The screen

| From the top (320 by 240 glass) | What |
|---|---|
| y 34 to 90 | The face, 56 px across: amber and smiling for a win, blue and sad for a loss, gray and level for a draw, a calm sand-colored level one for Game over and Time's up. It pops (100 to 112 percent and back in 160 ms) when the screen appears. |
| y 94 | The result in the 24 px font: You won! / You lost / Draw, or Game over / Time's up. |
| y 124 | The game's score line in the 20 px font. Left out when the game has none. |
| y 150 | The best line ("Best 30") in the 16 px font, or the amber "New best!" mark in its place when the score beat the old best. |
| y 176 to 232 | Two buttons, 148 by 56 px, 8 px margins and an 8 px gap: Play again (blue) and Quit (dark). |

The banner row stays over the top 28 px as on every game. A touch in the gap, the margin or above the buttons hits nothing, so a slip never quits. Spanish: Ganaste, Perdiste, Empate, Otra vez, Salir, Nuevo record (plain letters, as the games' other Spanish text, because the games' fonts have no accents).

## What a game supplies

```
mgo::build(parent, result, score_text, best_text, new_best, es)   // MGO_WON, MGO_LOST or MGO_DRAW
mgo_beats_best(score, best, lower_is_better)                      // decides new_best
```

| Game | Result words | Score line (English) | Best | Lower is better |
|---|---|---|---|---|
| Four in a Row | won, lost, draw | Score 38 | Best 30 | no |
| Memory Match | won | 14 turns | Best 18 | yes |
| Hangman | won, lost | Score 70, or "The word was robot" | Best 90 | no |
| Mine Finder | won, lost | Cleared in 82 s, or Boom! | Best 96 s | yes |
| Tic-Tac-Toe | won, lost, draw | Wins 3 | Best 22 | no |
| 2048 | won when the 2048 tile is made, otherwise Game over (no move left) | Score 20480 | Best 20480 | no |
| Snake | Game over (a wall or itself) | Length 34 | Best 31 | no |
| Color Memory | Game over when a round is missed (a new best is still marked) | Round 9 | Best 14 | no |
| Whack-a-Mole | Time's up (a score-only timed game) | Score 120 | Best 287 | no |
| Do It | Game over on the first miss (the score is the points before it) | Score 12 | Best 30 | no |
| Rock Paper Scissors | won, lost or draw by the best of three | Match 2 to 1 | Best 3 | no |
| Tic-Tac-Toe | won, lost or draw | Wins 3 | Best 22 | no |

Games with no end (Magic 8 Ball, Dice and Coin) do not show the screen. A rock paper scissors round inside a match does not either; the match end does.

Answered (owner decision 31): a score-only game never says "You won!" or "You lost"; it says Game over or Time's up with the score and the new-best mark. The result word is one table entry per game.

## What the unit does

- **Sound** when the screen shows: win `MGS_C_FANFARE`, loss `MGS_C_GRID_LOSE` (the data packs may keep `MGS_C_BAD`), draw `MGS_C_GRID_DRAW`; after a win or loss that is a new best, `MGS_C_TING`. The core names the moment (`mgo_cue`); the unit's sound policy (muted, quiet hours, volume) decides as always.
- **Animation**: the face pops with `mgo::set_pop(screen, elapsed)` from the game's tick for `MGO_POP_MS`. Nothing else moves, so the screen costs nothing while it stays up.
- **Touch**: the game's touch handler asks `mgo_hit(x, y)`. Play again starts the same game fresh (a new seed; the game's level stays). Quit ends the game and returns to the games page.
- **Timing**: the screen stays until a button is touched or the idle rule ends the game (ten minutes). It replaces the games' old "result held for three seconds, then the game ends" behavior.
- **Best**: saved by the game as today, at the moment the screen shows, so a power cut on the screen keeps the record.
- **Memory**: the screen is about 14 small LVGL objects, built when the game ends and freed on Play again or Quit; no PSRAM, nothing held at rest (`docs/dev/memory-budget.md` row to be added with the wiring).

## What is in this patch and what is not

In: the shared screen (core, drawing), its host test (`game_over_core_test.c`: 56 px buttons, 8 px gaps and margins, hit areas, texts, cues, best rule), the renderer command, 16 goldens (win, lose, draw and new best for the seven games, plus Spanish).

Not in, the firmware track's: wiring each game's end into `mgo::build` (`maipai_grid.cc` `finish()`, `maipai_games.cc` `end_locked()`), the touch routing, the restart, the sound calls, and the memory row. These need the game state machines, which are changing in SF76 and SF77.

Not yet proven on a unit: the touch feel of the buttons, the sound timing, the restart.
