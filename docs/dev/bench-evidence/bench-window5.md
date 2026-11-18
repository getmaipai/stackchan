<!-- Bench note copied from the bench agent's notes; paths, serial ports, hashes, addresses and ids removed. -->
# Bench window 5 (2026-11-18, script only)

R = <path> (checkout at origin/main 44c087c)
Image recorded first: ota_0 = 1.6.2-maipai.1; backup <path> (ota_0 identical to the window-4 record).

## (1) Memory per bisect step: fw-stress.py 600 s, bench images, host running, 20 s after flash
bisA and bisnoSF were NOT re-run; their numbers are from the b15 window (same script, same 600 s, same host state).
| image | internal_free median | internal_min | int_big | frag | gate | evidence |
|---|---|---|---|---|---|---|
| bisA | 69,533 | 33,484 | 25,600 | 0.37 | PASS | R/stress-bisA.log (earlier window) |
| bisnoSF | 69,609 | 33,484 | 25,600 | 0.37 | PASS | R/stress-bisnoSF.log (earlier window) |
| bisSF04 | 69,239 | 33,484 | 25,600 | 0.37 | PASS | R/stress-bisSF04.log |
| bisSF09 | 65,507 | 33,484 | 25,600 | 0.39 | PASS | R/stress-bisSF09.log |
| bisSF12 | 63,853 | 33,484 | 25,600 | 0.40 | FAIL (frag 0.40 vs 0.5; all else ok) | R/stress-bisSF12.log |
| b28 | 65,411 | 33,484 | 25,600 | 0.39 | PASS | R/stress-b28.log |
- The median falls at SF09 (first-run wiring): -3,732 B (SF04 only -370 B vs bisnoSF; SF12 a further -1,654 B). Minimum and largest block never change.
- b28 recovered 1,558 B over bisSF12 (63,853 to 65,411) and passes the frag gate again, but is still 4,198 B below bisnoSF and 94 B below bisSF09. So SF24's move of the mouth cue lists recovered less than half of the loss from SF09 plus SF12.

## (2) b28 build-talkover mic3_check (R/mic3-w5.txt). windows = [room, tone] 200 ms windows
| volume | gain_db | ch0 tone / room / peak | ch1 tone / room / peak |
|---|---|---|---|
| 0 | 0 | no data (windows [0,0], all zero; two tries) | no data |
| 0 | 24 | 53 / 165.6 / 517 | 3 / 3.4 / 31 |
| 40 | 0 | 17,153 / 164.8 / 17,949 | 213 / 1.1 / 220 |
| 40 | 24 | 17,152 / 167.1 / 17,758 | 975 / 3.4 / 995 |
| 70 | 0 | 38,514 / 166.1 / 32,768 | 755 / 1.1 / 762 |
| 70 | 24 | 38,511 / 160.1 / 32,768 | 3,486 / 3.4 / 3,517 |
- ch0 follows the volume (about 0 at volume 0) and ignores gain.
- ch1 follows the volume too (3 at volume 0 and gain 24, 213 at 40, 755 at 70) but moves only about 13 dB for the 24 dB gain step (213 to 975 is 13.2 dB; 755 to 3,486 is 13.3 dB), not about 24. By your rule ch1 is not a clean loopback; the numbers say it tracks the speaker but with about 11 dB less gain than set. Firmware's slot 2 and 3 rebuild should say which channel is which.
- The volume 0, gain 0 call returns empty windows every time; the other five calls are good.

## (3) b28 bench head recording
- scripts/fw-head-record.py on origin/main still calls self.robot.set_head_angles and still has the first-call "Unknown tool" and bare-true defects (no change found on any remote). I ran it through R/head_run5.py, which fixes those and maps each move to self.bench.set_head (hold_ms 0, speed 1000). Moves refused without that mapping (idle rule), as in window 4.
- With set_head the head follows: R/head-w5.csv (374 samples, 24 moves, median round trip 207 ms, about 5 samples a second, whole degrees). First samples after the first step (pitch to 10): 10, 6, 5, 5, 5 (settling at rest 5). Readings change with the commanded step and settle in about 0.6 s, so get_head_angles reports servo feedback, not the last target. But the head reaches only about 40 to 46 percent of each step (pitch 30 gives 12, 70 gives 32, 80 gives 37; yaw 60 gives 25, 120 gives 55). The limiter was lifted by the script; status showed state free; the reason for the shortfall is not known (speed or torque limit, a scale of about 0.4, or the unit's own limit).
- Fit (calibrate.py, no --write; R/fit-w5.txt): rms 9.16 deg (poor), yaw_kp 0.0847, yaw_kv 0.0265, pitch_kp 0.0293, pitch_kv 0.0333, joint_damping 0.0045, torque_limit 0.0047, command_delay 0.88 ms. Treat as unreliable: the shortfall is not modelled, and readings are whole degrees at 5 per second.

## (4) b28 build-linkpsk self.bench.link_selftest (R/linkpsk-w5.txt), 4 runs
| run | agree | ms | internal RAM dip (bytes) | min drop |
|---|---|---|---|---|
| 1 | true | 806 | 672 | 0 |
| 2 | true | 398 | 0 | 0 |
| 3 | true | 395 | -104 | 0 |
| 4 | true | 818 | 944 | 0 |
- Both sides agree every time; about 400 ms, or about 810 ms on alternate runs; free internal RAM dips under 1 KB and the minimum never drops.
- Firmware defect: the answer is invalid JSON when the six-digit code starts with 0 (run 2 returned "sas":041903, a leading-zero number); the serial tool wrapped it as text. The code should be sent as a string.

## Restore
Full flash of the backup, hash verified; ota_0 read back byte-identical; unit rejoined Wi-Fi (ws_up 04:51:19) and the host shows it online. USB lock removed.
