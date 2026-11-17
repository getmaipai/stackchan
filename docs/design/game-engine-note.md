# Game engine note (Train 3 item 15, design only, 2026-11-16)

Placement: design note for the firmware lane. Nothing is built. Item 15 of `feature-gap-2026-11-16.md` is skipped in Train 3 on purpose: it is the one L-sized item, it needs a pack format that two lanes must agree on first, and `repo-boundaries.md` puts games in Home's package list with only the engine primitives in the `home` preset firmware. This note fixes the shape so the build can start cleanly.

## Update, 2026-11-16 (built)

Built as patches `G01` to `G03` and described in `games-2026-11-16.md`. The owner overrode the verdict below: the engine is in the core firmware behind `MAIPAI_GAMES` (default `y`), not only in the `home` preset, because the memory gate passed. Answers to the open questions: the pack is a compiled binary with a host compiler (question 1); the unit keeps the scores itself and the Home pack catalog and the way a signed pack reaches the unit are still open (question 2); none of the three games needs a per-frame draw loop (question 3).

## Verdict and scope

Verdict: REBUILD small, in the `home` preset (not the core image). The core image keeps its memory room for the face, timers and mood. Test against `AGENTS.md` scope: a game does not work with only the LLM and the robot, and Home already owns packs, scores and saved state, so Home supplies content and the unit supplies a player.

## Shape

- One player, no scripting runtime (firmware-memory.md). A game is a data pack, signed with the same Ed25519 key path as updates (patch 155), refused when the signature is wrong.
- The pack is a table, not code: `states` (a name, a screen made of drawn shapes from a fixed set: filled circle, rounded box, ring, text line in the shipped font), `events` (tap in a named region, timer elapsed, round counter reached, sequence step matched or missed), `transitions` (state, event, next state, optional actions), `actions` (play a shipped tone by name, set a counter, set a lamp color, add to the score, draw the next step of the sequence, end the game).
- Randomness comes from one seeded generator the pack names, so a pack is testable on a PC with a fixed seed.
- The player has a hard step budget per event (for example 64 transitions), so a bad pack cannot spin.

## Memory

- The pack loads into PSRAM when a game starts and is freed when it ends. Target: 16 KB per pack, 64 KB ceiling; the player's state is under 2 KB.
- Internal RAM cost while idle: zero. The player allocates nothing until a game starts and runs on the existing one-second and 20 ms ticks plus the existing LVGL timer. No new task.
- Flash: the player is about 6 to 10 KB of code, estimated, not measured. Packs live in the assets partition (3.7 MB free), a few KB each.
- Gate: a full spoken turn with a game running and the heap line for 10 minutes, same thresholds as every other step (internal_free at least 25 KB, internal_min at least 15 KB, int_big at least 16 KB, psram_min above 6 MB).

## First game: color memory

Four colored regions on the 320 by 240 screen (quarters inside the touch edges of `maipai_touch_core.h`). The unit shows a sequence with a lamp and a tone per color, the person taps it back. A round adds one step. A miss plays the error tone and shows the score. Best score is a 2-byte record in its own NVS namespace, written once at the end of a game, never during play.

## Rules the build must keep

- Touch edges stay reserved: a swipe from an edge still opens quick settings and the stop swipe still stops a game.
- Privacy and quiet states win: mute, full quiet and vision off still apply; a game never starts while the unit is in full quiet.
- Sounds go through the sound policy; hard mute silences the game.
- No game moves the head hard (safety-and-privacy.md: no hard shaking by games); a game may only use the existing eased moves.
- A pack that does not fit (size, signature, version) is refused with the problem and the next step in plain words, in English and Spanish.

## Open questions for the build lane

1. Pack file format: a small binary with a version byte and a checksum, or JSON compiled by a host script. Recommendation: compiled binary, host tool in this repo, so the unit has no JSON parser cost.
2. Where Home keeps the pack catalog and scores (Home package) and how the host hands a pack to the unit (the signed-update push path already exists).
3. Whether the second game (an action game) needs a per-frame draw loop; if so it needs its own measured budget before it ships.
