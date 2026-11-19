# What the games cost in the image (measured from a built tree, 2026-11-18)

Firmware track. Source: the plain image of build b74 (main plus the unproven patches up to SF106), read from its linker map (`esp_idf_size --files`) and its symbol table. **Measured** means read from those; per-game numbers inside a shared object are function sizes from the symbol table, so they leave out the inline header cores that the compiler folds into the callers.

## Flash, by object file (bytes)

| Object | Total | Code | Read-only data | Internal RAM (bss) | What it holds |
|---|---:|---:|---:|---:|---|
| `maipai_games.cc` | 34,411 | 27,509 | 4,019 + 1,812 | 1,071 | the data-pack game player, the games page glue, score store, game-over wiring |
| `maipai_grid.cc` | 17,180 | 13,383 | 3,046 + 692 | 59 | Four in a Row, Memory Match, Hangman, Mine Finder, 2048, Snake: one drawing function, one tick, all the cores inlined |
| `maipai_qa_game.cc` | 14,491 | 12,496 | 1,150 + 836 | 9 | the question games (riddle, trivia, 20 Questions) and the pantry tellings |
| `maipai_mumble.cc` | 4,336 | 3,554 | 302 + 256 | 224 | the offline mumble |
| the seven data packs (`.mpk`, in the image) | 17,828 | | 17,828 | 0 | bopit 2,692, dice 2,294, eightball 3,646, memory 1,058, rps 3,968, tictactoe 2,436, whack 1,734 |

## Inside the grid object (largest functions)

| Function | Bytes |
|---|---:|
| the one draw callback for every grid board | 2,991 |
| the tick (input, search slices, tweens, end of game) | 2,547 |
| Mine Finder tap and long-press action | 659 |
| Four in a Row disc landing | 491 |
| Four in a Row search (negamax) | 385 |
| Four in a Row drop | 189 |
| Four in a Row win test | 126 |

The grid games share one draw function and one tick, so a seventh grid game costs its core (a few hundred bytes to about 1.5 KB of code) plus its share of the draw switch, not a new object.

## Shared screens

| Piece | Bytes |
|---|---:|
| shared game-over screen (`mgo::build`) | 751 |
| question screens: riddle 335, trivia 318, twenty 196, label 114, root 103 | about 1,070 |

## RAM while a game runs (estimates; the heap rows are in `schema/memory-budget.json`)

| Game kind | Internal RAM | PSRAM | Basis |
|---|---:|---:|---|
| a data-pack game | about 2 KB (LVGL objects) | the `Game` struct | `screen.*` rows |
| a grid game | about 600 B | the `Grid` struct | SF77 row |
| the game-over screen | about 2.1 KB | none | `screen.game_over` row (estimate) |
| a question game | about 2.4 KB | 800 B | `screen.qa_games` row (estimate) |

Every game-RAM number above except the bss column is an estimate until two `self.bench.heap_info` calls (idle, playing) measure it; the bench train can do that for each game.
