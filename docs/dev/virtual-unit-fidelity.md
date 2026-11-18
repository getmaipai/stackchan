# Virtual unit fidelity: handlers against the firmware lambdas (2026-11-18)

What was done: a checker (Codex Luna low, read only) compared every tool handler in `scripts/virtual-unit/tools/*.py` with its firmware lambda and listed differences with line evidence. Pass 1 found 90 differences in 11 modules. A fixer run per module confirmed each one against the cited lines, corrected the handler or kept it (hardware values, checker wrong), and added a test per fix (`host/tests/test_vu_tools_*.py`). Pass 2 (same checker, fixed handlers) flagged 104 lines.

Reading pass 2: it did not converge, and the new flags are mostly different in kind: nitpicks on text, bounds and labels, "not established in the excerpt" cases, and some wrong flags (for example `self.face.gaze`, where the refusal words are identical). The checker is not a fixed point. What it does show are the real remaining gaps below.

## Known remaining differences (concrete, with evidence in the pass 2 reports)

- Games: `game.status` returns inputs and board when no game runs (the firmware omits both); `game.bench_event` ignores its event argument (range 3 to 11); `game.bench_swipe` does not check the ranges; `game.bench_install` always refuses a valid pack.
- Timers: `timer.list` returns an `ok` key the firmware does not; `timer.snooze` does not refuse a zero or negative time; `timer.cancel` does not check the id range; `timer.alarm` uses a fixed zone table, not the device clock.
- Clock: `clock.set` accepts the exclusive maximum epoch.
- Lock: `lock.bench_touch` and `lock.bench_key` approximate the keypad path.
- Face: `face.bench_mode` knows `dirty` only (the firmware also takes `sprite_off`, `ls_wide`, `one_buffer`).

## How to use the virtual unit given this

Trust a handler for the result shape, defaults, refusals by name and the main state change. Do not use it as proof for the listed gaps or for anything the unit measures (counters, timing, camera, radio). A bench check that matters is proven on the unit; the virtual run is the dry run.

The pass 1 and pass 2 reports are in the coordinator's notes folder (`vu-handler-checks`). Fixing the list above is a small Codex job per module; do it when one of those tools starts to matter.
