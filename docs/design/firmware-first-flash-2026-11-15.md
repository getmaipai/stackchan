# First flash of the rebased firmware, 2026-11-15

## Result

The rebased firmware (tree `~/esp/stackchan-rebase/main`, branch `ours`) boots on the unit, joins Wi-Fi, reaches the idle face and passes the memory gate. No restore was needed. The unit now runs the plain build (no measurement edit).

## Steps and what was seen

1. Backup: `~/stackchan-backups/2026-11-15/unit-flash-16MB.bin`, 16,777,216 bytes, SHA-256 `3f1611bc...49e13e`, matches the recorded hash.
2. Clean build (`idf.py fullclean`, then `set-target esp32s3 build`): passed. App image 3,064,240 bytes, smallest slot 5,177,344 bytes, so 40.8 percent of each OTA slot is free (gate: 20 percent).
3. Flash with `idf.py flash` to `/dev/cu.usbmodem103401`: hash verified on every image, hard reset.
4. Serial at 115200 baud: clean boot from the new partition table (ota_0 and ota_1 at 5 MB each, assets at 0xa00000), HAL init, IMU, servos, RTC all ok. No panic, backtrace, watchdog or reboot over 12 minutes. One reset line, the one I caused to start the capture.

## Memory gate

Release logs are WARN level and the heap line is INFO, so nothing was printed. For the measurement I changed one log line (`SystemInfo::PrintHeapStats`) to WARN and added largest block and PSRAM minimum, flashed that, measured, then restored the source and reflashed the plain build. The measurement build differs only in that line. The edit is saved at `/tmp/claude-501/ff/system_info.cc.gate` (scratch) and a permanent gate line is worth adding.

| Point | internal_free | internal_min | int_big | psram_min |
|---|---|---|---|---|
| Boot, 4 s | 117,643 | 52,912 | 63,488 | 8,166,952 |
| 8 s (after audio start) | 65,079 | 39,828 | 31,744 | 8,154,472 |
| 28 s | 63,715 | 39,828 | 31,744 | 8,131,772 |
| 10 min idle (658 s) | 63,719 | 39,828 | 31,744 | 8,131,772 |
| Gate | at least 25,000 | at least 15,000 | at least 16,000 | above 6,000,000 |

All four pass with wide margin. Steady value did not move over 10 minutes (63,715 to 63,719), so no leak at idle. This was idle only: no spoken turn, camera or music, so the full gate run (step 1 of firmware-memory.md) is still open.

## What works, from serial only

- Boot to idle face: seen (avatar idle motion start logged at 10.6 s).
- Wi-Fi join: the saved-network credential path logged at 6.6 s and the unit then answered tool calls from its client, so it is online. No IP line is printed at WARN.
- Timer tool: registered ("add timer tools", reminder tools also listed). Not called, so not proven to work.
- Stop word: not observable. The wake and stop engine logged "wake word stays off: muted or in full quiet". Not tested.
- Battery, head angle and motion tools answered the client.

## Problems found

The client calls tools this build does not have, about 350 error lines in 12 minutes: `self.robot.set_idle_motion` (119), `self.audio.set_sound_policy` (117), `self.screen.set_face_background` (64), `self.music.set` (43), `self.audio.sound_info` (11), `self.power.keep_awake` (once). They fail with "Unknown tool" and nothing crashes, but the hub side expects them, so the matching firmware patches or a hub-side change are needed. `E:VS-ISR OVF` and `E:RX:153600-15360` lines appear in the first seconds of boot only (camera driver); none after.

## Next check

Run one spoken turn with camera and music on and read the heap line for 10 minutes (blocked until the missing music and sound-policy tools exist).
