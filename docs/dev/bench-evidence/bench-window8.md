<!-- Bench note copied from the bench agent's notes; paths, serial ports, hashes, addresses and ids removed. -->
# Bench window 8 (2026-11-18, script only)

R = <path> (checkout origin/main 1d7ffff). Copies of the CSVs and result files: ./bench-w8-data/ in this notes folder.
Image: b29 build-talkover rebuilt with SF28 (4,349,088 bytes). Recorded first: ota_0 = 1.6.2-maipai.1; backup <path> (ota_0 identical to the window-7 record). First-run set done with self.bench.firstrun.
Limiter as found: state free, usb false, usb_limit "limited", scale 100, speed_cap 1000. Final: the same (state free, usb_limit limited, scale 100, speed_cap 1000), read back before the restore flash.

## (1) servo_rate after SF28 (calls per s / steps per s; window 1000 ms, speaking 800 ms)
| condition | axis, step | repeat 1 | repeat 2 | repeat 3 |
|---|---|---|---|---|
| idle | yaw 15 | 92 / 37 | 78 / 24 | 90 / 28 |
| idle | yaw 120 | 89 / 32 | 96 / 32 | 96 / 37 |
| idle | pitch 25 | 84 / 29 | 84 / 25 | 92 / 29 |
| idle | pitch 70 | 90 / 29 | 88 / 28 | 82 / 30 |
| face animating | yaw 15 | 92 / 32 | 70 / 25 | 98 / 34 |
| face animating | yaw 120 | 90 / 41 | 94 / 39 | 98 / 43 |
| face animating | pitch 25 | 84 / 30 | 90 / 31 | 90 / 30 |
| face animating | pitch 70 | 90 / 37 | 88 / 33 | 88 / 35 |
| speaking | yaw 120 | 62.5 / 30.0 | 62.5 / 30.0 | 60 / 28.8 |
| speaking | pitch 70 | 72.5 / 30.0 | 50 / 32.5 | 58.8 / 55.0 |
- Before SF28 (window 7): 26 to 31. Now 24 to 43 (the face-animating, large yaw step reaches 39 to 43), most idle and speaking runs 28 to 37: not the 40 to 50 you expected, and only a little above before. Rows are noisy (24 to 37 within one cell). A step that finishes inside the 1 s window counts fewer steps in the rest of it, so the counter understates moves that end early; a longer window or a longer move would give a cleaner steps-per-second. Evidence: bench-w8-data/rate8-*.txt.

## (2) Head recording and fit (fixed scripts/fw-head-record.py, --usb-limit-off), CSVs head-w8.csv and head-w8off.csv
Important finding: with usb_limit "limited" (the setting as found) the script's --usb-limit-off does nothing, because motion.status reports state free (scale 100), so the script only lifts the limit when state is usb_limited. The head then reaches only 43 to 48 percent of each step (run head-w8). That limited setting halves the excursion even though the status reports no limit. I then set usb_limit off explicitly (head-w8off) and put it back to limited after.
| run | reach per step | rms | delay | speed caps | fit verdict |
|---|---|---|---|---|---|
| before SF28 fix (window 7, usb_limit off) | 93 to 96 percent | 3.92 | 101.7 ms | pitch 536 deg/s, yaw not reached | ok |
| head-w8, usb_limit limited | pitch 43 to 48, yaw 43 to 47 (small yaw 20 to 27) | 9.45 | 0.88 (start value) | pitch 2250 | poor |
| head-w8off, usb_limit off | pitch 92 to 96, yaw 93 to 98 (15 degree steps 67 to 73) | 4.91 (pitch 2.04, yaw 6.64) | 91.8 ms | pitch 495 deg/s, yaw 856 deg/s | poor (yaw) |
- Fit after SF28 with limit off: yaw_kp 0.314, yaw_kv 0.00005, pitch_kp 0.303, pitch_kv 0.0002, joint_damping 0.000035, torque_limit 0.203. Against before (yaw_kp 0.384, pitch_kp 0.351, delay 101.7): gains about 18 percent lower, delay 10 ms shorter, rms worse (4.91 vs 3.92) mainly in yaw. Reach is near 100 percent for large steps, as expected; small yaw steps (15 degrees) reach only 67 to 73 percent in whole-degree readings (4 degrees of error is large against 15).

## (3) Dance safety, limiter "limited" (as found), angles by get_head_angles pipelined (about 33 to 36 samples a second, unit timestamps from its own log; whole-degree readings, so speed from a 100 ms window carries about 10 deg/s of rounding)
Evidence: bench-w8-data/dance8-*.csv and dance8-analysis.txt.
| dance | yaw range / pitch range | peak speed yaw, pitch (100 ms window) | peak accel yaw, pitch (100 ms) | 200 ms window speed yaw, pitch |
|---|---|---|---|---|
| happy | -12..25 / 3..3 | 140, 0 deg/s | 1,352, 0 deg/s2 | 100, 0 |
| sway | -39..19 / 3..3 | 175, 0 | 1,377, 0 | 121, 0 |
| robot | -22..44 / 3..18 | 398, 54 | 3,801, 847 | 242, 54 |
- Limit is 400 deg/s times the limiter scale. The status reports scale 100, so the limit is 400: robot yaw reads 398 on a 100 ms window (only 2 under; by 200 ms window 242). If the "limited" setting really halves motion, as the reach result suggests, the effective limit is about 200 and robot yaw would be over it. Whether the limit counts the scale 100 or an effective 0.5 is a firmware answer; the numbers here are what the head did. Happy and sway stay far under in any case.
- Stop dance: robot dance started, self.robot.stop_dance sent at 3.0 s; the head went from yaw -22..41 to -4..0 and pitch 3 within the next second and stayed there for the following 6 s (bench-w8-data/dance8-robot-stop.csv). Stops: yes.
- The yaw and pitch for happy and sway pitch stay at 3: those dances move yaw only on this unit.

## Not done
Carried or tilted behaviour (a person's job).

## Restore
Full flash of the backup, hash verified; ota_0 read back byte-identical. Host running and the unit online (settings API, ws_up 06:44:31). USB lock removed.
