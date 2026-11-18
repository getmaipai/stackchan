# Adding a second robot behind the seam

The Reachy Mini body is the worked example. A new robot is four things, each checked by `host/tests/test_second_robot_conformance.py`.

| Piece | Where | What the test checks |
|---|---|---|
| Profile | `host/maipai_body/bodies/<robot>/profile.py` | every axis has a source and date; each leased channel has a safe stop |
| Seam client | the same package (`client.py`, `fake.py`) | the client answers every method of `HeadActuator`, `AudioIO`, `Camera`, `Imu`, `FaceTracker` and `Teachable` that its profile claims |
| Robot description | `scripts/virtual-unit/physics/robots/<robot>.robot.json` | passes `docs/plan/spec-proposals/robot-description.schema.json`; every joint names real params; every number is `measured` with a source note or `assumed` |
| Shared records | `docs/plan/spec-proposals/` | the movement-limiter state, memory admission and brain capabilities records are the same shape for both robots |

## Rules
- One number, one place: the description's joint ranges equal the profile's axis limits (a test compares them). Change the profile, then the description.
- A param is `assumed` until a bench recording fits it. Never present a physics result as the robot's behavior while it depends on an assumed param.
- The Reachy description is a stub: the physics playground has no model builder for a 6-DoF head yet, so only the description, the profile and the fake are checked. The virtual unit (the StackChan fake) stays the first full simulation.
- What a Reachy adapter must still implement for the virtual unit panel is listed in `docs/plan/reachy-virtual-unit-readiness.md` (tool schema, handlers over `fake.py`, parity suite, motion-trace scenarios).
