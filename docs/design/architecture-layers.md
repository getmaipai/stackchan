# Architecture layers: kernel, modules, assets, host (design, 2026-11-18)

Placement: unit (firmware track, owns everything here except Layer 4), host and dashboard (app track, owns the Layer 4 section), virtual unit (playground, enforces the rules in section A and the budgets in section B). Serves owner decisions 11, 13, 15, 17, 19 and 20 (`docs/design/decisions.md`). No code is written. Every number carries its source.

**Bottom line.** The installed-set idea holds for everything, with one hard limit: no code ever loads onto the unit. That gives four layers. The kernel (always on, works alone), modules (code compiled into the one image, switched on and off at run time, flash cost only while off), assets (signed data in installed-set slots, loaded on demand) and the host (everything heavy). One image fits: the plain image is 3,743,456 bytes in a 5,177,344 byte slot, and with every module on plus IR and NFC it is about 3.78 to 3.80 MB, which leaves about 344,000 to 364,000 bytes before the 20 percent rule (estimate). Flash is not the problem. Two things are: the largest free internal block (1.6 KB of margin with the link up) and PSRAM, which this note finds is tighter than the older notes say: the free PSRAM margin over the gate is about 1.17 MB, and a full picture-face pack plus its decode buffers alone is about 1.46 MB if the pack is copied into PSRAM. So v1 needs four things: a runtime switch and an admission check on every module, a PSRAM budget in the slot manager, the picture pack read in place from flash, and the streaming signed install. Profiles (decision 19, narrowed by 20) stay a described fallback, not v1.

Evidence tags: **[code path:line]** read in code (the replayed tree `/Users/jessetorres/esp/stackchan-rebuild/b47/firmware`, called "the tree"; paths are relative to it unless they start with `scripts/`, `docs/` or `schema/`, which are in this repo); **[doc path]** taken from a repo doc; **[est]** estimate with the method named; **[measure]** unknown until measured on the unit. Short names for docs in tables: MB = `docs/dev/memory-budget.md`, IS = `docs/plan/installed-set.md`, IT = `docs/dev/internal-ram-tasks.md`, IR = `docs/plan/ir-and-nfc.md`, CF = `docs/plan/camera-frames-path.md`, WW = `docs/plan/custom-wake-word.md`, OF = `docs/plan/offload-to-host.md`, SB = `schema/memory-budget.json`, FM = `docs/design/firmware-memory.md`, DE = `docs/dev/dance-entry-points.md`, WD = `docs/dev/watchdog-inventory.md`, UA = `docs/dev/unit-choices-audit.md`, FL = `docs/dev/feature-ledger.md`, OC = `docs/dev/off-cost.md`.

A problem to fix first: `docs/plan/installed-set.md` holds unresolved merge markers (lines 1, 313 and 357). The top half is the firmware design (push over the link, 128-byte release-signed asset header, `self.assets.install` with a header and signature). The bottom half is the host design (pull with `url`, manifest signed by a host key). The two disagree on the install tool's arguments, the signing key and the transport. Section F says which parts this note follows; the two tracks must finish the merge.

## A. The four layers and the rules between them

| Layer | What it is | Holds | Cost model |
|---|---|---|---|
| 1 Kernel | Code always on the unit; the robot is complete with it alone | Voice client, timers, alarms, clock, privacy (mute, vision off, full quiet), lock, always-on cues, update, link, display shell, body safety | Counted in the baseline; a new kernel item needs an owner decision |
| 2 Modules | Code compiled into the one image, switched on and off at run time | Talk-over, camera stream, IR, NFC, games logic, subtitles, overlays, picture faces, music dance, seek, private network | Flash only while off; allocate on enable, free on disable |
| 3 Assets | Signed data in installed-set slots, loaded on demand | Faces, picture faces, languages, fonts, sounds, game data, dances, phrases, character packs, wake-word model and phrase, icons | Flash while installed; PSRAM or none while loaded; internal RAM none |
| 4 Host | Everything heavy, on the person's computer | Pages, setup, speech, models, analysis, memory, personas, the dashboard | Zero on the unit |

No dynamic loading of code onto the unit. There is no safe way on this chip (the image runs from flash through the cache and the MMU, and an executable region loaded at run time would have to be signed, placed and trusted by a loader we would have to write), and a script VM costs RAM and attack surface. Any asset that looks like logic (a game pack) is a declarative data table with a validator, never an instruction stream (section H).

Rules between the layers:

1. **Calls go down, data goes up.** A module may call the kernel. The kernel never calls a module except through a registration table of hooks (a module registers a hook when it is enabled and removes it when it is disabled), so the kernel compiles and runs with an empty table. An asset is read through one function, `maipai_asset_get(kind)`, by the kernel or a module, and holds no code. The host reaches the unit only through the tool protocol and events.
2. **A kernel feature never depends on the host.** Every host call has a local fallback and a bound. The list that must work with no host is already fixed: timers and alarms with their backstop, privacy, the lock, the cues, the clock, the stop word and the short on-device commands, Wi-Fi setup, pairing, the movement limiter, and what the face needs to draw itself [doc OF, "Rule that bounds this list"]. Nothing local waits for the host [doc WD, host-away rules].
3. **A module that is off costs zero.** Zero means no task, no timer, no heap block, no registered tool and no stored state beyond one flag; flash is the only cost. Today this is proven for the compile switches (the plain image shows 0 symbols, 0 bytes and 0 strings for talk-over, the canceller, the encrypted link, the bench tools and heap trace [doc OC]). Section A gap 1 below is that the one-image plan needs the same proof for a module that is compiled in and switched off at run time.
4. **A missing or damaged asset falls back to a built-in default and never crashes.** Never a half-drawn language, never a blank face. Table in section C.
5. **No module and no asset can hide a cue.** The camera-on cue is drawn by the capture path itself, so a frame cannot be taken without it [doc CF]; the listening cues need at least one of sound, light or face on [doc UA]; the remote-control cue cannot be switched off. These live in the kernel and nothing in layers 2 and 3 can reach them.
6. **Memory admission before any large allocation.** A module or an asset asks one kernel function, `maipai_mem_admit(owner, internal_block, psram_bytes)` (proposed name), before it allocates. It refuses when the largest free internal block would fall under the stream floor (20,000 for the camera stream, 16,000 to stop it [doc MB]) or free PSRAM would fall under 6,000,000 [doc MB, gate]. A refusal shows plain words on the screen and leaves the module off. This turns the three rules the memory budget already states by hand (camera stream gate, camera and pack write exclusive, install refused under a floor) into one place.
7. **One module record per module.** Each has an id, a Kconfig switch (build), a stored run-time flag (NVS, in the preference store of patch TA01), a row in `schema/memory-budget.json` with `loaded_when` and `freed_when`, and, if it has a long task, a supervisor registration with a beat [doc WD, rule for a new long-running task].

Gaps against these rules, read in the code:

- **Gap 1, most modules are compile switches, not run-time switches.** `MAIPAI_TALK_OVER` (`main/Kconfig.projbuild:359`), `MAIPAI_TALK_OVER_AEC` (`:366`), `MAIPAI_LINK_PSK` (`:383`), `MAIPAI_PICTURE_FACES` (`:453`), `MAIPAI_FACE_DETECT` (`:471`) are build options. The plain image has talk-over and the encrypted link off (`sdkconfig.fplain:1043,1045`) and the private network on (`sdkconfig.fplain:1048`). The `full` kind turns on talk-over, the canceller, the link and the camera stream together [code `sdkconfig.full.defaults:1-6`; `scripts/fw-build.sh:16-26`]. To be one image, each module needs a run-time flag that the canceller's audio-front-end start, the link's key presence and the stream's start read. Modules that are already lazy: games, picture faces (nothing allocated until a pack is sent [code `main/Kconfig.projbuild:453-462`]), the private network (runs only after three failed connects and a key [code `:399-410`]), the LAN avatar (created on first use, SF47 [doc MB]), face detection (loads a model only while asked [code `:471-494`]).
- **Gap 2, the camera stream patch is not in the series.** SF44 is referenced by the `full` overlay (`CONFIG_MAIPAI_AVATAR_TO_HOST`) and by the memory notes, but `firmware/patches/ORDER` runs SF43 then UX11, UX12, SF46 and the tree's Kconfig has no such option [code: grep of `main/Kconfig.projbuild` found none]. The figures for it come from the b43 dev build [doc MB].
- **Gap 3, the 20 percent rule is checked on the image size alone.** `UpdateFitsSlot` refuses an image above 80 percent of its slot [code `xiaozhi-esp32/main/update_verify.h:40-43`]. It does not look at the memory budget, so a combination that fits in flash can still break the heap gate. The admission function in rule 6 closes that.

## B. Every feature in its layer

Rows are grouped by layer. Memory cells give bytes. "In image" means the item is inside the 3,743,456 byte plain image [code `build-plain/maipai-stackchan.bin`] and its own share is not split out [measure]. Internal RAM is the scarce number; PSRAM has a margin of about 1.17 MB over the gate (see the note after the tables). Baseline facts used by many rows: internal free median 64,093 to 69,075, lowest 33,484, largest free block 25,600 with the link up, always-on internal items 37,072 [doc MB; doc FL, Memory section]; static internal RAM of the plain image 170,771 [doc MB].

### Layer 1: kernel

| ID | Feature (ledger rows and patch families) | Flash | PSRAM | Internal RAM | Source | What must change to fit |
|---|---|---|---|---|---|---|
| K1 | **Voice client**: wake word (the shipped WakeNet model), audio in and out, echo-free wake (L01 to L09, 014, 016, 061, 068), websocket client and tool server, Opus | In image; model inside `srmodels.bin` 2,469,827 in the assets partition | Opus stack 24,576 (static, M02); tool descriptors (M03); AFE models (`AFE_MEMORY_ALLOC_MORE_PSRAM`) | audio_input 4,096, audio_output 4,096, ws_reconnect 4,096, one tcp_receive 4,096 per plain socket, stackchan 5,120; all inside the baseline | IT; MB; IS | None for memory. Keep every task registered with the supervisor (SF49). The voice socket's receive stack cannot move to PSRAM (it reads saved settings) |
| K2 | **Timers, alarms, clock, hourly chime, quiet hours, mood** (090 to 094, T02, M01 mood, U03, F04, F06) | In image | 0 | Static and small, under 1,000 for timers (verified); mood 8 bytes of NVS | MB audit table; Kconfig help | None. The time zone list stays only for a unit with no host; the host sets the zone otherwise [doc UA] |
| K3 | **Privacy**: mute, vision off, full quiet, microphone guards (106, 107, L07, Y02, `self.privacy.set`) | In image | 0 | In baseline; no separate row in SB | UA | Add a declared row so the virtual unit can show it is flat. No change otherwise |
| K4 | **Lock**: passcode, lockout that survives restart (LK01 to LK03, SF13, SF16, SF38) | In image | 0 | Keypad screen about 2,500 only while shown (placeholder); state in NVS | SB `screen.keypad` | Measure the keypad; free its objects on unlock (already the rule) |
| K5 | **Always-on cues**: camera-on cue (T05), listening cues (TB01, TA light, sound, face), visible remote control (TB05, TC04), find-my-robot and game cues (Y02 to Y04), mouth cues (SF10, SF24, SF30, SF32) | In image | Mouth cues in PSRAM (SF24) | No task; drawn by the paths that need them | CF; WD | None. Their code must stay out of the module table so no switch can reach it |
| K6 | **Update**: signed update with build floor and board id, first-boot trial and rollback (155 to 160, SF25, SF37, SF40, SF41, FM01, UX04, UX09) | In image | 0 | `fwupdate` task 10,240 while an update runs (transient) | IS (B6, from `maipai_update.cc:30,149`) | It is the largest transient internal block. Make it exclusive with installs, the camera stream and the private network through the admission function |
| K7 | **Link**: pairing, Wi-Fi (saved networks 023, roaming RM01 to RM05, setup hotspot RM06 and RM07), encrypted link (SF20, SF21, SF22, SF33, SF35), reconnect and supervisor (SF49, 077, R02, R04) | Link code +7,524 (measured over the bench kind); supervisor about 6,000 | Link per TLS session about 26,000 to 30,000 [est] | Link static +304; net 0 per socket (the TLS receive stack replaces the plain one, 4,096) [est]; supervisor one esp_timer, no task | MB | Decision 13 makes the encrypted link the default, but the plain image has it off (`sdkconfig.fplain:1045`). Turn it on in the one image after the handshake stack margin is measured; offer one cipher suite |
| K8 | **Display shell**: face and styles (F01, X01, X02, H02, V10 to V12, V21 to V26, UX01 to UX03), banner row, boot cover, control sheet, swipe pages (P10 to P13, NX01 to NX04), Wi-Fi setup page (P01 to P05), setup app, first-run flow (UX05, UX08, UX11, UX12), screen words and Latin-1 fonts (UX07) | In image; fonts Noto basic 16 and 20 px about 67,000 and 102,000 | Picture frame in M9 | Face objects permanent (largest permanent screen cost, not itemized); first run 3,700 measured while open; sheet 3,000, settings 4,000, banner 800, boot cover 2,000 (placeholders) | MB audit; SB; IS (A) | Free first-run page objects as soon as the next page shows (ranked change 4 in MB). Move settings pages that duplicate the host page to the host and keep only Wi-Fi, address, pairing digits and the physical controls [doc OF, candidate 2] |
| K9 | **Body**: servo task and movement limiter (SF28, SF31, SF38, SF39, ML01), IMU, touch, pickup, pet, shake, tap (047, 048, 056, 080, TB04, C04, I01), battery ladder (T01, C01), light ring (A01), dances as keyframes (020, MD02) | In image; the ladder and limiter grew the image by about 13,000 | 0 | Servo task 3,072 always (measured); limiter about 80; a dance modifier about 450 while it runs | FM (dance section); MB | None. `servo_step` stays internal (not provably flash-free) [doc IT] |
| K10 | **Offline behavior**: offline strip and tone, "can't reach Home" line after ten minutes (075, 143, T04, SF49), idle command (034) | In image | 0 | 0 | WD | None |
| K11 | **Sound core**: 26 built-in Ogg clips played from flash in place, sound policy and notify tools (115, 116, 117, TB01) | 107,188 for the clips | PCM block transient | Decoded block transient | IS (A) | None. Extra clips are assets (A5) |
| K12 | **Stop word and short on-device commands**: stop, mute, quiet, don't move (049, 094, L09, decision 15) | In image | 0 | 0 | decisions | None |
| K13 | **Reset, heal and crash record**: reset on device (R01), restart guard (R02, R04, SF04, SF08), core dump (FM02, FM05, Z01, SF11) | In image; core dump partition 65,536 | 0 | `heal_restart` 4,096 and `mp_reset` 4,096, transient | IT; `partitions.csv:9` | None |
| K14 | **Preference store, tool protocol, hello gate, token gate, version screen, memory line** (TA01, 021, 018, SF02, TC01, U05, M01 memory-line, TN05, 156, 157) | In image | Tool table in PSRAM (M03) | Small | MB | None. The new run-time flags in rule 7 live in the preference store |
| K15 | **Built-in language and fonts**: six first-run tables (en, es, fr, de, pt, it), English words, Latin-1 fonts | In image; the 19 Latin-2 letters (Polish, Czech, Turkish) add about 4,000 [est] | 0 | 0 | IS (D1, D6) | Bake the Latin-2 letters into the kernel fonts (cheaper than a pack). Every screen string gets a stable id so a language asset can replace the table |

### Layer 2: modules

| ID | Feature (ledger rows and patch families) | Flash | PSRAM | Internal RAM | Source | What must change to fit |
|---|---|---|---|---|---|---|
| M1 | **Talk-over**: echo canceller and barge-in (SF15, SF18, SF22, SF29, SF34, SF42; ledger "Voice") | +620 (code over the bench kind) | Filter and history: unmeasured [measure] | Static +1,008; runtime about 1,000 [est] | MB | Needs a run-time flag read at audio-path start (a restart of the audio path, not a reboot). The microphone slot choice (MIC3 against MIC2) is a build switch today; SF22 adds a slot setting [code: patch name `SF22-talk-over-slot-setting`], so read whether it already covers the switch |
| M2 | **Camera stream to host** (SF44; "Showing live view", "Face follow", the frame path) | +4,915 | JPEG output 10,000 to 30,000 per frame; the frame buffers are in the baseline (M06) | 4,096 while streaming (the second socket's receive stack, persistent while it runs) [est] | MB; CF | Allocate the socket and buffers only while streaming. Start only if the largest block is at least 20,000, stop under 16,000. Exclusive with a pack write and an update. Put the patch into the series (gap 2) |
| M3 | **LAN avatar for the phone app** (`avatar_lan`, `avatar_rx`; SF47) | In image | 0 | 8,192 plus 4,096 while up (created on first use) | IT; MB | Done in SF47; waits for the plain boot proof and the post-SF47 heap map |
| M4 | **Turn toward faces by motion** (S10 to S14, NX05, NX06, FI02, FI07; "Face follow" local half) | In image | 40 by 30 gray frames (1,200); task stack in PSRAM | About 0 | WD; MB | None for memory. It is the no-host fallback for turning toward a person, so it stays a module that defaults on (NX06) |
| M5 | **Face detection on the unit** (FD01 to FD04; experiment image only) | Models in the app image: about 191,000 (two-stage) or 480,000 (one-stage) [code `main/Kconfig.projbuild:471-494`] | Weights and activations, freed 10 s after last use [code same] | Guarded by two Kconfig minimum-free thresholds (`:516`, `:520`) | Kconfig help | Keep out of the release image. The host detects faces from the camera frames (OF candidate 5). If it is ever kept, the model becomes an asset kind in the assets partition: the 480,000 model does not fit the remaining flash beside everything else |
| M6 | **Infrared learn and send** (planned; bench probe SF50) | 6,000 to 10,000 [est] | 8,000 to 16,000 while learning or sending [est] | Under 200 on; 2,000 to 4,000 while active (one 3,072 stack) [est] | IR | Build only after the input-only probe sees a real remote. Create the RMT channels on first call and delete after 10 s idle (already the plan) |
| M7 | **NFC tag reader** (planned; bench probe SF50) | 3,000 on; 14,000 to 22,000 with watch on [est] | 2,000 [est] | Under 200 on; 3,000 to 4,000 with watch on [est] | IR | Same as M6. Reader task exists only while watch is on; poll, no interrupt (pin unknown) |
| M8 | **Games logic**: engine, seven games, talk games (G01 to G03, UI12 to UI15, GM01 to GM06; "Games" rows) | Engine in image; seven packs 17,828 | The running pack copy (cap 16,384) | A running game about 4,000 (placeholder); `pack_boot` and `pack_write` 6,144 each, transient (12,288) | IS (A); SB | Replace the two pack tasks with the streaming install (section F); then a game start never opens a 6,144 hole. Confirm whether the pack carries opcodes (section H) |
| M9 | **Picture faces and picture frame** (H03, H04, FI07, TB02; "Picture faces" rows) | Code in image; the pack sits in the asset pool (A3) | Pack as held up to 1,000,000, up to three decode buffers of 153,600 (460,800), 20,480 stack | 0 persistent | IS (A); `main/Kconfig.projbuild:453-462` | **Read the pack in place from flash and decode from there**, instead of keeping it in PSRAM. Saves up to 1,000,000 of PSRAM (see the PSRAM note). Verify how the pack is held after boot first [measure] |
| M10 | **Overlays, effects and decorators**: 18 overlays, 10 presets, CRT, glow, color modes, night dim, notes (TA02 to TA04, O01 to O03, U01, MD03; the "Overlays" rows) | In image (code) | Three layers 2,760 | 1,500 per active layer, notes 1,200 (placeholders) | IS (A); SB | Measure the placeholders. The governor already hides layers under load (O03). Presets as data can follow as an asset (256 bytes each [est]) |
| M11 | **Subtitles and captions** (F02, N01, N02, FI05; default off) | In image | Glyph payload while a caption shows [measure] | Label about 1,500 (placeholder; may stay allocated) | MB; SB | Free the label when the caption ends (ranked change 6). Let the host send pre-broken `lines` (OF candidate 4) |
| M12 | **Music dance and beat features** (V03, V04, MD01 to MD03, SF14, SF51, MF01) | About 9,000 for SF51 | 0 | State under 120 and one one-second timer (no task idle); beat features run from the unit's own microphone about once a second | DE; OF candidate 10 | The MF01 patch name sets a 6,144 byte stack for the music task [code: patch name `MF01-music-feature-task-stack-6144`]; read whether it is internal and whether it can be created only while music is heard |
| M13 | **Face extras**: word reactions, time-of-day looks, face clock, decor (F03, F04, U01, U02; ledger "Face extras and word reactions") | In image | 0 | Small [measure] | Kconfig; UA | Runtime flags only. The audit already makes time-of-day and night dim automatic |
| M14 | **Private network (travel)** (TN01 to TN07, RM03 to RM05) | Compiled in the plain image (`sdkconfig.fplain:1048`); size [measure] | Inside the client [measure] | `tailnet` task 5,120 and about 20,000 in all while it runs [code `main/Kconfig.projbuild:399-410`] | Kconfig help | The biggest internal user of any module. Already starts only after three failed connects and a key, and refuses to start under the floor. Put it behind the admission function and make it exclusive with the camera stream and updates |
| M15 | **Custom wake word detector** (stock `CustomWakeWord`, MultiNet; planned) | Already in the base; the model is an asset (A9) | Model working memory [measure] | Per-frame buffer, a few KB [est, WW] | WW | One detector at a time (switching restarts the audio path). Not before the signed asset path exists |

Not in any layer (maker image only): bench and serial tools, face bench counters, heap trace, latency trace, power and IR and NFC probes (V01, H01, V20, V24, L06, SF23, SF26, SF27, SF34, SF42, SF48, SF50, FI03). They are separate build kinds and never in a release; the bench kind adds 14,980 bytes of static internal RAM and about 52,000 bytes of flash over plain [doc MB; doc OC reports 52 symbols and 571,628 bytes when on]. Cut or removed: the stock network test (U04, calls vendor services [doc UA]), Bluetooth (098, decision 19 of 2026-11-15), the stock apps (097), the CJK font and emoji in the app image (096), the baby monitor (scrapped, decision 10 of 2026-11-18), sound direction (decision 20 of 2026-11-15).

### Layer 3: assets

All assets are data only. Slot counts and caps are the firmware design's proposal [doc IS, section C]; the host half proposes different counts (faces 3, dances 3, games 4) and the two must be merged into one table, `schema/asset-kinds.json` [doc IS, B1]. Flash lives in one shared pool of 382 sectors of 4,096 bytes, 1,564,672 bytes [code `main/hal/maipai_packcache_core.h:25-31`]. Loaded cost is PSRAM or none; internal RAM is none persistent for every kind.

| ID | Kind (ledger rows) | Slots, cap per item | Flash (pool) | PSRAM while loaded | Internal | Source | What must change to fit |
|---|---|---|---|---|---|---|---|
| A1 | **Face styles** beyond the five baked (big eyes, eyes only, stock, classic, minimal) | 8 slots, 256 bytes | About 40 bytes plus name [est] | 0 | 0 | IS (A) | Add the consumer (a style row from a slot, ids 16 and up). The audit proposes keeping three baked styles [doc UA, owner question 1] |
| A2 | **Languages**: strings (the language rows, "Language packs", "Six languages") | 2 slots, 16,384 | About 6,000 per language [est] | About 6,000, two ping-pong slots today at 181 bytes | 0 | IS (D2) | One string catalog with stable ids (`schema/strings.json`); a missing id falls back to English. Today a pack carries only 181 bytes of weekdays, months and chip words |
| A3 | **Picture faces and character packs** (one kind, `look`) | 2 slots, 1,000,000 total | Up to 1,000,000 | **None if read in place** (see M9); else up to 1,000,000 plus 460,800 decode | 0 | IS (A, C) | Read in place; trust rule for owner-made pictures (section H) |
| A4 | **Fonts** (CJK and later scripts; "Language packs") | 1 slot, 800,000 | CJK 20 px: 480,000 to 735,000 [est]; one font only | 0 (mapped in place, whole 64 KB MMU pages [est]) | Under 500 for the font object, freed on release [est] | IS (D3) | Needs the in-place loader and a validator that checks every offset before the first draw. A swap drops the old font first, so a power cut leaves the built-in Latin set |
| A5 | **Sounds**: thinking sounds (`filler`), sound packs | filler 1 at 400,000 (80,000 per clip); sound 2 at 400,000 | Up to the cap | The unzipped pack, up to 400,000, held | Decoded block transient | IS (A) | Admit only if the PSRAM budget allows; filler and sound share one arena |
| A6 | **Game data** (`game`) and **dances** (`dance`, 100,000 cap) | games 8 at 16,384; dances 3 at 100,000 (host proposal) | Games 1,000 to 4,000 each [measured]; seven embedded, 17,828 | The running pack, cap 16,384 | Running screen (M8) | IS (A, C); `maipai_games_core.h:32` | Built-in seven stay in the image as the defaults. Dance rows are compiled in today (`maipai_dances_core.h`); the loader has the type but no consumer |
| A7 | **Offline phrases** (`phrase`, V02, K12; "Offline phrases") | 1 slot, 150,000 (16 clips) | Up to 150,000 | Up to 150,000 held | Decoded block transient | IS (A) | The plain image embeds the clips (`CONFIG_MAIPAI_OFFLINE_PHRASES_EMBED=y`, `sdkconfig.fplain:1028`), so they count against the 3,743,456 bytes. Move the embedded copy out only if flash is ever short |
| A8 | **Overlay presets and style data** | Later; 256 bytes each [est] | Small | Small | 0 | IS (E1) | Not v1 |
| A9 | **Wake-word model and phrase** (WakeNet model, MultiNet commands from `index.json`) | 1 model, phrase is data | Inside the 2.47 MB models file; MultiNet 2.1 MB: whether it is inside or added to the 2,469,827 bytes is [measure] | Model buffers [measure] | [measure] | WW; IS (A) | Needs the signed asset header first; until then the phrase file must not be installed from the network (USB only) |
| A10 | **Icons and pictures** | Fixed, 17 files about 0.70 MB read in place in the stock assets image | 0.70 MB | 0 | 0 | IS (A) | Not slotted. Reclaiming the 1.29 MB stock font and the 0.59 MB of large icons is possible only after measuring that the pool is too small, and needs a USB reflash on units already out [doc IS, open question 2] |
| A11 | **Personas** | 0 on the unit | 0 | 0 | 0 | IS (A) | Host only. A persona that names a wake phrase, voice or face is those other kinds |

### Layer 4: host (row list; the unit pays nothing)

| ID | Feature | Unit cost | Notes |
|---|---|---|---|
| H1 | Settings page, first-run brain choice, pages, wall tile editing, parent view, setup and the three brain choices | 0 | The unit keeps Wi-Fi setup, the address, the pairing digits and the physical controls [doc OF] |
| H2 | Speech to text, text to speech, the language model, persona, speech speed and pitch, cloned voices, "Persona, speech speed and pitch" | 0 | Own-model brain or Home |
| H3 | Face recognition, name list, last seen, watch and alerts, find my robot map, live view, photos ("Camera, remote, monitor" rows) | 0 | Needs M2 for frames; the unit keeps the cue and the privacy gates (K3, K5) |
| H4 | Memories, content rules, companions, calendars, briefings, scenes, display lists, per-person settings, per-person wake phrase | 0 | Home owns household policy (decision 1 of 2026-11-18) |
| H5 | Installed-set library, signer, reconciler, the "On my robot" page | 0 | Section F and the Layer 4 section |
| H6 | Music identification, dance director and the ladder show, word reactions table, mouth cues | 0 | Beat features stay on the unit (OF candidate 10) |
| H7 | Local API, event stream, home-automation bridge, MQTT, metrics, the coding companion, Home Assistant, memory notes, wake-word maker packages | 0 | Optional packages, off by default |
| H8 | Face detection and seeking when frames reach the host (OF candidate 5) | 0 | Replaces M5; M4 stays as the no-host fallback |
| H9 | Service, supervision, several-robot handling, health page, update delivery and signing | 0 | Decision 16; the release signing key stays off the serving host |
| H10 | Playground (simulation and live backends), release tooling, ledger, bench scripts ("Virtual playground", "Scripts and tools", "Host modules", "Tool protocol" maker rows) | 0 | Not shipped on the unit |

### Coverage: every ledger section and every patch family

| Ledger section (rows) | Rows in this note |
|---|---|
| Battery and power (1) | K9 |
| Camera, remote, monitor (45) | K3, K5 (cues, remote token gate), M2, M4, H3, H7; alerts and map rows are H3 |
| Faces and moods (52) | K8 (moods, styles, colors), A1, A3 and M9 (picture faces), M10, M11, M13, H4 |
| Games (20) | M8, A6, H7 (outside and stack rows) |
| Languages (11) | K15, A2, A4, H1 (setup ways) |
| Lights and sounds (25) | K5 (light and tone cues), K11, A5 |
| Link and travel (12) | K7, M14, H1, H9 |
| Motion and dances (31) | K9, M12 |
| Music and dance (3) | M12, H6 |
| Optional packages (1) | H7 |
| Overlays (36) | M10 |
| Parent view (5) | H1, K4 |
| Safety and privacy (9) | K3, K4, K5 |
| Screens and pages (17) | K8 |
| Settings page (12) | H1, H9, M6 and M7 (infrared and NFC rows) |
| Time (6) | K2 |
| Updates and setup (7) | K6, H1 |
| Voice (22) | K1, K12, M1, M15, A7, A9, H2, H9 |
| Wanted, not started (17) | K9 (pickup), K2 (focus countdown), K7 (encrypted link at home, roaming), K12 and A7 (offline commands), M6, M7, M4 (wake look-around), M8 and H7 (outside games), A2 (reviewed translations), A9 and H4 (wake phrases), H4 (scenes), H1 (phone as host), M5 and H8 (face detection) |
| With MaiPai Home (3) | H7 |
| Maker: firmware patch series (41 groups), build and gate | the patch families below |
| Maker: host modules (288), scripts (67), tool protocol (34), packages (8), playground (24), brain and tools (3), link and security (3), updates and release (5), docs (2) | H1 to H10; the schema files are the one definition of the tool protocol |

| Patch family (from `firmware/patches/ORDER`) | Rows |
|---|---|
| Numbered base patches (001 to 160), B01, S01, S02 | K1, K2, K3, K6, K7, K10, K12, K14; 096, 097, 098 are cuts |
| A01, A02 | K9, and the partition in section E |
| C, I, T01, T03, T04, Y | K9, K8, K7, K5 |
| F, N, UX, UI, QS, NX (except NX05, NX06, UI12 to UI15) | K8, M11, M13 |
| P, RM06, RM07 | K8 |
| R, FM, Z, TC | K13, K5, K14 |
| M01 to M06, TN05 | K14, K1, M2 |
| V01, H01, V20, V24, L06, SF23, SF26, SF27, SF48, SF50, FI03 | maker image |
| V02, K10 to K13, TB02, TB03, FM04, U06 | A2, A3, A5, A7 and the loader (section F) |
| V03, V04, MD, MF, SF14, SF51 | M12 |
| TN, RM01 to RM05 | M14, K7 |
| U01, U02, TA02 to TA04, O | M10, M13, M11 |
| G, GM, UI12 to UI15 | M8, A6 |
| H02, H03, H04, FI07, V10 to V12, V21 to V26, X | K8, M9 |
| S10 to S14, NX05, NX06, FI02 | M4 |
| FD | M5 |
| L, W, TB01, TB04, TB05, SF (SF01 to SF14, SF16, SF17, SF19, SF30, SF32, SF36, SF38, SF39, SF43, SF46) | K1, K3, K4, K5, K8, K9 |
| SF15, SF18, SF22, SF29, SF34, SF42 | M1 |
| SF20, SF21, SF33, SF35, SF49 | K7 |
| SF25, SF37, SF40, SF41 | K6 |
| SF28, SF31, ML | K9 |
| SF47 | M3 |
| LK, SF13, SF16 | K4 |
| TA01 | K14 |

### Notes on the tables

- **Flash.** Plain image 3,743,456 bytes, 72.3 percent of the 5,177,344 byte slot; the 20 percent rule allows 4,141,875 [code `build-plain/maipai-stackchan.bin`; `update_verify.h:40-43`]. All optional modules compiled in (talk-over, the link, the camera stream) add 14,560 bytes in the b43 builds (3,731,312 plain, 3,745,872 `full`) [doc MB]. IR and NFC add 20,000 to 40,000 [est, IR]. So the all-in image is about 3,743,456 + 14,560 + 40,000 = 3,798,016 at most, which leaves 343,859 [est]; with the smaller IR and NFC figure, about 363,859. The one-stage face model (480,000) does not fit; the two-stage model (191,000) would take more than half the room.
- **Internal RAM.** The combined worst cases are the ones already in the memory budget: link plus camera stream, 4,096 plus JPEG work buffers; everything at once, 11,000 to 14,000 [est, MB]. The new module costs in this note (IR, NFC, the private network at about 20,000) are not in that sum. The private network and the camera stream must be exclusive, or the sum fails the largest-block floor.
- **PSRAM (new finding).** The lowest free PSRAM seen on the gate image was 7,170,496, against a floor of 6,000,000, so the margin for every PSRAM user is 1,170,496 [doc FM, dance section; doc MB gate]. A picture-face pack held in PSRAM (up to 1,000,000), its three decode buffers (460,800) and its 20,480 byte stack total 1,481,280 alone, which is more than the margin. Adding two TLS sessions (about 60,000) and a JPEG output (30,000) gives 1,571,280, over the margin by about 400,000 [est; whether those windows had a pack loaded is not stated]. The fixes, in order: read the pack in place (M9), give the slot manager a PSRAM budget for loaded assets (proposal: about 900,000, which is the margin minus the module PSRAM and a 10 percent reserve, to be fixed after measuring), and admit every load through rule 6.

## Layer 4: host (the app track writes this section)

The app track writes the host half: the offload-to-host design and the installed-set host protocol, merged. Only what the unit needs from the host is listed here, with the names that already appear in the repo docs.

- **Asset delivery and choice:** the `self.assets.list`, `install`, `data`, `commit`, `remove`, `swap` and `abort` tools (firmware design) or `list`, `install {kind, id, url, name}`, `remove`, `swap` (host design) [doc IS]; the signed manifest and ranged fetch endpoint `/assets/<unit>/<sha256>/manifest|data` [doc OF]; the unit's events `assets_state` (in the hello), `asset_wanted`, `asset_progress`, `asset_done`, `asset_failed` [doc IS]. The two designs must agree on one install tool, one signing key path and one transport before code (section A, the merge problem).
- **Choice and defaults:** the dashboard chooses the set, fills the defaults on first run, and swaps with one action; the unit reports its slots and free bytes in `list`.
- **Time and place:** `self.clock.set`, `self.clock.set_zone`; the host sets the zone.
- **Privacy and state:** `self.privacy.set`, `self.pages.set`, `self.prefs.set`; the unit refuses what the lock or the cues forbid.
- **Update and health:** `self.firmware.update` with the signed header; `self.version.get` (reports `fw_build`, `reset_reason`, the `watchdog` list); `self.bench.heap_info` for bench.
- **Camera and sensors:** the avatar socket frames and the start and stop frame types, `self.avatar.status` [doc CF]; `self.robot.ir_learn`, `self.robot.ir_send`, `self.robot.nfc_watch` and the `nfc.tag` event [doc IR]; the `look` claim for who steers the head.
- **Words:** the `lines` field on `tts sentence_start` for pre-broken captions [doc OF, candidate 4]; the language catalog `schema/strings.json` [doc IS, D1].
- **Profiles (not v1):** the unit reports its profile in the hello; the host refuses a combination the profile does not hold (decision 19).

## C. Failure behavior without a host

Rule: the unit never crashes and never shows half of anything when an asset or the host is missing. The kernel does not wait for the host; the face, timers, privacy, lock, cues and the stop word keep working [doc WD, doc OF].

| Missing, damaged or unsupported | What the person sees |
|---|---|
| Language table | English words. The six first-run tables stay built in. A language that needs a font the unit lacks falls back to English as a whole, never with missing glyphs [doc IS, B6] |
| Font for a chosen language | Same as above, plus a one-line banner "This language needs a font. Connect to your computer to install it." (proposed text) |
| Face style | Big eyes (the table lookup already defaults [doc IS, A]) |
| Picture face or character pack | The built-in drawn face (`TPC_ST_DAMAGED` means built-in [code `maipai_packcache_core.h:69`]) |
| Sound pack or thinking sounds | The built-in tones and clips |
| Game or game data | Only the seven built-in games are listed |
| Offline phrases | The existing offline strip and tone; no phrase plays |
| Wake-word model or phrase | The shipped "Hi, StackChan" model |
| Directory unreadable or checksum wrong | Empty set, built-ins only, `dir_corrupt` reported in the list [code `maipai_packcache_core.h:75-76`] |
| Asset format outside the firmware's range | Treated as damaged: `state:"unsupported"`, built-in used, the host reinstalls a compatible one when it returns |
| A module refuses to start (memory floor) | It stays off; the screen says in plain words what was refused and why ("The camera is paused while a game loads" is the model line [doc MB]); a counter records the reason |
| Host away more than ten minutes | "Can't reach Home. Check it is on and on the same Wi-Fi. I keep trying." and every 30 minutes after [doc WD] |

Each fallback is checked by the virtual unit: a scenario removes the asset, restarts, and requires the same screen as the built-in set and no error banner (decision 15g).

## D. First-use fetch delay

- **Prefetch the chosen set.** The host reconciles when a unit connects, when a choice is saved, and every 30 seconds for a unit that is not fully installed [doc IS, host half]. So a chosen item is normally on the unit before the person ever needs it.
- **When it is not there yet,** the unit shows the built-in default at once and draws progress. It never blocks the screen task or a voice turn on a fetch. `asset_progress` goes out every 10 percent; the screen shows the banner row for small items (released 2 s after use) and the update cover for large ones [doc IS, B6; doc MB audit].
- **A person picks a language that is not on the unit** (the first-run list): the unit keeps English, marks the choice pending, and sends `asset_wanted`; the host pushes it if paired [doc IS, B6].
- **The delay.** The transfer pushes 2,048 byte pieces in base64 (a third larger), so a 0.5 MB font is about 250 pieces [doc IS, B6]. Rate over the link is [measure]; the dashboard shows an estimate from bytes, a measured rate, and the 4/3 overhead. Show nothing until one second has passed, so a fast install shows no flicker.
- **A fetch is refused,** with a plain reason, while a game runs, another install runs, the unit is speaking, or the largest free internal block is under the floor (the number for this path is [measure]; 20,000 is the working figure [doc IS, B3]).

## E. Flash wear

Partition layout [code `partitions.csv:3-9`]:

| Partition | Offset | Size (bytes) | Use |
|---|---|---|---|
| nvs | 0x9000 | 16,384 | Settings, keys, counters; shared with Wi-Fi |
| otadata | 0xd000 | 8,192 | Which slot boots |
| phy_init | 0xf000 | 4,096 | Radio calibration |
| ota_0 | 0x20000 | 5,177,344 | App slot |
| ota_1 | 0x510000 | 5,177,344 | App slot (offset follows from ota_0 plus its size) |
| assets | 0xA00000 | 6,225,920 | Stock models, fonts, icons, then the asset pool at the tail |
| coredump | 0xFF0000 | 65,536 | Crash record |

Flash is 16 MB, so the table ends exactly at the top (0xFF0000 plus 0x10000 is 0x1000000) [code `partitions.csv:9`]. Nothing is free. A partition change does not reach units already out (an update does not rewrite the table), so **no partition change in v1**.

Inside `assets` [code `maipai_packcache_core.h:25-31`; doc IS, C]:

| Region | Bytes |
|---|---:|
| Stock assets image (fonts, models, icons) | 4,463,226 |
| Margin | 189,830 |
| Cache region at 0x470000 inside the partition: directory 2 sectors now | 8,192 |
| Cache region: data, 382 sectors | 1,564,672 |

Wear budget:

1. **Typical endurance** of this class of flash is about 100,000 erase cycles per sector [est; the part's datasheet is not in the repo, check it].
2. **Rotating allocation.** Today the allocator starts at sector 0 each time, so a heavy user wears the first sectors only [doc IS, C; code `maipai_packcache_core.h:235-258` as cited there]. Start each search after the end of the last written run and wrap. A 0.5 MB install erases 128 sectors; two a day for ten years is about 2,450 erases per sector across the 382, twenty a day about 24,500 [est: arithmetic from IS].
3. **Directory ring.** Every install writes the directory once, alternating between sectors. Two sectors at 50 installs a day for ten years is about 91,000 writes per sector, near the rating; a ring of 8 (32,768 bytes, from the 189,830 margin) brings it to about 22,800 [est]. Use the ring.
4. **Rate caps in the unit:** at most 8 installs an hour and 50 a day; the host honors the same caps [est, proposal].
5. **Writes that cost nothing:** a resend of an identical item writes nothing; `swap` writes one directory sector; `remove` writes one directory sector and no erase [doc IS].
6. **Other writers** do not touch the pool: NVS has its own wear leveling and the mood value is written at most every 15 minutes [code `main/Kconfig.projbuild:390-397`]; the core dump partition is written only on a crash.
7. **Flash writes stall the cache.** An erase runs while the screen and audio tasks read from flash. The stall on the face refresh and the audio path during a sector erase is [measure]; until measured, refuse an install while the unit is speaking.

## F. Atomic install and versioning

Follow the firmware design's install flow [doc IS, B3], which is a streaming write into free sectors plus one directory flip. Reasons to prefer it over the host design's pull: the push path already exists, resumes by offset and needs no new task or socket, while copying the signed update's fetch would add a transient 10,240 byte internal task [doc IS, B6].

Atomic steps:

1. `begin`: the host sends the signed header (below). The unit verifies the signature, the magic, the board id, the kind, the minimum firmware build and that the version is not lower than an installed item of the same name. It refuses an oversize item (per-item cap, free pool bytes, declared PSRAM above the budget) before it erases anything.
2. Choose a run of free sectors that overlaps nothing the directory lists, and never the run of the item being replaced.
3. Stream pieces in order; the offset must equal what the unit has. Each 4,096 byte sector is erased, written and fed to SHA-256. No whole-pack copy in PSRAM, no 6,144 byte write task. The write runs on the tool task, whose stack margin during a flash write is [measure].
4. `commit`: check length and SHA-256 against the header, read the run back and hash it, and only then write the new directory sector with a higher sequence number.
5. A power cut before step 4 leaves the old directory the newest valid one. The old item is intact and the half-written run is unlisted free space. The existing cache test proves this by cutting power at every step; the multi-slot directory extends the same test [doc IS, B3; test `host/tests/firmware/packcache_core_test.c`].
6. When the pool is too tight for two copies (a font), drop-then-write applies and a power cut leaves the built-in set [doc IS, C].

Versioning and compatibility:

- **Signed asset header, 128 bytes** [doc IS, B4]: magic `MPAH1`, asset version, body length, SHA-256 of the body, board id, kind, body format version, flags, minimum firmware build, name, code, PSRAM when loaded, flash used. Its first 56 bytes keep the update header's field positions so one parser and one SHA path serve both. The update header itself is 56 bytes: magic `MPUH1`, build number (only goes up), image length, SHA-256, board id [doc `docs/plan/signed-update-header.md`]; the unit refuses a build not above the highest it has confirmed, kept in flash, and the image carries its own number (`CONFIG_MAIPAI_FW_BUILD`) so a USB flash still refuses an older signed release [doc `docs/plan/signed-update-anti-rollback.md`].
- **Compatible-range check (proposed addition).** The doc compares only a minimum firmware build. Make it a range: the firmware carries, per kind, the body format versions it reads (a minimum and a maximum, generated from `schema/asset-kinds.json`), and the asset carries its format version and its minimum firmware build. Accept when the format is inside the range and the minimum build is at most the running build floor. After a firmware update that drops an old format, or a rollback (the first-boot trial restores the old image [patch 160, FM01]) to a firmware that does not know a new one, held items outside the range become `unsupported` with one directory write; the built-in default shows; the host reinstalls a compatible item. Nothing is erased and nothing crashes.
- **Catalog version for languages** [doc IS, D2] must not need equality with the firmware's; use the same range rule so a language pack survives a firmware update that only adds strings.
- **Asset rollback.** An asset of the same name must not have a lower version than the installed one. A reinstall of the same version is allowed (it writes nothing if identical).
- **Board id.** An asset for another board is refused, as an image is [doc `docs/plan/signed-update-header.md`, board id].

The two designs in `installed-set.md` differ in who signs (release key against host key) and who pulls; section H sets the trust classes this note recommends.

## G. Fragmentation

- **A fixed PSRAM arena per kind**, created the first time a kind loads, sized from the slot table (`psram_arena` per kind in `schema/asset-kinds.json`), and kept while the kind is active. No allocate and free cycle per item; a swap parses into the idle half and flips one pointer, the way the language loader already does with two slots [doc IS, A, reuse item 3]. A kind that cannot afford two halves (a picture pack) drops the old item first.
- **No small internal allocations from an asset.** Allocations under 256 bytes are always internal (`CONFIG_SPIRAM_MALLOC_ALWAYSINTERNAL=256` [code `sdkconfig.fplain:2778`]); 64 KB of internal RAM is reserved for internal-only callers (`:2781`). A font object, its descriptor and its character map are under 500 bytes in all [est, IS D3]. Allocate them once into a small fixed slab and free them on release, so repeated swaps do not split the top free area, which has 1.6 KB of margin.
- **Fonts and picture packs are mapped or read in place** from flash, not copied. A font mapping uses MMU pages, not heap [est, IS B2].
- **The worst case, with each kind loaded at its cap** (estimate from the caps): look 1,000,000, decode buffers 460,800, filler or sound 400,000, phrase 150,000, two language halves 32,768, game 16,384, frame stack 20,480: about 2,080,000 in all. That is more than the PSRAM margin, so the sum of loaded arenas must be held by the PSRAM budget in rule 6, not only each cap on its own.
- **Transient internal blocks** (the update task at 10,240, the pack tasks at 6,144 each, the private network at about 20,000) are started before the link opens, or are exclusive with other transient users, so a hole does not open in the top area [doc MB, ranked changes 3 and rule 2].

## H. Security

- **Data only.** No layer-3 item holds code, a function table or a pointer. Each kind has one validator that runs at install and again before the first load after boot: bounds on every length and offset, UTF-8 for strings, counts inside the declared caps, no offset outside the body. A font is the case to be most careful with: the in-place loader follows offsets read from the file, so a bad offset could read outside the mapped region; refuse to map a font that has not been hashed and validated since boot (hash in the background the first time it loads, as proposed [doc IS, B6]).
- **Game packs.** The engine is a data-pack player and the loader has an admission rule with an Ed25519 signature and a 16,384 byte ceiling [doc IS, A; `maipai_games_core.h:32,604-620` as cited there]. Read whether a pack carries anything that behaves like opcodes; if it does, the validator must bound steps and memory, or the format must change to plain tables. [measure: to read]
- **Signing paths.** Two trust classes, both Ed25519 with a key compiled into the image (there is no eFuse key, decision 14, so a key changes only by a signed update):
  1. *Release-signed:* language, font, game, sound, phrase, style, wake. Signed with the release key on the same path as the update header [doc `docs/plan/signed-update-header.md`; `update_verify.h:11-15` as cited in IS].
  2. *Household-signed:* owner-made content (picture faces and character packs, a family wake phrase, personas where they reach the unit), which the release key cannot sign. Proposal: signed by a host key pinned at pairing, accepted only over the paired link, and, once the encrypted link is the default (decision 13), the link itself authenticates the sender. Until then picture packs behave as today (SHA-256 and length only). This touches credentials, so it is an owner decision, not made here.
- **What a signature adds.** With the encrypted link on, the link already stops network injection. The signature still protects against a foreign or compromised host and a plain link, and it makes a half-written or altered item fail at load. A person with USB access can already read and flash everything [doc `docs/dev/software-only-protection.md`]; assets do not change that.
- **Abuse limits.** Rate caps (section E), per-item caps checked before the first erase, a refusal while locked, and no asset install that can change the lock, tokens or the link key.
- **No eFuse, ever** (decision 14): `scripts/efuse-check.py` runs after every build [code `scripts/fw-build.sh`, last lines].

## I. Profiles (decision 19, narrowed by decision 20): when and how, not v1

**When.** Only if the measured memory budget proves the features cannot all fit in one image. Today flash fits with room (section B notes). The open question is runtime internal RAM: if the post-SF47 heap map still shows the largest free block under 24,000 bytes with the link up and the camera stream running, the smallest split is one second image, "Camera and sensors" (camera stream, IR, NFC, avatar to host), so the everyday image never allocates them [doc MB, recommendation]. Two is the expected number; never more than four. Decision 19's example list has four (Standard, Voice plus, Camera and sensors, Maker); decision 20 narrows it, and this note keeps the expected two.

**How.**

1. Profiles are built from the same patch series with different module switches (`scripts/fw-build.sh` already builds kinds from overlays: `plain`, `full`, and the bench kinds [code `scripts/fw-build.sh:16-26`]; release profiles are a new, named subset of those, not the bench kinds).
2. Each profile contains the whole kernel and the same safety rules, has its own memory table, gate and bench proof, and never changes what an asset slot holds (assets stay assets).
3. **Build-kind manifest.** A small signed file next to the image names: the profile id, the board id, the release build number, the modules compiled in with their run-time flag keys, the asset format range per kind, and the hash of the memory-budget table the profile was proven against. The unit reports the profile id and module list in its hello. The dashboard reads the manifests to list what each profile adds and costs, and offers a switch only for a combination that fits.
4. A switch installs the other profile's image through the normal signed update: the other app slot, the first-boot trial and the automatic rollback. Settings stay (the NVS version must be readable by both).
5. The update header has no free byte: all eight reserved bytes now hold the board id [doc `docs/plan/signed-update-header.md`, board id]. A profile id needs a new header version (`MPUH2`, the 56 bytes plus an 8 byte profile id) or a second signed file. Prefer the new header version so one signature covers all of it.

**Anti-rollback at the same build number.** A profile switch inside one release has the same build number, which today is refused ("not higher than the confirmed number"). Proposed rule:

- The build number is per release and is the same for every profile of that release (the release script writes the same number into each profile's header).
- Accept a header when its build is above the floor, **or** when it equals the floor and its profile id differs from the running profile (a switch inside the same release).
- Never accept a build below the floor, in any profile.
- The profile id sits inside the signed bytes, so an image cannot be passed off as another profile.
- Cap profile switches (for example one an hour [est]) so the other slot is not rewritten in a loop.
- A bench or maker profile is not signed with the release key. Decision 19 lists a Maker profile with the bench tools; that widens the attack surface of a signed image, so it needs an explicit owner decision before it exists.

## J. Ranked changes, and what is v1

Ranked by value over cost. V1 means the first public release.

| # | Change | Layer | V1 | Notes |
|---|---|---|---|---|
| 1 | Finish the merge in `docs/plan/installed-set.md`; one asset-kinds table, one install tool, one signing path | 3, 4 | yes | Doc work, blocks everything below; slot counts differ today (faces 2 or 3, dances, games 8 or 4) |
| 2 | The seven measures on the unit, after the plain boot proof of SF47 (heap map, link handshake, stream, game start, wake model, subtitles) | all | yes | Decides whether profiles are ever needed [doc MB] |
| 3 | `maipai_mem_admit` plus run-time flags per module, with the off-at-run-time check in the off-cost script | 1, 2 | yes | The rule that makes "off costs zero" true for the one image |
| 4 | Streaming signed install, no `pack_boot` and `pack_write` tasks | 3 | yes | Removes 12,288 bytes of transient internal RAM |
| 5 | Asset slot manager: multi-slot directory, signed header, validators, languages and styles first | 3 | yes | Reuses the pack cache and its power-cut test [doc IS, E1] |
| 6 | Picture pack read in place; PSRAM budget in the slot manager | 2, 3 | yes | Saves up to 1,000,000 of PSRAM; verify the current holding first |
| 7 | Encrypted link on in the one image, one cipher suite, after the handshake measure | 1 | yes | Decision 13 |
| 8 | Directory ring of 8, rotating allocation, rate caps | 3 | yes | Part of 5; cheap |
| 9 | Fixed arena per kind and the compatible-range check | 3 | yes | Part of 5 |
| 10 | Bake the Latin-2 letters into the kernel fonts (about 4,000 bytes) | 1 | yes | Cheaper than any pack |
| 11 | Free first-run page objects early; free the caption label when it ends | 1, 2 | yes | Small; 3,700 and about 1,500 bytes |
| 12 | Put SF44 into the patch series; allocate its socket only while streaming | 2 | yes | Gap 2 |
| 13 | IR and NFC modules, after the bench probes pass | 2 | if the owner wants them | Flash 20,000 to 40,000 [est]; no internal cost while off |
| 14 | Face detection stays on the host; the experiment image stays out of release | 2, 4 | yes | Saves 191,000 to 480,000 of flash |
| 15 | Font packs (CJK), then right-to-left and shaped scripts | 3 | no | Needs the in-place loader; tier 2 and 3 of decision 18 |
| 16 | Custom wake word | 2, 3 | no | After the signed asset path; measure the model and the two-hit barge-in rule [doc WW] |
| 17 | Move the embedded offline phrases out of the image | 3 | no | Only if flash is ever short |
| 18 | Reclaim the stock font and large icons in the assets partition | 3 | no | USB reflash needed on units already out; only if the pool is too small |
| 19 | Image profiles, build-kind manifest, header version 2, same-build switch rule | all | no | Only if measure 2 proves one image cannot fit the heap |
