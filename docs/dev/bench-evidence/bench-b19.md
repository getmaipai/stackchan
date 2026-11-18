<!-- Bench note copied from the bench agent's notes; paths, serial ports, hashes, addresses and ids removed. -->
# Bench b19 window (2026-11-18)

R = <path>
Image recorded first: ota_0 = 1.6.2-maipai.1 (Nov 17 2026); full backup <path> Flashed app slot only (partition table identical to the unit's).

## (1) MIC3 check on build-talkover (self.bench.mic3_check, 1 kHz for 2 s). Evidence R/mic3.txt
| volume | gain_db | MIC1 tone / room rms / peak / dB | MIC3 tone / room rms / peak / dB |
|---|---|---|---|
| 30 | 0 | 11355 / 149.1 / 13447 / 34.6 | 157 / 2.5 / 189 / 30.0 |
| 30 | 6 | 11357 / 141.8 / 13483 / 35.0 | 157 / 2.4 / 189 / 30.3 |
| 30 | 12 | 11360 / 142.3 / 13524 / 35.0 | 158 / 2.4 / 189 / 30.2 |
| 30 | 18 | 11358 / 144.7 / 13471 / 34.8 | 158 / 2.6 / 189 / 29.9 |
| 30 | 24 | 11362 / 155.7 / 13451 / 34.2 | 158 / 2.6 / 190 / 29.9 |
| 70 | 0 | 11361 / 156.8 / 13532 / 34.1 | 158 / 2.8 / 189 / 29.3 |
| 70 | 6 | 11363 / 136.8 / 13554 / 35.3 | 158 / 2.3 / 189 / 30.5 |
| 70 | 12 | 11362 / 147.6 / 13481 / 34.7 | 158 / 2.4 / 190 / 30.3 |
| 70 | 18 | 11359 / 157.3 / 13440 / 34.1 | 158 / 2.6 / 190 / 29.7 |
| 70 | 24 | 11363 / 154.0 / 13401 / 34.3 | 158 / 2.6 / 190 / 29.9 |

Reading the numbers, not a verdict: by the tool's rule MIC3 passes (tone about 30 dB over its room, peak 190, far under 30000) at every setting. But MIC3's tone amplitude (157 to 158) does not change with gain_db 0 to 24, and neither MIC1 nor MIC3 changes between speaker volume 30 and 70 (MIC1 stays 11,355 to 11,363). A real acoustic path should scale with both. This looks like a fixed or digital signal (a reference or loopback channel), or the volume and gain arguments not reaching the hardware. I did not find which. Do not rely on this as proof that MIC3 hears the room; a person making a sound near the unit and a log of MIC3 level would decide.
Delay between played and captured tone: the tool reports no delay, so none recorded.

## (2) Lockout on b19 bench. Evidence R/b19-lock.txt
- 5 wrong, reboot, correct code: too_many. PASS. After the time had run (about 120 s), the correct code worked.
- 4 wrong, reboot, 1 wrong: that one answered wrong_current (it is the 5th wrong), and the next call (correct code) answered too_many. The count did survive the restart; the 5th wrong answers wrong_current, as it does with no restart (first test: 5 wrong all wrong_current, the 6th too_many). If the expectation was "the 5th wrong itself answers too_many", it does not.

## Restore
Full flash of the backup, hash verified; ota_0 read back byte-identical to the recorded image (the lock code set during the test is gone with the NVS restore). Unit rejoined Wi-Fi (ws_up 03:20:02); the host is online. USB lock file removed.
