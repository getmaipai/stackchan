<!-- Bench note copied from the bench agent's notes; paths, serial ports, hashes, addresses and ids removed. -->
# Bench b15 window (2026-11-18)

R = <path>
Image recorded first: ota_0 = 1.6.2-maipai.1 (Nov 17 2026), otadata seq 1; full backup <path> (identical ota_0 to the earlier b9 window backup).

## (1) Memory bisect: fw-stress.py 600 s, memory line on, bench images, same host (running), 20 s after flash, each run resets the unit
| image | internal_free median | internal_min | int_big (median and lowest) | frag int_big/free | gate | evidence |
|---|---|---|---|---|---|---|
| bisA (ORDER at e02c714, no UX01, no SF) | 69,533 | 33,484 | 25,600 / 25,600 | 0.37 | PASS | R/stress-bisA.log |
| bisnoSF (today's ORDER, no SF) | 69,609 | 33,484 | 25,600 / 25,600 | 0.37 | PASS | R/stress-bisnoSF.log |
| b15 (everything) | 63,903 | 33,484 | 25,600 / 25,600 | 0.40 | FAIL (frag floor 0.5; every other floor ok) | R/stress-b15.log |

The median does not drop from bisA to bisnoSF (+76 B). It drops 5,706 B from bisnoSF to b15: the step is the SF patches. Minimum and largest block do not change in any step (33,484 and 25,600). Earlier b13 bench median was 67,319 and the b9 bench 65,575 (run 420 s, same script). The frag gate result: the same 0.38 to 0.40 ratio was shown "ok" for b13 and "BELOW" for b15, so the script's rule depends on something besides the ratio (not investigated).

## (2) Lockout on b15 bench
PASS. 5 wrong codes (5th answers wrong_current, the 6th call too_many), self.reboot, then the correct code answered too_many at 18 s and 40 s after the restart; the correct code worked at about 62 s after the 5th wrong code (03:06:36 vs 03:05:34). Evidence R/b15-lock.txt. Lock cleared afterwards.

## (3) b15 extras
- mouth_cues: PASS. self.face.bench_speak at steady level 90 for 20 s with cues 4 for 0 to 8 s and 0 for 8 to 16 s: mouth open at 1 to 3 s, closed at 11 s although the steady level was still on, closed after the end. Pictures R/b15-open1.png, R/b15-late.png, R/b15-end.png. Real host speech is only about 1.3 s long on the bench question, too short to judge by snapshot. Note: the first-run flow covered the face until I completed it with bench taps (the restored NVS has no first-run record).
- listen_ended: NOT REPRODUCED, blocked. The host ends the turn about 6 s after wake (speech-to-text answers no_speech) before the unit's 9 s silence guard; the unit's event fires only when the guard ends the listen. There is no host setting for that timeout (turn.py has fixed constants). Forcing it needs a second host instance with a longer no-speech time or a person holding the unit's listening open with the host paused; I did not change the family's host.

## Restore
Full flash of the recorded backup, hash verified; ota_0 read back byte-identical; unit rejoined Wi-Fi (ws_up 03:11:19) and the host shows it online.
