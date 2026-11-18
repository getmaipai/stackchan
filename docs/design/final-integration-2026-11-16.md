# Final integration, 2026-11-16

Placement: unit firmware plus bench scripts. Tree: `~/esp/stackchan-rebase/final2` (the pristine base `28b9f0c8` plus the nested vendor tree at `49b4380`, then every entry of `firmware/patches/ORDER` in order). Nothing is committed. Window scripts and logs: `~/esp/stackchan-rebase/final2/{win*.sh,gate.py,logs/}`.

## Result

The final image is on the unit and passed everything that could be run. It is the PLAIN image (no memory line, no serial tools): `build-plain/maipai-stackchan.bin`, 3,439,216 bytes, sha256 `86ad296544e4c6b8eff47e1f722acbc9cab35431707ca0147b9d90850ec68527`, written to the app partition only (0x20000; NVS, otadata, assets and the core dump partition untouched), device hash verified, read-back hash equal. The unit's assets partition was read first and equals the build's assets (sha256 `84a76e6d...`), so it was not written. The gate image (same code plus the memory line) ran a 721 s soak first: gate pass, zero resets after the first, zero task watchdog, zero panics, zero host websocket drops. Where it is: in the working tree of `~/Developer/github.com/getmaipai/stackchan` (uncommitted) and on the unit; not on GitHub. The image is everything before S10 in ORDER; S10, S11, O01, O02 stay after FI04, unreordered.

## The order and the replay

`firmware/patches/ORDER` has 169 entries. The first 167 are this integration: the merge set (141 entries), FM01 to FM05, M01 to M06, V20 to V26 and N01 to N04 as the five lanes left them (163), then FI01 to FI04 from this pass. Entries 168 and 169 (S10, S11) were appended by another session while this pass ran and are not in these images (see the end). The whole list replays with `git apply` onto a fresh copy of the base with no failure. The replayed `firmware/` tree and the final tree differ only in files a build makes or the component manager rewrites (`dependencies.lock`, `maipai_bench_clips.c`, `lang_config.h`, `managed_components`, `sdkconfig*`, `build*`), and in the two core headers S10 and S11 add after FI04 (header-only, nothing includes them yet).

One conflict, found by the replay: N02 was written against a tree without FM03, and its hunk on `self.remote.session` expected the property list on one line while FM03 had added the `host` property on a second. The N02 patch file was edited (one context line more, the hunk header counts fixed); no other patch needed a hand edit. The host test that applies the patches in order (`host/tests/test_face_preview_parity.py`) now applies the whole of ORDER and keeps only the `*_core.h` files, so a patch added or moved can no longer break a hand kept list; its spring numbers pass again.

| Group | Patches | What it does | Status in the final images |
|---|---|---|---|
| Review fixes | FM01 to FM05 | first-boot trial and rollback, flash core dump, second floor on the remote gate, pack boot on the first standby, PSRAM-stack lint | in all images; core dump kept on (below) |
| Memory | M01 to M06 | stack margin line, opus task stack in PSRAM, tools in PSRAM, trimmed stacks, camera DMA in PSRAM | in all images; M02 kept (below) |
| Fast eyes | V20 to V26 | counters, dirty rectangles, springs, pictures, lock holds, two half buffers | in all images |
| Zones | N01 to N04 | banner row, subtitle strip, fixed face zone, stock bar removed | in all images |
| This pass | FI01 | banner builds only the parts that show (about 3.4 KB at idle) | in all images |
| | FI02 | camera driver: event queue created before the V-SYNC interrupt can run | in all images |
| | FI03 | bench snapshot includes the top layer (banner, strip, subtitles), runs off the main task; bench caption tool | bench image only |
| | FI04 | LVGL task stack 7168 to 8192 | in all images |

## What was fixed

- **Banner idle RAM (FI01).** The row (5 objects), the strip container and all five glyphs (about 24 objects) were built whenever any strip glyph showed and kept 20 s after. Now the row exists only while a message shows (plus 2 s), the container only while a glyph is on, and each glyph's objects only while its flag is on. Not measured on its own (the lane's count is about 3.4 KB); the gate numbers below include it.
- **Camera race (FI02).** The vendor DVP controller registered its V-SYNC interrupt (which enables it) before it created the queue the interrupt posts to, so a sensor that was already streaming asserted in `xQueueGenericSendFromISR` (queue.c:1180). The queue is now created first, freed once on the error path, and the interrupt returns when there is no queue. The component is not edited: `firmware/vendor_fixes/camera_vsync.cmake` copies the one file into the build directory at configure time, edits it, and swaps it into the target; the configure stops with an error naming the file if a component update changes the text. Build check: `build.ninja` compiles the copy, not the vendor file. Seen since: 17 cold USB-reset boots on this unit in this pass (about half on images that have FI02), no assert. The vendor sensor's own early messages (`VS-ISR OVF`, `RX:153600`) still print at boot before the camera task runs; they are log lines, not faults.
- **Core dump (FM02).** The switch is the one the code already tests, `CONFIG_ESP_COREDUMP_ENABLE_TO_FLASH` (default y in `sdkconfig.core.defaults`; the boot summary in `maipai_heal.cc` compiles out when it is off). Its cost is about 4 KB of internal RAM. The gate below passes with it on, so it stays on.
- **LVGL task stack (FI04), found by this gate.** In the first full run the task's lowest free stack fell from 2,224 to 976 bytes under CRT, overlays and the banner text; the floor is 1,024. It is now 8,192 bytes (1 KB more internal RAM) and the lowest reading in the passing run is 2,096.
- **Bench snapshot (FI03).** `self.face.snapshot` left out the top layer; it now lays it over the screen. It also drew on the main task, where every tool runs: with a 6 KB main stack (M04) one snapshot left 316 bytes free. It now runs on a worker with a PSRAM stack (reviewed in `test_firmware_trackc_patches.py`: no flash, no settings). New bench tool `self.face.bench_caption` gives the face its words for a picture.

## Gate on the bench image

Bench image (plain, memory line on, serial tools and face bench on), sha256 `72ab5792605b72bee67bf908e8e872794ba06fc492573801100df1202d577d7a`, 726 s from boot, one real window (the unit's saved quiet state turned off for the run and put back). Actions: 12 minutes of `scripts/fw-stress.py` (idle, 4 sound cues, listen test, 3 light colors, every overlay, CRT on and off, nod, shake, look, center, the game, dance, photo, network test, repeated; 101 host calls, 96 answered ok; the 5 refused are the shutter beep and the photo call, which the host rejects (no vision service)), a remote session chip, a camera frame, a snapshot.

| Number | Measured | Floor |
|---|---:|---:|
| `internal_free` steady (median) | 73,719 | 40,000 |
| `internal_min` | 33,484 | 24,000 |
| `int_big` steady and lowest | 25,600 | 24,000 and 16,000 |
| `int_big / internal_free` at the end | 0.34 | 0.5, applied only below 64 KB free (73 KB free, so not applied) |
| `psram_min` | 6,868,080 | 6,000,000 |
| resets after the first, task watchdog, panics, host websocket drops | 0, 0, 0, 0 | 0 |

The ratio fails the literal rule "at least 0.5 after stress"; the memory lane's rule (`memory-headroom-2026-11-16.md`) applies it only below 64 KB free and `int_big` itself is above its floor. The bench image carries the serial task and trace strings; the gate image below is the comparison that counts.

Lowest free stack per task over the run (bytes; `i` internal, `p` PSRAM; floor 1,024 on tasks we create): stackchan 1,420, Tmr Svc 1,444, sys_evt 1,536, imu 1,548p, musicfeat 1,576p, listen_ring 1,656p, ws_reconnect 1,756, audio_input 1,816, tcpip 1,868, audio_output 2,048, esp_timer 2,084, taskLVGL 2,096, tcp_receive 2,288, wifi 2,432, snap_worker 2,444p, main 3,068, headtouch 3,760p, sertools 6,680p, audio_afe 10,124p, opus_codec 15,968p (4,528p after real spoken replies: the encode half uses about 20 KB of the 24 KB). dvp_task 1,308. The system's own idle and inter-processor tasks (ipc0 372, ipc1 572, IDLE0 772, IDLE1 780) have fixed sizes and are listed, not gated.

## Screen speed (bench image, effects off and on)

Measured in the first window (image `cc7a63ae...`, the same face code; FI03 and FI04 do not touch it). "Effects on" is CRT plus the rain overlay. Each row is one 10 second `bench_run`.

| Workload | Refresh per second (off / on) | p99 gap between refreshes ms (off / on) | Merge image before (refresh per second, off / on) |
|---|---|---|---|
| Idle (drift and blinks) | 12.2 / 20.8 | 100 / 100 | 20.5 / 21.4 |
| Eyes moving | 33.0 / 33.0 | 55 / 60 | not measured |
| Speaking (synthetic level) | 28.3 / 29.3 | 100 / 77 | 15.6 / 18.6 |

The idle row is lower than the merge number because a resting face now draws only what changed (dirty rectangles); the 100 ms p99 is the last bin of the counter (a still face draws nothing). Moving and speaking reach the targets of `fast-eyes-2026-11-16.md` (30 and 28 a second); the p99 gap goal of 50 ms is met only by the moving case without effects (55 ms is just over it, as that note found).

## Voice (final bench image against the merge bench image)

Same script (`scripts/fw-voice-bench.py` style rounds, run by `gate.py voice`): the firmware plays the wake phrase and a question into the microphone path at real-time pace; everything after the microphone is real (wake engine, Opus, Wi-Fi, the host, the host's speech back, decode, speaker queue). Four rounds each, listening state on, one window with both images.

| | Final image (M02 on) | Merge image (`ad429ac7...`) |
|---|---|---|
| Wake event to listening sound queued (ms) | 5, 4, 1, 2 (median 3) | 5, 1, 1, 3 (median 2) |
| Replies that started | 4 of 4 | 4 of 4 |
| Spoken reply time (s) | 24.2 in total | 16.2 in total |
| Output gaps over 80 ms, slow outputs | 1 and 0 (a 113 ms gap at the start of one reply) | 3 and 1 |

The Opus stack in PSRAM (M02) adds about 1 ms to the wake-to-sound figure and no gap, so it stays on (`MAIPAI_OPUS_STACK_PSRAM` stays y). The rounds are too few to rank gaps per minute (the final run spoke 24 s in its window, the merge run 16 s); the claim is "no worse", not "better". Wake to first sound out of the speaker is 6 to 12 s in both: that is the host's stage (end of speech, transcript, model, speech).

A recorded phrase played from the Mac (`afplay`, three gains up to 3.0, 3 turns) did not wake the unit: the microphone heard it (peaks of a few hundred) but no wake event followed. The Mac's output is a monitor over HDMI with no volume control; whether the unit is near enough was not established. So there is no spoken-turn proof through the air; the firmware path above is the proof used.

## Pictures

Opened and judged (bench image, `self.face.snapshot` with the top layer):

- Big eyes at rest with a banner (the remote session chip and the remote glyph at the right end): `~/esp/stackchan-rebase/final2/logs/win1c/snap_rest_banner.png`. Banner at y 1 to 27, eyes in the face zone, nothing in the subtitle zone.
- Speaking with subtitles and a banner: `~/esp/stackchan-rebase/final2/logs/win1f/snap_subtitles_a.png`. The two line subtitle at the bottom, the chunky speaking mouth, the banner on top, Big eyes at the 0.82 scale. The words came from the new bench caption tool, not from a reply (next section).

## Found, not fixed

- **The host sends no words with a reply.** `send_audio` sends `tts sentence_start` with no text, so no real reply shows subtitles; only the unit side draws them. The brain half of the subtitle feature is missing (org rule: a missing brain half hides the feature).
- **Captions default.** The host's settings table lists `captions_mode` default "subtitles", but the unit shows no captions for Big eyes until a person chooses them (`mp_captions_mode` falls back to the face's flag, off). Pick one.
- **The running host is older than the repo.** The host process on this Mac (started 20:42) answered "Unknown setting captions_mode" to a prefs save. It was not restarted.
- **The unit's saved state was "full quiet"** (no listening, no moving) when this pass began. The gate turned it off for each run and put it back (verified by reading it) before every image restore; the stress run in quiet mode would not have moved the head or played sounds.
- **Not tested:** the pickup (needs a person), a 30 minute soak, music mode, a camera frame through the vision service (the photo tool reached the explain step and stopped on "Image explain URL or token is not set", so a frame was captured but not described).
- **S10 and S11** (face seek core and the turn-to-faces setting) were appended to ORDER by another session at 00:36 and 00:39. They are core headers with their own tests and are not in these images.

## Images and the unit

| Image | Bytes | sha256 | Where it ran |
|---|---:|---|---|
| Plain (final, on the unit) | 3,439,216 | `86ad296544e4c6b8eff47e1f722acbc9cab35431707ca0147b9d90850ec68527` | flashed, read-back checked, 75 s of console after: 1 reset (the flash), no panic, no watchdog, no assert; the unit reconnected to the host (`newhost.log` 01:21:21 "connection open") |
| Gate (plain plus memory line) | 3,439,664 | `dccc4433834af3c97fa15593fb7cf85dee12567cc229220f81954001c1f478f2` | 12 minute soak below |
| Bench (final code) | 4,037,888 | `84d736823a723eab14fd5d45f64af946520becd567c387fcb0e0aae73ed75285` | pictures; the gate run used the build before the caption tool, `72ab5792...` (4,036,864) |
| Known-good before this pass (merge image) | 3,415,424 | `c5ccc3b69da725a71f2de4456df8eb1273da6bca1abf44e86a7cef22ab56ac6c` | put back, read-back checked, after every window until the last |

Gate image soak (721 s, 73 memory lines, 101 host calls plus two spoken-turn attempts): `internal_free` steady 89,951 (floor 40,000), `internal_min` 33,484 (24,000), `int_big` steady and lowest 36,864 (24,000 and 16,000), `int_big / internal_free` at the end 0.41 (not applied above 64 KB free; it is 0.5 or more only on the lane's rule), `psram_min` 7,197,352 (6,000,000); lowest stack margins imu 1,292p, stackchan 1,408, no task of ours under 1,024. The gate image has 16 KB more free internal RAM than the bench image (serial and bench code), which is the number that applies to the plain image.

The first window's lost second try: the first restore of the known-good image failed with a readback mismatch because the serial server of my own script still held the port; the image was restored by hand (hash verified) before anything else ran. The saved privacy state (full quiet) was put back before each image restore; read back after the last.

Host: the running host process was not restarted (see "Found, not fixed").

Tests: host suite 4,268 passed, 86 skipped (before FI04 and the doc; the firmware-related subset was rerun after: 39 passed with `MAIPAI_FW_TREE`, 19 renderer checks pass against the final tree after `test_firmware_face_render.py` took the N04 box sizes). `look_core_test.c` had 581 failing checks (the face zone and the 0.82 scale of N04, V23 pictures); its five expectations were updated deliberately to the final core (Big eyes 79 by 85, mouth 38 by 7, brow 7, dots y 48 to 56 from the zone middle, eye box right edge 130, zone centers), and it passes against the final tree. `scripts/check.sh --pre` passes for these files; it reports British spellings in `host/maipai_body/overlay_shapes.py`, another lane's new file.
