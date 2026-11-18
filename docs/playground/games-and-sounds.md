# Games and sounds

The robot has games on its screen. A game never starts when the robot is in full quiet, and it never moves the head.

**Sounds.** The robot makes its game sounds from a tiny table of tones, so they cost almost no space. You can hear them as WAV files in `docs/dev/game-sounds/on-the-robot/`. Next to them are twenty sketches in `docs/dev/game-sounds/` that show what richer sounds could be, with what each would cost. Nobody has judged the sketches by ear yet.

Back: [Start here](start-here.md).

## 2048 and Snake

Both are steered by swiping, as on the robot: a swipe of at least 60 pixels in under half a second slides every tile of 2048 or turns the snake. In Mine Finder a tap opens a cell and a touch held for half a second plants a flag. The pictures of these games are drawn by the robot's own game code (`host/tests/golden/screens/game-slide-*`, `game-snake-*`, `game-mines-flagged`).
