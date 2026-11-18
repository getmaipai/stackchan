# Head moves are about twice as fast as before (2026-11-18)

The servo animation advanced a fixed 20 ms of animation per step, and a step ran only when 20 ms had passed since the last one. The body update calls came every 11 to 13 ms, so a step ran about every second call: 26 to 31 steps a second instead of the designed 50, and the head moved at roughly half the designed speed (measured with `self.bench.servo_rate`; reach per step 93 to 96 percent once the bench wrapper held the move).

Since patch SF28 a step still waits for 20 ms (the servo bus is written at most 50 times a second) but advances the animation by the real time since the last step, between 20 and 50 ms. The same move takes the same real time at any update rate. A ceiling of 400 degrees per second, scaled by the movement limiter's percentage (carried, cable, battery and orientation rules), keeps the head under the servo's own limit; the spring stiffness caps of the limiter stay as they were.

What changes for a person: every head move, dance step and look-at is faster than the images flashed before SF28. The dances were judged on the slower motion; check one on the unit when a person is there. Host test: `host/tests/firmware/servo_clock_core_test.c`.
