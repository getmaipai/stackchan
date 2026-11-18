<!-- Bench note copied from the bench agent's notes; paths, serial ports, hashes, addresses and ids removed. -->
# Bench window 4 (2026-11-18)

R = <path>
Image recorded first: ota_0 = 1.6.2-maipai.1; backup <path> Ran on b19 build-bench, then b19 build-talkover.

## (1) Head recording: NO USABLE RECORDING, nothing fitted
- scripts/fw-head-record.py needed two workarounds (run through the wrapper R/head_run.py, repo script untouched): the first serial call after opening the port is answered "Unknown tool", and the move tool answers a bare true, which the script reads as a dict and crashes on (`reply.get`). Both are script defects for the firmware track.
- Two full runs, both axes, small and large steps, usb limit lifted for the run: R/head-w4.csv, R/head-w4b.csv (408 samples each, 24 moves, median round trip 205 ms, so about 5 samples a second; angles are whole degrees).
- First samples after the first step: pitch 10 (row at send), then 7, 5, 5, 5. After that pitch reads 5 and yaw 3 or 4 in every hold for every commanded step (pitch 30 to 80, yaw 15 to 120), so the readings are neither the last target nor a response: the head did not follow any step.
- Cause found in the serial log: `set_head_angles ignored: idle and idle movement is off`. The unit ignores head commands while idle unless idle movement is on, and the host keeps turning idle movement off (log lines `set_idle_motion: false`). With idle movement on, the head moves on its own random path (yaw and pitch change with no command), so the commanded steps are still not followed cleanly. The household's own bot process (releases/0.2.104 under /usr/local/maipai-home) is also running; I did not touch it.
- So I cannot say whether get_head_angles reports servo feedback: the values do change when the head moves by itself (yaw 20 to 6, pitch 27 to 17), which points to feedback, but no clean step exists.
- Fit: scripts/virtual-unit/physics/calibrate.py on R/head-w4b.csv fails with a math domain error on this flat data; no gain, damping or delay reported, nothing written (`--write` not used).
- Needed from the firmware track: a bench way to command the head while idle (a bench tool or a flag that bypasses the idle rule), or a non-idle state the bench can hold for 45 s.
- Limiter check: during the run the limiter read free (usb limit off); the script puts it back; the final state is restored with the flash.

## (2) MIC3 corrected check, build-talkover, MIC1 NOT covered (needs a person to cover it). Evidence R/mic3b.txt
| volume | gain_db | MIC1 tone / room rms / peak | MIC3 tone / room rms / peak |
|---|---|---|---|
| 0 | 0 | 11028 / 769 / 13929 | 154 / 11.1 / 189 |
| 0 | 12 | 11321 / 1622 / 22677 | 157 / 20.8 / 346 |
| 0 | 24 | 11130 / 63 / 32768 | 155 / 1.5 / 514 |
| 70 | 0 | 11054 / 3916 / 17349 | 154 / 56.7 / 252 |
| 70 | 12 | 11235 / 63 / 32768 | 156 / 1.5 / 586 |
| 70 | 24 | 11373 / 621 / 17424 | 158 / 8.9 / 269 |
- With the speaker volume at 0 the tone amplitude is the same as at 70 (MIC1 about 11,000, MIC3 about 155). A tone that does not shrink with volume 0 is not coming through the air: the tool's tone reading looks digital (the played signal itself), so the earlier "MIC3 passes" numbers do not show an acoustic MIC3. The "room rms" figures swing from 1.5 to 3,900 between calls with nothing else changing, so the room figure is also unreliable (it may include the end of the previous tone or other sound).
- The test with MIC1 covered was not done: it needs a person to cover MIC1 (a finger over the left hole) while the tool runs. Run it at volume 70 gain 12, then volume 0.

## Needs a person
1. Cover microphone 1 and run mic3_check (volume 70, then 0).
2. If the head recording is retried on hardware, nobody is needed, but the unit must be put in a state where it accepts head commands (see above).

## Restore
Full flash of the backup (hash verified); ota_0 byte-identical to the recorded image; unit rejoined Wi-Fi (ws_up 03:35:37) and my host (restarted with start-newhost.sh after I stopped it during the test, pid in <path>) shows it online. Settings I changed (idle movement on, usb limit off) went back with the NVS restore. USB lock removed.
