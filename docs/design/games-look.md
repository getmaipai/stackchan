# The look of the games: style guide (skeleton)

Status (2026-11-19): the bench has reported (`docs/plan/games-richer-look-bench.md`, patch UX26) and **the richer look failed on this display**: Four in a Row's worst tick gap was 81 ms plain, about 170 ms with gradients and rims, about 200 ms with shadows (limit 60). A full 320 by 240 redraw takes about 65 ms, not 30. So this page now says what a look may spend on this display, with the measured box times, and the richer board look waits for a faster flush. A rule marked **(bench)** is a number a later bench still sets.

## 1. The rules that hold whatever the bench says

These come from what the unit has (`docs/plan/games-visual-budget.md`) and from the owner's standards (`docs/design/screen-style.md`):

1. **One draw callback.** A game screen is the root and one object whose callback draws everything: board, pieces, text and chips. At most 15 LVGL objects in all, and the board games use 3. Every object is internal RAM (allocations of 256 bytes and less never go to PSRAM).
2. **Static gradients and shadows only, drawn once.** A vertical gradient and a soft shadow belong to things that do not move (the backdrop, a button), and are drawn when the screen appears. Measured: a shadow of blur 6 is 13.2 ms for a 100 by 100 box, blur 14 is 20.9 ms (a flat box is 8.5). Blur 6 is for static things only, at most 3 on a screen; blur 14 only tiny (60 by 60 px at most); nothing that moves has a shadow.
3. **No per-game bitmaps.** Parts that are a picture come from the shared asset bank (decision 17), once for all games; a disc, a pip, a card corner and a spark are drawn from rectangles.
4. **Dirty rectangles, small.** The game says which rectangles a step changed (`<game>_dirty`) and the screen invalidates only those (`lv_obj_invalidate_area`). A test shows that no changed pixel lies outside them. Never invalidate the whole object on a tick. The motion rule (budget section 4): a frame of a motion at most 16,000 px worst and 6,500 px on average; a particle is its own rectangle of about 100 px, never a band; a one-off full-screen frame (up to 100 ms) only when a screen appears.
5. **The standards of the screen:** targets of 56 px (secondary 48), 8 px between them and from the glass edge, text of 16 px and more, no text over text or over a button, a board cell of 24 px at least, an error says what to do.
6. **Words in six languages**, plain ASCII where the font lacks the glyph, short enough for one row (the language with the longest word sets the box).
7. **The end is the shared screen.** A game with a winner ends on You won, You lost or Draw; a score-only game on Game over or Time's up; both with the score and the new-best mark.
8. **Sounds from the tone table**, nothing stored per game.

## 2. Families and palettes

One palette per family so a child learns what a color means. The colors are fixed by the bench pass (a color is only a flash constant, so this part is free); the family sets the roles:

| Family | Games | Backdrop | Surface | Accent (yours) | Accent (the unit's) | Notes |
|---|---|---|---|---|---|---|
| Boards | Four in a Row, Tic-Tac-Toe, Reversi, Battleship-lite, Hangman, Mine Finder, Match | dark navy to black | blue plate | amber | red | the person is always amber |
| Table | Dice and Coin, Dice Poker, Higher or Lower, Rock Paper Scissors | felt green gradient | cream | amber | pale blue | felt for chance |
| Reflex | Do It, Whack-a-Mole, Color Memory, Pong, the flyer | one saturated color per game | lighter tone | amber | white | the cue is the brightest thing |
| Tilt | Balance, Maze, Racing, Flying | deep blue | pale blue | pale white | amber | the goal is amber |
| Oracle | Magic 8 Ball, the question games | dark gray | slate | amber | blue | text first |

## 3. Components, each with its cost on the unit

Every component is a function the games share, drawn from rectangles. The cost is the unit's measured time to draw and flush a 100 by 100 pixel box (`self.game.bench_box`, 2026-11-19); a component that was not measured says "estimate" and uses the host ratio times the flat box.

| Component | What it is | Objects | Unit ms, 100 by 100 box | Verdict on this display |
|---|---|---:|---|---|
| Plate | gradient rounded rectangle with a light edge | 0 (in the callback) | 9.3 (gradient, measured) | at a screen's entry; inside a ticking board it is repainted in every dirty rectangle: the richer board failed (81 to 200 ms gaps) |
| Tile | rounded rectangle with a highlight strip | 0 | 11.0 (estimate) | fine on a screen that does not tick |
| Disc | rim, face and highlight (three rectangles) | 0 | 9.9 (circle, measured) | a rim and a face yes; the highlight only at rest |
| Hole | dark socket with a light edge and an inner floor | 0 | 10.1 (outline, measured) | one hole is small; 42 of them in a dirty rectangle are what broke the board |
| Title strip and score chip | a rounded chip with a number | 0 | 9.1 (radius, measured) | used freely |
| Soft shadow, blur 6, static | under a button or a resting tile | 0 | 13.2 (measured) | static, drawn once, at most 3 on a screen |
| Glow | an outline on the one thing that is lit | 0 | 10.1 (measured) | used with a limit: one thing at a time |
| Confetti | tiny rectangles, one dirty rectangle each | 0 | about 50 px a piece | used: 18 pieces for 1.7 s (the game-over look) |
| Squash (a small tile, 200 ms) | scale of one tile | 0 | 44 (estimate, for 100 by 100); 7 for 40 by 40 | 40 by 40 px at most |

## 4. Pass numbers

The pass rules are those of `docs/dev/measure-a-game.md` section 4, with the gap numbers re-based on the unit: the worst tick gap of a look must be at most **100 ms** and the median at most **46 ms** (the plain Four in a Row measures 81 and 40 to 44; the budget's 60 ms rule is not met even by the plain look, so a look is judged against the plain look plus 19 ms), internal free within 1,000 bytes of the plain look, no flicker. A screen that does not tick is judged by the motion rule instead (budget section 4): entry frame at most 100 ms, a motion frame at most 16,000 px worst and 6,500 px on average. Components are used freely, used with a limit (written in the table above), or not used on a screen that ticks.

## 5. A new game inherits all of this

Start from `docs/dev/measure-a-game.md`'s checklist; draw with the components above in the game's family palette; name the dirty rectangles; add the row to `games_cost.py`; run the bench train. A game that adds an LVGL object beyond the rule says why in its spec.
