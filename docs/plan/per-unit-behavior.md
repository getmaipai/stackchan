# Per-unit behavior (decision 16, many robots)

Placement: host (app track). Goal: a second connected unit gets its own touch, reaction, rest and idle handling; today only the first unit does.

## Today
`StackChanBehavior` (host/maipai_body/app.py) has 119 fields set in `__init__` and about 40 more hooks set by the `_wire_*` functions. One instance serves `voice.robot.robot`, polls `voice.robot.client.companion().poll_events` (the first unit's events) and runs one presence thread. Other units get privacy, timers, sounds and fan-out settings (see service-and-supervision.md), but a tap, pet or pick-up on a second unit does nothing on the host.

## What stays shared and what becomes per unit
- **Shared (by reference, set once):** the night rule, power rule, settings listeners and their values (idle level, look switches, greeting mode), the announce path, the sound service, the score book, the vision bridge and camera counters (one camera pipeline), the dance settings.
- **Per unit (new instance):** the robot handle (`create_stackchan_robot(client.for_unit(id))`), `event_poll`, the expression engine, the rest state (`_rest`, `_last_touch_wake`, `_hold_until`, `head_busy`), `reaction`, `reaction_tick`, `orientation`, the presence thread and its `_active` flag, the head filter, `unit_facts`.
- **Not duplicated now:** face search and tracking (`_search`, `_tracker`, `_sees`, `watch_for_faces`): they read one camera, so they stay on the primary unit until the camera path is per unit.

## Design
1. `UnitBehaviors` registry: `for_unit(id)` returns the primary behavior for the first unit, else a lazily built second instance created with `vision_bridge=None`, `watch_level="off"`, shared hooks copied by reference, and its own `event_poll`.
2. A trimmed loop for extra units runs `wake_on_touch` and `reaction_tick` first (built, step 2); idle render, `orientation_tick`, `rest_step` and `face_watchdog` follow in steps 3 and 4. A unit's event queue is read once, by the other-unit poll, which hands the events to the unit's behavior (`UnitBehaviors.feed`), so no event is lost to a second reader. The loop runs each unit inside `ACTIVE_UNIT`, so its faces and tools go to it.
3. Built on unit connect (`voice.session_listeners`), stopped on disconnect; one failure never touches another unit (`_warn_limited` is per instance).

## Migration order (each step green and pushed)
1. This plan. 2. `UnitBehaviors` with the trimmed loop and a unit test with two fake robots (touch on the second wakes only the second). 3. Reactions and orientation per unit (their wiring takes the unit's behavior). 4. Rest state and keep-awake per unit. 5. Music dance, self-heal hold, light and alarm services as per unit instances, one at a time. 6. Fleet e2e: two virtual units, a tap on each, the other unaffected; then the 10 and 25 unit fleet scenarios still pass.

## Tests
Unit: two `StackChanBehavior` instances with fake robots and event queues; events of one never reach the other; a raise in one loop leaves the other running. Rig: `scripts/virtual-unit/e2e.py` fleet scenarios with a tap injected on the second unit. Existing `test_many_units.py` and the chaos scenarios stay green after every step.

## Size
Steps 2 to 4 are about a day; step 5 is one service at a time (half a day each, five services); step 6 is half a day. Steps 5 and 6 can go to a cloud session once step 4 lands.

## Status
Step 2 built 2026-11-18: `unit_behaviors.py`, `test_unit_behaviors.py` (6 tests), fleet scenario `fleet_touch` (a stroke on unit 1, then unit 2: only that unit shows the heart); `second_unit`, `fleet_2`, `fleet_10`, `fleet_unit_state` and `chaos_cut_connection` stay green. Spoken reactions on extra units: closed 2026-11-18 (`speak_reaction(text, device_id)`; only that unit's own turn, speech and mute decide) and a rest that needs the per-unit turn state before it can run (step 4).
Step 3 built 2026-11-18: each extra unit has its own `OrientationReactions` (face, rotation, orientation timer, reassert on connect); the motion hold is the unit's own limiter (ML01). Fleet scenario `fleet_orientation` counts the handling (the host log names no unit): one tip is handled once, never by another unit's object. Spoken pose lines work per unit (see below).
Step 4 built 2026-11-18: `StackChanBehavior.extra_unit_tick` (idle look, touch, reactions, orientation, keep-awake, rest, face watchdog; no camera work) runs per extra unit; a turn on an extra unit is rendered by that unit's own behavior (the turn sink asks `UnitBehaviors.behavior_for(ACTIVE_UNIT)`), so its busy flag and wake from rest are its own; keep-awake is per unit; a connect resets that unit's rest clock. Test: two real behaviors keep turn and rest apart (one sleeps, the other stays awake). Fleet regression (second_unit, fleet_2, fleet_10, fleet_unit_state, chaos_cut_connection, fleet_touch, fleet_orientation, spoken_turn) green. Not proven: a real rest of a second unit over the 5-minute policy on a rig (too slow for the suite; a bench step). Steps 5 and 6 go to the cloud session.
Spoken reactions built 2026-11-18: `StackChanTurnBridge.speak_reaction(text, device_id)` speaks a reaction line to one unit of several; another unit mid-turn no longer silences it. `fleet_orientation` checks that unit 1 says its pose line aloud and no other unit speaks.
Step 5a (light) built 2026-11-18: each extra unit has its own ring light service (indicator, battery poll, sleeping state); the turn sink and the green live cue go to the unit that is talking or listening (`UnitBehaviors.light_for`, `bridge.live_sink_for`); a settle that arrives outside its unit's scope is routed to the unit that was talking; a light service ignores a repeat of the same fact (no redundant write). Fleet scenario `fleet_light`: a turn on unit 1 lights unit 1's ring and writes no other ring. Before this, a turn on any unit lit the first unit's ring (a wrong-unit privacy cue). Not per unit yet: the camera cue (one camera pipeline), a leak's fault look, music dance, self-heal hold, alarm service (steps 5b to 5d).
