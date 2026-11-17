# Play games and care for your pet

The games and the pet mood run on the robot itself, so they work with your own LLM and with MaiPai Home. No finger, screen or sound has been checked on a robot yet.


## Games

The next robot image removes Reaction Time, makes games full height with a swipe-down bar and makes game sounds follow the system volume. Built, not flashed.

The robot has six games. Color memory, reaction time and whack-a-mole are on the flashed robot. Tic-Tac-Toe, Do It and Rock Paper Scissors, the funny moles and the talk games are built but not flashed yet, and not tested on a robot. They run on the robot itself, so they work even when MaiPai Home is off.

- **Color memory.** The robot shows a pattern with lights and sounds. Tap the colors back in the same order. Each round adds one step. Your score is the number of rounds you got right.
- **Reaction time.** The screen is red. When it turns green, tap as fast as you can. Three rounds. Your score is your average in milliseconds, and lower is better.
- **Whack-a-mole.** Funny moles pop up in a grid of nine holes: a grinning one, one with its tongue out, a startled one and one in a helmet. Tap each one before it hides. A hit gives a dazed mole with stars and a bonk or a squeak. A tap on the wrong hole and a mole that gets away each have their own funny sounds. There are 15 moles.
- **Tic-Tac-Toe.** <span class="planned-tag">Built, not flashed</span> Pick a level by tapping a row: Easy plays random moves, Medium takes a win and blocks yours, Hard never loses. You are X and go first. The robot plays its O and tells you its move, "I played row 2 column 3". A win scores 10, 20 or 30 by level, a draw 3, 6 or 9.
- **Do It.** <span class="planned-tag">Built, not flashed</span> The robot calls a move and a clock runs. Press the big tile that matches, or do the move itself: tap, swipe left, swipe right, shake the robot, pet its head or tilt it. Every round is a little faster. A wrong move or a late one ends the run. Your score is the moves you got right.
- **Rock Paper Scissors.** <span class="planned-tag">Built, not flashed</span> Tap rock, paper or scissors. The robot shows its pick. A tie plays again. Your score is how many you win in a row.

To start one by touch, swipe left on the face to open the Games page (or swipe up from the bottom and press **Games**), then press the game you want. Each tile shows your best score, and **More games** shows the rest. To start one by voice, say "play memory", "play reaction" or "play whack-a-mole". In Spanish, say "juega a memoria" or "juega a los topos". Say "what games do you have" to hear the list.

To stop a game, swipe down from the bottom edge of the screen, or say "stop". A game you stop early does not save a score.

The robot keeps your best five scores for each game. Open the robot's settings page and press **Show games and best scores** to see them.

A few rules keep games polite:

- In full quiet, a game will not start, and one that is running ends.
- If the robot is muted, the game still plays, with no sound.
- Games never move the robot's head.
- The edges of the screen still work while you play: a swipe that starts at the very side edge changes the volume, and the stop swipe ends the game. The page swipes and the control sheet wait until the game is over.

Colors always sit in a fixed place on the screen, so you can play without telling colors apart.

![The color-memory game with four shapes.](../images/game-memory.svg)

![The whack-a-mole variant mid-round.](../images/game-whack.svg)

To start one by voice, say "play tic tac toe", "play do it", "play rock paper scissors" or "play whack a mole".

Every game is a small data file that one built-in game engine plays. A game from outside the robot's firmware must be signed with the update key, and an unsigned one is refused with a plain message. Loading outside games is not switched on yet.

## Talk games

<span class="planned-tag">Built, not flashed</span> Not tested with a live model.

These games are played by talking, and the robot's language model plays them. You need a model connected (your own, or MaiPai Home).

Say one of these to start:

- "Play twenty questions" (you think of something; the robot asks yes or no questions)
- "Tell me a riddle"
- "Let's play trivia"
- "Word chain"
- "Would you rather"
- "Tell me a bedtime story"

Spanish works too: "juguemos a veinte preguntas", "dime una adivinanza", "juguemos a la trivia", "cadena de palabras", "qué prefieres", "cuéntame un cuento".

The robot starts with a fixed line, with no model needed. After that the model plays and reacts with faces and effects when you are right or wrong. A game ends when you say "stop the game", "I'm done" or "that's enough", when it reaches its round limit, or after five quiet minutes. Then chat is normal again. The games follow the same child and content rules as ordinary chat. The settings page lists them under **Talk games** on the Games page.

## Pet mood

The robot has a mood that depends on how you care for it. Petting, talking and playing lift it. Being ignored for days lowers it.
The mood is saved across days and shows in the face and the idle moves. It never affects what the robot can do for you.
Turn it off with `pet_mood = false`.

![Three mood faces: happy, bored and lonely.](../images/mood-faces.svg)


## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
