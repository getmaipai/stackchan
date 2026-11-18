<!-- Bench note copied from the bench agent's notes; paths, serial ports, hashes, addresses and ids removed. -->
# Bench b9 and b13 (2026-11-18, Mac Studio, unit on <serial port>)

Evidence folder: <path> (called R below). Nothing committed, no firmware source changed.

## Step 0: what the unit ran before
- Full 16 MiB backup before anything: <path> (sha256 starts <hash>).
- Read from that backup: otadata seq 1 means app slot ota_0; ota_0 = version 1.6.2-maipai.1, built Nov 17 2026 20:23:56; ota_1 empty.
- Note: this is NOT the folder <path> (differs). The restore used the exact backup, not known-good.
- Host was down at the start (last log line Nov 17 23:18). I started it with <path> (pid in newhost.pid); it is still running.

## Step 1: memory (static image size by idf.py size; runtime from fw-stress.py 420 s, memory line on)
final15 reference: 86 KB median free, 33 KB min.
| image | static DIRAM used / free | app bin bytes |
|---|---|---|
| b9 plain | 171,687 / 170,073 | 3,623,776 |
| b9 bench | 186,379 / 155,381 | 4,239,584 |
| b9 gate | 171,703 / 170,057 | 3,624,208 |
| b13 plain | 173,335 / 168,425 | 3,716,144 |
| b13 bench | 188,027 / 153,733 | 4,331,520 |
| b13 gate | 173,351 / 168,409 | 3,716,483+ (3,716,592 file) |
Runtime (bench images only; plain and gate images were not flashed): 
- b9 bench: internal_free median 65,575 B, internal_min 33,484, int_big 25,600, psram_min 7.1 MB, 0 resets/wdt/panics. GATE PASS. (R/stress-bench.log)
- b13 bench: internal_free median 67,319 B, internal_min 33,484, int_big 25,600, psram_min 7.1 MB. GATE PASS. (R/stress13.log)
- Versus final15: median free is about 19 to 21 KB lower (86 KB there); min equal (33 KB). The bench image carries extra bench code, so a gate or plain image was not measured and the median gap is not proven for the shipping image. Size reports: R/size-*.txt, R/size13-*.txt.

## Step 2 table (flashed: b9 bench first, then b13 bench; app slot only at 0x20000, bootloader, table, assets, NVS untouched until the NVS restore below)
| check | result | evidence |
|---|---|---|
| lock tools answer too_many after 5 wrong codes | PASS (b9 and b13) | R/lock.txt, R/b13-lock.txt |
| lockout survives restart | FAIL (b9 and b13): after self.reboot the correct code is accepted at once; counter is RAM only (matches review item 2) | R/lock.txt, R/b13-lock.txt |
| lock.config auto_minutes 0 with a code set and no current answers current_needed | PASS | R/sf02.txt |
| prefs.set turning off all three listening cues answers an error | PASS | R/sf02.txt |
| lift/tilt above 70 degrees mid-dance stops it | NEEDS PERSON (a hand must lift and tilt the unit during a dance) | |
| privacy switch: tap on mouth mutes, tap while muted does nothing, hold unmutes | PASS (bench finger via self.page.bench_tap; first touch after idle only wakes) | R/privacy.txt, R/privacy2.txt |
| alarm-stop press toggles nothing | PASS for no toggle (mute stayed 0); but an injected tap did not stop the ringing alarm (ringing stayed true until self.timer.stop). A real finger must confirm the stop | R/alarm.txt |
| game-end press toggles nothing | PARTLY: a tap during a game toggled nothing; the game end by stop request ended it. A real end-of-game screen press not exercised | R/game.txt |
| camera mark above a game | PASS (icon top right over Color Memory; needs status_icons on, which is off by default) | R/game-banner2.png |
| events reply valid JSON | PASS (valid array; the host drains events while connected so a later read is `[]`) | R/events.txt |
| 12 s sentence after wake heard fully | NOT DONE: needs a person speaking 12 s (no clip that long exists). fw-voice-bench.py --gate on short clips: PASS both images, 5 of 5 replies, 0 resets | R/voice.log, R/voice13.log |
| dance and head moves, no new stutter | NO stall found: stress run (dance, nod, shake, look around) 0 task watchdog, 0 panic, 0 drops. A person must judge smoothness by eye | R/stress-bench.log, R/stress13.log |
| restart test restarts | PASS (self.reboot restarts the unit; rst:0xc software reset in the log) | R/serial/fw-serial.log |
| Wi-Fi setup: wipe with self.wifi.forget, setup code readable | PASS: forget needs index (0 twice); after reboot the unit says WiFi setup required, shows name, address and a code; screenshot readable. Look flaws: the address breaks across lines (http: / //<address>) and "Connecting to Wi-Fi..." shows above the setup line | R/wifi-setup.png (the code is in this screenshot; not repeated here), R/wifi.txt |
| Wi-Fi restored after the wipe | PASS: only the NVS partition rewritten from the backup; the unit rejoined, host reconnected | R/nvs-restore.log |
| first-run flow shows once after Wi-Fi, never again | PASS: the unit had no mp_firstrun record, so it appeared on first boot of the new image (language, name, how to think, private by design). Completed with bench taps (English, Astro, own model, Got it); one first_run_done event in the host log; after reboot the flow did not return. Text flaw: on "Private by design" two lines touch | R/fr-*.png, R/fr-after-reboot.png, newhost.log |
| Updating screen during an update | NOT DONE: needs a signed image; the host serves none without a release key |
| FM01 trial | NOT DONE for the same reason (no update works without a release key) |

## b13 extras
| check | result | evidence |
|---|---|---|
| self.face.mouth_cues then speak moves the mouth and ends closed | PARTLY: ends closed (smile) PASS; mouth moving per cue is NOT shown, because self.face.bench_speak drives a steady loudness, not real speech, and snapshots are 1 to 2 s apart. Needs real speech | R/m1.png m2.png m3.png |
| find-me volume returns 5 s after the last chirp | PASS: 10 to 70 on the find chirp, back to 10 after 7 s | R/find.txt |
| listen_ended event after 9 s silence | NOT REPRODUCED: with the host connected the host ends the turn (no_speech) at about 6 s, before the unit's 9 s guard; the unit event never fires. Needs the host's silence timer to be longer or a person | R/listen.txt, newhost.log |
| accented words (fr/de/es) on screen | PASS: first-run language buttons show Espanol, Francais, Portugues with accents | R/b13-boot.png |

## Needs a person (one list)
1. Lift and tilt past 70 degrees mid-dance.
2. Real finger: stop a ringing alarm; press at game end; check no mute toggle.
3. Say a 12 s sentence after the wake word.
4. Watch dance and head moves for stutter.
5. Say a sentence with real speech and watch the mouth follow the cues.
6. A signed test update for the Updating screen and FM01.

## Step 4 restore
Full flash of the recorded backup written back (0x0, 16 MiB, hash verified). Read-back of the ota_0 slot is byte-identical to the recorded image. The unit booted, joined Wi-Fi (wifi state=ws_up), and the host shows it online. USB lock file removed; no serial server or esptool left running.
