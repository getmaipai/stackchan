# Virtual unit fidelity: handlers against the firmware lambdas (2026-11-18)

What was done: a checker (Codex Luna low, read only) compared every tool handler in `scripts/virtual-unit/tools/*.py` with its firmware lambda and listed differences with line evidence. Pass 1 found 90 differences in 11 modules. A fixer run per module confirmed each one against the cited lines, corrected the handler or kept it (hardware values, checker wrong), and added a test per fix (`host/tests/test_vu_tools_*.py`). Pass 2 (same checker, fixed handlers) flagged 104 lines.

Reading pass 2: it did not converge, and the new flags are mostly different in kind: nitpicks on text, bounds and labels, "not established in the excerpt" cases, and some wrong flags (for example `self.face.gaze`, where the refusal words are identical). The checker is not a fixed point. What it does show are the real remaining gaps below.

## Gaps closed after pass 2 (2026-11-18, Codex fixes, tests added)

Games (`status`, `bench_event`, `bench_swipe`, `bench_install`), timers (`list`, `snooze`, `cancel`), `clock.set` bound, lock `bench_touch` and `bench_key`, and face `bench_mode` (all four modes). Reports: `.runs/vu-gaps-*.md` of that run; summary of the evidence is in the tests.

`timer.alarm` and `clock.get` now follow the zone's own POSIX rule with daylight saving (`scripts/virtual-unit/posixtz.py`, checked against the system zone database for 2026 in seven zones).

## Known remaining differences

- Lock `bench_key` models digits, delete and clear only; the firmware's keypad has more states.
- Anything the unit measures (counters, timing, camera, radio) is a fixed documented value.
- The checker is not a fixed point: a third pass would flag new nitpicks. Fix a gap when a test needs it.

## How to use the virtual unit given this

Trust a handler for the result shape, defaults, refusals by name and the main state change. Do not use it as proof for the listed gaps or for anything the unit measures (counters, timing, camera, radio). A bench check that matters is proven on the unit; the virtual run is the dry run.

The pass 1 and pass 2 reports are in the coordinator's notes folder (`vu-handler-checks`). Fixing the list above is a small Codex job per module; do it when one of those tools starts to matter.
