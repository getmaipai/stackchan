<!-- Bench note copied from the bench agent's notes; paths, serial ports, hashes, addresses and ids removed. -->
# Bench window 11 (2026-11-18, script only)

R = <path> (checkout origin/main 9419027, the SF34 commit). Data: ./bench-w11-data/.
Recorded first: ota_0 = 1.6.2-maipai.1; backup <path> (ota_0 identical to the window-10 record). Limiter as found: usb_limit "limited"; at the end read back: limited (and the flash restore).
Image checks:
- b29 build-bench: built 07:42:28, three minutes BEFORE the SF34 commit time (07:45:19). It does carry SF34 content (the new tools are in it: heap_info, say_test, and servo_rate answers the new fields anim_ms and steps_per_anim_s, the status has the applied block with state and age_ms). I used it. I did not ask.
- b29 build-aec: built 06:45:12, no SF34 (no say_test, no heap_info). So no image has both the AEC overlay (barge) and say_test: barge-in cannot be tested. Blocker, details in (4).
- bisA build-bench no longer exists (the bisA tree is gone). final15 has build-bench/gate/plain from Nov 17 21:05 and none contain heap_info; bisnoSF, bisSF09, bisSF12 and b7 do not either.

## (1) Heap map (self.bench.heap_info {min_used 4096}), b29 bench, first-run finished, 3 calls (bench-w11-data/heap-b29-bench-1..3.json)
bisA and final15 were NOT run: bisA is not on disk, and no final15 (or bisSF) image has the tool. A comparison needs those two rebuilt with SF34's bench tool.
| call | largest free | total free | free blocks | used >= 4 KB | tasks |
|---|---|---|---|---|---|
| 1 (about 60 s after boot, before the link tasks) | 46,804 | 87,432 | 8 | 11 | 23 |
| 2 (after the host link is up) | 25,624 | 66,628 | 16 | 14 | 26 |
| 3 | 25,624 | 67,192 | 16 | 14 | 26 |
Call 3: largest free blocks [address, size] 3fcf1be4 25,624; 3fcc90ac 14,736; 600fe180 7,780; 3fcc5744 6,144; 3fcc7400 5,428; 3fce2ca0 3,884. Used blocks above 4 KB with owner: wifi 6,656 at 3fcbd430; tcp_receive 4,096 at 3fcc1848; ws_reconnect 4,096 at 3fcc4740; taskLVGL 8,192; (no owner) 4,096 at 3fcf0bc0; esp_timer 4,096; main 6,656; tcp_receive 65,536 at 3fcbca44 (the receive buffer); no owner 6,400 at 3fccca48 and 6,400 at 3fcce34c; no owner 30,720 at 3fcd0704; stackchan 5,120; audio_input 4,096; audio_output 4,096. Task stack bases: main 3fcb9674, taskLVGL 3fcec418, stackchan 3fcdb9b4, tcpip 3fce6a98, audio_input 3fce4474, audio_output 3fce55dc, servo_step 3fcdcf1c, dvp_task 3fcd81ec, sys_evt 3fce7d48, wifi 3fcbd430, esp_timer 3fcb81cc, Tmr Svc 3fcbc0ac, ipc0 3fcb655c, ipc1 3fcb6bc4, IDLE0 3fcbb1dc, IDLE1 3fcbb944, tcp_receive 3fcc1848, ws_reconnect 3fcc4740 (the others sit in PSRAM: imu, headtouch, seek, listen_ring, musicfeat, sertools, opus_codec, audio_afe).
What differs between call 1 and calls 2 and 3 (same image, link coming up): the two 4 KB stacks tcp_receive and ws_reconnect appear low in the heap (3fcc1848 and 3fcc4740), the 65,536 block changes owner label from wifi to tcp_receive, a 4,096 block with no owner appears at 3fcf0bc0 inside the area that was one 32 KB free block (3fcf02e4), and the biggest free block drops from 46,804 to 25,624 (the new 25,624 sits right above it at 3fcf1be4). The unowned 4 KB at 3fcf0bc0 is what splits the top free area; it is also at the place where the frag number (largest block against free) stays at 0.38 to 0.40. Fixing that one block's placement (or moving the two 4 KB stacks) is the lever.

## (2) servo_rate (R/rate11.txt, bench-w11-data/rate11.txt): 3 repeats each, idle, limited
| axis, step | steps | anim_ms | steps_per_anim_s | steps_per_s (1 s window) | interval ms median / p95 / max | stack min |
|---|---|---|---|---|---|---|
| yaw 15 | 40, 36, 36 | 800, 723, 725 | 50.0, 49.8, 49.7 | 40, 36, 36 | 20 / 24 to 25 / 25 | 1,636 |
| yaw 120 | 46, 45, 46 | 920, 904, 920 | 50.0, 49.8, 50.0 | 46, 45, 46 | 20 / 24 to 25 / 24 to 25 | 1,636 |
| pitch 25 | 39, 38, 39 | 779, 762, 781 | 50.1, 49.9, 49.9 | 39, 38, 39 | 20 / 23 to 25 / 25 | 1,636 |
| pitch 70 | 43, 42, 42 | 860, 861, 860 | 50.0, 48.8, 48.8 | 43, 42, 42 | 20 / 24 / 25 | 1,636 |
Steps per second while animating: 48.8 to 50.1, as designed. The 1 s counter (steps_per_s) is lower only because the move lasts 0.72 to 0.92 s of the 1 s window. Interval median 20 ms, p95 under 25, max 25. Stack margin 1,636 bytes.

## (3) Limiter (R/lim11.txt)
- Status headline with usb_limit limited: right after a boot or while idle it says state free, usb false, scale 100; about one to two seconds later it flips to usb_limited ("on a USB cable", usb true, scale 50, speed_cap 600). So it says usb_limited (not "limited") once the unit has seen USB; before that the headline is free.
- Applied block now has state and age_ms. A move made while the headline still said free was applied as free (angle 600 in, 600 out, scale 100, speed 1000 out), age 210 ms; two seconds later the block still showed that move (age 2,407) while the headline was usb_limited. With usb_limit off the applied state read usb_limited (scale 50, speed 600, age 1,922) for an old move before the switch, then free for the next move. So the limiter follows the usb flag at the moment of the move; the first move after idle can pass unlimited because the flag is not up yet.
- Dance, limit off (R/dance11-analysis.txt; about 33 to 38 samples a second, whole degrees): robot yaw peak 508 deg/s on a 100 ms window (before 667) and 388 on a 200 ms window; happy yaw 193 (143 on 200 ms). The ceiling is 400 at scale 100: the 200 ms reading is under it; the 100 ms reading is 108 over, partly whole-degree rounding (about 10 deg/s) and partly a real short peak, so it is not clearly under. Limit on (limited): robot yaw 304 (100 ms) and 177 (200 ms), happy 136 and 88; the ceiling with the limit is 240, so robot's 100 ms reading is above it in this run (it was 241 in window 10).

## (4) Barge-in and soak
- Barge-in (20 rounds): NOT DONE. It needs the AEC overlay and say_test together; build-aec (06:45) predates SF34 and has no say_test, build-bench has say_test but no barge code (the "silence_ms" line and the wake-hit logic are in the AEC overlay only). Needed: build-aec rebuilt with SF34.
- say_test works on the bench image (one 15 s reply plays through the real playback path). Soak with what exists: 6 calls of say_test 100 s back to back (about 10.5 minutes, about 600 s of speech, R/soak11.txt): all answered ok, 0 resets, 0 watchdog, 0 panics, internal_free median 62,871 and lowest 62,559 over 61 lines. No barge code in this image, so "no self-interruption" is trivial here; the real soak needs the AEC image. Note: 384 "slow_out" lines (an output of 1 to 2 s) appeared during the speech, which is much more than in the short canned replies earlier; worth a look by firmware.

## Restore
Full flash of the backup, hash verified; ota_0 read back byte-identical. Host running, unit online (ws_up 08:06:16). USB lock removed.
