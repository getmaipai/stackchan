# Listen longer on the bench (developers)

After the wake word, the host waits 6 seconds for speech and then ends the turn. The robot has its own 8-second silence rule, so on the bench you never see it.

To test the robot's rule, start the host with the setting `MAIPAI_BENCH_MIN_LISTEN_S=12`. The host then waits at least 12 seconds. The setting never makes the wait shorter than 6 seconds and is capped at 60. It is for developers only and is off by default.
