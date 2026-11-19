# Question games on the unit: what patch SF88 does differently from the interface table

The interface table is in `docs/plan/qa-games-firmware.md` (on the playground branch). Patch SF88 builds it, with these small differences. The host adapter should follow this page.

- **Choices travel as one text.** A tool property cannot be a list, so `self.qa.question` takes `choices` as one string with a `|` between the choices (`"Paris|Rome|Lima"`). Trivia needs two to four; riddle and twenty send none.
- **`self.qa.question` also takes `guess`** (true marks a 20 Questions guess: the header says "My guess"). `hint` is accepted and ignored: the riddle screen has no hint button.
- **`self.qa.verdict` also takes `right`:** the number (0 based) of the right choice, so a wrong answer can show the right tile in green. `-1` means unknown.
- **A riddle's Reveal asks the host.** The unit does not know the answer. Reveal sends `qa_giveup {id}`; the host answers with `self.qa.verdict` whose `text` is the answer; the answer then stays under the words until the person taps Next, which sends `qa_answer {id, text:"next"}`.
- **20 Questions answers** go out as `qa_answer {id, text:"yes" | "no" | "maybe"}`; I give up sends `qa_giveup {id}`. The host replies with the next `self.qa.question` or `self.qa.end` (no verdict needed).
- **Order rules.** `self.qa.question` is refused while the last question has no answer yet (the host waits for the event); it is accepted after a verdict, after Next and after any answer event. `self.qa.verdict` needs the id on the screen.
- **Also sent:** `game_started` and `game_ended` with the games' own fields (`game` is `qa_riddle`, `qa_trivia` or `qa_twenty`), so the host's game bookkeeping sees these games like the others. `qa_ended` carries `how`: `quit`, `host` (self.qa.stop), `host_gone`, `quiet`, `update`, `timeout`.
- **Best score:** one number per game in the unit's NVS (`mp_qa`), higher is better, shown on the game-over screen.
- **Not here yet:** the typed-at-mumble-pace rule needs no work (the same 14 characters a second); the pantry-fed local mode is the pantry reader's patch.
