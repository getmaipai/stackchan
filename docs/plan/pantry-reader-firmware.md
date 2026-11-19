# Content pantry on the unit: the reader, the size budget and the heard list (firmware track, 2026-11-18)

Owner decision 25: the unit keeps a pantry of typed records (things to say or show with no host) in the installed-set store, and remembers which ones the person has heard. The unit half: how big the pantry may be, how the unit reads it, and when it writes the heard list.

## Size budget (against the installed-set and the assets partition)

| Item | Bytes | Basis |
|---|---:|---|
| Assets partition | 6,225,920 | `partitions.csv` (measured) |
| Used by the image today | 4,463,226 | wake-word models 2,469,827, stock font 1,287,460, icons and pictures 705,939 (measured) |
| Free today | 1,762,694 | measured |
| Free with the stock font left out (SF80) | 3,050,377 | measured: 1,287,683 more |
| Installed-set reserve for packs (languages, styles, picture faces, games) | to decide in `docs/plan/installed-set.md` section C; the pantry takes what is left | |
| One record | at most 256 bytes: a 4-byte header (kind, language, tags, length) and up to 250 bytes of text (UTF-8) | design limit |
| A pantry of 2,000 records | about 0.5 MB | arithmetic |
| A pantry of 10,000 records | about 2.5 MB | arithmetic: the practical ceiling with the font left out |

The pantry is one **asset kind** in the installed-set store (`docs/plan/installed-set.md`, section G: typed header, license id, memory class "flash in place"). It is **read in place from the mapped flash** (never copied into PSRAM): a record is found by its index through a table of 4-byte offsets (2,000 records: 8 KB table, in flash too). The reader keeps no record in RAM beyond the one being spoken or shown (at most 256 bytes on the stack of the application task). Memory row in `schema/memory-budget.json`: pantry in use: 0 internal, 0 PSRAM, flash only (the table is mapped).

## The reader

A pure core `maipai_pantry_core.h` (plain C99, host-tested): `mpy_find(kind, tags, language, heard, rng)` picks a record that matches the request, is **not already heard** (or, when all matching records are heard, the least recently heard), by a seeded choice; `mpy_get(i, buf)` copies one record. Validation at install: header magic and version, the table inside the asset, every offset inside the asset, lengths 1 to 250, UTF-8 well formed, no code (a record is text); an asset that fails is never mapped. The record text is the only thing returned; the unit never interprets it as a command.

## The heard list

- **What is stored:** one bit per record (2,000 records: 250 bytes; 10,000 records: 1.25 KB) plus a count, in the unit's own NVS namespace, saved as one blob. A new pantry version resets the bits whose record text changed (the hash of the record is not stored: the bit of a record whose index now holds other text is cleared by the pantry version number).
- **Write policy (batched):** the bit is set in memory at once (so no repeat). The blob is written **at most once every 10 minutes**, and also when 20 new records have been heard, at the end of a game or a conversation, and when the unit is about to sleep or restart for an update. A power cut loses at most the heard marks since the last write: a record may repeat once, never a data loss. **Never from a task that has its stack in PSRAM** (a flash write there crash-looped the unit before: SF39 and the PSRAM-stack lint), never from the display task: it runs on the application task through `Application::Schedule`, like the clock-style and slider saves.
- **Wear:** NVS spreads writes over its pages; a 1.25 KB blob written six times an hour is about 140 blob writes a day, far under the flash's erase budget (about 100,000 cycles a page, spread across the namespace): no concern at this rate.
- **Reset:** a person's "forget what you have heard" (a setting) clears the blob; a factory reset erases the namespace.

## Interactions to keep

1. The pantry never changes what the privacy rules allow: muted or full quiet, nothing is spoken; a record is shown or spoken with the same gate as any unit sound or caption.
2. A pantry record spoken with no host uses the mumble voice (`docs/plan/offline-mumble-firmware.md`): the record text is its input.
3. Installing or updating a pantry goes through the host and the signed install flow (installed-set section B3 and G5); with no host the pantry on the unit keeps working and cannot change.
4. Large pantries are installed over several `self.assets.data` pieces and verified by hash before the directory flip; the old pantry stays until the new one is complete (power-cut safe).

Not built yet: this note fixes the limits so the host side (the app track) and the dashboard can size the content, and so the memory rows can be written when the reader lands.

## Kind `line` (app track note, 2026-11-18)

The host adds a sixth record kind, `line` (kind byte 5): a canned line for a situation. `text` is at most 100 bytes, `extra` is one of 20 situation tags (listed in `docs/design/content-pantry.md`, "Lines by situation"; `host/maipai_packages/pantry/record.py` `SITUATIONS` is the order), no answer, rating `kid`. The reader asks `mpy_find(kind=line, tag=<situation>, language, heard, rng)`, shows the text as the subtitle and plays the mumble. The reader needs the kind byte 5 accepted and the situation tag carried in the record's `extra` field. This also covers kind byte 4 (`object`, twenty questions, `docs/design/twenty-questions-library.md`). The unit keeps 13 of the 16 recorded offline phrases out of the image once this lands (the list is in the same section).
