# Virtual unit fidelity: handlers against the firmware lambdas (2026-11-18)

What was done: a checker (Codex Luna low, read only) compared every tool handler in `scripts/virtual-unit/tools/*.py` with its firmware lambda and listed differences with line evidence. Pass 1 found 90 differences in 11 modules. A fixer run per module confirmed each one against the cited lines, corrected the handler or kept it (hardware values, checker wrong), and added a test per fix (`host/tests/test_vu_tools_*.py`). Pass 2 (same checker, fixed handlers) flagged 104 lines.

Reading pass 2: it did not converge, and the new flags are mostly different in kind: nitpicks on text, bounds and labels, "not established in the excerpt" cases, and some wrong flags (for example `self.face.gaze`, where the refusal words are identical). The checker is not a fixed point. What it does show are the real remaining gaps below.

## Gaps closed after pass 2 (2026-11-18, Codex fixes, tests added)

Games (`status`, `bench_event`, `bench_swipe`, `bench_install`), timers (`list`, `snooze`, `cancel`), `clock.set` bound, lock `bench_touch` and `bench_key`, and face `bench_mode` (all four modes). Reports: `.runs/vu-gaps-*.md` of that run; summary of the evidence is in the tests.

`timer.alarm` and `clock.get` now follow the zone's own POSIX rule with daylight saving (`scripts/virtual-unit/posixtz.py`, checked against the system zone database for 2026 in seven zones).

## Closed since (2026-11-18, with tests)

- Lock `bench_key` now follows the lock core's keypad rules: keys are ignored while the keypad is not up, at most six digits, every digit from the fourth on is checked against the code (no enter key), six wrong digits clear the entry, the keypad goes back to the lock screen after 15 s with no key. `host/tests/test_virtual_unit_fidelity.py`.
- `self.robot.set_head_angles` goes through the unit's own movement limiter (carried or on its side refuses, USB halves the excursion, battery bands, speed cap), and a carried unit ends a running dance. `self.bench.set_head` exists (the bench tool of patch SF23): the same move, answering the head's angles.
- A body (power, cable, Wi-Fi, battery, carried, orientation) drives the status bar, the boot covers, the tired look and the limiter inputs (`scripts/virtual-unit/hw.py`, `docs/dev/virtual-unit-3d.md`).
- The tool list is generated from the patches in order and checked against the firmware sources (`tools_extract.py`, 138 tools).

## Known remaining differences

- Anything the unit measures (counters, timing, camera, radio) is a fixed documented value; the virtual unit's head is a ramp at the commanded speed, while the real servo caps its own speed and acceleration (the bench saw 40 to 46 percent of a step in 0.6 s). The physics mode models that cap; its numbers stay assumed until `calibrate.py` has a clean recording.
- Boot cover durations, the dances' head paths and the serial cable's effect are stand-ins.
- The unit ignores head moves while idle unless idle movement is on; the virtual unit moves the head whenever asked (the bench tool exists for that reason on the real unit).
- The petting reaction is host-driven (the firmware's own reaction is compiled out: `kUnitPetReaction` is false), and the renderer does not draw face decorators (hearts, sweat), so a head touch cannot be shown as the unit shows it.
- The checker is not a fixed point: a third pass would flag new nitpicks. Fix a gap when a test needs it.

## How to use the virtual unit given this

Trust a handler for the result shape, defaults, refusals by name and the main state change. Do not use it as proof for the listed gaps or for anything the unit measures (counters, timing, camera, radio). A bench check that matters is proven on the unit; the virtual run is the dry run.

The pass 1 and pass 2 reports are in the coordinator's notes folder (`vu-handler-checks`). Fixing the list above is a small Codex job per module; do it when one of those tools starts to matter.
