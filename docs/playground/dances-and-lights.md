# Dances and the light show

Pick a dance on the robot's screen or call `self.robot.dance`. The four dances (happy, robot, panic, look around) start a **dance session**: the eyes look side to side, then the head nods, then it sways, then the full dance, then it winds down. It lasts about a minute.

| Step | What you see |
|---|---|
| 1 Eyes | The eyes step side to side on the beat. The head stays still. |
| 2 Nod | The head nods. The ring breathes mint and gold. One music note floats by. |
| 3 Sway | The head sways. The ring chases around. A small disco ball shows. |
| 4 Full | Head and eyes together. A gold swell on the ring. The disco ball, three notes and a burst of confetti. |
| Down | The same steps backwards, then the eyes look ahead and the lights go dark. |

A muted robot or one in full quiet keeps the plain keyframe dance. `self.robot.stop_dance` ends a session at once. Pictures of each step are the `dance-session-*` frames in `host/tests/golden/screens/`.

Back: [Start here](start-here.md).
