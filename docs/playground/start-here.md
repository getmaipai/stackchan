# Start here

## What it is

A StackChan on your screen. It runs the same display code the real robot runs, so its screens look the same. It has a 3D body you can turn, a head that moves, lights, a battery, two USB ports and a clock you can speed up.

## What it is not

It is a simulation. It is not your robot. It does not hear you or see the room unless you turn on the Talk feature (planned). Sounds, speed and servo strength are close to the real thing, not exact.

## Three ways to use it

| Way | What you need | State |
|---|---|---|
| **In the browser** | A browser. The site has no server. | Planned. The simulation only. |
| **On your computer** | Python and this repository. | Works today. |
| **Live, with one of your robots** | A robot paired to your own host. | Planned. You control one robot at a time. A banner says LIVE. |

### On your computer

1. Build the screens once: `bash scripts/virtual-unit/build-face.sh`, then `bash scripts/virtual-unit/build-screens.sh`.
2. Start it: `python3 scripts/virtual-unit/view.py 8780`.
3. Open http://127.0.0.1:8780/ in your browser. The address works only on your own computer.

You will see the robot's face. Click the screen to tap it. Drag to swipe. Swipe up from the bottom for the control sheet.

## Safe by design

Nothing you do in Simulation reaches a real robot. In Live mode the robot's own limits still apply: the head limits, privacy, the lock and the visible remote-control cue.

Next: [the screen tour](screen-tour.md).
