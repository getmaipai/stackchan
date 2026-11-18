# Request to the firmware track: an emergency stop (estop)

The shared spec lists `estop` as a capability with the verbs `engage` and `release` and the state `engaged` (`robot-api.json`, `capabilities.json`, and the StackChan device example). The firmware has none: a search of every patch finds no emergency stop, only the carried hold (ML01) and the stall guard in face tracking (FD04).

One-line request: add a tool pair `self.motion.estop` (engage, release) that sets the movement limiter to the same state as "carried" (every servo target refused, the head holds where it is, dances stop), keeps it until released, shows the state in `self.motion.status` as `estop`, and survives nothing: a restart releases it.

What the virtual unit does meanwhile: the panel's Carried hold and Stop dance stand in for it. When the firmware has the tool, the virtual unit maps its Stop button to it and the movement-limiter-state spec proposal gains the state name `estop`.
