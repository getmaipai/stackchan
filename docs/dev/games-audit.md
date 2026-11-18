# Screen audit of the data-pack games

Made by `scripts/virtual-unit/games_audit.py --write` from the touch regions of each pack (the games renderer's `targets` command). A board (six or more cells that touch) follows the board rule of `docs/design/screen-style.md`: every cell at least 24 px, the board as a whole 8 px from any other target. Other regions follow the ordinary rules.

| Pack | Regions | Board | Failures | Warnings |
|---|---:|---|---:|---:|
| bopit | 1 | none | 0 | 0 |
| dice | 4 | none | 0 | 3 |
| eightball | 1 | none | 0 | 0 |
| memory | 4 | none | 0 | 0 |
| rps | 5 | none | 0 | 2 |
| tictactoe | 9 | 9 cells of 93 x 56 px | 0 | 0 |
| whack | 9 | 9 cells of 93 x 57 px | 0 | 0 |
