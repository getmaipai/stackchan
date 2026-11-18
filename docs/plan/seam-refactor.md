# Put StackChan behind the robot seam (plan step 4), proposal 2026-11-18

Goal: a second robot (Reachy Mini, a later step) shares the host by implementing the same seam, not by copying StackChan's wiring.

## What is there today (counted)
- `host/maipai_body/app.py` is 4,761 lines. `_serve_stackchan_channels` is 651 lines and builds everything in order: servers, the robot adapter, faces, the behavior object, privacy, timers, sounds, night, power, light, self-heal, the settings page, the encrypted listeners. Pieces share state through closures and `behavior.<attr> = ...` assignments.
- `StackChanBehavior` is 1,785 lines.
- Two turn engines: `run_loop.ConversationLoop` (the Reachy path) and `bodies/stackchan/turn.py` `StackChanTurnBridge`. Both implement wake, listen, think, speak, cancel, followup.
- The brain seam exists (`brain/interface.py`: `Brain`, `BrainFeature`, `TurnRequest`; `OwnLLMBrain`, `HomeBrain`) but the Home path bypasses it: the bridge builds `TurnClient`, `SttStreamClient` and `TtsPlaybackClient` itself (`stt_factory`, `turn_factory`, `tts_factory`), and own-model speech is a special case (`_local_speech_from`).
- The hardware seam exists (`hal/seam.py`: profile, actuators, audio, camera, IMU protocols); StackChan implements part of it through `StackChanRobotAdapter`, and the services reach the unit through `XiaozhiDeviceClient._call(tool, args)` strings instead.

## Target shape
1. `Body` (one object per robot kind) owns: its servers, its unit registry (per-unit client, privacy, events), and the services it needs. `StackChanBody` is built by one function, `build_stackchan_body(config, env)`, in `bodies/stackchan/wiring/`.
2. `app.py` only picks the body from the profile and runs it. No StackChan names in `app.py`.
3. One `TurnEngine` protocol (`listen`, `cancel`, `state`), implemented by both engines. Shared steps (wake patience, follow-up window, cancel, echo tail) move into one helper module both call.
4. Every answer goes through `Brain`: `HomeBrain` wraps the hub's STT, turn and TTS clients; `OwnLLMBrain` wraps the local engines. The bridge asks `brain.transcribe_stream`, `brain.stream_turn`, `brain.speak` and nothing else.
5. Per-unit: the registry hands each service the unit's own client (`XiaozhiDeviceClient.for_unit`) and privacy state (`PrivacyUnits`), so a second unit is not special.

## Order of work (each step its own small commit, full suite green: `bash scripts/test-all.sh`)
- **P0 Pin the behavior.** `tests/test_service_startup_pin.py` (background threads the service starts). Add before P1: a snapshot of the `behavior` attributes set by wiring, and the existing turn tests (`test_stackchan_turn.py`, the Home path tests) stay as the turn pin. Nothing moves in P0.
- **P1 Cut `_serve_stackchan_channels` into named builders** (`wire_listeners`, `wire_services`, `wire_privacy`, `wire_light`, `wire_settings`), same order, same closures, no behavior change; the startup pin must pass unchanged after each cut.
- **P2 Move the builders to `bodies/stackchan/wiring/` and return a `StackChanBody` object** instead of a bag of locals; `app.py` calls one function.
- **P3 Brain for the Home path.** Wrap the hub clients in `HomeBrain` methods (`transcribe_stream`, `stream_turn`, `speak`); change the bridge to call the brain; delete `_local_speech_from` by making `OwnLLMBrain` the same interface. Pin: the Home path tests and the own-model tests pass unchanged.
- **P4 One turn engine interface.** Extract the shared steps, make both engines implement `TurnEngine`; Reachy's loop is only moved, not changed.
- **P5 Body protocol.** `app.py` selects a `Body` by profile; the StackChan names leave `app.py`.

## Risks and how each is held
- A closure moved out of order changes behavior without failing a unit test: the startup pin (threads) plus the `behavior` attribute snapshot catch a missed assignment; hardware behavior is checked on the unit at the next flash window.
- The Home path is the one real users have: P3 lands only with the Home path tests green and a run against the fake hub.
- Two engines in the middle of P4: change one at a time, StackChan first.

## Not in scope
Firmware, the hub, and the Reachy hardware itself.

Status (2026-11-18): P0 and P1 done. P2 done in the form the code allows: `_build_stackchan_body` returns a `StackChanBody` (servers, pairing, link policy, units, faces, vision, behavior), `_wire_firmware_update` is out of the serve function (about 150 lines now); the `_wire_*` functions stay in `app.py` because tests patch names on that module. P3 done (`speech_backend.py`: `HubBackend` and `LocalBackend`). P5 done in part: `bodies/registry.py` is the one table that says which body a process serves and whether it is hosted; `app.py` asks it.

P4 decision: no shared `TurnEngine` interface. `ConversationLoop` is a polling loop the daemon body drives (`run(stop_event)`); `StackChanTurnBridge` answers one voice session at a time when the unit connects in (`listen`, `on_audio`, `abort`). They share no call shape, so a common Protocol would name methods neither can honor. What they share are the steps (speech to text, turn, text to speech, reply tags, the speech backend), and those already sit behind `speech/` and the P3 backend. Further sharing means moving steps into `speech/`, one at a time, when a change needs it.

Not done and why: moving the `_wire_*` functions into `bodies/stackchan/wiring/` (tests patch them as `app.<name>`; the move should follow a change of those tests), and taking every StackChan name out of `app.py` (the daemon body and the hosted body still share the file).
