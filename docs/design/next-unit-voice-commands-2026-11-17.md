# Next: more offline voice commands on the unit (review suggestion, 2026-11-17)

Placement: unit firmware. A basic the robot must do with no host and no brain (the carve-out in `docs/dev/scope-core-vs-home.md`). Local.

**What exists [from code]:** the unit already runs the speech library's wake word engine and its command recognizer for one command, the stop word (patch 049, internal RAM budget 051), plus a voice activity model and the echo handling tuned by patches L01 (no echo reference on purpose, after stutter) and L05 (wake detection mode).

**Proposal:** grow the offline command list beyond "stop": pause, resume, cancel (timer or alarm), next, previous, louder, quieter, mute, lock. Each maps to an existing unit action (timers 090 to 094, volume, mute, pages, the lock core). They work with the host asleep and add almost no RAM because the recognizer is already loaded; the cost is the phrase list and the model's grammar. English first. Spanish needs a check that the recognizer has a Spanish model [unverified]; if not, Spanish commands stay on the host.

**Rules:** the recognizer only listens while the unit already listens (after wake, or while a timer rings for stop); it never opens the microphone by itself; commands never bypass the lock (a locked unit accepts none); a destructive command (cancel) needs the target to be unambiguous or it asks on screen. A false-accept test with background speech and music is part of the gate.

**Echo cancellation (the audio front end):** the unit already has it available; patch L01 removed the playback reference on purpose because learning the room caused stutter and latency. Revisit only with a bench A/B (barge-in success rate while the robot speaks, stutter, internal RAM). Not planned now.

**Order:** after the current batch: (1) the phrase list and the action table with host tests and a bench false-accept run; (2) the on-screen disambiguation for cancel; (3) Spanish if the model exists.

## Languages (owner question, 2026-11-17)

Yes, the unit's command recognizer is language specific. The model on the unit is the English one (`mn5q8_en`, patch 049), and its commands are written as English phonemes with the speech library's phoneme tool. Chinese is the other language Espressif ships; whether any other language model exists is [unverified].

**What we do about it**
1. **One model, one phrase list per language.** The unit loads the one English model and swaps only the phrase list when the unit's language changes (a small table in the assets, a few hundred bytes per language). No second model in flash or RAM.
2. **English first, fully.** Stop, pause, resume, cancel, next, previous, louder, quieter, mute, lock.
3. **Other languages: a short critical list only**, written as the closest English phonemes (for example the Spanish words for stop, enough and quiet). This works for short, distinct words and fails for long phrases. It is measured, not assumed: clips made with the host's local voices in each language plus a native-speaker check, with false-accept and false-reject numbers. A language whose numbers miss the bar gets no unit-side commands.
4. **Everything else stays on the host.** The host's local command router already has phrase lists in six languages and runs with no model, but only while the host is awake.
5. **Touch is the offline fallback in every language.** Stop a ringing alarm with one tap; cancel from the Timers and Alarms apps; the control sheet. No language needed.
6. **Later options:** a custom keyword model trained for a specific word in a specific language (Espressif offers custom wake word training), or a newer multilingual model if one ships.

**Gate:** per language, at least 90 percent accepts on clean clips, under 1 false accept per hour of background speech and music, and no change in the memory gate.

## Wake word first, or no wake word (owner question, 2026-11-17)

**Default: wake word, then the command.** The wake word engine runs on the unit, so "Hi Stack Chan, quiet" works with the host asleep: the unit hears the wake word, opens a short command window (about 4 seconds), and the offline recognizer takes the command. No host, no network, no model. This is the mode for every command in the list.

**Commands with no wake word are limited to the moments the robot is already making sound** (armed states): while it speaks (the stop word today), while an alarm or timer rings, and while a countdown is ending. In those moments "stop", "quiet" and "enough" work alone, because a person is already being interrupted by the robot. At every other time the robot ignores command words.

**Optional, off by default: "hands-free" commands** (a setting): a very short list such as "mute" and "stop the timer" with no wake word. Off by default because every always-armed word is a false-trigger risk (a meeting, a video call, a TV). If switched on, the false-accept gate is stricter: under 1 false accept per 8 hours of speech and music, measured on the unit.

**Meetings and false triggers (what protects you now):**
- Mute and full quiet turn the wake word off entirely (the privacy switches already do this and show their cue).
- A Meeting preset (see `next-ui-countdown-2026-11-17.md`) sets the unit to do-not-listen for the length of the countdown, with a visible cue, then restores listening by itself. Voice: "meeting mode for an hour".
- A wake word sensitivity setting (low, normal, high) and the existing detection mode; the settings page shows the false wake count per day from the unit's own counters so the owner can tune it.
- The unit shows its listening state with the light and the face at all times; a false wake that hears no speech goes back to idle quickly (the quiet-turn rule).
