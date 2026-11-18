<!-- Bench note copied from the bench agent's notes; paths, serial ports, hashes, addresses and ids removed. -->
# Bench window 7 (2026-11-18, script only)

R = <path> (checkout origin/main eb9efa6)
Image: b29 build-talkover (4,348,960 bytes, SF26 and SF27). Recorded first: ota_0 = 1.6.2-maipai.1; backup <path> (ota_0 identical to the window-6 record). First-run set done with self.bench.firstrun before the tests (same as window 6).

## (1) firstrun_loop (R/frloop-w7.txt, R/w7x.txt)
| call | free internal before | after | delta |
|---|---|---|---|
| n=20 | 89,503 | 89,743 | +240 |
| n=200 | 88,783 | 88,687 | -96 |
| n=200 (after a restart) | 69,759 | 69,751 | -8 |
| n=200 again | 69,791 | 69,703 | -88 |
No leak: 200 open and close cycles change free RAM by under 100 B.
Memory median line (fw-stress.py 600 s, which resets the unit at its start, so it ran after the loops but on a fresh boot): internal_free median 68,031, internal_min 33,484, int_big 25,600, frag 0.38, 0 resets/wdt/panics, GATE PASS (R/stress-w7.log). Finished-flow value for this image was 67,847, so it stays there (+184 B).
Because the stress script resets the unit, I also ran a passive check with no reset: restart, 2 x firstrun_loop n=200, then 10 minutes of the unit's own memory lines: 68 samples, median 70,163, lowest 69,183, internal_min 33,484 (idle, not under stress; R/serial/fw-serial.log).

## (2) Head speed: self.bench.servo_rate, window 1000 ms (speaking rows 800 ms), usb limit off, 3 repeats each (calls per s / animation steps per s)
Design target: 50 steps/s. Evidence R/rate-idle.txt, R/rate-anim.txt, R/rate-speak.txt.
| condition | axis, step | repeat 1 | repeat 2 | repeat 3 |
|---|---|---|---|---|
| idle | yaw 15 | 92 / 27 | 80 / 26 | 86 / 26 |
| idle | yaw 120 | 82 / 31 | 84 / 31 | 82 / 31 |
| idle | pitch 25 | 84 / 26 | 80 / 26 | 86 / 26 |
| idle | pitch 70 | 81 / 29 | 84 / 29 | 78 / 29 |
| face animating (bench_speak running) | yaw 15 | 92 / 26 | 74 / 26 | 87 / 26 |
| face animating | yaw 120 | 82 / 31 | 86 / 31 | 80 / 31 |
| face animating | pitch 25 | 82 / 26 | 80 / 26 | 74 / 26 |
| face animating | pitch 70 | 82 / 29 | 76 / 29 | 78 / 29 |
| speaking (canned audio through the host, started at tts_start) | yaw 120 | 60 / 28.8 | 52.5 / 26.2 | 67.5 / 30.0 |
| speaking | pitch 70 | 60 / 51.2 | 65 / 27.5 | 65 / 30.0 |
- The animation runs at 26 to 31 steps per second in every condition, about half of the designed 50, and does not depend on idle, animating or speaking (one speaking repeat read 51.2, a single outlier). Servo update calls are 75 to 92 a second (60 to 67 while speaking). Larger steps give slightly more steps per second (31 and 29 against 26).
- This matches the 22 to 25 to 30 range that would explain a head that moves at about half speed. Whether the cause is a 40 ms animation tick, a 2x slower servo update, or the step time per call is not shown by these numbers; firmware owns that.

## (3) Head recording with the fixed scripts/fw-head-record.py on origin/main (set_head, usb limit off), R/head-w7.csv, R/fit-w7.txt
- No wrapper this time. 350 samples, 24 moves, 206 ms round trip, about 5 samples a second. First samples after the first step: yaw 3, pitch 9, 9, 8, 9 (at rest, no jump; the readings are servo feedback).
- Reach is now almost full: pitch cmd 30 gives 28, 70 gives 67, 80 gives 74, 60 gives 56; yaw 60 gives 56, 120 gives 115, -120 gives -116 (93 to 96 percent), unlike windows 5 and 6 (about 0.5), which used my own wrapper with a zero-hold set_head; the earlier half-reach looks like an artifact of that wrapper, not of the unit.
- calibrate.py (no --write): verdict ok, rms 3.92 deg overall (pitch 2.76, 3.9 percent of a 70 degree step; yaw 4.81, 4.0 percent of 120). Fitted: yaw_kp 0.384, yaw_kv 0.0007, pitch_kp 0.351, pitch_kv about 0, joint_damping 7.4e-05, torque_limit 0.12, pitch speed cap 536 deg/s (yaw cap not reached: 16,917 deg/s), command delay 101.7 ms.
- Limiter: before the run state free, scale 100, speed_cap 1000, usb_limit "off" (I had set it off for the rate runs); the script did not need to lift or restore it. I put it back to "limited" and confirmed by reading status (limited, free, scale 100). It is back in any case after the flash restore.

## Restore
Full flash of the backup, hash verified; ota_0 read back byte-identical. The host (pid in <path>) is running and the unit is online (settings API; ws_up 06:22:03). USB lock removed.
