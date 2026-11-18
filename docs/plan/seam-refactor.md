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

Status: P0 done (startup pin). P1 in progress: `_wire_power` and `_wire_light_and_health` are out of `_serve_stackchan_channels`; the long function is now about 560 lines. P2 onward not started.
