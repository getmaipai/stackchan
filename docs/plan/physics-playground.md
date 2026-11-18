# Physics playground (plan and status, 2026-11-18)

Goal: an optional physics mode in the browser view of the virtual unit, so a desk robot's head can be pushed, nudged, shaken and lifted, and its servos watched working. Off by default. Walking and learning are out: StackChan sits on a desk.

## Shape
1. **Description file** per robot (`scripts/virtual-unit/physics/robots/stackchan.robot.json`). Every number is `{v, src, note}`; `src` is `measured` (a data sheet, the firmware, a bench recording) or `assumed`. Masses, sizes, joint limits and the tool speed range are measured; servo gains, torque limit, friction, the neck geometry and the mass split are assumed.
2. **Model builder** (`physics/mjcf.py`): the model text from the description. A free base on a table, a yaw hinge, a pitch hinge, a head box with the CoreS3's mass, position servos with gain, velocity gain, damping, dry friction and a torque limit, an IMU site. Inertia comes from the box shapes and masses.
3. **Driver and sandbox** (`physics/physics.js`, same for every robot): joint targets by role from the head target of the unit's own tool path (set head angles, look at, dances, after the movement limiter), IMU out, nudge, shake, lift, mouse push (Shift and drag), servo load, overshoot and settling readouts.
Interface for a second robot: `docs/plan/spec-proposals/robot-description.md` (schema, driver contract, honesty rule). A second desk robot (Reachy Mini) writes a description file and, if its layout is not pan-tilt, a builder; the driver does not change. No outside simulation assets are imported or copied.

## One code path
The flat unit stays the truth. The host computes the head target as before (limiter scale and speed cap, 40 moves a minute, dances). Physics only makes the body follow that target with real dynamics. The model's accelerometer and tilt go back to the host (`POST /imu`) and pass through `physics/imu.py`, the movement limiter's own pickup rule, which sets carried and orientation; the unit's limiter then refuses moves, shrinks them or lifts the limit exactly as on a real body. Lift the robot and `self.robot.set_head_angles` is refused with the limiter's words; put it down and it moves again.

## What physics adds
Settling and overshoot of the nod servo, steady error under gravity, servo load while dancing, the head ringing after a nudge, sliding and tipping when the table is shaken, a lift and drop that move the IMU numbers, a power-off head that sags.

## Engine and loading
The engine (Apache-2.0, official WebAssembly build, about 11 MB) loads from a pinned public address recorded in `physics/THIRD-PARTY-physics-engine.json`, only when Physics mode is switched on; nothing is vendored and the flat view stays light. It is named only in `THIRD-PARTY.md` and `NOTICE` (a test checks the playground's files). If the address cannot be reached the panel says so and the flat unit is unchanged.

## Calibration
`physics/calibrate.py RECORDING.json` fits the pitch servo's gain, velocity gain, damping and torque limit to a bench recording (angle against time, a step or a ramp, over serial) with the same equation the engine integrates, and with `--write` marks the fitted values `measured`. Tested on synthetic noisy recordings. A recording with one step identifies the gain well and the damping poorly: record a step and a ramp.

## Status
Built and looked at in the browser: model, servos, nudge, shake, lift (carried flag and limiter state change), settling readout, calibration, the spec proposal and tests (`host/tests/test_virtual_unit_physics.py`). Not done: yaw calibration (needs the yaw inertia), mouse push checked only by code, the glb body from the model branch (the view still uses its own shapes for display; physics reads only the description), anything measured on a unit.
