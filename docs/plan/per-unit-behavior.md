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
2. A trimmed loop `unit_loop` for extra units runs idle render, `wake_on_touch`, `reaction_tick`, `orientation_tick`, `rest_step` and `face_watchdog` (the same methods, no search or tracking).
3. Built on unit connect (`voice.session_listeners`), stopped on disconnect; one failure never touches another unit (`_warn_limited` is per instance).

## Migration order (each step green and pushed)
1. This plan. 2. `UnitBehaviors` with the trimmed loop and a unit test with two fake robots (touch on the second wakes only the second). 3. Reactions and orientation per unit (their wiring takes the unit's behavior). 4. Rest state and keep-awake per unit. 5. Music dance, self-heal hold, light and alarm services as per unit instances, one at a time. 6. Fleet e2e: two virtual units, a tap on each, the other unaffected; then the 10 and 25 unit fleet scenarios still pass.

## Tests
Unit: two `StackChanBehavior` instances with fake robots and event queues; events of one never reach the other; a raise in one loop leaves the other running. Rig: `scripts/virtual-unit/e2e.py` fleet scenarios with a tap injected on the second unit. Existing `test_many_units.py` and the chaos scenarios stay green after every step.

## Size
Steps 2 to 4 are about a day; step 5 is one service at a time (half a day each, five services); step 6 is half a day. Steps 5 and 6 can go to a cloud session once step 4 lands.
