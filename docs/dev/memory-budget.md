# Memory budget of the optional features (owner decision 11, 2026-11-18)

Firmware track, 2026-11-18. Method: static analysis of the replayed tree (b43 and b44, patches through SF43, with SF44 and SF45 in the dev tree), the ELF section sizes of each build kind, the sdkconfig, the task table (`docs/dev/internal-ram-tasks.md`) and the bench windows already reported. **Every number says where it came from.** The unit was not used for this note; the numbers that need it are listed at the end.

## The gate and where the unit stands

Gate (`docs/dev/gate-numbers.md`): internal free median at least 40,000 bytes, lowest at least 24,000, largest free internal block median at least 24,000 and lowest at least 16,000, PSRAM lowest above 6,000,000, task stack margin at least 1,024.

| Number | Measured on | Value | Gate | Margin |
|---|---|---|---|---|
| Internal free, median | aec bench image, turns playing (window 10) | 69,075 | 40,000 | 29,075 |
| Internal free, median | image with the servo task (window 10) | 64,093 | 40,000 | 24,093 |
| Internal free, lowest | aec bench image (window 10) | 33,484 | 24,000 | 9,484 |
| Largest free block | link up (windows 10 and 11) | 25,600 to 25,624 | 24,000 median | **1,600** |
| Largest free block | before the link is up (window 11) | 46,804 | 24,000 | 22,804 |

The binding constraint is not the free total but the **largest free block, with 1.6 KB of margin once the link is up**. A new persistent internal allocation of about 2 KB or more can fail the gate by splitting the top free area, however much total RAM is free. The window-11 heap map named the cause: an unowned 4 KB block at 3fcf0bc0 and the `tcp_receive` and `ws_reconnect` stacks (4 KB each) split the top area when the link comes up.

## Static internal RAM per build kind (ELF sections, measured on the builds)

IRAM text plus `.data` plus `.bss`, in bytes:

| Image | Static internal | Difference | Flash code | Note |
|---|---:|---:|---:|---|
| plain (the release image) | 170,771 | | 2,545,216 | b44 |
| bench (proxy: the `cam640` kind, bench and gate only) | 185,751 | +14,980 over plain | 2,597,220 | the bench tools and gate are the cost, never in a release |
| bench plus echo canceller and barge-in (`aec`) | 186,759 | +1,008 over bench | 2,597,840 | |
| bench plus encrypted link (`linkpsk`) | 186,055 | +304 over bench | 2,604,744 | code +7.5 KB |
| linkpsk plus camera to host (`avatar`, SF44) | 186,103 | +48 over linkpsk | 2,609,708 | code +4.9 KB |
| aec plus heap trace (`heap`) | 188,107 | +1,348 over aec | 2,599,508 | a bench-only kind |

So **the static cost of each optional feature in internal RAM is at most about 1 KB**; the plain image carries none of it (`docs/dev/off-cost.md`: zero symbols and strings with every switch off). The runtime cost is what matters.

## Runtime cost per feature

Tasks with an internal stack are the main runtime cost (`internal-ram-tasks.md`). Buffers: mbedTLS is already built with `CONFIG_MBEDTLS_EXTERNAL_MEM_ALLOC=y` and dynamic buffers, so TLS contexts and record buffers are allocated in PSRAM.

| Feature | Static internal | Runtime internal | PSRAM | Effect on the largest block | Source |
|---|---|---|---|---|---|
| Echo canceller and barge-in | about 1 KB | the AFE already runs; the canceller sits in PSRAM (`AFE_MEMORY_ALLOC_MORE_PSRAM`); about +1 KB median seen | the canceller's filter and history, unmeasured | none known | ELF; window 10 (69,075 median with turns playing) |
| Encrypted link (TLS-PSK) | 0.3 KB | one `ssl_receive` stack of 4 KB per open socket, which replaces the `tcp_receive` stack of the plain socket (net 0 per socket); the handshake runs on the connecting task's stack (4 KB for `ws_reconnect`) | per session about 16 KB in plus 4 KB out record buffers plus the contexts: about 26 to 30 KB (estimate from the config: `SSL_IN_CONTENT_LEN` 16,384, `OUT` 4,096) | none by itself; the voice and the avatar socket each hold a session | sdkconfig; the PSK handshake internal dip is not measured (`self.bench.link_selftest` measures the key exchange only) |
| Camera stream to the host (SF44) | 0.05 KB | the frame buffer is PSRAM (M06); the JPEG encoder's work buffers and the output buffer: not measured; a second socket with its own `ssl_receive` or `tcp_receive` 4 KB stack | the 150 KB frame (QVGA) or 600 KB (VGA) plus the JPEG output | the second socket's 4 KB stack is a new internal block | ELF; `docs/plan/camera-frames-path.md` estimate |
| Custom wake word (MultiNet) | not built | the model's buffers: not measured | model working memory (the model file is 2.1 MB in the assets partition) | none known | design note `docs/plan/custom-wake-word.md` |
| Subtitles (captions, glyph text) | in the base | the glyph payload and labels while a caption shows: not measured | the glyph bitmaps | not measured | not measured |
| Games | in the base | `pack_boot` and `pack_write` tasks of 6,144 bytes each, transient, internal because they read flash | the pack | a transient 6 KB block can split the top area while it lives | task table |
| Picture faces and the picture frame | in the base | the frame task's stack is in PSRAM (20 KB); no persistent internal block | 153,600 per frame request, 20 KB stack | none | `docs/design/picture-faces-2026-11-16.md`; the leak is fixed (SF11) |
| First-run flow | in the base | the screen objects live in internal RAM while it is open: **about 3.7 KB median while open** (window 10, left open on the unit), returned when finished | none | a held block while open | window 10 |
| Servo task (SF31) | 0 | 3 KB stack plus the control block, always on | none | one more internal block | window 10: median 3,938 B lower |

## The combinations that can run at the same time

All figures are internal RAM and are estimates added from the table above (static, so no new measure), to be confirmed on the unit.

| Combination | Extra internal runtime over plain | What stands out |
|---|---|---|
| Link on, voice socket only | about 0 to 1 KB (stack swap) | the handshake peak on the 4 KB reconnect stack: confirm no stack overflow (margin gate 1,024) |
| Link on, voice and avatar sockets | about 4 KB (a second `ssl_receive` stack) | one more internal block of 4 KB in the area that is already splitting |
| Link plus echo canceller plus speaking | about 1 to 2 KB | the canceller is PSRAM; check the heap trace for the 4 KB block's owner |
| Link plus camera stream | about 4 KB plus the JPEG work buffers (unmeasured) | the stream refuses to start under 20,000 free largest block, and stops under 16,000 (SF44 gate), so it cannot push the unit under the lowest-block floor |
| All on (link, AEC, camera, a game starting) | 4 KB + 1 KB + JPEG work + a transient 6 KB pack task | the game's 6 KB pack task is the risk: it can make the largest block fall below 16,000 for a moment |

## Cheapest TLS configuration for the link (owner decision 13: encrypted link as the default for a paired host)

What the unit already has: TLS 1.2 only, PSK and ECDHE-PSK key exchange, hardware AES, SHA and MPI, mbedTLS memory in PSRAM, dynamic buffers on, session tickets on. The proposal, in order of saving:

1. **Offer one cipher suite: `TLS_PSK_WITH_AES_128_GCM_SHA256`** (set `ciphersuites_list` in the vendor hook `vendor_fixes/link_psk.cmake`; the host's TLS listener offers the same). It needs no elliptic curve calculation at all (no ECDH on the connecting task's stack, about 100 to 200 ms and 1 to 2 KB of stack less than ECDHE-PSK), keeps the hardware AES-GCM path and the smallest handshake. **Cost of the choice:** no forward secrecy: if the key `K` is read from the flash later, traffic someone recorded earlier can be decrypted. Because `K` sits in plain NVS (see `docs/dev/software-only-protection.md`) and a person with USB access can read it, forward secrecy would protect only against a later leak that does not come with the flash; ECDHE-PSK stays an option for the owner to buy (about +1 to 2 KB of handshake stack and +150 ms per connect).
2. **Keep the TLS memory in PSRAM** (already so) and keep the record buffers at 16,384 in / 4,096 out: the host (Python's TLS) does not negotiate a smaller maximum fragment, so a smaller input buffer could fail on a large record. Cost: about 26 to 30 KB of PSRAM per session, two sessions with the avatar socket: about 60 KB, against 6,000,000 free.
3. **One session at a time where possible.** The voice socket is the first; the avatar socket is a second session only while the camera stream is wanted. The second session's internal cost is its 4 KB receive stack.
4. **Disable what the link never uses in the image** (RSA, ECDSA and ECDHE-RSA key exchanges, certificate parsing for the link): code size only (tens of KB of flash), no RAM change; leave for later because the public certificate bundle is still used by other callers.
5. **Make the receive stack smaller only after measuring** its low-water mark on the linkpsk image.

Cost summary for the link as the default: internal RAM net about 0 for one socket, about +4 KB with the avatar socket; PSRAM about 26 to 30 KB per session; flash code +7.5 KB; CPU one handshake per connect (the measured number is needed).

## Ordered recommendation

1. **Nothing may add a persistent internal block of 2 KB or more** until the largest-block margin (now 1.6 KB) is raised. The cheapest ways to raise it, in order: find and move the owner of the unowned 4 KB block (heap trace), move `avatar_lan` (8 KB, if its call graph is flash-free), and a persistent receive task for the sockets.
2. **Encrypted link as the default is affordable** for the voice socket (net 0 internal), with the single cipher suite above; enable it first for the voice socket alone and measure the handshake stack margin.
3. **Camera stream stays opt-in** (switch off by default, and a unit setting on top): its gate refuses to start when the largest block is under 20,000, which keeps it from breaking the floor; land SF44 after the link measurement shows the second socket's cost.
4. **Custom wake word: not before the signed-asset path and a measured model footprint.**
5. **Cut or reshape:** the 6 KB `pack_boot` and `pack_write` tasks (make them one task that exists only while a pack is written, or start them before the link comes up so the area is not split); the first-run flow's 3.7 KB (free the objects as soon as a page is left).
6. **Exclusive:** the heap trace kind and the bench kinds are never combined with a release image.

## What must be measured on the unit (nothing else is unknown)

1. The plain image's memory line (median, lowest, largest block) with the link up, to replace the proxy figures.
2. `self.bench.link_selftest` and a real handshake on the linkpsk image: the internal dip and the stack low-water mark of the connecting task, for PSK-only and for ECDHE-PSK.
3. The heap trace of the plain-class heap image: the owner of the 4 KB block at 3fcf0bc0 and every internal block of 2 KB or more.
4. The camera stream (SF44) running: the JPEG work buffers' internal peak, the second socket's cost, and the largest block while streaming.
5. A game start with the link up: the largest block while `pack_boot` and `pack_write` run.
6. The custom wake word's model footprint (only if it is built).
7. Subtitles: internal RAM while a long caption shows.

## Audit of every feature under owner decision 15 (load nothing not needed; prefer PSRAM and flash; never hold the largest internal block)

Status words: **verified** (read in the code or measured), **estimate** (from sizes and configs), **to read** (not yet read), **to measure** (needs the unit). Where a thing lives: F flash (read in place, no RAM), P PSRAM, I internal RAM.

| Thing | Loaded when | Freed when | Lives in | Status |
|---|---|---|---|---|
| Language tables, screen words, first-run words | compiled in | never (read in place) | F | verified: constant tables and string views |
| Fonts (Noto Sans Latin-1, Montserrat symbols) | compiled in | never | F | verified: constant font data |
| Sounds (the built-in Ogg tones and clips) | played on demand: the demuxer reads from the flash image | after each play | F (the decoded PCM block is transient, P/I per block) | verified: `PlaySound` demuxes from flash |
| Bench clips (wake phrase, questions) | bench images only | never | F | verified: not in the plain image |
| Face (eyes, mouth, effects, overlays) | at boot | never (it is the product) | I (LVGL objects) | verified; the largest permanent screen cost |
| Boot cover and link strip | at boot | the cover when the first face shows; the strip when not needed | I | verified in `stackchan_display.cc` (24 creates, 7 deletes: the face stays) |
| Pages (clock, timers, games, actions, frame, tiles), quick settings sheet | when opened | when closed (the page timer is deleted too) | I | verified: `maipai_pages.cc` creates 5 and deletes 4 object trees; `s_page` is null when closed |
| Banner row | when a message needs it | 2 s after nothing needs it | I | verified: `maipai_banner.cc` idle release |
| Setup app (Wi-Fi page, menus) | when opened | when closed (and now after 90 s idle, SF36) | I | verified: `AppSetup::onClose` resets the pages |
| First-run flow | first standby of a unit with no record | when finished | I, **about 3.7 KB median while open** | measured, window 10 |
| Picture faces and the picture frame | on use | the frame buffer after the draw | P (frame task stack 20 KB in P, decode buffers in P) | verified |
| Subtitles, captions | on a caption message | when the caption ends | I (label), glyph payload | to read: the caption label may stay allocated; to measure |
| Games | on start | on exit | I while running | to read; `pack_boot` and `pack_write` tasks 6,144 B each are created for a pack and deleted after: transient I |
| Timers (state, ring) | boot | never | I, static and small (under 1 KB) | verified |
| Camera driver | at boot | never | frame buffer P (M06), driver state I | verified |
| MCP tools list | at boot | never | descriptors in P (M03) | verified |
| TLS contexts and buffers (link) | per connection | on close | **P** (`MBEDTLS_EXTERNAL_MEM_ALLOC`) | verified in the config |
| Models (wake word, noise, voice activity) | at audio start | never while listening | P (`AFE_MEMORY_ALLOC_MORE_PSRAM`) and F | verified |
| Opus task stack | at boot | never | P (static stack, M02) | verified |

### Tasks that always run (stack in internal RAM)

`stackchan` 5,120 (screen and logic), `servo_step` 3,072, `audio_input` 4,096, `audio_output` 4,096, `ws_reconnect` 4,096, one `tcp_receive` 4,096 per plain socket (`ssl_receive` per TLS socket), the system event task 3,072, the `tcpip` task 3,072, the timer task 3,584, main 6,144, IPC 1,280 and a few small ones. **Removed from always-running by SF47:** `avatar_lan` 8,192 (now created when the phone App announces its endpoint). **Already created on demand:** `pack_boot`, `pack_write`, `tailnet`, `activation`, `fwupdate`, `heal_restart`, `mp_reset`, `bench_say`.

### Changes ranked by internal RAM saved

| # | Change | Saves (internal) | Status |
|---|---|---:|---|
| 1 | `avatar_lan` created on first use (SF47) | 8.5 KB at boot, one 8 KB block less in the heap | built, in the b45 images, waiting for the plain boot proof |
| 2 | A persistent receive task for the sockets with its stack in PSRAM, if the receive path can be made flash-free (the voice receive callback saves settings in the hello, so it needs a hand-off to the main task first) | 4 KB per socket | to read, then design; needs a vendor patch for the network component |
| 3 | `pack_boot` and `pack_write` run as one task, started before the link comes up, 6 KB for a few seconds | no steady saving; stops a 6 KB hole opening mid-heap when a game starts | to read |
| 4 | First-run flow frees each page's objects as soon as the next shows | up to 3.7 KB during first run only | to read |
| 5 | Lower the three IDF stacks that had measured margins (system event 3,072, `tcpip` 3,072, timer 3,584) | 0.5 to 1 KB each if the margins allow | to measure (margins from the stack line of the plain image) |
| 6 | The caption label and glyph payload freed when the caption ends | to measure | to read |
| 7 | Settings and setup screens that duplicate the host's web page move to the host (decision 15c) | the Setup app is created and freed on use already, so this saves flash and code, not steady RAM | design with the app track |
| 8 | Wi-Fi buffers: static receive 3, dynamic 6, TX dynamic are already small; AMPDU is on | under 1 KB if reduced; not worth the throughput loss | estimate: leave |

The target (largest block above 36 KB with the link up and a second socket open) cannot be met by change 1 alone if the other blocks stay where they are: the heap dump (`self.bench.heap_trace`) decides which of the 4 KB blocks to move next. The numbers that need the unit are the seven above, plus the plain boot proof of the b45 images.

### Rules for every new feature (decision 15f)

Its patch header states its memory cost (static internal, runtime internal, PSRAM, largest block effect); it allocates on first use and frees on close; it keeps no persistent internal block of 2 KB or more; and it fails the gate if it breaks the budget (the gate numbers above). SF44 (camera to host) must allocate its second socket and its buffers only while streaming.

## Does everything we want fit in ONE image? (owner decision 20)

**Answer: yes for flash and for static RAM; the runtime internal RAM is decided by rules, not by a split.** Measured on a build with every optional module compiled in and no bench tools (build kind `full`: talk-over and echo canceller, encrypted link, camera to host (SF44), on the b43 tree):

| Image | Binary | Share of the 5,177,344 byte app slot | Room before the 20 percent free rule (4,141,875) | Static internal RAM (IRAM text, data, bss) |
|---|---:|---:|---:|---:|
| plain (release image) | 3,731,312 | 72.1 % | 410,563 | 171,107 |
| **full** (all optional modules on) | 3,745,872 | 72.3 % | **396,003** | 171,123 (+16) |

All the modules together add **14.5 KB of flash and 16 bytes of static internal RAM**; a module that is switched off in plain costs nothing, and one that is on costs flash only until it runs (decision 15). Not in this build and still to add: IR and NFC (the rows in `docs/plan/ir-and-nfc.md`; an estimate of 20 to 40 KB of flash), the supervisor and the reconnect rules (SF49: about 6 KB, already in the b47 plain), so the all-in image is about 3.8 MB, 340 KB under the limit. **One image fits in the slot.**

### The runtime question: the worst simultaneous combinations against the gate

Gate: internal free median at least 40,000, lowest 24,000, largest block median 24,000 and lowest 16,000. Today (windows 10 and 11, link up): median about 64,000 to 69,000, lowest 33,484, largest block 25,600. Adding SF47 (avatar_lan not created at boot) should add 8.5 KB; it is not measured yet.

| Combination | Extra internal RAM while running (estimate) | Median free after | Largest block after | Breaks the gate? |
|---|---:|---:|---|---|
| Link on, voice only | about 0 | 64,000 or more | unchanged (25,600, 34,100 with SF47) | no |
| Link plus echo canceller plus speaking | 1 to 2 KB | 62,000 or more | unchanged | no |
| Link plus camera stream (second socket) | 4 KB stack plus JPEG work buffers (to measure) | 57,000 to 60,000 | **can fall to 21,500 without SF47 (under the 24,000 median floor), 30,000 with SF47** | **yes without SF47; no with it, if the JPEG work buffers are in PSRAM** |
| Link plus camera plus AEC speaking | 5 to 7 KB | 55,000 to 58,000 | as above | same as above |
| IR or NFC while speaking | one RMT driver and an I2C transaction: under 1 KB (to measure) | no change | no change | no |
| A game starting (6 KB `pack_boot` task, transient) while the link is up | 6 KB for a few seconds | no change after | **a transient hole of 6 KB in the top area** | possibly: the lowest-block floor is 16,000 |
| Everything at once | 11 to 14 KB | 50,000 to 53,000 | about 20,000 with SF47 | passes the median gate; the lowest-block floor is the tight one |

So the gate is not broken by a combination of modules **provided the camera stream runs only after SF47 and refuses to start when the largest block is under 20,000** (the SF44 gate); the dangerous pair without those two is link plus camera.

### The smallest fix without a split: rules in the kernel

1. **SF47 first** (done, waiting for the boot proof): it removes the 8 KB task from the top area; everything else is sized against that.
2. **Exclusivity by memory, not by switch:** the camera stream and a game pack write do not run at the same time (the pack task asks first; the stream pauses while it runs). The unit says so on the screen in plain words ("The camera is paused while a game loads").
3. **Allocate the stream's second socket and its buffers only while streaming**, and release them when the host stops the stream (SF44 as designed).
4. **One TLS session at a time where possible** (decision 15e): the avatar socket is the second session only while streaming.
5. **Do not hold the largest block:** the transient 6 KB pack tasks start before the link comes up, or run as one task (see the ranked changes above).

### Recommendation

**One image**, with the modules switchable at runtime and the rules above. **No profile split is needed for flash or for the median gate.** What remains open is measured on the unit: the largest block with the link up and a second socket open, with SF47 in. If that measure is under 24,000 median after SF47, the smallest split is a single second image, "Camera and sensors" (camera stream, IR, NFC, avatar to host), so that the everyday image never allocates them; the everyday image would then be the plain one plus the supervisor. Nothing is decided by this estimate: the numbers that decide are items 1 to 4 of the list "what must be measured on the unit" above plus the post-SF47 map.
