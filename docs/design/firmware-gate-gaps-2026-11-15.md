# Firmware gate gaps, 2026-11-15

## Result

Gap 1 (patch replay) closed, gap 2 (`audio.notify`, `take_photo`) closed, gap 3 (real unit) partly closed: the unit boots, answers `self.audio.notify` and holds the memory gate over 10.8 minutes of repeated turns. A timer ring, a head move and a spoken reply could not be driven (reasons below). The unit runs the plain build; flash read-back hash matches the build. No restore was needed.

## 1. Patch replay

- `143-offline-label-after-45-s.patch` in `firmware/patches/` already applies. What did not apply was the older copy in `host/maipai_body/bodies/stackchan/firmware/patches/` (its context is the old base; `scripts/patch-replay.sh` reads that copy and reports CONFLICT when each patch is tried alone on the clean base). That copy was left alone.
- Replay of the whole `ORDER` on a clean copy of the base (outer commit 28b9f0c plus xiaozhi 49b4380), patch by patch with `git apply`: every patch applied. The result was not the tree that was flashed: 11 files in the nested xiaozhi tree (ota, application, esp_video, i2c_device, wifi_board, core-s3 audio codec) carried 219 added and 148 removed lines that lived only as uncommitted edits in the lane tree.
- New `B01-xiaozhi-base-adapt.patch` records them and is last on `ORDER`. After it, a clean replay of all 56 ORDER entries equals the lane tree (`diff -rq` over `firmware/`, build output and local config excluded: no difference).

## 2. Two tools the host asks for

| Call | Cut tag | What was done |
|---|---|---|
| `self.audio.notify` | CORE-V1 (timers and replies need a notice) | New `117-audio-notify-tool.patch`. The unit has no voice of its own, so the tool plays the popup tone (exclamation when `urgent`) through the same sound policy and hard mute as `play_sound` and answers `{ok, spoken:false}`. Both tools share one function. Built clean (app 0x2ee870 bytes, 41 percent of the slot free). Spoken text still arrives in the reply stream. |
| `self.camera.take_photo` | HOME-PRESET | Not a missing tool: the stock tool exists and answers "Image explain URL or token is not set" (29 times in 10 minutes), which the host treated as a lost robot. The host now maps that answer to NotSupported, asks once, then skips and returns no photo. Two tests in `host/tests/test_night.py`. |

Host tests: 3,541 passed, 2 failed, both in `test_stackchan_release.py` (the shell `python3` has no `tomllib`; unrelated to this change). The stackchan, xiaozhi, night and ambient subset passes (1,549). `bash scripts/check.sh`: hygiene and boundary ok.

## 3. On the real unit

Flashed with `idf.py flash` to `/dev/cu.usbmodem103401` (hash verified). Backup `~/stackchan-backups/2026-11-15/unit-flash-16MB.bin` hash checked before flashing (3f1611bc...49e13e).

What was driven: the host's local self-test (the only loopback entry; the live hub host holds the unit) repeated 28 times in 10.8 minutes.

| Check | Observed |
|---|---|
| speech (`self.audio.notify`) | pass 27 of 27 (was failing with Unknown tool). The host's pass means the call returned; whether a tone was audible was not heard, and the unit is muted. |
| led, reply | pass 27 of 27 each |
| movement | fail 27 of 27, "Yaw moved 0 degrees" in 0.02 s: the host's software stop is engaged. A stop set by a person is kept, and only the host's own recovery releases a lost-body stop. The loopback entries (`/selftest`, `/robot/updating`) have no release, and the hub is root's process. Not released, so no head move was observed. |
| hearing, wakeword | fail 27 of 27: no audio frames; the unit is muted ("wake word stays off: muted or in full quiet"). The mute was not changed, so nothing to restore. |
| camera | fail 27 of 27 (the live hub host is the old release; the host fix ships with the next host release) |
| timer set, ring, touch stop | not driven. No loopback entry sets a timer on the unit (`self.timer.*` is called only from the chat path), and touching the screen needs a hand. |

Memory over the run (heap line raised from INFO to WARN for the measurement only, 66 lines, last at 648 s):

| Measure | Observed | Gate |
|---|---|---|
| internal_free, lowest | 58,931 (steady 58,931 to 60,435) | at least 25,000 |
| internal_min | 39,828 | at least 15,000 |
| int_big | 31,744 | at least 16,000 |
| psram_min | 7,822,856 | above 6,000,000 |

Pass on all four. No panic, backtrace or watchdog line; the one reset line was the serial open. Compared with the last run (internal_free low 60,195, psram_min 8,137,616) the cost of 117 and a busier run is about 1.3 KB internal and 0.3 MB PSRAM. Other lines seen: `Unknown tool` for `self.music.set` (43) and `self.screen.set_face_background` (63; the old host release still asks), `self.screen.show_symbol` once, `Unknown system command: wake_selftest` (11), `i2s_channel_disable` errors (27) and EspVideo buffer warnings (29).

After the run: source restored (`system_info.cc` byte-identical to the original), plain build rebuilt (sha256 `d26e5b7f...56973f`, same as the build before the measurement), flashed, and a read-back of the 3,074,160 bytes at 0x20000 gave the same hash. The unit rejoined the hub and the self-test ran again as above.

## Open

- Timer ring and touch stop, head move, and a spoken reply need either a hand on the unit, a release of the host's software stop, or a host with a tool-call entry; the unit is also muted.
- `wake_selftest` is sent by the host and unknown to the unit (patch 086 is not built).
- `show_symbol` is called by the host and absent on the unit.

## Where the change is

Patches 117 and B01, ORDER, the host edit and the test are uncommitted files in the main checkout of the stackchan repo (not on GitHub). The 117 firmware commit is on branch `ours` in the scratch tree. The unit runs the plain build with 117. The live hub host is the old release without the host edit.
