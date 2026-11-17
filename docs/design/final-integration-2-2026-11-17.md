# Final integration 2 (2026-11-17)

Bottom line: the whole `ORDER` (through the packs, pages and face seek patches, plus one new hardening patch, FI07) builds, replays byte for byte onto the pristine base, passes the 14 minute stress gate on the unit, and the plain image of it is flashed. Four things only the owner can check are listed at the end.

## Image on the unit

- Before the work: the integration 2 plain image (`final3`), sha256 `c1583752bb8420b20d4f2b1913def767c7bbc06e3b8049997c967d81801104ec` (found by an on-device digest check; the `final4` plain image `c124069f...` was not on the unit).
- Now: the final5 plain image, sha256 `a76dd99946535b10af67168643437cf49328216a8f42b62d3dd627780891bd50` (3,508,864 bytes), app partition `0x20000` only, device-side hash verified and read-back hash equal. The assets partition matched the build (`84a76e6d...`), so it was not written. NVS was never touched.
- Bench image (not left on the unit): `c89b037112853f26dd956de32025a5e02084e680d33a1229c5c77691a12b1901`, 4,110,992 bytes.
- Tree `~/esp/stackchan-rebase/final5`; logs in `final5/logs/` (`win10`, `win11`, `win12`, `win12b`).

## Patches

| Patch | What it adds | Source lane |
|---|---|---|
| K10 | Pack types, phrase packs, cache format 2, PSRAM-state inflate (`maipai_inflate.h`) | packs |
| K11 | Language pack holds the screen words | packs |
| K12 | Offline phrases pack | packs |
| K13 | Loader consumers (filler, phrase, language) | packs |
| P10 | Gesture state machine core | pages |
| P11 | Pages data and layout core | pages |
| P12 | Pages and control sheet drawing | pages |
| P13 | Wiring, tools, the swipe switch; bench-only `self.page.bench_swipe` and `self.page.bench_tap` | pages |
| S12 | Seek core, measured geometry | face seek |
| S13 | Seek wire core and camera grab | face seek |
| S14 | Seek task, tools, the `turn_to_faces` setting | face seek |
| FI07 (new) | The picture look loader and frame decoder use the PSRAM-state inflate | this integration |

K10 to S14 applied to `final4` in `ORDER` order with no conflicts (`git apply`, no 3-way needed: each lane's patch was cut against the one before it). A fresh replay of all of `ORDER` onto the pristine base (`final5-replay`) equals `final5` file by file; the only differences are the generated `dependencies.lock`, the generated `lang_config.h`, and the bench-only files the gate builds add (`maipai_bench_clips.c`, `sdkconfig.bench.defaults`, `sdkconfig.gate.defaults`).

## Hazards closed

- `maipai_picface.cc` called the ROM inflate (about 11 KB of decompressor state on the caller's stack) in two places. `look_inflate` ran on the tool task when a look pack is applied. Both now call `maipai_inflate_raw` or the new `maipai_inflate_zlib`, whose state lives in PSRAM (patch FI07). No ROM inflate call is left in our sources.
- `scripts/psram-stack-lint.py` passes: 11 PSRAM-stack tasks, 0 unreviewed paths.
- `touch_inject` and both bench swipe tools sit behind `CONFIG_MAIPAI_FACE_BENCH` (declaration, definition and the two tools). The plain image has none of them.
- Stack margins of tasks we create (lowest seen over the 14 minute run): `dvp_task` 1,180 B, `stackchan` 1,416, `Svc` 1,444, `imu` 1,548, `taskLVGL` 2,096, `snap_worker` 2,444, `seek` 2,988, `headtouch` 3,768. None is under 1,024 B, so no stack was changed. The system `ipc0`, `ipc1` and `IDLE` tasks have fixed sizes and are outside the rule.

## Gate (bench image, window 11, 847 s)

Order of the run: refresh measurements (plain, overlay, page open, sheet open), every swipe check through the bench finger, a language, a phrase and a filler pack pushed and removed, a seek burst and a calibration, every overlay once (heavy ones measured), a game, the listen test, subtitles, one voice round, two played turns, then the scripted stress drive for the rest of the run (42 host calls, all answered 200: beeps, flashes, overlays, CRT, nod, shake, look, game, dance, photo, network test).

| Check | Result | Floor |
|---|---|---|
| internal_free steady (median) | 69,519 | 40,000 |
| internal_min | 33,484 | 24,000 |
| int_big steady (median) | 25,600 | 24,000 |
| int_big lowest after settling | 25,600 | 16,000 |
| int_big / internal_free at end | 0.37 (free is above 64 KB, so the ratio rule does not apply) | 0.5 |
| psram_min | 6,881,488 | 6,000,000 |
| Lowest stack margin of a task we create | 1,180 B (`dvp_task`) | 1,024 |
| Panics, task_wdt, resets after the start, host websocket drops | 0, 0, 0, 0 | 0 |

GATE PASS. The smoke run before it (window 10, 764 s) passed the same way (internal_free 69,967, int_big 25,600, psram_min 6,958,540).

Swipe and page checks (`final5/winp5.py`, 33 of 33 passed): swipe right and left between pages, a bump at the end of the strip, swipe up for the sheet, the sheet closing by itself after 6 s, swipe down closing the sheet and leaving a page, edge swipes changing no page, a slow drag and a tiny move doing nothing, a page returning to the face after 20 s, all six host-driven pages, a new strip set and read back, repeated and unknown names refused with a sentence. In the smoke run two checks failed for script reasons only: the sheet timer was read after a 5 s snapshot, and the memory call named a tool that does not exist. Both are fixed in `winp5.py`.

Packs over the serial tool path (bench build): language pack accepted (224 B), phrase pack (78,194 B), filler pack (25,886 B), each held; French screen words drawn from the language pack; all three removed afterwards and the face language put back.

Face seek: a wake-word-triggered address ran 5 bursts, 10 frames, 5 head moves, longest camera grab 191 ms, no late skips, no grab failures, longest loop gap 392 ms. A calibration ran to the end and answered `inconsistent` (the room had nobody in it to measure against), so nothing was applied.

Refreshes per second and 99th percentile gap in milliseconds (CRT and glow on, subtitles on):

| Case | Idle | Moving | Speaking |
|---|---|---|---|
| Face only | 11.5, 100 | 33.2, 58 | 29.0, 100 |
| Heavy stormy overlay | 22.9, 100 | 19.0, 98 | 26.2, 98 |
| Clock page open | 13.6, 100 | 28.4, 72 | 25.9, 100 |
| Control sheet open | 11.3, 100 | not run | not run |

Speaking with other heavy overlays: rainy 19.5, 100; windy 24.1, 98; party 16.4, 100; celebrate 24.0, 90. Governor time at each level over the whole run (from the unit's log): level 0 full 64.3 percent, glow off 7.1, scanlines off 6.4, particles 50 percent 5.6, particles 30 percent 12.9, flat 3.7. No overlay was hidden in any status poll.

Wake to first sound: not measured. The household host holds full quiet (the owner's own setting; the host reported "the robot is full quiet" and refused every spoken reply and every wake turn). The bench wake injection reached the unit's wake cue in 2 ms; no sound plays in full quiet. The host refused the scripted `say` with the "did not allow that message" sentence for the same reason. I did not change the owner's quiet setting.

## Pictures (opened and judged)

In `final5/logs/win11/` and `final5/logs/win11/winp/` unless noted:

- Big eyes with subtitles and the remote banner: `snap_caption_two.png` (banner at the top, eyes, smile, the second sentence on the strip), `snap_caption_one.png`; with a storm overlay `snap_caption_overlay.png` (rain and clouds, eyes and mouth clear); `snap_bigeyes_subtitles_banner.png` is the same face after the caption was cleared.
- Control sheet: `winp/04_sheet.png` (title bar, Wi-Fi and battery line, Volume and Bright sliders, Mute, Quiet, Light, Find me, then Timers, Games, More). Judged correct.
- Clock page: `winp/01_clock.png` (large digits, date, three page dots). Games page: `winp/02_games.png` (three game rows with best scores, dots).
- French screen words from the language pack: `snap_french_words.png`.
- Camera cue: `final5/logs/win12b/cue_1.png` (the camera glyph in the top right corner during a seek look). Two earlier tries missed the glyph (`win12/cue_*.png`) because the snapshot did not land inside a burst.

## Windows

- Window 10 (bench smoke): 13.8 min. Window 11 (full gate, then the plain image kept): 15.2 min. Window 12 and 12b (camera cue picture): 2 and 3 min, each returning the plain image with a read-back hash. Lock file and `usb-queue.txt` used and cleaned each time.
- The unit's preferences were put back as found: captions off, CRT off, glow off, `turn_to_faces` talk, pages strip as it was, face language as it was, privacy back to quiet on (the saved state).
- A bench tap on the face during the swipe checks toggled vision off (the real face gesture); the gate turned it back on before the seek step and restored the saved state at the end.

## Host

- Host restarted from the current repo code (pid 29881); the unit reconnected (`unit boot` and `wifi state=ws_up` in `newhost.log`, unit online in the settings API). `http://127.0.0.1:9782/settings` lists Swipe pages, Packs, Language and Who turns toward faces.
- Host tests in six chunks under `nice -n 15`: 4,430 passed, 86 skipped, 1 failed. The failure was `look_core_test.c` inside `test_stackchan_train4.py`: its header chain stopped at FI04 plus K10 and K11, so `ml_eye_center_y` (added by O02) was missing. The chain is now all of `ORDER` (the pure headers only), and the file passes (50 of 50). `test_link_loss_run_loop` passed three times alone and in its chunk. `bash scripts/check.sh` passes (hygiene 1,868 files, boundary ok).

## Only the owner can verify

1. A real wake by voice and the first sound after it (the host is in full quiet).
2. How the finger swipes feel on the glass (the bench finger passes every rule, but speed, edge grip and dimming are a hand's judgment).
3. Turning toward a real face (the seek ran, but no person stood in front of the unit, and calibration needs one).
4. Subtitles in a real spoken conversation with the host's sentence text, and the sounds of packs, fillers and phrases at the speaker.
5. Pickup (no tool can lift the unit).
