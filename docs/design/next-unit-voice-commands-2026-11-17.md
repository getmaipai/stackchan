# Next: more offline voice commands on the unit (review suggestion, 2026-11-17)

Placement: unit firmware. A basic the robot must do with no host and no brain (the carve-out in `docs/dev/scope-core-vs-home.md`). Local.

**What exists [from code]:** the unit already runs the speech library's wake word engine and its command recognizer for one command, the stop word (patch 049, internal RAM budget 051), plus a voice activity model and the echo handling tuned by patches L01 (no echo reference on purpose, after stutter) and L05 (wake detection mode).

**Proposal:** grow the offline command list beyond "stop": pause, resume, cancel (timer or alarm), next, previous, louder, quieter, mute, lock. Each maps to an existing unit action (timers 090 to 094, volume, mute, pages, the lock core). They work with the host asleep and add almost no RAM because the recognizer is already loaded; the cost is the phrase list and the model's grammar. English first. Spanish needs a check that the recognizer has a Spanish model [unverified]; if not, Spanish commands stay on the host.

**Rules:** the recognizer only listens while the unit already listens (after wake, or while a timer rings for stop); it never opens the microphone by itself; commands never bypass the lock (a locked unit accepts none); a destructive command (cancel) needs the target to be unambiguous or it asks on screen. A false-accept test with background speech and music is part of the gate.

**Echo cancellation (the audio front end):** the unit already has it available; patch L01 removed the playback reference on purpose because learning the room caused stutter and latency. Revisit only with a bench A/B (barge-in success rate while the robot speaks, stutter, internal RAM). Not planned now.

**Order:** after the current batch: (1) the phrase list and the action table with host tests and a bench false-accept run; (2) the on-screen disambiguation for cancel; (3) Spanish if the model exists.
