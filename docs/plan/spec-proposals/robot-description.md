# Proposal: robot description for the physics playground

A robot is one description file. The physics harness has three layers and only the first is per robot; a second desk robot (Reachy Mini) writes its own description file and, where its layout differs from a pan-tilt head, its own model builder, and runs the same driver and sandbox.

| Layer | Per robot? | What it holds |
|---|---|---|
| Description file (`robots/NAME.robot.json`) | yes | `params` (every number is `{v, src, note}` with `src` measured or assumed), `joints` (name, role, axis, limits, servo gains by parameter name), `sensors` (the IMU and its outputs), `capabilities` from the shared vocabulary |
| Model builder (`mjcf.py`) | one per layout | text of the physics model from the description; no number lives anywhere else |
| Driver and sandbox (`physics.js`) | no | maps the shared tool protocol onto joint targets by role, reads the sensors, runs nudge, shake, lift and push, and reports servo load and settling |

## The driver contract
- Inputs: the head target the unit's own tool path produced (set head angles, look at, dances, after the movement limiter), as role to value: `head.yaw`, `head.pitch`, `head.roll`, and so on in degrees. The shared spec's `head` part verbs (set, goto, hold, enable, disable) decide what is a target; `enable` false lets the servos go.
- Joint targets: for each joint whose role has a value, `ctrl = radians(value)`; the joint's `range` bounds it. A role with no joint is ignored and reported once.
- Outputs, named as the spec's `imu` part names them: `imu.accel` (m/s^2, specific force in the head frame), `imu.gyro` (rad/s), `imu.tilt_deg` (angle of the body's up axis from gravity). The host feeds these to the same carried and orientation rule as the unit's pickup detector (patch ML01), so the movement limiter answers for the simulated body exactly as for the real one.
- Extra read-outs, not in the spec: servo load as a share of the torque limit, overshoot and settling time of the last move.

## Honesty rule
A parameter marked `assumed` is a stand-in until `calibrate.py` fits it from a bench recording of real moves (angle against time over serial); the fit rewrites it as `measured` with the recording named in `note`. Never publish a physics result as the robot's behavior while the parameters it depends on are assumed.

Schema: `robot-description.schema.json`. Fixtures: one valid pan-tilt file, one with a role the vocabulary does not know.
