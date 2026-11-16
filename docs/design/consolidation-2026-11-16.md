# One consolidated image, 2026-11-16

Placement: unit firmware plus host. Tree: `~/esp/stackchan-rebase/final` (the faces tree with Y04 applied and Z01 added). Nothing committed.

## Why

Two lanes flashed the same unit in turn: the faces lane (X01, X02, Y01 to Y03, no Y04) and the reliability lane (latency base, Y01 to Y04, no faces core). The unit ended up on the reliability image. This note records the one image that holds every patch in `firmware/patches/ORDER`.

## Patches in the image

All 125 patches of `firmware/patches/ORDER`, in that order, on the pristine StackChan base `28b9f0c8` (outer repo) and the nested Xiaozhi tree at `49b4380` (v2.5.2 line, before the first local commit).

| Series | Patches | What it holds |
|---|---|---|
| 001 to 143 | 46 | Base changes: server URL empty, persistent socket, stop word, timers, privacy and mic guards, offline mode, sounds, clock-free boot |
| A, B, C, F, S | 17 | Per-pixel LED tool, assets partition, battery, connecting screen, swipe gestures, face config, captions, time of day, clock, thinking cue, timers, core trim and sdkconfig defaults |
| 155 to 160, R01 to R04 | 10 | Signed updates from the paired host, no public CA roots, first-boot rollback, reset on device, restart guard with back-off |
| P, T, M, V, TN | 22 | Wi-Fi portal, low battery ladder, hourly chime, wake cue, mood from care, serial tool path, travel private network, memory gate line |
| U, G, H, I, W | 15 | Face decorators, word reactions, time zone picker, network test, version screen, face packs, offline phrases, music dance, games, face bench tools, fluid motion, picture faces, orientation, screen wake |
| L01, L03 to L09 | 8 | Latency and calm: echo canceller off for wake, 8 s follow-up window, ignore idle host looks, wake detection 95, bench latency trace, privacy source log, no connecting flash, stop word not probed |
| X01, X02 | 2 | Faces core: one look core (circle eye with a lid, one family of mouths, sleep sequence, thinking dots), five styles with Big eyes the default, white eyes, per-person screen colour, tint, tired low-battery look |
| Y01 | 1 | A user head move (source=user) passes the idle gate |
| Y02 | 1 | Find my robot sounds through mute and quiet |
| Y03 | 1 | Opus decode task above the screen task (spoken replies stopped stuttering) |
| Y04 | 1 | "Here I am!" face on find, "Best N" and "New best! N" on the game screen |
| Z01 | 1 | New: the boot event names the reset and, after a crash, the last task (below) |

## Replay proof

The whole `ORDER` (125 patches) replayed onto a fresh export of `28b9f0c8` plus nested `49b4380` with `git apply`: 125 applied, 0 failed. The replayed `firmware/` tree and the final lane tree differ only in two generated files (`maipai_bench_clips.c`, `lang_config.h`) and build output. Hash over every source file (shasum of the sorted file hashes, without `.git`, build, managed and fetched components, sdkconfig files, the two generated files): both trees give `9aca93fc59b1ca90`.

## Y04 onto the faces tree

`git apply --check` was clean on the faces tree (maipai_sounds.cc, maipai_games.cc), no conflicts to resolve.

## Z01: crashes named in the host log

The boot event now carries `reason_name` (poweron, software, panic, int_wdt, task_wdt, wdt, brownout, usb and the rest) and, after a crash, `last_task`: the task that ran on the other core at most 100 ms before the reset, its core, and the uptime in seconds (`name@c1+1234s`). The motion task writes that breadcrumb to RTC no-init memory every 100 ms with a checksum. Limits: it samples the other core only (the sampler itself is on this core), so it names a likely culprit and not proof; it survives a panic or watchdog reset and not a power loss. The host already logs every boot field. First boot after the flash: `unit boot: boot reason=11 reason_name=usb last_task= ...`.

Not done: a flash core dump. The partition table has a 64 KB `coredump` partition at 0xFF0000 and `CONFIG_ESP_COREDUMP_ENABLE_TO_FLASH` is off. Turning it on would give a full backtrace after a panic; that is a separate decision (it needs the host to fetch and decode it).

## Memory gate (plain image, memory line on, 831 s from boot)

Gate build: sdkconfig `MAIPAI_MEMORY_LINE=y`, same patches. The owner was not talking, so the run was idle plus 19 successful tool calls (nod, shake, look, head, centre, beeps, flashes, three spoken lines, two photos, find on and off; one head call was refused by the host as out of range), three style changes (big_eyes, minimal, stock, then back to classic), and the Colour Memory game started and left running for about 2 minutes.

| Number | Measured | Gate |
|---|---|---|
| internal_free steady | 45,027 to 53,507 | at least 25,000 |
| internal_min | 33,484 | at least 15,000 |
| int_big | 25,600 (never below) | at least 16,000 |
| psram_min | 7,366,808 | above 6,000,000 |

All four pass with wide margin. The 15,360 int_big dip the faces lane saw was not reproduced. The only snapshot code is the bench-only `self.face.snapshot` (`maipai_facebench.cc`, `lv_snapshot_take`), which is not compiled into a plain image; the dip belongs to bench builds. No allocation was changed. If a plain image ever shows int_big below 16,000, start with the LVGL snapshot and the picture-face frame buffers (the latter are already PSRAM).

## Image on the unit

Final build: plain image, memory line off, sdkconfig otherwise as the lane tree. Flashed to the app partition only (0x20000, ota_0; NVS, otadata and assets were not touched, nothing erased), under `usb-switch.lock`, read back from the unit.

- Size: 3,314,864 bytes (0x3294b0), 36 percent of the 0x4f0000 slot free.
- sha256 of the image and of the read-back from flash: `98b40bd1032efc181954335f9146734926f72630591daf65978a3d24daeda3c7`.
- Gate image (memory line on, replaced): `e2f0ec0382f1d7999157b6209ad1bf95e47654456635faa01c528ae67f05ec93`.
- The unit reconnected to the new host and sent its boot event with the Z01 fields. Lock removed.

## Host

The host (pid file `~/stackchan-models/newhost.pid`) was restarted from the current code. `DEFAULT_STYLE` is `big_eyes`; the settings page Look choices are Big eyes, Eyes only, Stock, Classic and Minimal. This unit keeps its saved style, which is Classic (it was Classic before the soak and was restored to it after); pick Big eyes on the Look page to change it.

## Host tests

Full run of `host/tests` at nice 15: 4090 passed, 77 skipped, 3 failed. Causes and fixes:

- `test_stackchan_face_watch` (the speaker-turn test): the look-toward-speaker setting has been off by default since ae29812; the test now turns it on. Real, fixed.
- `test_stackchan_touch_core`: the C test was updated for the 70 ms press floor (L07) but the Python test built the core from patch 105 alone; it now applies L07's header change first. Real, fixed.
- `test_stand_in_hub::test_a_turn_streams_signal_then_done_with_the_reply` and `test_fakes_stand_in_hub::test_the_default_turn_script_still_streams_signal_then_done`: failing at HEAD before any of this work. The stand-in hub streams the reply as a cue-less delta event between the two cues; both tests now compare only the cue events. Real, fixed.
- `test_stackchan_voice_e2e::test_tts_start_precedes_first_frame_and_loop_never_blocks_over_100ms`: an event loop stall of 0.379 s under load (a firmware build, a soak and a video render were running); passes alone. Timing flake, not changed.

## Left alone

- The host asks for `self.screen.set_face_background` and `self.screen.get_ambient_light`, which this firmware does not have; the host logs a warning and carries on ("the face colour stays as flashed"). Old, not part of this work.
