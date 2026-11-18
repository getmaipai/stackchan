# Reachy Mini: what the virtual unit gives a second robot (2026-11-18)

One page. The virtual unit (`scripts/virtual-unit`) has pieces that depend on the StackChan firmware and pieces that depend only on the idea of a robot with tools. This lists which a Reachy Mini body would implement, reuse as is, or skip. Facts about the Reachy body: `host/maipai_body/bodies/reachy_mini/profile.py` (6-DoF head with roll, antennas, body yaw, camera, microphones, speaker, no screen, no LED ring) and the HAL seam (`hal/seam.py`: `HeadActuator`, `AudioIO`, `StateFeed`).

## Reuse as is (nothing to write)

| Piece | Why it carries over |
|---|---|
| The side panel of the 3D view (`view.py`, `view.html`): call a tool by name, the log with the fake clock, scenario playback, record and replay | it speaks only `tools/list`, `tools/call` and a few `sim/*` messages; it never looks inside a tool |
| Scenario format (`scenarios.py` steps: call, advance, raw) and recordings (`recordings/*.json`) | steps are tool calls and waits; a Reachy scenario is the same file |
| The release report and the gate checker (`scripts/release-report.py`, `scripts/gate-check.py`) | image size and memory sections say "not measured" when a body has none; the spoken-turn latency gate is body independent |

## Implement for Reachy (small, and the point of the exercise)

1. **A tool schema for the body** (`schema/tools.json` equivalent): the list of tools the Reachy body offers, with argument types. The StackChan one is generated from firmware patches; the Reachy one would be generated from the daemon's API (or written by hand once, 10 to 15 tools: head goto with roll, antennas, body yaw, volume, camera frame, state feed).
2. **Handlers behind a registry** (`tools/<group>.py`, `@tool("...")`): head and antenna moves on a fake clock with the profile's limits (`AxisLimit`), the same refusal reasons the daemon gives. `bodies/reachy_mini/fake.py` already holds this behavior at the HAL seam; the handler layer would call it.
3. **A parity suite** like `test_virtual_unit_parity.py`: every tool in the schema is simulated or a named gap. It caught real drift on StackChan (a removed tool) in its first run.
4. **Golden motion traces instead of golden frames**: Reachy has no screen. A scenario records head and antenna joint values over fake time and compares them to a stored trace (tolerance per axis), the way the screen scenarios compare pixels.

## Not needed for Reachy

- The LVGL renderer, golden frames, face consistency, contact sheets, frame cost and the screen style standard: no screen. (The eyes are physical antennas and the head; the expression mapping is a host-side table, tested already.)
- First-run screens, the Updating cover, the link covers: the daemon app flow does these in the Reachy dashboard.
- Memory gates in bytes: Reachy runs on a Pi-class computer or a PC; the governor proposal (`spec-proposals/memory-governor.md`) says a body states only the budget classes it has.

## Needs a decision or new work

- **A 3D model of the Reachy head** for the browser view (the StackChan view draws a box and a screen texture). The side panel and the gesture log carry over; the model and the mapping from joint angles to the model are new (about a day with a simple URDF-based figure; the daemon serves its URDF at `/api/kinematics/urdf`).
- **Shared tool names**: the head tools differ (StackChan has yaw and pitch; Reachy has roll, antennas and body yaw). The shared spec would name the common core (`head.goto`, `audio.volume`, `battery.status`, `camera.frame`) and let each body add its own; that is a `commons/spec` proposal, not done here.
- **The simulator the host uses today** is the daemon's own simulation; the virtual-unit protocol would sit beside it as the fast, deterministic path for tests (fake clock) while the daemon simulation stays the realism check.

## Order of work if it is wanted

1. Hand-written schema and 10 handlers over `bodies/reachy_mini/fake.py` (Codex Luna low, one chunk). 2. Parity suite. 3. Motion trace scenarios. 4. The 3D figure last.
