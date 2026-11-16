# Faces wired in and busy gate, 2026-11-16

## Result

Host wiring done and tested. Firmware F01 to F06 are on in a clean build, flashed to the owned unit, and the unit held the memory gate over 11.6 minutes. The face tools themselves could not be called on the unit (nothing that holds the link calls them yet), so what the faces do on screen is not observed. The unit runs the plain build with all six switches on; the flash read-back hash equals the build.

## 1. Host

| Where | What |
|---|---|
| `host/maipai_body/cli.py` | New `stackchan face show\|set\|sync\|reset UNIT` (`--style`, `--colour`, `--captions on\|off`, `--schedule on\|off`, `--hours 6,9,18,21`, `--lang`, `--host-url`). The running host owns the saved settings, so a change goes through its settings page and reaches the unit at once. With no host running it saves to the same file and says the unit gets it when the host next sees it connect. Errors say what is wrong and what to type. |
| `host/maipai_body/settings_page.py` | Face section per unit on the page (style, colour or none, captions, time-of-day with the four hours, save, back to the plain face). Routes `GET /api/stackchan/faces/<id>` and `POST /api/stackchan/faces/<id>` and `.../reset`, local administrator only. A unit that is not paired is refused. Without a live link the unit counts as offline: saved, sent later. |
| `host/maipai_body/faces.py` | `turn_cue` (thinking on at the `thinking` turn state, off at `speaking` and `settle`, never fails a turn), `sync_on_connect`, `offline_call`. |
| `host/maipai_body/app.py` | One `FaceService` per host. `sync_on_connect` is a session listener (pushes only when the unit differs). The turn sink starts and ends the cue on a one-worker queue so the calls stay in order and off the turn's thread. Cue goes to every connected unit (the turn event carries no unit id). |
| `host/maipai_body/dashboard/server.py` | The dashboard serves the new face GET route too (one line). |
| `host/maipai_body/i18n.py` | 21 `settings.face*` strings, English and Spanish; the catalog test still passes. |

Tests: `host/tests/test_faces_wiring.py` (10 tests: strings in both languages, page routes save and refuse, offline save, cue order, cue never fails the turn, sync, the real turn sink, CLI set/show/reset with no host, CLI errors). Full host suite: 3,663 passed, 66 skipped. `scripts/check.sh`: hygiene and boundary ok.

Not done: no on-screen check of the page (the page code was exercised through its routes and the rendered HTML, not a browser); the CLI `sync` with no host running only says the host is not running.

## 2. Firmware

`firmware/sdkconfig.core.defaults` now states the six switches as `=y` (they already defaulted to y and the tree's `sdkconfig` already had them on; the lines make it explicit). `idf.py fullclean` then build: image 3,093,200 bytes (0x2f32d0, same as the faces status note), sha256 `a485a27a...619cf5`.

| Step | Observed |
|---|---|
| Backup | `~/stackchan-backups/2026-11-15/unit-flash-16MB.bin` hash `3f1611bc...49e13e`, matches its `.sha256`, checked before flashing. |
| Flash 1 (measurement build) | One log line raised to WARN in `system_info.cc` to print `internal_free`, `internal_min`, `int_big`, `psram_free`, `psram_min`. Hash verified. Booted; heap lines printed. |
| Gate run | 694 s of serial (71 heap lines). Driver: the host self-test endpoint on the live hub host, 37 rounds started. The hub host restarted at 01:19:43 (a new process id, not ours): the unit logged four failed connects (about 364 s to 381 s), reconnected, and rounds resumed; 21 rounds returned results, 16 got no answer during the restart. |
| Source restored | `system_info.cc` hash `c5e60152...`, same as before the edit. |
| Flash 2 (plain build) | Rebuilt: byte-identical to the first plain build (cmp). Flashed, hash verified, flash read-back of 3,093,200 bytes at 0x20000 equals `a485a27a...`. |
| After | Boots, rejoins the hub; self-test `speech` and `reply` pass. |

### Memory against the gate

| Measure | Observed | Gate | Last run (2026-11-15) |
|---|---|---|---|
| internal_free, lowest | 56,283 (steady 58,0xx to 58,2xx) | at least 25,000 | 58,931 |
| internal_min | 39,828 | at least 15,000 | 39,828 |
| int_big | 31,744 | at least 16,000 | 31,744 |
| psram_min | 7,824,012 | above 6,000,000 | 7,822,856 |

All four pass. internal_free low is 2.6 KB under the last run (steady about 0.9 KB under); internal_min and int_big are unchanged and PSRAM is the same. The six face features are idle in this run (clock, schedule and captions are off by default, no timer was set), so this measures their resident cost, not their cost while drawing.

### Other lines in the serial log

No panic, backtrace or watchdog during the 11.6 minutes. Same noise as last time: `Unknown tool` for `self.music.set` (44) and `self.screen.set_face_background` (63), `Image explain URL or token is not set` (21), `i2s_channel_disable` (22), `wake_selftest` unknown (6).

One abort: the first boot after the plain flash stopped at `ESP_ERROR_CHECK failed: esp_err_t 0x108` in `I2cDevice::ReadReg` during board init, rebooted by itself and booted cleanly. Three more serial resets booted cleanly. It happened before any face code runs and once in five boots; cause not shown by the evidence (an I2C part not ready right after a flash reset is a guess). Watch for it on the next flash.

## 3. Not observed

- No face tool was called on the unit: the host on the hub is release 0.2.104 and does not know them, and the unit has one link. So `self.face.set_config`, `get_config`, `show_clock`, `thinking` and the clock, schedule, caption and timer-chip drawing are untested on hardware. After the host ships, call `stackchan face set UNIT --style big_eyes --captions on` and read the unit's reply; the faces status note lists a "Check after a flash" line per patch.
- Each switch on and off was not run on the unit. Off builds were measured earlier only for size (480 bytes smaller than the baseline with `MAIPAI_FACE_CONFIG` off).
- No picture of the screen.
- movement, hearing, wakeword and camera self-test checks fail as before (head stop engaged, unit muted, host release); unchanged.

## Where the change is

Only uncommitted files in the main checkout of the stackchan repo (host files above, `firmware/sdkconfig.core.defaults`, the face patches and tests from the earlier note); firmware commits are on branch `ours` in the scratch tree. Not on GitHub, not in a release. The unit runs the plain faces build; the hub host does not have the host wiring.
