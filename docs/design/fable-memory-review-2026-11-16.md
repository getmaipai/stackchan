# Memory and risk review of the merged firmware, 2026-11-16

Status: read-only review of the notes at HEAD `325bc4a` (merge, consolidation, firmware-memory, strip-results, latency,
picture faces, games, legacy audit, travel, update, security, the two queue briefs). Nothing was built, flashed or
measured by this review. Labels: [sure] follows from the toolchain's own behavior or a number in the notes; [measure]
is a plausible gain that a build must confirm; [guess] is an informed guess with no number behind it.

## Bottom line

The merged image passes the gate by 384 bytes on the one number that matters most (`int_big` 16,384 against 16,000).
That is not headroom, it is luck: the same tree measured 25,600 and 31,744 on earlier trains, so about 9 to 15 KB of
largest-block room was spent by the last two tracks (overlays, prefs, pack loader, remote gate, anime face). The plan
(headroom pass, per-feature budget, data in PSRAM, loadable packs) is right. Three things should change before any
queued feature is built: the gate must run with a real spoken turn and the camera on (every gate so far ran with the unit
hard muted), the gate needs a fragmentation number and a long soak, and on-device face detection does not fit the core
image as designed and should be planned as a measured experiment in a separate build, not as a default-on setting.

## 1. The memory plan, and what I would do differently

Ordered by expected internal bytes freed, risk noted. Numbers are per the notes or the toolchain's documented sizes.

1. **Stop registering every tool's descriptor on the heap at boot.** [sure] Four game tools cost 1.2 KB of steady internal
   heap (games note). The image registers on the order of 60 to 90 tools, so the tool table alone is likely 15 to 25 KB of
   internal heap, held forever. Keep descriptors as `const` tables in flash and build the `tools/list` reply on demand into
   a PSRAM buffer. Risk: low, one place to change. This is the largest single win available and costs no feature.
2. **Finish the PSRAM-stack rule and make it a lint.** [sure] Two boot loops (TB01 ring task, V03 music worker) came from the
   same cause: a task on a PSRAM stack reached NVS or the flash API. Rule: a PSRAM-stack task never calls NVS, `spi_flash`,
   or anything that reads saved settings; it asks the main task through a queue. Add a debug wrapper around the settings
   reader that asserts the current stack is internal, and a script that lists every task created with the external-memory
   caps and the symbols it reaches. Frees nothing by itself, but it is what lets the next items move stacks safely.
3. **Move the remaining internal task stacks that do no flash work.** [measure] Legacy 058 measured 5 KB from trimming audio
   input (6144 to 4096), audio output (4096 to 3072) and reconnect (6144 to 4096) to their high-water marks. The main task,
   system event task, timer task and IPC task stacks are each a build option; read the high-water marks first (one minute
   line with `uxTaskGetSystemState` while the memory line is on) and trim to high-water plus 1.5 KB. Expect 4 to 8 KB.
4. **Wake engine and front end in PSRAM.** [measure] The front end can be told to allocate more in PSRAM (its memory mode
   option). The 9.2 KB `dl_nn_activation` table in internal `.data` (strip map, rank 1 object) belongs to the model library;
   check whether the current library version has a flash-table option. Expect 5 to 20 KB. Risk: wake latency and the
   stop-word creation test (34 KB free needed at creation; the stop word is off today, which hides this).
5. **Wi-Fi and the IP stack buffers in PSRAM.** [measure] The option that tries PSRAM for Wi-Fi and IP stack allocations
   moves the dynamic buffers out of internal RAM; the static receive buffers stay internal because they are DMA targets
   (about 1.6 KB each, three today). Expect 10 to 20 KB. Risk: uplink audio throughput; measure wake-to-first-frame and
   the 60 ms frame pacing before and after. The strip note's "3 to 2 static buffers made no linked change" is expected:
   these buffers are heap, not static, so only a runtime line shows them.
6. **TLS library allocations in PSRAM.** [sure] The option for external memory allocation in the TLS library exists in
   this toolchain. The core speaks plain WebSocket, so this only matters when the private-network client runs (one TLS
   session to the control plane). Expect 0 at home, 10 to 30 KB while traveling. Risk: none at home.
7. **Flash driver in ROM.** [measure] `libspi_flash` holds 8.2 KB of internal RAM (strip map, rank 4). The option to use
   the chip's ROM flash driver drops most of that. Risk: low on this chip; check the flash chip model is in the ROM list.
8. **LED buffer and small static tables to PSRAM.** [measure] `single_led` holds 3.7 KB static internal. The pixel buffer
   can live in PSRAM if the driver copies to a small internal DMA buffer. Expect 3 KB. Risk: low.
9. **Screen draw buffer size.** [sure] The draw buffer must stay internal because the display flush uses DMA. Legacy 058 cut
   it from 20 to 10 lines (6.4 KB). The redraw timer is now 20 ms; measure refresh rate at 10 lines before accepting.
10. **I2S DMA descriptors.** [measure] Descriptor and DMA buffers are internal. Lower the descriptor count to what the 60 ms
    frame needs plus one; expect 2 to 4 KB. Risk: audio underruns; the playback-gap trace (legacy 070) must exist first.
11. **Camera frame buffers in PSRAM, DMA buffers freed when idle.** [sure] Frame buffers belong in PSRAM; the driver's DMA
    half buffers are internal and exist from init. Deinit the camera when no feature holds it (the cue path already knows).
12. **Compiler and placement options.** [measure] Heap and ring-buffer functions placed in flash free IRAM (IRAM and DRAM
    share the same pool on this chip, so IRAM freed is DRAM gained). The note forbids moving scheduler functions to flash;
    heap and ring-buffer placement are different options with a smaller latency cost. Expect 2 to 5 KB.

Do not: lower the always-internal threshold below 256 (already applied; 128 risks DMA and ISR allocations landing in
PSRAM), or turn Wi-Fi IRAM options off without a throughput measurement on the owner's mesh network.

What I would not do differently: PSRAM for all feature data, one pack loader with a flash cache, lazy start for the
private-network client, admission control before a module starts. Those are right.

## 2. The gate

Today: steady `internal_free` at least 25,000, `internal_min` at least 15,000, `int_big` at least 16,000, `psram_min` above
6,000,000, 10 minutes, no reset. Weak points: every recorded run had the unit hard muted, so the voice path, camera and
music never ran during a gate; `int_big` alone does not show fragmentation; 10 minutes shows no leak.

Proposed gate, every build step:

| Number | Rule | Why |
|---|---|---|
| `internal_free` steady | at least 40,000 | 25 KB leaves one feature's worth of room; the merged image shows 35 to 38 KB and already cannot take the next step |
| `internal_min` | at least 24,000 and never more than 20,000 below steady | catches a boot or turn spike that eats the margin |
| `int_big` steady | at least 24,000 | the stop word needs a block this size; the private-network client needs 24,000 to start |
| `int_big` minimum | at least 16,000 | the current floor, kept as the hard floor |
| fragmentation | `int_big / internal_free` at least 0.5 at steady, measured after the stress script, not only at idle | a heap with 40 KB free in 2 KB pieces is full |
| `psram_min` | above 6,000,000 with the largest pack held | unchanged |
| per-task stack | high-water margin at least 1,024 bytes on every task, printed once a minute | stack overflows show as random resets |
| stress script | the same scripted 12 minutes every time: one real spoken turn through the bench clips, camera photo, music mode on, every overlay, a game, a remote cue, a listen test, a pack push | today's gate skipped the voice path |
| soak | 24 hours with the memory line on, once per release candidate: `internal_free` drift under 2,000 over the run, no reset, no watchdog, heap integrity check passes at the end | leaks and slow fragmentation show only over hours |
| off costs nothing | each optional feature compiled out against linked but off: within 1,024 bytes on `internal_free` and `int_big` | the existing rule, kept |
| latency | wake to listening sound queued at most 50 ms; p95 frame time at most 33 ms during a spoken turn | the performance contract, measured not estimated |

A build that fails the proposed gate but passes the old one ships behind its switch, default off, and is named.

## 3. Queued features against the budget

| Feature | Fits as designed? | What to change | Order |
|---|---|---|---|
| Banner row | Yes [sure]: one container and one label, about 1 KB of screen objects, created once | Draw it in the existing face layer; no task, no timer | 1 (the remote cue depends on it) |
| Bigger overlays, combined presets | Yes for memory [sure], no for draw time [measure] | Particles in PSRAM, cap stays, governor sheds; measure CRT plus rain plus speaking p95 | 3 |
| Swipe pages and control sheet | Yes if built on dismiss and destroyed on close [sure] | Never keep a hidden sheet alive; one screen object tree at a time | 2 |
| More languages as packs | Yes [sure]: flash and PSRAM only | Make sure string tables are `const` in flash, not copied into RAM at boot | 4 |
| Motion blob and pan-stop search | Yes [measure]: a 40 by 30 gray frame difference is about 2.4 KB, camera on only while searching | Build this first as the local "look for you"; it needs no model | 5 |
| On-device face detection (int8 model) | **No, not in the core image** [sure for the margin, measure for the model]: the model's working memory and the camera's DMA buffers both want internal RAM, and the merged image has 16 KB of largest block | A separate `eyes` build or the `home` preset, behind `MAIPAI_FACE_TRACK`, with admission control (at least 40 KB free and a 24 KB block before the camera starts), the detector run only at the pan stops, never continuously; ship default on only if the proposed gate holds with it running during a spoken turn | 6, after the headroom pass reaches the proposed gate |

Build order: headroom pass to the proposed gate first (nothing else lands until `int_big` steady is 24 KB), then 1 to 6 above.
Each checkpoint is flashed and gated, as the brief says.

## 4. Avoidable internal RAM and latency in what exists

- **Tools registered at boot**: see item 1 above. Largest avoidable cost in the image.
- **Six-language string tables**: fine if `const`; a boot-time copy into heap strings is the failure mode. Check the map.
- **Pack loader**: the flash cache checksum at boot reads up to 1 MB from flash on the main task; that is about 100 ms of
  boot time, acceptable. The pack boot task starting 15 s after boot is a workaround, not a design: a task with a PSRAM
  stack cannot end itself, so it stays allocated. Make it a one-shot on the main task's idle hook instead.
- **Picture face core**: three decoded 153,600 byte frames in PSRAM and a 20 KB PSRAM decode stack are fine. The decode
  task is kept forever once created; acceptable, but it must never touch NVS (item 2).
- **Game engine**: zero internal when idle except the tool table; good. 4.1 KB while whack-a-mole runs is screen objects
  and returns. Nothing to change.
- **Private-network client**: 20 KB internal and about 220 wakeups a second while running, lazy start, no clean stop. At
  home it costs nothing. Away, it and the camera cannot both run on today's margin; admission control must say so in words.
- **Face loop priority**: correct (below audio and servo). The one 97 ms ring update against a 30 ms budget is the ring
  task on a PSRAM stack doing SPI output; measure whether it is cache misses on the PSRAM stack or the LED driver blocking.
- **Overlay and preference state**: already moved to PSRAM in TC03. The 200 byte error buffer is fine.

## 5. Top five other risks in what exists

1. **Rollback timer meets the cold-boot camera panic.** [guess, check first] Patch 160 keeps a new image only after 20 s
   of uptime with the host link up. The vendor camera component panics on about half of cold USB boots (merge note). A
   new image whose first boot is a cold boot can be marked invalid by a fault that is not its own, and roll back. Check:
   install an update, power-cycle, read the boot event. Fix: count a panic against the image only after the camera init
   has finished, and accept "60 s of uptime with no panic" as a second way to validate when no host is reachable (a unit on a
   trip has no host link at boot).
2. **Remote cue trust boundary.** [sure] The unit's gate passes any call whose `source` is not `remote`, and the caller
   chooses the field. The paired host is trusted by design, but one host bug lets a controller act with no cue. Fix: the
   host routes set `source` themselves and refuse a controller-supplied `source` or token; the unit adds a second floor,
   independent of `source`: a head move, dance, game or find with no open cue window and no recent wake, touch or spoken
   command is refused and logged. Document the boundary in `safety-and-privacy.md`.
3. **Every gate ran with the unit hard muted.** [sure] The wake engine, uplink, decode, camera and music paths never ran
   during a memory gate. The stop word is off because it needs 34 KB at creation, which hides a second failure. Fix: the
   stress script in section 2, with the bench clip injection that already exists.
4. **Boot-loop class is not closed.** [sure] The PSRAM-stack flash access fault appeared twice in two days. Without the
   lint in item 2 it will appear again in the next task someone adds. The restart guard with back-off (R04) hides it from a
   user as a slow unit, not as a crash, which makes it harder to see.
5. **Test gaps that hide real behavior.** [sure] Pickup and set-down were never exercised (the owner must lift it); the
   picture pack never crossed the real paired link; wireless update was never run on a unit and the Home-served path sends no
   signature; the quiet mode toggled itself twice with no recorded touch before the 70 ms floor, and the floor was not
   verified against that fault; the core-dump partition is off, so the next panic has no backtrace. Turn the flash core
   dump on (64 KB partition exists, zero RAM cost) before the next soak.

## What this review could not check

No tree was built and no map file was read, so every size in section 1 is the strip note's number or the toolchain's
documented default, not a measurement of the merged image. The tool-table estimate scales one measured number (1.2 KB
for four tools) by a count of registered tools taken from the patch list, not from a `tools/list` reply.

## Fix status

Written 2026-11-16 by the fixes session (Claude, tree `~/esp/stackchan-rebase/fable`, a copy of `merge` with patches FM01 to FM05 on top; nothing committed, nothing flashed). The headroom items (tool descriptors, stack trims, wake front end memory mode, Wi-Fi buffers, gate stress script and floors) belong to the headroom session in tree `mem`; their rows say so and carry no status from this session.

| Review item | Done | By | Evidence |
|---|---|---|---|
| Risk 1, rollback meets the camera panic | Done in FM01. The image is marked good at first boot and a flash record judges it: free passes for a crash before the camera settles, a strike after, two strikes roll back, 20 s with the host or 60 s with no crash keeps it, 120 s open rolls back. | Fixes session | `update_core_test.c` (scripted boots: good install, trip with no host, three camera panics, two real crashes, power cuts, hang, camera never settles); the image builds |
| Risk 5, core dump off | Done in FM02: flash dump on, 20 tasks, log strings off, `boot_core` event after a crash, `scripts/fw-coredump.py` reads and decodes. Not run on a real crash (needs a unit). The review's "zero RAM cost" was wrong: the build grew internal static RAM by 4,048 B (164,051 to 168,099 on `idf.py size`) and flash by 11,344 B (image 3,426,768 B). The merged image's `int_big` margin was 384 B, so the unit's memory gate decides whether it stays on in the core image. | Fixes session | build size lines; `test_psram_stack_lint.py` (reader checks) |
| Risk 2, remote cue trust boundary | Done in FM03 and `remote_trust.py`: second floor on the unit that ignores `source`, host id stamped at the one chokepoint, controller requests naming `source`, `token` or `host` refused and logged. Documented in `safety-and-privacy.md`. | Fixes session | `remote_floor_test.c`, `test_remote_trust.py` (14 tests, includes the chokepoint with the socket stubbed) |
| Section 4, pack boot task | Done in FM04. The review described a PSRAM-stack task that cannot exit; the code is an internal-stack task that ends itself, started by a 15 s timer. Now the main loop starts it on the first standby (or after 120 s), the timer is gone. | Fixes session | `packboot_core_test.c`; build |
| Risk 4, boot-loop class | Done in FM05 and `scripts/psram-stack-lint.py`: finds every PSRAM-stack task and follows calls by name to NVS, flash, partitions, settings. It finds the ring task in the earlier tree and the music worker in `final`. In the merged tree it found real hazards: the pickup reaction (IMU task) could reach the saved volume (late find restore) and be the first reader of the privacy state and the sound policy. Fixed: `maipai_stackrule.h`, guards in the loaders, closed answer on a wrong stack. The Settings class check is patch M05 of the headroom session (its test in `test_firmware_trackc_patches.py` still names M06 and fails until that name is fixed). | Fixes session (M05: headroom session) | `test_psram_stack_lint.py` (13 tests) |
| Risk 5, tests that never ran | Done: the pack and picture-face push against the firmware's own C cores with fragments of 1 to 4096 bytes, a dropped link before and after a piece, a reboot and a reconnect (`test_wire_packs.py`, 19 tests); the unit's real Ed25519, paired-host, 20 percent and key checks compiled for the PC with a fresh key, over the host's one-read route that serves the image and its `.sig` (`test_unit_update_check.py`, 8 tests); pickup events through the real companion, touch poll and reactions (`test_pickup_events_host.py`, 9 tests). Still needing hardware: the unit lifted by hand, a wireless update on a unit, the zlib probe and the screen for picture packs. | Fixes session | the three test files |
| Findings from those tests | The host wakes a sleeping unit on any pickup event, including `set_down`; the host makes no reaction to the unit's `shaken` (the unit shows its own). Left as built, named here. | Fixes session | `test_pickup_events_host.py` |
| 1. Tool descriptors in flash | Not in this session | Headroom session | |
| 3. Internal task stacks | Not in this session | Headroom session | |
| 4. Wake front end in PSRAM | Not in this session | Headroom session | |
| 5. Wi-Fi buffers in PSRAM | Not in this session | Headroom session | |
| 2. The gate (stress script, floors) | Not in this session | Headroom session | |

Flash: none. The unit was not touched; the USB lock was absent at the start and the port was left alone. Before any flash of this tree: a bench image, a 15 minute soak with zero panic and zero watchdog, the lock held, app partition `0x20000` only, and the known-good image ready to go back.

Patch order: FM01 to FM05 follow TC04 on `ORDER`. They replay onto a clean copy of `merge` with `git apply` and reproduce the `fable` tree byte for byte. The headroom session's patches touch some of the same files (`hal_mcp.cpp` for FM03, `sdkconfig.core.defaults` for FM02, `maipai_tbprefs.cc`-adjacent code for FM05): replay both sets once and fix any hunk that moved.
