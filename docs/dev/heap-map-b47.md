# The internal heap map of b47 (bench window 14): what holds the largest block, and what would move it above 36 KB

Firmware track, 2026-11-18. Data: `self.bench.heap_info` calls 1 to 3 and the heap trace of the b47 heap image (the bench notes, `bench-w14-data`), read with the b47 ELF. Call 3 is with the link up.

## The numbers

| | Before SF47 (b29, window 11) | b47, link up (call 3) |
|---|---:|---:|
| Largest free internal block | 25,624 | **32,024** (at 3fcf02e4) |
| Second free block | 4 KB class | 24,548 (at 3fcc76c8) |
| Total free internal | about 64,000 | 67,956 |
| Memory line at 24 s | | internal_free 68,519, internal_min 39,828, int_big 31,744, psram_free 7,834,532 |

SF47 (the avatar_lan task created on first use) gave +6.4 KB of largest block and removed the unnamed 4 KB block that sat in the top area in the b41 map (3fcf0bc0): it was part of the avatar_lan start (its 8 KB stack and the receive buffer of the avatar socket); that is an inference from the address and the change, not a proof (the trace does not record task stacks).

## What is in the used list (call 3)

| Block | Bytes | What |
|---|---:|---|
| `wifi` task stack | 6,656 | stack (IDF) |
| `main` task stack | 6,656 | stack |
| `taskLVGL` | 8,192 | stack |
| `stackchan` | 5,120 | stack |
| `audio_input`, `audio_output` | 4,096 each | stacks |
| `tcp_receive`, `ws_reconnect`, `esp_timer` | 4,096 each | stacks |
| unnamed | **30,720** | probably the camera driver's internal DMA area (the size is about a fifth of a 320 by 240 frame; it sits beside the `dvp_task` stack). The heap trace does not see it (allocated before the trace starts). To confirm: start the camera late and see the block move |
| unnamed | 6,400 and 6,400 | the two half draw buffers of the display (`stackchan_display.cc:222`, patch V26, 10 lines of 320 pixels at 2 bytes) |
| listed as 65,536 "tcp_receive" | | **an artifact**: the entry starts at 3fcbd6b4 and overlaps the `wifi`, `tcp_receive` and `ws_reconnect` blocks that are listed separately, so it cannot be one allocation. The owner match only found a stack base inside it. It is most likely the walker reporting a heap region's start. Do not read it as a 64 KB buffer; the proof is that the free blocks plus the other used blocks add up without it |

The heap trace of the run (588 records, none of 4,000 bytes or more) shows only small allocations: task stacks and the large boot-time blocks are outside it. So the owner of every large block comes from the stack list and the sizes above.

## Why the largest block is 32,024 and what would raise it

Layout around the second free block: the free block at 3fcc76c8 (24,548) ends at 3fccd6b8; the first display draw buffer (6,400) starts there; the second display buffer (6,400) follows at 3fccefbc; then a gap of about 2.7 KB and the 30,720 byte block at 3fcd1374. The largest free block is a different, higher region (3fcf02e4).

| Change | Result (estimate from the addresses) | Cost and risk |
|---|---|---|
| **Move the two display draw buffers to PSRAM** (`buff_spiram` instead of internal DMA) | the 24,548 block joins the 12,800 bytes of the two buffers and the gap: about **37 to 40 KB contiguous**, the new largest block | LVGL draws into PSRAM, slower; SPI DMA from PSRAM works on the S3 but needs the cache line alignment the port handles. **The face refresh gate (30 a second, 44.7 measured) must be re-measured**; a bench change, not a blind one |
| Start the camera driver late, free after use | frees a 30,720 block above the buffers; does not join the 24,548 block (the display buffers are in between), so no gain for the largest block unless the buffers also move | the first frame after a start is old; the seeker and photos wait about 0.5 s |
| Both | about 68 KB contiguous from 3fcc76c8 to 3fcd8b74 | both risks |
| Persistent receive tasks for the sockets (a vendor patch) | none for the largest block (the stacks sit low) | skip |

**Recommendation:** the display buffers first (one line in `stackchan_display.cc`, a bench measurement of the refresh rate and a look for tearing), because it alone passes 36 KB with no change to behavior. The camera stays as it is until its owner is confirmed. Patch SF54 adds the two numbers that settle one more question (the speaker volume now and saved) to `self.audio.sound_info`; the display change is not written until the bench can measure the frame rate.

## Answers to the playground's four questions (`docs/plan/memory-budget-model.md`)

1. **Placeholders:** the page and overlay sizes cannot be read statically; a measure is two `self.bench.heap_info` calls, before and after opening the page (the page tools and the face quick sheet open them). I left those rows as placeholders and listed the procedure; the rows that could be filled are filled (display buffers 12,800, the camera block 30,720, `avatar_lan` 8,704 as transient, the dance session, the supervisor) and the baseline is the b47 numbers above.
2. **Does a page cost internal RAM?** Yes while open: LVGL objects come from the LVGL memory pool (the unit gives LVGL a pool that includes PSRAM, `lcd_display.cc:126` to `153`), so a page's objects may be in PSRAM. Which of them are internal is not known; the first-run flow measured 3.7 KB internal while open, so at least part is internal. The conservative reading (all internal) is the model's current one; the two `heap_info` calls will say.
3. **`pack_boot` and `pack_write` transient (lowest only)?** Yes: both exist only while a pack is read or written. They are 6,144 bytes each, internal because they read flash. A write also holds the pack in PSRAM. Treat them as lowest-block items (the model does).
4. **Interactions:** yes, three. The link and the camera stream share the second socket's receive stack (4 KB) only if both are on one socket; they are two sockets (voice and avatar), each with its own 4 KB stack, so the model should add 4,096 per socket, not share. The camera stream (SF44) also depends on `camera.dvp_buffer` being present (always, today). The dance session needs the overlay layer and notes rows while it runs (the model should add those rows when the dance starts at step 3 and 2).

## For the landing script (decision 15f)

The budget file changes in the same patch as the cost. The landing routine should refuse a patch that adds a task, a buffer or a switch with no row in `schema/memory-budget.json`; the patch header already carries the memory cost line, so the check is "a header line 'Memory cost:' exists and the file was touched". Not built yet.
