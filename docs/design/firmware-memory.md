# Firmware memory

Internal RAM is the constraint. Flash and PSRAM are comfortable. Figures below were measured or estimated on the
old base and must be re-measured on the new base (firmware-base.md) before any saving is trusted.

## Known numbers (old base)

- PSRAM: about 7.2 MB free of 8 MB.
- App slot: 5 MB, about 1.75 MB free (34 percent). Assets partition: 3.7 MB free.
- Static internal RAM: 173,247 B used of 341,760 B. 168,513 B left for heap.
- Free internal heap: about 76 KB (low water 53 KB) before the private-network client. About 29.7 KB (largest block 28.7 KB) with it on.
  The gap of about 23 KB matches that client's estimated 20 KB.
- Thin stacks: audio input 1.76 KB, audio output 1.58 KB, reconnect 2.1 KB, avatar 1.43 KB, detection 1.85 KB.
- Headroom was only 4 to 5 KB above the floor with the client on. Nothing new fits in internal RAM without freeing something first.

## Memory gate (every build step)

1. Flash the unit. Run one full spoken turn with camera and music on. Read the per-minute memory report for 10 minutes.
2. Pass: steady `internal_free` at least 25 KB, lowest seen at least 15 KB, `int_big` at least 16 KB.
   No reset, stall dump or watchdog fire. Audio lateness p95 no worse than baseline.
3. A step costing more than 4 KB steady needs a written reason. More than 8 KB means move a stack or buffer to PSRAM first.
4. New features allocate from PSRAM. A new internal stack needs a measured high-water mark with at least 1.5 KB left.
5. Flash: keep at least 20 percent of each OTA slot free. PSRAM: keep `psram_min` above 6 MB.
6. The stop-word model needs at least 34 KB free at creation.
7. Record every number in a table with build id and date.
8. A latency gate sits beside it: p95 per stage must not get worse.

## Freeing internal RAM first (estimates, order of work)

1. Start the private-network client only when the LAN path fails: about 20 KB, plus about 220 wakeups a second. Needs a clean stop.
2. Close the PSRAM-stack experiment (Opus stack to PSRAM): up to 24 KB, needs a 30 minute soak.
3. Wi-Fi and lwIP IRAM options off: 10 to 25 KB static, throughput risk.
4. Find the 36 KB static `.bss` and 36 KB `.data` consumers: 5 to 30 KB.
5. Wake engine alloc-more-PSRAM: 5 to 20 KB.
6. Small-allocation threshold 512 to 256: 3 to 8 KB.
7. Wi-Fi buffer counts, AMPDU, LVGL draw buffer, camera DMA buffer, avatar task stack: a few KB each.
8. Remove the gateway fallback, MQTT and IPv6 (small RAM, 25 to 40 KB flash).

Change one variable at a time. None of these is proven until measured.

## Cut list (flash, ranked, estimates)

1. Old stop-word model out of assets: about 2,136 KB. Replaced by a small command set (decision 15).
2. Icon font subsets: 70 to 80 KB. 3. ASCII-only font: about 100 KB (accented names would show blank).
4. MQTT out of the source: about 25 KB. 5. Cert bundle reduced to the roots we need: 35 to 65 KB.
6. Wi-Fi portal page replaced: 65 to 75 KB. 7. Unused LVGL widgets: 15 to 30 KB. 8. IPv6 off: 10 to 20 KB.
9. Log level to WARN: 30 to 80 KB. 10. Wi-Fi extras off: 20 to 60 KB. 11. Leftover stock sounds: about 15 KB.

Do not: turn C++ exceptions off (tool exceptions are caught so a failed tool never fails the answer), move scheduler functions to flash, drop the logging library.

## Tiers

- Tier 0, resident core: audio loop and one wake model, face and ring, network and pairing, clock and timers, settings, local commands, privacy cues.
- Tier 1, local modules the owner installs (work offline): face packs, one language pack, sound packs, a chosen number of game packs, alert tones.
- Tier 2, host-run (online only): other games, vision, tutors, rare-script caption rendering. Offline they hide with a plain message.
- Tier 3, hub-only: household features.

Every optional module has a manifest: `needs_host`, `offline_ok`, `flash_kb`, `psram_kb`, `internal_kb`, `max_runtime`.
The settings page shows a budget meter. A module that does not fit is refused in plain words, naming what to remove.
Games and packs are signed data run by one engine. No scripting runtime.

## Rule: off costs no memory

1. Build switch: a Kconfig flag and a `firmware.toml` option compile the feature out.
2. Runtime switch: linked but off means no task, no heap or PSRAM, no timer, no socket, nothing in the idle loop.
3. Proof: the gate runs one baseline with the feature compiled out and one with it linked but off.
   `internal_free` and `int_big` must match within about 1 KB.
Linked code can still hold static internal `.bss` and `.data`. For each optional feature read the linker map first and move large buffers to PSRAM.

## Guardrails for dynamic memory

1. Heavy choices (client, camera stack, wake model, language, face pack, games) are made in settings and apply at next restart.
2. The core reserves its pools first, in a fixed order, and keeps them.
3. Module data lives in PSRAM only. One PSRAM arena (for example 256 KB) with a bump allocator reset on exit.
4. Small packs are read in place from flash by memory mapping.
5. Admission control: a module starts only if the arena and the internal watermark allow. Never try and see.
6. Every module allocation is checked. A failure aborts that module, frees the arena, shows a message. The core keeps running.
7. Modules load only when idle. The audio hot path stays internal.
8. Lazy start is limited to features built for it, with one owner and a leak-tested clean stop.

Tests: cycle every module on and off 1,000 times (return to baseline within about 1 KB), a 24 hour soak, forced allocation failures,
the heaviest allowed combination at once, stall and latency checks with a module loaded.
Stages: (1) v1 selects everything at boot, nothing swaps at run time. (2) The PSRAM arena after v1 data. (3) Hot swap only if the first two prove stable.

## Open

- Re-measure the baseline on the new base and settle the 29.7 versus 76 KB figures with two 10 minute runs from one build id.
- Whether the new base leaves enough room that stages 2 and 3 are unnecessary.
- Which task stacks the minute report omits.

## Dance ladder and movement limiter (patches ML01, MD01 to MD03), 2026-11-17

Gate image soak, 12 minutes, unit on the USB cable (first build, before the stale-reading fix, which changes no allocation):
`internal_free` median 85939 (floor 40000), `internal_min` 33484 (floor 24000), `int_big` 38912 (floor 24000), `psram_min` 7170496
(floor 6000000), no panic, no watchdog fire, no host drop; lowest margins on our tasks 1176 (tcp_receive) and 1444 (Svc).
App image grew by about 13 KB of flash (3598000 to 3611360 bytes, plain). New steady RAM: one small struct for the limiter (about
80 bytes) and, while a dance runs, one modifier (about 450 bytes) on the heap; no new task, no new stack. `scripts/psram-stack-lint.py`
reports 0 unreviewed paths.
