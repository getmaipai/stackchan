# Question and answer games on the unit: the interface and the rules (firmware track, 2026-11-18)

Riddles, trivia and 20 Questions (decision 26: model-powered games screens). The host (a language model or the pantry) makes the questions; the unit shows them, takes the person's answer, and ends on the shared game-over screen. Screens: `docs/design/qa-game-screens.md` (the playground). This note is the unit's tool and event shapes, for the app track to build the host half against. **Proposal, not built.** Nothing here changes the quiet, mute, lock, limiter or camera rules.

## Tools the host calls (all refused in full quiet, while locked and during an update, with a plain sentence)

| Tool | Arguments | What the unit does |
|---|---|---|
| `self.qa.start` | `game` (`riddle`, `trivia` or `twenty`), `lang`, `rounds` (trivia: 3 to 20) | Shows the waiting screen ("thinking") and replies `{ok}`; the unit starts a 2 minute watchdog: no message from the host for 2 minutes ends the game with a plain notice. |
| `self.qa.question` | `id`, `text` (at most 96 characters; longer is cut with dots), `choices` (trivia: 3 or 4 texts of at most 40 characters; riddle: none; twenty: none), `hint` (optional, riddle) | Shows the question typed at the caption pace (the voice or the mumble rate), then the choices or the buttons (riddle: Hint, Give up; trivia: the choices; twenty: Yes, No, Sometimes, I give up). |
| `self.qa.verdict` | `id`, `correct` (bool), `text` (at most 60 characters, optional), `score` (current score) | Shows the verdict for 1.2 seconds (green or red mark, the text), plays the right or wrong sound, updates the score line. |
| `self.qa.end` | `result` (`won`, `lost`, `draw`), `score_text`, `score` (integer) | Builds the shared game-over screen (UX15): the face, the result, the score line, the best line or the New best mark from the unit's saved best of that game, Play again and Quit. |
| `self.qa.stop` | none | Ends the game at once (the host going away, a new turn). |

## Events the unit sends (`device_events_push`)

| Event | Fields | When |
|---|---|---|
| `qa_answer` | `id`, `choice` (index) or `text` | the person tapped a choice (trivia) or a button (twenty: `yes`, `no`, `sometimes`) |
| `qa_hint` / `qa_giveup` | `id` | the person asked for a hint or gave up (riddle, twenty) |
| `qa_again` / `qa_quit` | `game` | a button on the game-over screen |
| `qa_ended` | `game`, `how` (`quit`, `again`, `timeout`, `host_gone`, `locked`), `score` | the game ended |

The unit never decides correctness: the host answers each `qa_answer` with `self.qa.verdict`, then the next `self.qa.question` or `self.qa.end`. Play again sends `qa_again` and waits for the host's next `self.qa.question`.

## The unit's rules

1. **Questions are short:** at most 96 characters, choices at most 40; the box cuts with dots as a guard, never a scroll.
2. **Typed caption pace:** the unit types the question at the speaking rate of the voice, or at the mumble rate when the mumble voice is on (about 14 characters a second), never faster than the screen can draw; touching the question shows it whole.
3. **Targets:** every answer target is at least 56 px on the 8 px margin and gap; an answer is taken on the lift.
4. **Sound:** the right and wrong sounds and the result sounds go through the sound policy (muted is silent, quiet hours the tone only), the same clips as the grid games.
5. **No head motion** (the games lint covers the new file), no camera.
6. **Best score:** the unit keeps one best per game in its NVS (like the grid games), shown on the game-over screen.
7. **No host:** with no host the question games are not offered (the host owns the content); a pantry-fed local mode is a later patch that reads typed records from the installed-set store (`docs/plan/pantry-reader-firmware.md`) and runs the same screens with `self.qa.local`.
8. **Safety:** question text comes from the host; the unit shows it as plain text and never interprets it. Child profile and content rules are the host's (`docs/SAFETY.md`).

## Build order

Core `maipai_qa_core.h` and `maipai_qa.h` from the playground's patch, then the state machine and touch routing (`mqa_hit`), the tools and events above with host tests for the state machine (a scripted host: question, answer, verdict, end), the game-over wiring, then the bench proof with a scripted host. Open owner question (in the spec): who "wins" 20 Questions on the game-over screen (proposal: the person wins when the unit's guess count is over 20 or it guesses wrong; the unit wins when it names the thing within 20 questions).
