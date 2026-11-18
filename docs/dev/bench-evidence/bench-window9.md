<!-- Bench note copied from the bench agent's notes; paths, serial ports, hashes, addresses and ids removed. -->
# Bench window 9 (2026-11-18, script only)

R = <path> (checkout origin/main 753f5f2)
Image: b29 build-aec (4,350,608 bytes; bench + gate + AEC overlay, SF29). Recorded first: ota_0 = 1.6.2-maipai.1; backup <path> (ota_0 identical to the window-8 record). First-run set done with self.bench.firstrun. Limiter as found and at the end: state free, usb_limit limited, scale 100 (not changed this window). Speaker volume found 35.

## What I could and could not drive
- Turns with canned audio: self.bench.inject (wake plus one of the five questions) every 25 s through the host: works, replies are short (about 1.3 s).
- This image prints no tts_start/wake_evt trace lines (only inj_*, heap, mic_peak, ws_*), so fw-voice-bench.py --watch cannot count replies. It prints one "AEC mic= ref= out=" line a second: that is what the AEC verdict reads.
- The Mac speaker did not wake the unit: I played "Hi, Stack Chan" plus a request for a long story with afplay (the Mac reports no output volume setting) and nothing reached the host (no new turn in the host log). So no long reply could be made.
- Host "say" (the only way I found to make the unit speak a long text) refuses: "The person at the robot did not allow that message", it needs a person's cue.

## (1) Memory with the canceller running while replies play (R/aec9-serial.log): 24 turns in 600 s (one every 25 s), volume 35
internal_free median 69,075 (lowest sample 66,831), internal_min 33,484, largest block 25,600 (median and lowest), 0 resets, 0 watchdog, 0 panics. Against the b29 talkover baseline 68,031 (stress line, a different load) the median is 1,044 B higher, so the canceller costs nothing visible in the median and stays far inside the 4 KB budget; internal_min and largest block are unchanged from the b29 baseline.

## (2) --watch aec verdict (echo return loss, the speaker playing the canned replies and chimes; seconds with the loopback ref above 50)
| volume | active seconds | median dB | lowest dB | need | verdict |
|---|---|---|---|---|---|
| 35 (default) | 111 | 66.6 | 28.1 | 20 | PASS |
| 60 | 32 | 66.6 | 33.0 | 20 | PASS |
| 100 (cap) | 32 | 63.9 | 23.3 | 15 | PASS |
Caveat: these are the unit's own trace lines on a quiet bench with short sounds; 60 to 66 dB is far above 20 dB, which is larger than a real room would give, so treat it as "the canceller works on this path", not as a room figure.
- --watch barge: NOT DONE. The firmware prints no "barge wake_to_silence_ms" line (grep finds none in b29), so the script's barge verdict has nothing to read, and no long reply was available to interrupt (see above). Nobody can judge 18 of 20 within 200 ms without both. Needs: a firmware trace line for the time to silence, and a reply of several seconds (host cue or a person asking a long question).
- --watch soak and the 10-minute long-reply self-trigger: NOT DONE with a long reply. What was run: 24 canned turns (short replies) over 600 s plus two 160 s runs at volume 60 and 100: zero "interrupted" lines, zero self-aborts. That is a weak substitute; the real soak needs a long reply.

## (4) Needs a person or a quiet room
1. A person (or an owner cue) to let the host speak a long reply, then: two wake words within 1 s (barge), and a 10-minute long-reply soak at the volume cap.
2. A real quiet-room echo measurement with the unit's own voice and a person speaking over it.
3. Firmware: the barge time-to-silence trace line, and the tts_start trace in the aec image so --watch can count replies.

## Restore
Full flash of the backup, hash verified; ota_0 read back byte-identical (this also puts the volume back to 35). Host running, unit online (ws_up 07:12:05). USB lock held until window 10 ends.
