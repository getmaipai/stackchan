# Screens for the question and answer games

Owner decisions 25 to 27 (2026-11-18): a content pantry of jokes, riddles and trivia on the unit, and games the model can run (jokes, riddles, trivia, 20 Questions). These are the unit's screens for them, in the finger-size style of the other screens (`docs/design/screen-style.md`). The words come from the pantry or from the model through the host; the screens do not care which. The pantry and host design is the app track's. Patch: `firmware/patches/UX17-question-and-answer-game-screens.patch` (two header-only files: `maipai_qa_core.h` for layout, hit rectangles and words, `maipai_qa.h` for the LVGL drawing). Pictures: `host/tests/golden/screens/game-riddle-*.png`, `game-joke-*.png`, `game-trivia-*.png`, `game-twenty-*.png`.

## Rules for all three

- Every target is at least 56 px high (tiles 96 or 148 px wide) on the 8 px margin and 8 px gap, 8 px above the bottom edge. A touch in a gap, a margin or on the words does nothing.
- The banner row stays over the top 28 px. A header line at y 30 (16 px text) says where you are; the words start at y 50 in the 20 px text, or the 16 px text when the question is longer than 58 characters. The words' box is 58 px high; a text longer than 96 characters is cut with dots at its last line and never runs over a button, so the pantry check and the model prompt keep questions to 96 characters.
- Spanish is plain ASCII like the games' other text (the games' fonts have no accents). Right and wrong are told in words and in color, never color alone.
- The end of a round uses the shared game-over screen (`docs/design/game-over-screen.md`); nothing here draws its own.

## Jokes and riddles

| Part | What |
|---|---|
| Header | "Joke" or "Riddle" (Chiste, Adivinanza) |
| Words | The setup or question, typed like a caption: `mqa_typed_chars(total, elapsed, cps)` characters show at the pace of the voice or the offline mumble, a `_` cursor follows while it types |
| Answer | Hidden until Reveal, then in amber at y 124 (a one-liner joke has none) |
| Buttons (y 176) | **Reveal** (or **Next** when there is no answer, or after it) and **Stop**, 148 by 56 px |

A tap on Reveal while the caption is still typing shows the whole text and the answer at once. Next fetches another item; Stop returns to the games page. There is no score and no game over.

## Trivia

| Part | What |
|---|---|
| Header | "Question 3 of 10" at the left, "Score 20" at the right. After an answer the left becomes "Correct" (green) or "Not quite" (red) |
| Words | The question |
| Answers (y 112 and 176) | Two to four tiles: four are two rows of two (148 by 56), three are two and one full width, two are one row. The answer text shows in 20 px, or 16 px when longer than 12 characters |
| After a tap | The right answer turns green; a wrong choice turns red; the header says which. The next question follows after the robot has spoken the verdict (the game's timing) |
| End | The shared game-over: won when at least half were right, lost otherwise; the score line "Score 80"; best by the game; new best marked |

## 20 Questions (voice first)

The person thinks of something; the robot asks yes or no questions by voice, up to 20, and then guesses. The screen is the same whether the person says the answer or taps it.

| Part | What |
|---|---|
| Header | "Question 7 of 20" (or "My guess" in amber), and "Or just say it" at the right: the voice is the main way |
| Words | The question, or the guess ("Is it a banana?") |
| Tiles (y 112) | **Yes**, **No**, **Maybe**, 96 by 56 px |
| Buttons (y 176) | **I give up** and **Stop**, 148 by 56 px |
| End | The shared game-over. Open question for the owner: it is shown from the person's side, so the person wins when the robot runs out of questions and the person loses when the robot guesses (score line "It was a pear"), unless he wants the robot's side |

## What the unit and the host supply

The game supplies: the words, the typed progress or the answer states, the question number and score. The unit draws with `mqa::riddle`, `mqa::trivia`, `mqa::twenty` and routes touches with the rectangle lists and `mqa_hit()`. Voice and the model run through the host as the other model games do; a model game with no network says so in words and offers the pantry items.

## Proof and what is not proven

Thirteen goldens (every state above, trivia long and three-answer cases, the Spanish pairs) and two for the shared game-over (trivia new best, 20 Questions loss). The layout rules are checked in `host/tests/firmware/qa_core_test.c` through `test_qa_screens.py` (targets 56 px, 8 px gaps and margins, hit areas, the font rule, the typed pace, ASCII words); the screen audit reads only the main renderer's targets, so the core test is the spacing audit for these screens. Not proven on a unit: touch feel, the typed pace against a voice, long model answers (the cut with dots is the guard).
