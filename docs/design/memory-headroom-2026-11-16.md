# Memory headroom, 2026-11-16

Placement: unit firmware (patches M01 to M06, after FM05 in `firmware/patches/ORDER`). Nothing is committed. Tree: `~/esp/stackchan-rebase/mem` (copy of `merge`, then FM01 to FM05, then M01 to M06). No feature was removed and no product value or limit changed.

## Result

The merged image passed the old gate by 384 bytes. With M01 to M06 the same scripted stress run gives:

| Number (stress run, memory line on) | Before: merge image, 10 min | After: HEAD + M01 to M06, 14 min | Floor now | Target asked |
|---|---:|---:|---:|---:|
| `internal_free` steady (median) | 37,367 | 89,715 | 40,000 | 45,000 |
| `internal_min` | 20,208 | 33,484 | 24,000 | 28,000 |
| `int_big` steady | 16,384 | 43,008 | 24,000 | 24,000 |
| `int_big` lowest after settling | 16,384 | 43,008 | 16,000 | n/a |
| `int_big / internal_free` at the end | 0.44 | 0.48 | 0.5 (only when under 64 KB free) | n/a |
| `psram_min` | 7,650,840 | 7,298,252 | 6,000,000 | n/a |
| task watchdog fires, panics, host websocket drops (not caused by a reset) | 0, 0, 0 | 0, 0, 0 | 0 | 0 |

An earlier 10 minute run of the same image gave 90,349 / 33,484 / 36,864 with the same zero counts. Lowest free stack in the after run, tasks we create: stackchan 1,344, Tmr Svc 1,444, sys_evt 1,540, ws_reconnect 1,888, audio_input 2,476, main 3,164, opus_codec 16,688 (PSRAM); all at least 1,024. The idle and inter-processor tasks (ipc0 372, ipc1 604, IDLE0 772, IDLE1 780) have sizes fixed by the system library and are listed, not gated.

Before and after are both the stress script `scripts/fw-stress.py` (idle, listen test, four sound cues, three light colors, all 16 overlays, CRT on and off, nod, shake, look around, center, the Color Memory game, dance, network test, status reads), run by `~/esp/stackchan-rebase/mem/window.sh` with the port lock held and the known-good image put back afterwards. The "before" image is the merge image (sha256 `c5ccc3b6...`, without FM01 to FM05); the "after" image is HEAD plus M01 to M06 (sha256 `a07a7c59...`; flash read-back verified; the known-good image was put back after each window and is on the unit now).

**Status: not flashed as the standing image.** The after image has not heard a real spoken turn and has not captured a camera frame (see Not done). Until the voice window below reports, the unit stays on the merge image.

## What was freed

Each row was applied and measured in one image against the one before it only where marked; the first four were measured together in one window (see Not done), so their split is the stack arithmetic below, not a separate reading.

| Patch | Change | Internal RAM freed | Risk | How checked |
|---|---|---:|---|---|
| M02 | Opus codec task stack (24,576 B) in PSRAM, static task on a stack allocated once | 24,576 B | Decode and encode run slower from PSRAM cache; the task reads no settings and calls no flash (callbacks only set event bits); `opus_codec` on the lint's reviewed list | Sound cues and listen test decoded through it in the stress run; lowest free stack 16,688 B of 24,576; no lateness measure yet |
| M06 | Camera receives frames into PSRAM (`CONFIG_CAMERA_PSRAM_DMA`); the driver held a 32,768 B DMA buffer internal for the whole run | up to 32,768 B | Capture path through PSRAM unverified under load (the host asked for 0 frames in every run, so no frame crossed the camera) | Camera init succeeds; `dvp_task` runs; no fault. The photo call returned HTTP 400 from the host (no vision service set), so no frame was captured. The serial photo tool is in the voice window |
| M03 | Tool descriptors built with every allocation allowed in PSRAM (`heap_caps_malloc_extmem_enable(0)` around `AddTool`, restored after) | not measured on its own | Low: one place, restores the 256 B threshold | `tools/list` unchanged; steady-state number only |
| M04 | audio_input 6,144 to 4,096; websocket reconnect 6,144 to 4,096; system event 4,096 to 3,072; main 8,192 to 6,144; stackchan loop 4,096 to 5,120 (it had 524 B free) | 6,144 B net (2,048 + 2,048 + 1,024 + 2,048 - 1,024) | Medium: a spoken turn is not in the stress run, so the main and audio_input margins are idle and sound-cue readings | After the trim: main 3,164, audio_input 2,476, ws_reconnect 1,888, sys_evt 1,540, stackchan 1,408 B free |
| M01 | Memory line adds a once-a-minute `stk` line: lowest free stack of every task, `i` internal, `p` PSRAM | 0 (a log line) | None | Read by `fw-stress.py` |
| M05 | Settings reader logs an error with the task name when opened from a PSRAM stack | 0 | None | Lint and test (`test_firmware_memory_headroom.py`) |

The sum of the three measured-by-arithmetic items (24,576 + 32,768 + 6,144 = 63,488 B) is more than the 52,982 B actually gained at steady state (90,349 minus 37,367). The camera buffer is allocated only when the camera is initialized and its real size depends on frame size, so the camera row is an upper bound; M03 is in the gap on top. The split is not proven per item.

## Where internal RAM goes (measured, baseline image)

- Static: 164,051 B of the 341,760 B (IRAM text 90,339, `.bss` 40,752, `.data` 31,932, vectors 1,028). Biggest: libspi_flash 18,967 (10,715 IRAM text, 8,196 `.data`), our app 16,080 `.bss`, the JPEG library 10,247 (9,799 IRAM text), freertos 9,759, hardware support 9,524, Wi-Fi core 9,178, ESP-DL tables 7,733.
- Boot: 95,163 B free at 4 s, 44,163 at 6 s (the wake engine and audio service take about 51 KB), 38,779 at 16 s, flat after.
- Task stacks (lowest free bytes in a ten-minute run, baseline stress with M01): main 5,068 of 8,192; audio_input 4,552 of 6,144; opus_codec 16,780 of 24,576 (internal); audio_output 2,128 of 4,096; ws_reconnect 3,980 of 6,144; sys_evt 2,600 of 4,096; stackchan 524 of 4,096 (below the 1,024 floor); tcpip 2,020 of 3,072; wifi 2,468; esp_timer 2,276; ipc0 404 and ipc1 636 of 1,280.
- Not measured: a per-allocation list. Heap tracing every allocation was tried and abandoned: it starved the screen task, fired the task watchdog on CPU 1 (decoded: `record_free` in `heap_trace_standalone.c` under the screen task's free calls) and the unit panicked at 21:10:45 with `audio_input` as the last task. That image (M01 measurement build with tracing) was the one on the unit at the time. It is not in the patch set.

## Gate set adopted by this pass

`scripts/fw-stress.py` implements the review's table: `internal_free` steady at least 40,000, `internal_min` at least 24,000, `int_big` steady at least 24,000 and lowest at least 16,000, fragmentation `int_big / internal_free` at least 0.5 (not applied when 64 KB or more is free), `psram_min` above 6,000,000, a stack margin of at least 1,024 B on every task we create (the idle and inter-processor tasks have sizes fixed by the system library and are listed, not gated), zero resets after the first, zero task watchdog fires, zero panics, zero host websocket drops. Floors in the older memory gate (`firmware-memory.md`) stay as the hard minimum.

## Not done, and why

- **Voice proof (open, queued).** No real spoken turn ran on the after image, so the encode half of the opus task on a PSRAM stack and the audio_input trim are unproven. The bench build has the wake and question injection, the gap and slow-output trace and the camera tool. `~/esp/stackchan-rebase/mem/window3.sh` (queued behind the banner and sprites windows in `~/stackchan-models/usb-queue.txt`) flashes three bench images in turn under one lock and runs `scripts/fw-voice-bench.py` on each: `b1.bin` (opus stack in PSRAM), `b0.bin` (the same with `CONFIG_MAIPAI_OPUS_STACK_PSRAM=n`, opus stack internal) and `mbench.bin` (the merge bench image, sha256 `ad429ac7...`); it then restores the known-good image. Output: `mem/logs/voice-window.out` and `mem/logs/voice-*.log` (wake event to listening sound in ms, output gaps and slow outputs per minute, lowest audio stacks, resets, task watchdog, one camera frame through the photo tool). Decision rule: if b1 adds more than 20 ms to wake-to-sound or any gap over b0 or the merge image, set `MAIPAI_OPUS_STACK_PSRAM` to n (keeps the other savings: about 29 KB still comes from the camera buffer, the tool table and the stacks).
- Per-item split of M02, M03, M06 and M04: one window measured them together. A split needs three more windows (about 12 minutes each).
- 30 minute soak, music mode, the pickup: not run.
- Camera capture under M06: no frame was captured in the stress runs.
- Wi-Fi and IP stack buffers to PSRAM, TLS buffers, ROM flash driver, IRAM ISR options, heap and ring buffer placement, LVGL draw buffer, I2S descriptor count, wake front end memory mode: not applied. The four numbers already exceed the targets by a wide margin, and each of these carries a throughput or latency risk that the stress run cannot judge. They stay on the list in `firmware-memory.md`.
- The pack boot task (review item): left as is. It reads flash, so its stack must be internal; it frees the stack when it ends, and FM04 now starts it on the first standby, which closes the fragmentation cause (TC03).
- Tool descriptors as flash tables with `tools/list` built on demand: replaced by M03 (same RAM goal, one function changed). A flash table would still be the cleaner design if more RAM were needed.
- Core dump to flash and the first-boot trial: done by FM01 and FM02 before this pass.

## Rules kept

- One image per window, port lock held, app partition only at 0x20000, read-back hash, known-good image (sha256 `c5ccc3b69da725a71f2de4456df8eb1273da6bca1abf44e86a7cef22ab56ac6c`) put back at the end of every window.
- Built with `nice -n 15`, `ninja -j2`, one build at a time.
- Tests: `host/tests/test_firmware_memory_headroom.py` fails if the stack sizes, the camera option, the two switches' defaults or the threshold restore drift; `test_firmware_trackc_patches.py` now lists the opus task as reviewed and checks static PSRAM-stack tasks too.
