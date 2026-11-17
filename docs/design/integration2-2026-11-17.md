# Integration 2, 2026-11-17

Placement: unit firmware plus bench scripts. Tree: `~/esp/stackchan-rebase/final3` (a copy of `final2` with S10, S11, O01, O02 and FI05 applied in ORDER). Nothing is committed by this pass. Window scripts and logs: `~/esp/stackchan-rebase/final3/{win3.sh,win4.sh,gate.py,logs/win3,logs/win4}`.

## Result

The PLAIN image from this tree is on the unit: `final3/firmware/build-plain/maipai-stackchan.bin`, 3,445,184 bytes, sha256 `c1583752bb8420b20d4f2b1913def767c7bbc06e3b8049997c967d81801104ec`, written to the app partition only (0x20000), device hash verified, read-back hash equal, host link back at 02:00 (`newhost.log`: "StackChan answered again"). The assets partition was read first and equals the build's (`84a76e6d...`), so it was not written. The known-good image before this one is the final2 plain image (`86ad2965...`, 3,439,216 bytes); it was never needed as a restore.

The 12 minute gate passed on the bench image (plain plus serial tools plus the memory line): internal_free median 72,467 bytes (floor 40,000), internal_min 33,484 (24,000), int_big 27,648 (24,000), psram_min 7,018,932 (6,000,000), zero panics, zero task watchdog fires, zero host websocket drops, one reset (the start), zero latency gaps. Lowest stack margins of our own tasks: dvp_task 1,244, tcp_receive 1,352 (floor 1,024).

Two things did not come out as hoped. Read them before relying on the overlays:

1. **The governor hides the overlays most of the time (found by this pass, not fixed).** Over the 12 minute run the governor spent 68 percent of the time at level 4 (the flat look: every overlay off), 29 percent at level 3 and 3 percent at level 2. It makes a loop: at level 4 the load is 3 to 20 percent and the worst frame 13 to 16 ms, so after 3 calm seconds it restores to level 3, which draws the overlays again; the redraw of the whole overlay extent is one frame of 60 to 120 ms (load 67 to 80 percent for that second), and the single-frame rule (`MG_SHED_WORST_US` 28 ms) sheds straight back to level 4. Overlays are visible for about one second in every ten to fifteen. It also happened with CRT and glow off (window 4: level 4 at every snapshot, fps 8 to 17, load 12 to 17 percent). So the screen snapshots of stormy, party, celebrate, rain and sleeping show no overlay at all, only the eyes and the banner. Candidate fixes, none applied: skip the governor feed for the one window after an overlay starts or is unhidden; or redraw only the dirty boxes when unhiding instead of the whole extent; or require two slow frames in a window before shedding on the worst-frame rule. Needs Jesse's pick because it changes TA05 behavior.
2. **A reply with several sentences was not tested end to end.** The host's `remote say` answers "The person at the robot did not allow that message" (consent gate), and the injected question never reaches a reply because the host brain has no model address set (the camera tool says the same). What was verified instead: the unit code in `application.cc` handles every `tts sentence_start` message on its own (no once-only guard); each goes to `SetChatMessage`, then `route_speech`, then `maipai_subtitles_say`, which restarts the strip with the new words (`ms_begin`). On the unit, two captions in a row through the bench caption tool showed the second sentence replacing the first on the strip (`logs/win4/s3_caption_two.png`: "The high will be seventy two degrees. Have a wonderful day!" on two lines, banner above). The host side (one `sentence_start` per spoken sentence) is covered by `host/tests/test_stackchan_captions.py`. Still open: one real spoken reply with the unit's `<<` log lines counted.

## Steps

1. **Replay.** `final2` copied to `final3`; `replay_from.sh` applied S10, S11, O01, O02 cleanly. FI05 failed: it was written against a table without the S11 row, so its hunk context lacked the `turn_to_faces` line. The patch file got that one context line and the hunk header counts (7 to 8 lines). The whole of ORDER (172 entries) then replays onto the pristine base; the replayed `firmware/` tree and `final3/firmware` differ only in files a build makes (`dependencies.lock`, `maipai_bench_clips.c`, `sdkconfig.*`, `lang_config.h`), as in final2.
2. **S10 and S11 change no behavior.** S10 adds `hal/maipai_seek_core.h` and nothing includes it (grep of the whole tree finds no include and no call). S11 adds the `turn_to_faces` row (default talk) to the preference table and nothing reads it. No camera use, no head move until S12 wires the core. The unit reports `turn_to_faces: talk` in `self.prefs.get`.
3. **Host tests.** `tests/test_firmware_*.py`, the three parity tests and the zone layout test: 92 passed, 20 skipped. Stale expectations fixed on purpose: `test_firmware_fx_cores.py` and `test_firmware_sprites.py` kept hand lists of patches that had drifted (the sprites list applied V21 twice; the fx list lacked O02, which `look_core_test.c` needs for `ml_eye_center_y`, and FI05, which `prefs_core_test.c` needs for the captions default of off); both now apply the whole of ORDER the way `test_face_preview_parity.py` does. `scripts/fw-stress.py` drives all 26 overlay names now, with the heavy ones at "heavy" (the old call sent a number the host ignores). A wider run (`-k "prefs or unit or overlay or caption or subtitle or sentence or banner"`): 377 passed.
4. **Builds.** `build-bench` (`sdkconfig.bench.defaults` plus `sdkconfig.gate.defaults`) 4,043,920 bytes and `build-plain` 3,445,184 bytes (33 percent of the app partition free), one at a time, `nice -n 15`, `-j2`.
5. **Gate window (01:47 to 02:00, within the final 25 minute window).** Everything in the same run: CRT on, glow on, subtitles on, the banner row on, every one of the 26 overlays once (15 s each; stormy, party and celebrate at heavy for 40 s), a game, a listen test, two voice rounds. Window 4 (about 6 minutes, bench image, effects off) repeated the overlay snapshots and the caption pair, then put the plain image back (read-back hash equal again). Prefs were put back after both windows (captions off, CRT off, glow off, listening state restored).

## Refresh rates and gaps with the heaviest overlays (bench image, CRT and glow on)

The face bench draws for 8 seconds in each mode. The governor was at level 3 or 4 for most of these seconds, so the overlays were mostly hidden and these numbers are the face with the governor's help, not the overlays at full cost.

| Case | idle fps / p99 ms | move fps / p99 ms | talk fps / p99 ms |
|---|---|---|---|
| no overlay | 11.5 / 100 | 33.6 / 57 | 27.6 / 100 |
| stormy, heavy | 14.9 / 100 | 33.9 / 50 | 28.6 / 93 |
| party, heavy | 13.1 / 100 | 33.9 / 48 | 27.7 / 100 |
| celebrate, heavy | 15.8 / 100 | 31.8 / 71 | 28.2 / 100 |

Idle is slow on purpose (the face redraws only when it changes). Single frames of 60 to 120 ms appear at every overlay start and every unhide; that is what trips the governor.

## Screen snapshots (opened and judged)

- Big eyes with the banner: the banner row reads "Remote connected: Settings pa..." with the record chip, the eyes and mouth are clean. Subtitles were off the strip because no reply was spoken (see 2 above).
- Big eyes with subtitles and banner (window 4, `s3_caption_two.png`): two lines of white text on the strip, banner above, the face stays clear. Good.
- Stormy overlay, sleeping zzz, party, celebrate, rain: no overlay in any picture (governor at level 4, see 1 above). The sleepy faces in window 4 are the host's rest routine, not the overlay.
- Files: `final3/logs/win3/snap_*.png`, `final3/logs/win4/s3_*.png`.

## Where it is

The patch edits (FI05 context line), the three test and script edits and this note are in the working tree of `~/Developer/github.com/getmaipai/stackchan`, uncommitted. The image is on the unit only; not on GitHub.
