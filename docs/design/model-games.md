# Model-powered games: jokes, riddles, trivia, 20 Questions, word chain (design, 2026-11-18)

Placement: unit (screens, tiles, mumble: firmware and playground tracks), host (skill, prompts, guard: app track, own-LLM package; Home takes over when paired). Design only, no code. Serves owner decision 27 (model games that work with only a model and the robot) and decision 24 (offline plan). Companion: `docs/design/content-pantry.md`. The game-over screen standard is `docs/design/game-over-screen.md` on branch `ux/unproven-games`. That branch is not in this mirror, so I could not read it. Section 6 states what this design needs from it and what to check when it is available (open question 1).

**Bottom line.** Five games, one start path. Each game has a body half (what the screen, the lights and the person's touch and voice do) and a brain half (a host skill that hands the model the rules, counts the score and guards the turn). Each plays in three states: S2 with a live model, S1 with the host and no model, S0 with only the unit. Only the five games below are in scope. Would you rather and bedtime stories already exist in `talk_games.py` and keep their current rules; the pantry carries stories for S0.

## 1. What exists

`host/maipai_body/bodies/stackchan/talk_games.py` has six talk games: twenty questions (24 rounds), riddles (8, scored), trivia (10, scored), word chain (20), would you rather (8), bedtime stories (6). A fixed start phrase starts one with no model call, the host keeps a small state per unit (round, limit, time of last turn), the model gets a rules text beside the persona for each turn, and a game ends on a stop phrase, the round limit or 300 seconds of silence. The host never filters, so the household's gates apply as they do in chat. The score stays 0 today: `add_point` is never called and the rules tell the model to "keep it in your own words". It is built, not flashed, not tested with a live model (`docs/user/games-and-pet.md`). The seven touch games run on the unit's engine and keep a best five scores (`docs/plan/more-games-engine.md`).

Gaps this design closes: no on-screen state, no real score, no game-over screen, nothing for S0 and S1, and the model keeps its own secret in 20 Questions only by playing the other way round.

## 2. The three states

| State | Who plays the host role | Input from the person | Output |
|---|---|---|---|
| S2 connected | the live model, with the host skill | voice, plus touch tiles | real speech, captions optional |
| S1 host, no model | the host skill, from its pantry library, no model | voice (speech to text is local) plus touch tiles | real speech (host text to speech) |
| S0 unit alone | the unit, from its shelf | touch tiles only, and the stop word | mumble plus captions |

S1 needs local speech to text and text to speech. If those are also down the host is in S0 for the game's purpose. Which games work in which state:

| Game | S2 | S1 | S0 |
|---|---|---|---|
| Jokes | live | pantry | pantry |
| Riddles | live | pantry | pantry, self-judged |
| Trivia | live | pantry | pantry, tiles |
| 20 Questions | live | not offered | not offered |
| Word chain | live | not offered | not offered |

20 Questions and word chain need a model: a fixed list cannot play them. When the model is gone the game's tile and its voice start are hidden, not shown dead (`AGENTS.md`: a missing brain half hides the feature). The person sees "needs the model" only if they ask for it by name.

## 3. The common frame (all five games)

**Start.** By voice with the existing fixed start line ("play twenty questions", "tell me a riddle", the Spanish asks, `talk_games.py` `_SPEECH`) or by touch from the Games wall, where model games get a second row of tiles under the seven touch games. A tile appears only when its brain half exists for the current state (section 2 table). Start costs no model call.

**Screen frame.** The unit already has a fixed top banner row for the game cue and a subtitle strip at the bottom (`docs/user/features.md`, "Top banner and subtitle strip"). Game play uses both: the banner shows the game icon and a round counter ("3 of 8"), the strip shows the caption. A game in progress does not hide the offline label. The face stays the main picture: eyes follow the game's mood tags, the mouth follows the speech or the mumble.

**Tiles.** Big touch targets at least 56 px high, four to a page, the same sizes as every page of choices (`docs/plan/dashboard-structure.md` states the robot standard). Colors sit in fixed places so the game is playable without telling colors apart (`docs/user/games-and-pet.md`). Swipe down from the bottom edge stops the game, and the bare word "stop" only hushes it, as in the touch games.

**Quiet rules.** Full quiet: a game does not start and a running one ends. Muted: tellings show as captions only, no mumble. Locked: no game starts.

**Stop.** Stop phrase, stop swipe, the round limit or silence ends the game with the game-over screen (section 6).

**Guard (host, every game).** The existing rule stays: the game rules never override the model's other rules, and the host adds no filter. Three host guards are new and are not content filters:

1. A turn limit per game and an overall cap (30 model turns per game) so a loop cannot run up cost.
2. The model reply is checked for the game's tag contract (section 4). A reply with no tag in a scored game counts as no point and does not stop the game.
3. In S1 and S0, only `kid` records are served unless the owner turned adult humor on (`content-pantry.md` section 6).

**Score and tags.** The model already receives the existing mood tags (cheer, think) and the host strips every tag before speech. This design adds a scoring contract on those tags: the rules text tells the model to end a reply with `[right]` when the person answered correctly and `[wrong]` when not; the host strips the tag, calls `add_point` on `[right]`, and keeps the round count. The host, not the model, owns the score, so the unit can show it. I did not find `right` and `wrong` in `host/maipai_body/reply_tags.py`; the module docstring in `talk_games.py` names them. Verify the names before building (open question 2).

## 4. The five games

### 4.1 Jokes

- **Body.** Tile "Tell me a joke". The robot tells the setup, waits a beat (1.5 s, an eyebrow raise on the face), then the punchline with a laugh face and a short laugh tone. Tiles after: **Another** and **Done**. No score. Round limit 5 per game, then "That is all the jokes I have for now" if S0 and the shelf is out of unheard jokes.
- **Brain, S2.** Rules: one short, kind, original joke per turn in the person's language; never repeat one told this game; end with `[cheer]`. The host passes up to 3 recent pantry jokes as "do not repeat" examples so the model avoids the pantry's.
- **Brain, S1 and S0.** Pick the next unheard `joke` record for this language and rating. Mark it heard when the punchline is told.
- **Game over.** No score line. Shows "5 jokes" and **Play again** and **Done**.

### 4.2 Riddles

- **Body.** Tile "Riddle". The robot says the question and the screen shows it in the strip. Tiles: **I know** (the person says it, S1 and S2), **Hint**, **Tell me**, **Another**. A right answer by voice or by the person tapping **Got it** after the reveal scores a point.
- **Brain, S2.** Existing riddle rules (one clear answer, one hint after a miss, the answer after a second miss, never repeat), plus the tag contract.
- **Brain, S1.** The host compares the heard answer to the record's `answer` (normalized, accents folded, an accepted list of up to 3 alternate spellings added to the record in a later format version) and replies from fixed lines ("Right", "Not quite, a hint: ...", "The answer is ..."). Without an accepted list the match is exact on normalized text, so a hint line is the fallback.
- **S0.** No microphone path beyond the stop word. The unit says the question, waits 8 seconds with a calm "thinking" face and dots, then shows tiles **I know it** and **Tell me**. **Tell me** reveals the answer in the strip. Then **Got it** and **Not yet** score the round honestly: self-judged. This is a game for a person and the robot, not a test.
- **Round limit** 8. Score is points out of rounds played.

### 4.3 Trivia

- **Body.** Tile "Trivia". Question in the strip and spoken. Three answer tiles in fixed places (top, middle, bottom, never color alone). A tap or the spoken answer picks one. Right: cheer face, chime, point. Wrong: kind face, the right answer shown. Round limit 10.
- **Brain, S2.** The model writes the question and three choices in one reply as a small structured block the host parses (question, three choices, which is right). The host shuffles the choices so the right one is not always in the same place and keeps the true answer itself. This removes the model's chance to change its mind. A malformed block is retried once, then the host takes a pantry record.
- **Brain, S1 and S0.** A `trivia` record's `answer` and `extra` (two wrong answers) fill the three tiles, shuffled by the host in S1 and by the unit in S0 (a small counter seeded by the heard counter, no random hardware cost). A trivia record without `extra` shows reveal only.
- **Verification.** Live trivia is not fact-checked by the host. The rules tell the model to ask only things it is sure of and to skip anything about recent events. The pantry's trivia was verified at generation (`content-pantry.md` section 6).

### 4.4 20 Questions

- **Played the other way round** (the existing rule): the person thinks of something, the robot asks yes or no questions. A model cannot keep a secret between turns.
- **Body.** Tile "20 Questions". Opening line: "Think of an animal or a thing. Say ready." Then the robot asks. Three tiles: **Yes**, **No**, **Maybe**, plus voice. The banner shows "Question 7 of 20". On question 20 or a right guess the game ends.
- **Brain, S2 only.** Existing rules. Added: the host holds the question counter (the model is told the count each turn, not trusted to keep it), and after question 20 asks "What was it?" and ends. A right guess is `[right]`, which gives the person no score; the game-over screen shows how many questions it took ("Got it in 11").
- **No S1 or S0.** Hidden.

### 4.5 Word chain

- **Body.** Tile "Word chain". The robot says a word, the person says a word that starts with its last letter. The strip shows the chain so far (the last 3 words) and the required letter in large type. Tiles: **Pass** and **Done**. Voice only for the person's word (typing is not available). A miss is the person's answer not starting with the letter, or a word already used.
- **Brain, S2 only.** The host keeps the used-word list and the required letter, and checks the rule itself (letter, not used). The model only picks its own word and says whether the person's word is a real word. The host passes both. The model is told its word must start with the letter and must not be in the used list. A score is the length of the person's chain.
- **Round limit** 20 words each. The game ends on a miss after one chance to retry ("Try again?"), on **Done**, or at the limit.
- **No S1 or S0.** Hidden.

## 5. Offline fallback and the mumble

In S0 the unit cannot speak. Decision 24 says the unit makes a code-made "mumble" and shows captions. No design for it exists in the repo (open question 3). What the games need from it:

- The mumble is generated in code from the caption text: short syllable bursts with a pitch that follows the persona, with no stored audio. The size cost is code, not data.
- The mouth follows the mumble using the same mouth cue path as speech (`host/maipai_body/mouth_cues.py`, `firmware/patches/mouth-cues-append`; read before building).
- Captions are forced on during a telling in S0 even when the owner left them off (decision 22 says off by default; this overrides it only while the unit has no voice). The caption is the strip at the bottom, one sentence at a time, held long enough to read (at least 2 seconds, plus 60 ms per character beyond 20).
- The mumble ends with the same stop and quiet rules as speech.
- The person is told once, on the first S0 telling, with one caption line: "I cannot talk right now, so I will read it." This line is a phrase string, not a model reply.

In S1 the host speaks the pantry record through its text to speech, so no mumble and no forced captions.

When the state changes mid-game (the host drops, the model returns) the game continues only if the new state supports it. Jokes, riddles and trivia carry on from the pantry. 20 Questions and word chain end with the game-over screen and a calm line, "I lost my thinking partner, so we will stop here", and the score so far is kept.

## 6. Score and game-over standard

The standard is `docs/design/game-over-screen.md` on `ux/unproven-games`, which this mirror does not have. Until it is read, this design commits to the following, which should match any sensible version of it, and lists what to compare when the file is available:

- A game-over screen for every game, shown on every end (limit, stop phrase, stop swipe, silence, state change).
- It shows the result in large type (score out of rounds, questions used, chain length), a short kind line, and two tiles: **Play again** and **Quit**. The same two buttons as Rock Paper Scissors (`docs/user/games-and-pet.md`).
- The best score is saved per game for scored games (riddles, trivia, word chain), kept to the best five like the touch games. 20 Questions keeps the fewest questions. Jokes keep none. Where: the unit's existing score storage, the same table the games wall reads for its tile caption.
- A game stopped early before round 1 completes saves no score (existing rule for touch games).
- Colors are never the only signal. No red except alarm and low battery (`docs/plan/OPEN-DECISIONS.md` item 7).
- No exclamation points in strings, grade 6 reading level for the fixed lines (`docs/STYLE.md`).

Compare when the file is available: the exact layout, the tile labels, the sounds, the order of result and best score, and whether the best score shows on the same screen.

## 7. Brain halves

| | Own-LLM | MaiPai Home |
|---|---|---|
| Skill | `host/maipai_packages/modelgames/` (or the existing `talk_games.py`, moved there if it belongs to the package scope; open question 4). Off by default, imported only when switched on in `robot.toml`. | Home runs the games with household rules and per person ratings. When paired, Home's version takes over (decision 1 test d). |
| Prompts | English rules, the model answers in the person's language, as today. | Home's own. |
| Guard | The three host guards in section 3. No content filter beyond what the connected model does (decision 13). | Home's household and child rules. |
| Pantry | Reads the package library (`content-pantry.md`). | Home's library through the same shelf format. |

`talk_games.py` currently sits under `host/maipai_body/bodies/stackchan/`. The boundary check forbids new Home feature code under `host/maipai_body` and treats a package as the home for optional features; whether the existing module moves is a placement call for the app track. A missing brain half hides the games.

## 8. Tests the playground needs

- Each game from start to game-over in S2, S1 and S0, with a fake model that returns fixed tagged replies.
- The tag contract: a reply with `[right]` adds one point; without a tag adds none; the tag never reaches speech.
- State change mid-game: host drops during a riddle (continues from the shelf), during 20 Questions (ends with the closing line and a saved score).
- Trivia shuffle: the right tile is in each of the three places over 300 rounds within 20 percent of even.
- Quiet, mute and lock rules.
- The screen tests for the banner, strip, tiles and game-over screen on the virtual unit, with the 56 px target check (`docs/dev/screen-audit.md`).

## Open questions

1. `game-over-screen.md` on `ux/unproven-games` is not in this mirror. Push it to a branch this repo can read, then compare section 6.
2. Confirm the `right` and `wrong` tag names and that the speech path strips them.
3. Who designs the mumble (decision 24)? The pantry only needs the interface in section 5.
4. Does `talk_games.py` move to a package? It is a Home-neutral feature that currently sits in `maipai_body`.
5. Does the owner want 20 Questions and word chain to appear in the unit's Games wall at all in S2, since the model may be slow (the latency of a turn is a second or more, `docs/design/latency-2026-11-16.md`)? I assumed yes.
6. Trivia in S2: accept the model's unverified facts, or add a second model call to check each? I assumed accept, with the skip-recent-events rule.
