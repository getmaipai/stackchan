<!-- Bench note copied from the bench agent's notes; paths, serial ports, hashes, addresses and ids removed. -->
# Bench window 10 (2026-11-18, script only)

R = <path> (checkout origin/main 10a3b79). Data copies and my recorder: ./bench-w10-data/ in this notes folder.
Image: b29 build-talkover with SF31 (4,351,520 bytes). Recorded first: ota_0 = 1.6.2-maipai.1; backup <path> (ota_0 identical to the window-9 record). First-run set done with self.bench.firstrun.
Limiter as found: usb_limit "limited", state free, usb false, scale 100. At the end: the same value (limited), read back; plus the flash restore.
USB-rule tool name: scripts/fw-head-record.py already calls self.motion.set {usb_limit: limited|off} (it does not use set_usb_limit); it judges and restores by reach (exit 5 if the reach did not come back). I did not use the script this window: it samples at about 5 per second (one tool call per sample, 206 ms round trip).

## Faster sampling (for the physics side)
No bench tool streams angles. self.bench.set_head returns only the end angle. What works: pipelined get_head_angles (six requests written back to back, no waiting) and read the unit's own log line, which carries a millisecond stamp; that gives 28 to 35 samples a second (mean 29.0, 28.8, 28.1 in the three recordings; 32 to 35 in the dance runs), about 6 times the script. Readings are WHOLE DEGREES. Sample times are unit time (log stamps), duplicates removed. The rate and this note are in the first line of each CSV (a # comment; I strip it for calibrate.py: *.fit.csv). Recorder: bench-w10-data/rec10.py (usb_limit limited|off, writes the applied block per move to *.applied.json).

## (1) servo_rate (R/rate10.txt), window 1000 ms, 3 repeats, idle, limited
| axis, step | calls/s | steps/s | interval ms: n, min, median, p95, max | servo_task_stack_min |
|---|---|---|---|---|
| yaw 15 | 98 to 100 | 34, 27, 26 | 98 to 100 / 14 to 15 / 20 / 24 to 25 / 25 to 26 | 1,684 |
| yaw 120 | 98 to 100 | 32, 33, 35 | 98 to 100 / 14 to 16 / 20 / 22 to 25 / 22 to 26 | 1,684 |
| pitch 25 | 98 to 100 | 26, 28, 27 | 100 / 14 to 17 / 20 / 21 to 25 / 24 to 26 | 1,684 |
| pitch 70 | 100 | 26, 27, 29 | 100 / 15 to 16 / 20 / 23 to 25 / 25 | 1,684 |
- Interval median 20 ms, p95 21 to 25 ms (under 30): as designed. Stack margin 1,684 bytes (over 600): fine.
- But steps_per_s is still 26 to 35, not near 50, although the median interval is 20 ms. The numbers disagree with each other: 100 intervals a second at a 20 ms median cannot add up to 28 steps a second. Either "steps" counts something else (only steps that moved the animation, not every 20 ms tick) or the interval list holds the calls (100 a second) and not the 20 ms steps. Firmware should say which; I report the raw numbers.

## (2) Head recording, usb limit on (limited) and off, via self.motion.set, applied block read right after each move (same call sequence)
Files: head-w10-limited.csv, head-w10-off.csv, head-w10-off2.csv (+ .applied.json and fit-w10-*.txt).
- Limited: every move shows applied angle_in 100, angle_out 50 (tenths of a degree: 10 degrees becomes 5), scale 50, speed_in 1000, speed_out 600 (speed_pct 60), while self.motion.status says state free, usb false, scale 100. So the limited setting really halves the angle and caps the speed to 60 percent whatever the status headline says. Reach: pitch 43 to 49 percent, yaw 43 to 49 percent of each step. Fit: rms 18.8 (poor; commands are halved, so the fit sees an unreachable target).
- Off: applied angle_out = angle_in, scale 100, speed 1000 for most moves, reach 92 to 97 percent. BUT in both off runs a second rule engaged mid-run: applied scale 30, speed_pct 40 (a ceiling of 400 deg/s times 0.4) for some consecutive moves (run 1: from the yaw moves on, status at the end orientation_limited scale 30; run 2: pitch 80 and then yaw 0, 15, 60 and pitch 10), then it cleared by itself. It started right after large pitch moves, so it looks like the orientation rule reacting to the unit's own head motion. Those moves reach only 16 to 42 percent. Run 2 per-move reach: pitch 30 93, pitch 70 16, pitch 80 28 (scale 30 applied), pitch 25 92, pitch 60 42, yaw 60 28, yaw -60 95, yaw 120 97, yaw -120 97. Fits are poor (rms 21.9 and 35.9) because of those clipped moves; no usable calibration from this window. The clean window-7 and window-8 off recording (rms 3.9 to 4.9) stays the best fit.
- Status headline vs the applied block: status flips between free (scale 100), usb_limited (scale 50, "on a USB cable") and orientation_limited (scale 30) while nothing is attached differently, and the usb flag changes between reads. The applied block is the reliable reading.

## (3) Dance, limiter on (limited) and off, peaks from the bus (about 33 samples a second, whole degrees; R/dance10-analysis.txt)
| limit | dance | yaw range / pitch range | yaw peak 100 ms window (accel) | yaw 200 ms | pitch peak 100 ms | pitch 200 ms |
|---|---|---|---|---|---|---|
| limited | happy | -11..27 / 3..3 | 109 deg/s (905 deg/s2) | 94 | 0 | 0 |
| limited | robot | -22..42 / 3..9 | 241 deg/s (2,054) | 166 | 29 (288) | 25 |
| off | happy | -27..28 / 3..3 | 186 (1,516) | 144 | 0 | 0 |
| off | robot | -44..44 / 3..19 | 667 (5,425) | 385 | 147 (1,529) | 78 |
- With the real limit on, robot yaw peaks at 241 deg/s on a 100 ms window (the expected ceiling 240) and 166 on 200 ms; happy 109. With the limit off, robot yaw reaches 667 (100 ms) and 385 (200 ms), above 400 times the scale; whole-degree rounding adds about 10 deg/s on a 100 ms window, so 667 is a real excess, not rounding. (Limit off is a bench setting.)

## (4) Memory median with the new servo task (fw-stress.py 600 s, limited)
internal_free median 64,093 (b29 talkover baseline 68,031: 3,938 B lower; you expected about 3 KB), internal_min 33,484, int_big 25,600, fragmentation 0.40 (floor 0.5: BELOW, so the gate fails on that alone), 0 resets, 0 watchdog, 0 panics, 0 host drops, lowest stack margins ipc0 372, ipc1 572 (the same as before). R/stress-w10.log.

## Restore
Full flash of the backup, hash verified; ota_0 read back byte-identical. Host running, unit online (ws_up 07:35:56). Limiter value back to limited. USB lock removed.
