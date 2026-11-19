# The look of the games: style guide (skeleton)

Status: the rules below are known; the numbers wait for the bench. This page is the one every new game inherits. It is filled in after the Four in a Row richer-look bench (`docs/plan/games-richer-look-bench.md`, patch UX26) reports. A rule marked **(bench)** is a number the bench sets; until it does, the budget's estimate stands.

## 1. The rules that hold whatever the bench says

These come from what the unit has (`docs/plan/games-visual-budget.md`) and from the owner's standards (`docs/design/screen-style.md`):

1. **One draw callback.** A game screen is the root and one object whose callback draws everything: board, pieces, text and chips. At most 15 LVGL objects in all, and the board games use 3. Every object is internal RAM (allocations of 256 bytes and less never go to PSRAM).
2. **Static gradients and shadows only.** A vertical gradient and a soft shadow belong to things that do not move (the backdrop, the board, a tile at rest). Nothing that moves every frame has a shadow of blur 14; a blur of 6 is allowed on a thing that moves seldom.
3. **No per-game bitmaps.** Parts that are a picture come from the shared asset bank (decision 17), once for all games; a disc, a pip, a card corner and a spark are drawn from rectangles.
4. **Dirty rectangles.** The game says which rectangles a step changed (`<game>_dirty`) and the screen invalidates only those (`lv_obj_invalidate_area`). A test shows that no changed pixel lies outside them. Never invalidate the whole object on a tick.
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

## 3. Components, each with its measured cost (to fill)

Every component is a function the games share, drawn from rectangles. The cost columns come from `self.game.bench_box` and the per-game bench train (`docs/dev/measure-a-game.md`); the first table is the budget's estimate until the bench replaces it.

| Component | What it is | Objects | Chip draw + flush for a 100 by 100 box, ms | Measured on the unit | Verdict |
|---|---|---:|---|---|---|
| Plate | gradient rounded rectangle with a light edge | 0 (in the callback) | 7.1 to 13.5 (estimate) | (bench) | |
| Tile | rounded rectangle with a highlight strip | 0 | 7.4 to 14.4 (estimate) | (bench) | |
| Disc | rim, face and highlight (three rectangles) | 0 | (bench) | (bench) | |
| Hole | dark socket with a light edge and an inner floor | 0 | (bench) | (bench) | |
| Title strip and score chip | a rounded chip with a number | 0 | (bench) | (bench) | |
| Soft shadow, blur 6, static | under a board or a resting tile | 0 | 10.5 to 21.7 (estimate) | (bench) | |
| Glow | an outline on the one thing that is lit | 0 | 8.6 to 16.6 (estimate) | (bench) | |
| Confetti (one burst) | at most 12 small discs drawn by the callback, 600 ms | 0 | (bench) | (bench) | |
| Squash (a small tile, 200 ms) | scale of one tile | 0 | 17.4 to 43.4 (estimate) | (bench) | |

## 4. Pass numbers (bench)

The pass rules are those of `docs/dev/measure-a-game.md` section 4. The prototype's own gate (`docs/plan/games-richer-look-bench.md`): worst tick gap at most 60 ms and median at most 40 ms, internal free within 1,000 bytes of the plain look, no flicker. When the numbers are in, this page says for each component: used freely, used with a limit (the limit written here), or not used.

## 5. A new game inherits all of this

Start from `docs/dev/measure-a-game.md`'s checklist; draw with the components above in the game's family palette; name the dirty rectangles; add the row to `games_cost.py`; run the bench train. A game that adds an LVGL object beyond the rule says why in its spec.
