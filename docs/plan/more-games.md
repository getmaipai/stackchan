# More games: a ranked list (playground track)

Status: plan, nothing built. Companion to `docs/plan/more-games-engine.md` (the firmware track's engine capacity and tool shapes). This file ranks new games by value for the cost, says what each needs, estimates its size, and says what it sounds like from the tone table. Every game ends on the shared game-over screen (`docs/design/game-over-screen.md`); a game with no real winner ends on Game over or Time's up (decision 33). A game needs its screen to meet the finger-size standard (`docs/design/screen-style.md`) and its memory row before it ships.

## What exists, so the estimates have a base

Grid games (Four in a Row, Memory Match, Hangman, Mine Finder, 2048, Snake) are small pure C cores the unit runs in `maipai_grid.cc`: the rules plus an optional search, 3 to 10 KB of source each (Hangman 3.3 KB, Match 3.1 KB, 2048 4.1 KB, Snake 4.2 KB, Mines 4.4 KB, Four in a Row with its search 9.6 KB), a game state of a few hundred bytes held in PSRAM while it runs, nothing at rest. Data packs (Tic-Tac-Toe, Color Memory, Whack-a-Mole, Do It, Rock Paper Scissors, Magic 8 Ball, Dice and Coin) are 1 to 4 KB each (16 KB ceiling, 12 touch regions, 8 counters). Sounds come from the tone table (`maipai_games_sfx_core.h`): about 160 bytes of table for nine clips, rendered when played. The renderer mirrors a grid game from the unit's own drawing code (`scripts/fw-face-render/grid_render.cc`), so each game below gets goldens the day its core exists. All flash figures are estimates **[est]** by analogy with those cores (flash code is about a third of the source size); none is measured.

## Ranked list

Cost is flash code plus state in PSRAM; nothing here needs internal RAM beyond the one game task the games already use.

| Rank | Game | Kind | Input | Flash [est] | State [est] | Sounds from the tone table | Risk |
|---:|---|---|---|---:|---:|---|---|
| 1 | **Higher or Lower** (cards, a streak; built as a core and screen, patch UX21, see `docs/design/higher-or-lower.md`) | data pack | two big buttons | 1.5 KB | 40 B | tick, good, bad | none: needs a card face (dots, the Match method) |
| 2 | **Dice Poker** (five dice, two rerolls, a hand rank) | grid core | tap dice to hold, Roll | 2.5 KB | 60 B | rattle (have), thud, fanfare | hand ranking table. **Built as a core, screen and goldens: `docs/design/dice-poker.md`, patch UX18** |
| 3 | **Reversi** (8 by 8, the unit plays; built, patch UX22, see `docs/design/reversi.md`) | grid core | tap a cell | 3 KB | 140 B | clack lo and hi, drop | the search must stay under 5 ms a slice (the Four in a Row slice pattern) |
| 4 | **Breakout** | grid core, timed | drag the paddle, or tilt | 3 KB | 200 B | tick by row, thud, lose | needs a 30 ms tick and redraw only what moves (SF78 does this) |
| 5 | **Balance** (a ball on a plate; keep it on) | accelerometer | tilt, continuous | 1.5 KB | 40 B | a soft rolling tick that rises in pitch toward the edge, lose | needs the analog tilt feed (below) |
| 6 | **Maze** (a marble through a labyrinth) | accelerometer | tilt, continuous | 2.5 KB | 150 B (8 by 8 maze from a seed) | tick on a wall, ting at the goal | analog tilt; a maze generator (about 60 lines) |
| 7 | **Battleship-lite** (6 by 6, one ship set, the unit hides) | grid core | tap a cell | 2.5 KB | 90 B | drop (splash), clack (hit), fanfare | none |
| 8 | **Flappy-style flyer** (tap to hop through gaps) | grid core, timed | tap | 2 KB | 80 B | tick on a pass, thud, lose | frame cost of a scrolling field: test on the frame table |
| 9 | **Racing** (three lanes, dodge; steer by tilt) | accelerometer | tilt left and right | 2 KB | 70 B | a rising engine tone, thud, lose | the head's small tilt range: a lane change per clear tilt (the discrete 4-way tilt of UI12 may be enough) |
| 10 | **Flying** (fly through rings, tilt up and down) | accelerometer | tilt forward and back | 2 KB | 70 B | whoosh, ting per ring | the discrete tilt is enough |
| 11 | **Pong** (against the unit) | grid core, timed | drag the paddle | 2 KB | 60 B | tick, thud | the unit's paddle speed sets the difficulty |
| 12 | **Tetris-lite** (10 by 8, swipe to move, tap to turn) | grid core, timed | swipes, tap | 4 KB | 120 B | clack, drop, a line clear fanfare | the most code of the list |
| 13 | **Darts** (a moving aim, tap to throw) | data pack | tap on time | 2 KB | 30 B | tick, ting by ring | timing needs the 80 ms engine tick: fine |
| 14 | **Pool-lite** (aim and flick, three balls) | new engine | drag to aim | 6 KB | 300 B | clack | physics: a fixed-point collision step (about 150 lines) and the frame cost of moving discs; rank last |
| 15 | **Blackjack-lite** | data pack or grid core | Hit and Stand buttons | 2.5 KB | 70 B | tick, good, bad | gambling feel: no money, points only |
| 16 | **Hangman variants** (animals, colors, a word you give it) | content only | the keyboard it has | 0 KB (a word list pack) | 0 | have | the pantry pattern (decision 24): a list, not code |

Already covered: connect-style (Four in a Row), trivia and quiz (the Q and A games, `docs/design/qa-game-screens.md`), shake games (Magic 8 Ball, Dice and Coin).

## Accelerometer games: what the unit can give

The accelerometer sits in the head and reads about 1 g along the axis that points up when the unit stands. Today a game sees four discrete tilts (left, right, forward, back: a 22 degree lean for two samples) and a shake (`maipai_games_input_core.h`). Balance, Maze and Racing want a continuous value. The firmware already filters the pull; a game could take the two filtered axes in tenths of a g each tick, through the same feed that carries the discrete tilt (`maipai_games_imu_feed`). That is the one engine change this list asks for: **an analog tilt reading, two 16-bit values a tick, 4 bytes of state**, and a dead zone of about 0.1 g so the head's rest pose reads as flat. The tilt range on a desk robot is small (the head turns, the body does not move), so continuous games use the head's lean as a gentle input and show the plate or the marble large on screen so a small lean reads. Racing and Flying are fine on the discrete tilt alone.

Safety: the head must not be driven by a game while the person tilts it, and a held or carried unit never starts a tilt game (the limiter already refuses head motion when carried).

## Sounds

Nothing new is stored. Each game above names clips from the existing table (tick, clack, drop, thud, ting, good, bad, fanfare, lose, draw, rattle, the grid clips of SF72). A rising tone (Balance, Racing) is one segment whose start and end pitch the game sets at run time: no new table entry. The tones are checked by `scripts/render-unit-sounds.py` and listened to on the sounds page (`scripts/sounds-demo.py`) before they ship.

## Memory notes

Every game runs on the one game task, allocates its state in PSRAM when it starts and frees it when it ends (the grid pattern), so nothing is held at rest and no persistent internal block of 2 KB or more is added (the rule of decision 11). The shared game-over screen is about 14 small LVGL objects built at the end and freed on Play again or Quit. A game with a search (Reversi, Battleship-lite's unit shots) bounds each slice to 5 ms as Four in a Row does. A timed game redraws only what moves (SF78). The memory model of the virtual unit (`schema/memory-budget.json`) gets a row per game when it is built; a placeholder row counts as "to measure".

## Suggested order

1. Higher or Lower and Dice Poker (cheap, no engine work, a new feel).
2. Reversi and Battleship-lite (board games the unit plays, the grid pattern is proven).
3. The analog tilt feed, then Balance and Maze (the accelerometer is the robot's own trick; no phone has a head like it).
4. Breakout, Racing, Flying.
5. Tetris-lite and Pong if the frame cost allows; Pool-lite last, or never.

## What is not decided

Which of these the owner wants first; whether Blackjack-lite belongs on a child's robot (no money, but the theme); whether the accelerometer games should be off by default on a robot on a shelf (a bump should not start a game: they start only from the Games page or a spoken request, as every game does).
