# Next games (2026-11-17)

Placement: backlog note. Built today: Color Memory, Reaction Time, Whack-a-mole (data packs in `firmware/games/`). Owner asked for a Bop-It style game and Tic-Tac-Toe, and for other ideas. Build after the current UI batch (one flash window per batch).

1. **Bop-It style ("Do it!").** The bot calls an action and a clock runs: Tap, Swipe left, Swipe right, Shake, Pet the head, Tilt. It speeds up each round; a miss or a late move ends the run. Needs engine support for swipe, shake (IMU) and head-touch inputs and a voice or tone cue per action.
2. **Tic-Tac-Toe.** Three difficulty levels (random, blocks wins, perfect). Big 3x3 board filling the play area; the bot plays by tapping its mark and says its move.
3. **Simon Says (head and face).** The bot says "Simon says tilt me" and so on; only commands starting with "Simon says" count. Uses the IMU only.
4. **Rock, Paper, Scissors.** Tap a choice; the bot shows its pick with a face and a sound.
Skipped on purpose: any game that needs sound direction (the unit has one microphone).

0. **Whack-a-mole polish (owner, 2026-11-17).** Draw real moles (head, ears, nose, eyes, a hole and dirt mound) instead of colored circles, with several funny faces (grin, goofy tongue, startled, wearing a helmet) picked at random; a hit shows a dazed face with stars. Sounds: a funny "bonk" or squeak on a hit, different funny sounds for a miss and for a mole that escapes (a few of each, chosen at random); volume follows the unit volume. Drawn from shapes in code (no picture files); sounds as short synthesized tone sequences or small clips in the assets partition. Same layout rules as below.

Rules: every game button inside y 28 to 232 with at least 8 px margin and at least 44 px high; tones and lights start together; scores saved through the existing game store; games are data packs wherever the engine allows.
