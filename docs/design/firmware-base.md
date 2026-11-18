# Firmware base and rebase plan

This is the one note that names the upstream firmware bases the repo patches.
Included code keeps its notice in LICENSE, NOTICE and THIRD-PARTY.

## Pins

- Old base: xiaozhi-esp32 v2.2.4 (`e77dedb`) on ESP-IDF 5.5.4, with the M5Stack StackChan firmware pinned at `1b57655`.
- About 130 patch files. 126 are applied by `recipe.sh`, 3 are orphans, and 149 is applied to the private-network library.
- Rollback tag for the old image: `stackchan-known-good-2026-10-20`.

## Decision: rebase before v1 (owner, 2026-11-15)

Two hops, one at a time:

1. Land on M5Stack's own pin: xiaozhi-esp32 2.5.2 with M5's 25 KB patch (11 files) on ESP-IDF 6.1. M5 has run it on hardware.
2. Bump xiaozhi-esp32 to 2.6.0. It is additive from 2.5.2 and its changes are in `websocket_protocol.cc` and its header.
   M5's own patch fails on 2.6.0 (3 rejected hunks in `esp_video.cc`), which is why there are two hops.

Use `release/v6.1` of ESP-IDF, not the tag.

Estimate (judgement): about 15 working days, range 11 to 20. IDF 6.1 and recipe 2, wake and audio rewrite 3,
application, audio and websocket 2, avatar socket 1.5, camera and codec 1.5, verify merges and re-tune RAM 5.

## First step: the spike (2 to 3 days)

Stock M5 main on a unit. Run a talking session and measure free internal heap, `int_big` and `psram_min`.
If the numbers are much worse than the old base, bring the result back before re-porting patches.

## Current series (2026-11-18)

`firmware/patches/ORDER` lists 293 patches, replayed by `scripts/fw-rebuild.sh` onto the pinned bases in `firmware/BASE` (StackChan 28b9f0c8, nested xiaozhi-esp32 49b4380, ESP-IDF 6.1.1). A replay of the whole list applies clean. Counts by family:

| Family | Patches | What it holds |
|---|---|---|
| Numbered and older families (V, P, NX, L, TN, RM, M, FI, GM, TB and others) | 221 | The re-ported feature set: voice, head, avatar, timers, games, music, private network, lock, privacy, face |
| UI | 17 | Screens, pages, banner, quick settings |
| UX | 17 | Playground track: palette, type ladder, accents, first-run screens, update cover, plain words |
| SF | 38 | Firmware track, safety and talk-over: time helper and lock limits (SF01, 08, 13, 16), hello and privacy (SF02), listening guard (SF03, 12), restart and servo lock (SF04, 08), mouth cues (SF10, 24, 30, 32), first-run wiring (SF09), servo clock and task (SF28, 31, 38), signed update header and build floor (SF25, 37), talk-over and echo canceller (SF15, 18, 22, 23, 26, 27, 29, 34), encrypted link (SF20, 21, 33, 35), limiter and bench (SF34, 39), Setup idle timeout (SF36) |

Optional switches (all default off; an off switch costs nothing, shown by `scripts/off-cost.sh` and `docs/dev/off-cost.md`):

- `CONFIG_MAIPAI_SERIAL_TOOLS`: bench tools over USB (`self.bench.*`). Never in a release.
- `CONFIG_MAIPAI_TALK_OVER`: reads the speaker loopback microphone (MIC3, slot 1) as the echo reference.
- `CONFIG_MAIPAI_TALK_OVER_AEC`: the echo canceller and a second wake hit that interrupts speech (needs the line above).
- `CONFIG_MAIPAI_LINK_PSK`: key exchange, key storage, TLS pre-shared key client and `self.link.pair`.
- `CONFIG_MAIPAI_FW_BUILD`: the build number compiled into the image (default 0, set by the release build; always on, costs a constant).
- `CONFIG_HEAP_TRACING_STANDALONE`: only the `heap` build kind (bench images).

Build kinds (`scripts/fw-build.sh TREE KIND`): plain (release), bench, gate, talkover, linkpsk, aec, heap. Memory budget of the series: `docs/dev/releases/b33-plain.md` and the gate numbers in `docs/dev/gate-numbers.md`.

The table below is the 2026-11-15 plan for the rebase and is kept as history.

## Patch map at the start of the rebase (replay of all 126 recipe patches on the newest tree; nothing compiled)

| Class | Count | Meaning |
|---|---|---|
| Obsolete | 2 | 044 (strongest-AP pin; upstream now sorts by signal), 009 (power-chip safe read; upstream adds it) |
| Conflict | 39 | 62 conflicting hunks, 9 in files deleted or moved upstream |
| Keep | 32 | our own features, small change expected |
| Clean | 53 | apply as is, 30 of them need a compile check |

- Conflict hunks by file: `application.cc` 12, avatar socket 11, `audio_service.cc` 10, `stackchan.cc` 7, `websocket_protocol.cc` 5.
- About 55 percent of patches that touch upstream sit in files that were rewritten.
- Rewrites, not rebases: 049, 059, 061, 065, 083, 086 (stop word, wake visibility, barge-in, echo reference, self-test). The wake files are replaced by a shared audio engine and 094 rides on 049.
- Orphans to delete: 045, 082-sound-direction, 082-sound-tap.
- Retire when their questions close: diagnostics-only patches 039, 046, 059, 064, 066, 070.
- Squash chains: head touch (047, 048, 052, 056, 076, 078, 080, 081), avatar credentials (011, 018, 019, 060, 063), offline behavior, music.

Ten riskiest: wake and audio rewrite; offline state machine 075; persistent socket 003; hard mute 106 (the mic must be proven off again);
the avatar cluster; RAM patches 051, 053, 055, 058; sound gates 142, 117, 141; private-network client 147, 149; update path 133, 145 (a mistake bricks the unit); `main.cpp` and CMake churn 097, 096, 007, 098.

## Re-port order, in layers

- A: avatar, skin, sound (low conflict). B: MCP tools and timers. C: power, ring, sensors. A to C can run in parallel.
- D: audio and wake (one lane, with review). E: `application.cc`, persistent socket, offline logic. D then E, serial.
- F: update path, security patch 155, portal, clock. F runs beside E after D.
- One unit session after each layer: flash, scripted turn, memory gate, latency gate.

## Toolchain changes to handle

- ESP-IDF 6: Picolibc is the default (keep Newlib). Compiler 14.2 to 15.1, warnings become errors. Scheduler and ring-buffer code moves to flash (restore IRAM placement options if needed).
- mbedTLS 4 with PSA: `psa_crypto_init()` first, some cipher suites removed. Flash grows about 37 KB (http client) and 41 KB (http server).
- A second `esp_wifi_init` now fails. Patches that start Wi-Fi twice must change.
- `wifi_provisioning` becomes `network_provisioning`. Legacy I2S, ADC and RMT drivers are removed.
- Config trap: upstream turns the hotspot Wi-Fi setup off by default. Bluetooth is off in our build, so `sdkconfig.defaults.local` must turn the hotspot option on or the unit has no Wi-Fi setup at all.
- `recipe.sh` pin logic to update: the IDF version check, the repo and lock hashes, the xiaozhi pin to `49b4380` (v2.5.2), the ESP-NOW commit, the Bluetooth-off check, the multinet config name, and the 6,225,920 byte assets limit (unchanged).

## Security fixes to cherry-pick or confirm arrive with the rebase

The rebase brings these. Confirm each is present after hop 2:

- WebSocket hello `transport` null dereference (`d4360977`).
- JSON parse without a length (`358819bf`).
- MCP error escaping and string limits (`aef2ab0c`, `acb2fc73`).
- Unsafe eFuse serial read (`f05adce2`).
- OTA URL validation (#2408).
- Ogg demux fix (`eeae329b`).
- M5: stop logging the Wi-Fi password over serial (`febcfdbc`) and reject `setWifi` with no ssid or password (`d2e95488`). Bluetooth is off, so low priority.

Patch 155 (remove or pin the four URL tools, add a signature check on updates) is ported onto the new base. See safety-and-privacy.md.

## Worth taking later

Streamed `notify` for idle spoken alerts. The shared wake engine. Glyph push and fonts for non-Latin text. Nothing here blocks v1.

## Toolchain status (2026-11-15)

ESP-IDF v6.1.1 is installed at `~/esp/esp-idf-6.1.1` for the esp32s3 target (install ran 84 s, ok). The rebase builds on `release/v6.1`, not the tag; switch before the spike.

## Rollback

Pin back to the previous release and the known-good tag above. Keep the last signed image and the unit's settings backup before the first reflash. Only one unit exists, so layers land one at a time.

## Open

- Whether xiaozhi 2.6.0 can host the command set natively.
- Whether upstream can take back some of our patches (watchdog, servo-wear limits, head-touch filters, SNTP and CA bundle options).
- Wi-Fi code that starts the radio twice, per patch.
