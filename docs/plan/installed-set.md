# The installed set: slots, signed assets, language and font packs (design, 2026-11-18)

Placement: unit (firmware track), host and dashboard (app track), virtual unit (playground). Serves owner decisions 15, 17 and 18 (`docs/design/decisions.md`). No code is written; every number carries its source.

**Bottom line.** Most of the machinery already exists. The shared pack loader (`maipai_packs.cc`, `maipai_pack_core.h`, `maipai_packcache_core.h`) already receives a pack in pieces, checks a SHA-256, writes it to a 1.5 MB region at the tail of the `assets` partition with a two-sector directory that survives a power cut at any step, and falls back to the built-in set when a pack is damaged. What it lacks for decisions 17 and 18 is four things: more than one item per kind, a signature (packs carry only a checksum today), a streaming install (today the whole pack is buffered in PSRAM, then a 6 KB internal task writes it), and consumers for fonts and full language tables (today a language pack carries only weekday, month and two chip words, 181 bytes). The smallest design adds an asset header signed on the same Ed25519 path as the update header, turns the directory from one entry per type into a few slots per kind, and adds `self.assets.list`, `install`, `remove` and `swap`. No partition change is needed for the first two kinds (languages and faces). The one risk that is real: a CJK font pack (to measure, estimated 0.3 to 0.7 MB) does not fit beside other kinds in the 1.5 MB region at the same time, so fonts get one slot and a swap drops the old font first. A power cut then leaves the built-in Latin set, which is a safe state.

Evidence tags: **[code path:line]** read in code (tree `~/esp/stackchan-rebuild/b47/firmware`, paths below are relative to `main/hal/` unless they start with another folder); **[doc path]** from a doc; **[est]** estimate with the method named; **[measure]** unknown until measured.

## A. What fits now, and what is baked or already loadable

The memory rule that binds every row: no persistent internal block of 2 KB or more, largest free internal block margin is 1.6 KB with the link up (`docs/dev/memory-budget.md`, "The gate and where the unit stands"). Every installed item below therefore lives in flash (read in place) or PSRAM. Free PSRAM must stay above 6,000,000 bytes at the lowest point [doc docs/dev/memory-budget.md, gate list].

Flash facts used throughout: the plain app image is 3,734,480 bytes in a 5,177,344 byte slot (72.1 percent) [read from `build-plain/maipai-stackchan.bin` and `partitions.csv:6`], so about 407,000 bytes remain before the 80 percent rule [`xiaozhi-esp32/main/update_verify.h:40-43` for the rule; arithmetic is an estimate]. The `assets` partition is 6,225,920 bytes at 0xA00000 [`partitions.csv:8`]. The stock assets image inside it is 4,463,226 bytes [`maipai_packcache_core.h` header comment; `build-plain/generated_assets.bin`] and holds: the text font `font_noto_sans_common_20_4.bin` 1,287,460 bytes, the speech models `srmodels.bin` 2,469,827, and 17 icon and picture files of about 0.70 MB together (seven of them 84,612 bytes each) [read by parsing `build-plain/generated_assets.bin`]. The pack cache owns the last 1,572,864 bytes (0x180000) of the partition: two directory sectors and 382 data sectors of 4,096 bytes, 1,564,672 bytes of data [`maipai_packcache_core.h:25-30`]. Margin between the stock image and the cache: 189,830 bytes [same file, header comment].

| Kind | Baked in the image today | Already loadable today | Slots now | Cost per item: flash, PSRAM, internal |
|---|---|---|---|---|
| Face styles | 5 styles as a const table: big eyes, eyes only, stock, classic, minimal [`maipai_look_core.h:39-44,70-84`]. A style is about 30 bytes of integers (eye size, spacing, mouth kind, brows, drift) [`maipai_look_core.h:50-68`]. 11 style numbers exist, 6 dropped [`maipai_face_core.h:20-29,110-114`] | No. The look pack carries pictures only: the loader refuses a look pack whose `kind` is not `picture` [`maipai_picface.cc:708`] | 5 baked, 0 loadable | Flash about 40 bytes plus name [est: struct size]. PSRAM 0. Internal 0 |
| Picture faces and character packs (one kind: the character pack is the picture pack with a manifest [doc docs/design/character-pack-format.md]) | None | Yes: type `look`, one per unit, up to 1,000,000 bytes, 7 expressions, 14 frames at most, 6 per expression [`maipai_pack_core.h:35`; `maipai_picface_core.h:27,45-48`]. Kept in flash and applied at boot [`maipai_packs.cc:95-98`] | 1 | Flash up to 1,000,000 [same]. PSRAM: the pack as sent up to 1,000,000, plus up to 3 decoded frames of 153,600 bytes (460,800) [`maipai_picface_core.h:25,46`]. Internal: none persistent, frame task stack is in PSRAM [doc docs/dev/memory-budget.md, picture faces row] |
| Languages (strings) | Six first-run tables (en, es, fr, de, pt, it), each about 24 strings, compiled in [`maipai_firstrun.cc:8-48`; `maipai_firstrun_core.h:17-23`]. English and Spanish pairs in other screens [`maipai_more.cc:380`]. Weekday, month and chip words for English [`maipai_lang_core.h:61-65`] | Partly: type `language` loads weekdays, months and the alarm and timer chip words, ASCII only, 181 bytes in two PSRAM slots [`maipai_lang_core.h:43`; `maipai_lang.cc:21-22`]. The gate is 200,000 bytes [`maipai_pack_core.h:35`], far above need | 1 | Flash: size of the pack, now a few hundred bytes [est]. PSRAM 181 bytes now; a full table is about 6 KB [est: about 150 strings at 40 bytes, to measure with the real catalog]. Internal 0 |
| Fonts | Noto Sans basic at 16 and 20 px, 890 glyphs each, about 67 KB and 102 KB of bitmap [measured by parsing `xiaozhi-fonts/src/font_noto_sans_basic_{16_4,20_4}.c`; used at `maipai_ui_style.h:9-10`]. Montserrat 14, 16, 20, 24 for symbols and ASCII [`sdkconfig.fplain:5767-5774`] | Not by us. The stock loader maps the 1,287,460 byte common font (6,845 glyphs: 5,258 Han, 147 kana, 464 Hangul) from the partition and sets it as the display text font [`xiaozhi-esp32/main/assets.cc:287-296`; index.json read from the built image]. Whether any MaiPai screen draws with it is [measure]: the MaiPai screens use the compiled basic fonts [`maipai_pages.cc:97`, `maipai_subtitles.cc:20`] | 0 | See section D |
| Games | 7 packs embedded, 1,058 to 3,968 bytes each, 17,828 bytes total [read from ELF symbols `_binary_*_mpk_*`; list at `maipai_games.cc:83-91`] | One external pack in PSRAM, bench builds only [`maipai_games.cc:75,94`]. The loader has type `game` (200,000 byte gate) but no consumer [`maipai_pack_core.h:35`; `maipai_packs.cc:68-69`]. An Ed25519 admission rule for external games exists but no shipped path calls it [`maipai_games_core.h:609-621`; `maipai_games.cc:1134-1175`] | 7 built in, 0 installed | Flash 1 to 4 KB [measured above]. Pack ceiling 16,384 bytes with signature [`maipai_games_core.h:32`]. PSRAM: the pack copy while it runs. Internal: screen objects while running [measure] |
| Sounds | 26 Ogg clips embedded, 107,188 bytes [read from ELF symbols `_binary_*_ogg_*`]. Played from flash in place [doc docs/dev/memory-budget.md, audit table] | Type `filler` loads (400,000 byte gate, 80,000 per clip, held in PSRAM) [`maipai_filler.cc:190-200`]. Type `phrase`: 16 offline clips, 150,000 bytes [`maipai_pack_core.h:30,35`]. Type `sound` and `dance` exist with no consumer [`maipai_packs.cc:68-69`] | filler 1, phrase 1, sound 0 | Flash up to the gate. PSRAM the unzipped pack (up to 400,000). Internal: the decoded block while playing, transient |
| Overlays | 18 overlays and 10 presets, drawn by code; three layers use 2.76 KB of PSRAM [`maipai_overlay_core.h:6-9,19-21`] | No | 28 fixed in code | Flash: code. PSRAM 2.76 KB. Internal 0 |
| Personas | None on the unit. No persona symbol exists under `main/hal` [read: grep] | Not applicable: the host owns personas | 0 on the unit | 0. A persona that names a wake phrase, voice or face is those other kinds |
| Wake-word model | One WakeNet model inside `srmodels.bin` 2,469,827 bytes [read from the built assets image; doc docs/plan/custom-wake-word.md] | The family phrase is data: MultiNet commands come from index.json, no new model [doc docs/plan/custom-wake-word.md] | 1 model, phrase is data | Flash: inside the 2.47 MB. PSRAM: model buffers [measure, memory-budget.md item 6]. Internal [measure] |
| Icons and pictures | 17 files, about 0.70 MB, read in place [read from the built assets image] | No | fixed | Flash only. Internal 0 |

What to reuse, in order of value:

1. **The pack cache directory and its write order** [`maipai_packcache_core.h:251-300`]: data sectors first, then the directory sector that points at them, alternating two sectors with a sequence number, a read-back check before the directory flips, and a host test that cuts power at every step [`maipai_packcache_core.h:9`, test `host/tests/firmware/packcache_core_test.c`]. Install atomicity is already proven here. It needs more entries and a signature, not a new design.
2. **The streaming SHA-256 and length check** of the signed update [`maipai_updatehdr_core.h:73-120`] and the Ed25519 verifier with the built-in key [`xiaozhi-esp32/main/update_verify.h:11-15,50-62`].
3. **The ping-pong slot trick** of the language loader: parse into the idle slot, then one atomic store makes it current, so the draw task never reads a half-written table [`maipai_lang.cc:1-5,21-22`].
4. **The in-place font loader** of the stock tree (`cbin_font_create`, `xiaozhi-fonts/src/cbin_font.c:33-80`): bitmaps and glyph descriptors are read from flash where they lie, only a small font and descriptor copy and the character-map table are allocated.
5. **The inflate helper with its state in PSRAM** [`maipai_inflate.h:1-8`], needed only for zip-wrapped kinds.
6. **The error pair** (`error`, `error_es`, a code) of every `self.pack.*` answer [`maipai_pack_core.h:195-250`].

What is NOT reusable as is: the pack receiver buffers the whole pack in PSRAM before writing [`maipai_packs.cc:290`] and writes it from a 6,144 byte internal task [`maipai_packs.cc:363`]; `pack_boot` is a second 6,144 byte internal task [`maipai_packs.cc:221`]. The memory budget already lists both as a cut [doc docs/dev/memory-budget.md, change 3]. The streaming install below removes both.

## B. The smallest unit-side mechanism

### B1. Asset slot manager

A new core file `maipai_assets_core.h` (plain C99, no heap, host-testable like the other cores) and a device file `maipai_assets.cc`. It replaces the "one entry per type" directory of `tpc_dir_t` with "a few entries per kind". Concepts:

- **Kind**: language, font, style, look, game, sound, phrase, wake (later). The table of kinds (name, max slots, max item bytes, trust level) is one JSON file, `schema/asset-kinds.json`, read by the host and the virtual unit and turned into a generated header for the firmware (one definition, one place; a drift check as for the other vendored shapes).
- **Slot**: an index inside a kind. An item stores `kind, slot, name, code, version, size, sha256, first sector, sector count`.
- **Installed** means the item is in flash and listed. **Active** means the kind has loaded it (one active item per kind, except games and sounds where all installed items are listed to the user). Items not installed cost nothing. Installed but not active costs flash only.
- **Directory**: the existing format with a larger entry array. A 96-byte entry [`maipai_packcache_core.h:53`] fits 42 per 4,096-byte sector after the 16-byte header, so one directory sector holds every proposed slot (see E for the counts, 25 in all). The directory also holds the active slot per kind. It lives in the assets partition, not in NVS: NVS is 16,384 bytes [`partitions.csv:3`], shared with Wi-Fi and settings, and a directory in NVS cannot be flipped together with the data [est: reasoning]. The settings the person already has stay in NVS (for example the language code [`maipai_face.cc:284`]).
- **Directory ring for wear**: grow the two directory sectors to a ring of 8 (32 KB, taken from the 189,830 byte margin or from the end of the data area). The newest valid sector by sequence number wins, the same rule as today [`maipai_packcache_core.h:251-258`]. See C for why.
- **Allocation**: first fit from sector 0 today [`maipai_packcache_core.h:235-249`], which concentrates wear on the low sectors. Change to a rotating start: begin the search after the end of the last written run and wrap.

### B2. Load and free on demand

- A consumer asks the manager for its active item: `maipai_asset_get(kind, &bytes, &len)` returns a pointer and a length. For small kinds (style, language table, game, sound pack, look) the manager copies into PSRAM and the pointer stays valid until the item changes, the same contract as `maipai_pack_bytes` [`maipai_packs.h:11-14`]. For fonts it maps the slot in place with `esp_partition_mmap` and hands the pointer to the font loader; IDF 6.1.1 does not require a 64 KB aligned offset for this call [`~/esp/esp-idf-6.1.1/components/esp_partition/include/esp_partition.h:475-478`], although the mapping uses whole 64 KB MMU pages internally [est: IDF behavior, to confirm on the unit].
- `maipai_asset_release(kind)` unmaps or frees. Nothing loads at boot except the active language table and the active style (a few KB); fonts load when a screen that needs them opens and free when it closes (decision 15a).
- No consumer holds a persistent internal block of 2 KB or more. The font object plus descriptor plus character-map array is under 0.5 KB [est: from `cbin_font.c:33-80`, `lv_malloc` of the font, the descriptor and `cmap_num` entries]. With `CONFIG_SPIRAM_MALLOC_ALWAYSINTERNAL=256` [`sdkconfig.fplain:2778`] these small allocations are internal, so they must be freed on release [measure the exact bytes].

### B3. Install flow, streaming and atomic

Steps on the unit (every refusal says what went wrong and what to do, with an `error_es` twin):

1. `self.assets.install` begin: the host sends the 128-byte asset header (below) and its 64-byte signature, as base64.
2. Verify the signature over the 128 bytes with the built-in key, the same path as the update header [doc docs/plan/signed-update-header.md "Unit steps"; code `maipai_updatehdr_core.h:50-71`, `update_verify.h:11-15`]. Check the magic, the board id (all zero refused, must equal `CONFIG_MAIPAI_BOARD_ID`), the kind, the minimum firmware build, and that the version is not lower than an installed item of the same name. **Refuse oversize here**: `length` above the kind's per-item cap, or above the free bytes left in the shared pool, or the declared PSRAM-when-loaded number above the PSRAM budget, answers `too_big` before a single sector is erased.
3. Choose a destination run of free sectors that overlaps nothing the directory lists, and is never the run of the item being replaced (so the old item stays intact). If no run exists and the kind is `font`, drop-then-write applies (see C); every other kind refuses with `full` and names what to remove.
4. Stream: `self.assets.data {at, b64}` pieces in order (same rule as `self.pack.data`: the offset must equal what the unit has [`maipai_pack_core.h:290-294`]). The handler fills a 4,096-byte PSRAM scratch sector [the scratch already exists: `maipai_packs.cc:138`], erases and writes that sector, and feeds `muh_sha_update`. No whole-pack PSRAM copy. The flash call runs on the tool task, which has an internal stack; the 6,144-byte `pack_write` task is not created [measure: stack margin of the tool task during `esp_partition_write`].
5. `self.assets.commit`: compare length and SHA-256 with the header (`muh_check_image`, `maipai_updatehdr_core.h:112-120`), read back the run and hash it (`tpc_verify` pattern), and only then write the new directory sector with a higher sequence number.
6. Power cut at any point before step 5's directory write: the old directory is still the newest valid one, the old item is intact, the half-written run is unlisted free space. This is the property the existing cache test proves by cutting power at every step [`maipai_packcache_core.h:9-16`]; the new test extends it with the multi-slot directory.
7. Free the scratch, send `asset_done`.

Install is refused while a game runs, while another install runs, and when the largest free internal block is under 20,000 bytes with the link up (the camera stream uses 20,000 to start and 16,000 to stop [doc docs/dev/memory-budget.md, ordered recommendation 3]; the right number for this path is [measure]).

### B4. The asset header (128 bytes, little endian)

The first 56 bytes keep the update header's field positions so the same parser and SHA code serve both; only the magic and the length of the header differ.

| Offset | Size | Field |
|---|---|---|
| 0 | 8 | magic `MPAH1` then three zero bytes |
| 8 | 4 | asset version, u32, 1 and up |
| 12 | 4 | body length, u32 |
| 16 | 32 | SHA-256 of the body |
| 48 | 8 | board id (ASCII, zero padded; all zero refused) |
| 56 | 1 | kind (index into `asset-kinds.json`) |
| 57 | 1 | body format version for that kind |
| 58 | 2 | flags: bit 0 right-to-left, bit 1 shaped script, bit 2 machine draft, bit 3 needs font pack |
| 60 | 4 | minimum firmware build, u32 |
| 64 | 40 | name (1 to 40 of letters, digits, space, dot, dash, underscore, first a letter or digit: the rule of `tpk_name_ok`, `maipai_pack_core.h:48-60`) |
| 104 | 8 | code (for a language the code such as `pl`; for a font the script) |
| 112 | 4 | bytes of PSRAM the item needs while loaded, u32 (so the dashboard and the unit can budget without loading) |
| 116 | 4 | bytes of flash the item occupies, rounded to sectors, u32 |
| 120 | 8 | reserved, zero |

Files next to the body: `<name>.mab` (body), `<name>.mah` (these 128 bytes), `<name>.mah.sig` (Ed25519 over the 128 bytes, 64 bytes). The `.mah.sig` name parallels `.hdr.sig` of the update [doc docs/plan/signed-update-header.md "Files"]. The body hash and length sit inside the signed header, so one signature covers the body.

Trust by kind (a decision to confirm, see E):

- Signed by the release key, required: language, font, game, sound, phrase, style, wake. Games already follow this rule [`maipai_games_core.h:604-620`].
- Owner-made content: look (picture faces and character packs are made from the owner's own pictures, so the release key cannot sign them). Proposal: accepted with SHA-256 and length only, and only over the paired host link; once the encrypted link is the default (decision 13, [doc docs/plan/link-key-exchange.md]) the link itself authenticates the sender. Until then this is exactly today's behavior for the `look` type. This is a credentials-adjacent choice, so it is listed as an open question for the owner, not decided here.

### B5. Tools

All answers keep the pair `error` and `error_es` and a `code`, like `self.pack.*` [`maipai_pack_core.h:195-250`]. The existing `self.pack.*` tools stay as aliases for the kinds that map one to one (look, filler, language words, phrase) until the host migrates; they are removed in a later release.

| Tool | Arguments | Answer |
|---|---|---|
| `self.assets.list` | none | `{ok, v:1, region_bytes, free_bytes, dir_ok, kinds:[{kind, max_slots, max_item_bytes, active_slot, items:[{slot, name, code, version, bytes, sha8, active, loaded, state:"ok"\|"damaged", psram_bytes}]}]}` |
| `self.assets.install` | `kind, slot (or -1 for the first free), header_b64, sig_b64` | `{ok, slot, accept_bytes, piece_bytes}` then pieces and commit |
| `self.assets.data` | `at, b64` (2,048 raw bytes a piece, the size the picture faces already use [doc docs/design/picture-faces-2026-11-16.md, protocol]) | `{ok, got}` |
| `self.assets.commit` | none | `{ok, slot}` after the hash, read-back and directory flip |
| `self.assets.remove` | `kind, slot` | `{ok}`: one directory write, no erase; space frees at the next install |
| `self.assets.swap` | `kind, slot` | `{ok, active}`: one directory write that changes the active slot, then the consumer reloads. No data written. This is the common user action in decision 17. |
| `self.assets.abort` | none | `{ok}`: drops an install in flight |

### B6. Host protocol and failure behavior

Events from the unit use the existing `device_events_push` path [`maipai_games.cc:938`, `maipai_update.cc:61-65`]. All are small JSON:

- `assets_state` in the hello: per kind the active item's name and `sha8`, plus `free_bytes`. The host diffs it against the dashboard's chosen set without a tool call.
- `asset_wanted {kind, code}`: the person chose something the unit does not hold (for example Polski on the first-run list). The host pushes it if paired; if not, the unit keeps English and shows the choice as pending.
- `asset_progress {kind, name, percent}` every 10 percent, modeled on `firmware_update_progress` [`maipai_update.cc:61-65`], and a screen indicator: the update cover for large installs [`maipai_update.cc:59`] or the banner row for small ones (`maipai_banner.cc`, released 2 s after use [doc docs/dev/memory-budget.md, audit table]).
- `asset_done {kind, name}` and `asset_failed {kind, name, code, error, error_es}`.

Transport choice: **push over the existing link first** (the host calls `self.assets.data`), because the path exists, resumes by offset, needs no new task and no new socket. The signed firmware update pulls over HTTP from the paired host [`maipai_update.cc:111-114`; `update_verify.h:33-37`] with a 10,240-byte internal task [`maipai_update.cc:30,149`]; copying that for assets would add a transient 10 KB internal block. Pull stays an option for font packs if push proves too slow (a 0.5 MB font is about 250 pieces, base64 adds a third; speed [measure]).

Without a host, the unit never crashes and never shows half of anything:

| Missing or damaged | Fallback |
|---|---|
| Language table | English words; the six baked first-run tables stay |
| Font a language needs | The language falls back to English as a whole (never a language with missing glyphs) |
| Style | Big eyes (the table lookup already defaults [`maipai_look_core.h:86`]) |
| Look pack | The built-in drawn face (`TPC_ST_DAMAGED` means built-in [`maipai_packcache_core.h:69`]) |
| Game, sound pack | Not listed; built-in tones and games |
| Directory unreadable | Empty set, built-ins only, `dir_corrupt` reported in the list [`maipai_packcache_core.h:75-76`] |

Boot cost: today each held pack is hashed at boot [doc comment `maipai_pack_core.h:6-8`]. A 0.5 MB font hashed every boot may be slow [measure]; proposal: verify small kinds at boot and in-place fonts once, in the background, the first time they load.

## C. Partition layout, slot sizes, wear

**No partition table change for the first two kinds.** The partition table (`partitions.csv`) is not rewritten by an OTA update, so a change reaches only freshly flashed units; keep it fixed.

Layout [read: `partitions.csv:3-9`]: `nvs` 0x9000, 16 KB; `otadata` 8 KB; `phy_init` 4 KB; `ota_0` at 0x20000 and `ota_1`, 0x4F0000 (5,177,344) each; `assets` (spiffs type, but used raw, not mounted [`maipai_packs.cc:163`: `esp_partition_find_first` by name]) at 0xA00000, 0x5F0000; `coredump` at 0xFF0000, 64 KB. Flash is 16 MB [`sdkconfig.fplain:931`].

Inside `assets` (offsets in the partition) [read from `maipai_packcache_core.h:25-30` and the built image]:

| Region | Bytes | Note |
|---|---:|---|
| Stock assets image (fonts, models, icons) | 4,463,226 | read in place |
| Margin | 189,830 | proposed home of the 8-sector directory ring (32,768) |
| Cache region: directory | 8,192 now | grows to 32,768 with the ring |
| Cache region: data, 382 sectors | 1,564,672 | the installed set |

**Pool, not fixed partitions per kind.** Slots are logical (kind and index); the 382 data sectors are one shared pool with a per-kind slot count and a per-item cap. The caps below do not add up to the pool on purpose; the manager and the dashboard enforce the sum (decision 17: "warns when a choice does not fit").

| Kind | Slots | Cap per item | Basis |
|---|---:|---:|---|
| style | 8 | 256 bytes | 30-byte struct plus name [est] |
| language | 2 | 16,384 | full table about 6 KB [est], one or two at a time (decision 18) |
| font | 1 | 800,000 | CJK 20 px estimates in D [est] |
| look | 2 | 1,000,000 total | the existing gate [`maipai_pack_core.h:35`] |
| game | 8 | 16,384 | `MG_MAX_PACK` [`maipai_games_core.h:32`] |
| sound (filler, effects) | 2 | 400,000 | existing gate [`maipai_pack_core.h:35`] |
| phrase | 1 | 150,000 | existing gate |

That is 24 slots; one more is held for `wake` later, so 25. The sum of every cap is about 2.9 MB, more than the 1.56 MB pool, so a full font plus a full look pack plus a full sound pack cannot coexist. The dashboard shows used and free bytes and refuses what does not fit.

**Atomicity and what a swap of a font costs.** Two copies of a 0.5 to 0.8 MB font cannot sit in a 1.56 MB pool beside a look pack. The existing store already handles this: it writes beside the old item when there is room, and drops the old item first when there is not, leaving the built-in set if power is cut [`maipai_packcache_core.h:265-290`]. For fonts that fallback is acceptable (Latin built-ins always work), so fonts use drop-then-write when the pool is tight. All other kinds are small enough to write beside the old item.

**Wear budget.** NOR flash sector endurance is typically about 100,000 erase cycles [est: typical figure, not in the repo; confirm from the flash part's datasheet]. Today: the two directory sectors alternate, so each sees one erase per two directory writes, and the allocator always starts at sector 0, so a heavy user wears the first sectors only [`maipai_packcache_core.h:235-258`, read]. The proposal:

1. A rotating allocation start spreads data wear over all 382 sectors. A 0.5 MB font install erases 128 sectors. Two such installs a day for ten years is about 934,000 erases over 382 sectors, about 2,450 per sector; twenty a day is about 24,500 per sector, still a quarter of the typical rating [est: arithmetic].
2. Every install writes the directory once. At 50 installs a day for ten years that is 182,500 writes: about 91,000 per sector with two sectors, which is near the typical rating, and about 22,800 per sector with a ring of 8 [est: arithmetic].
3. A rate cap on the unit: at most 8 installs an hour and 50 a day (the host honors the same caps) [est: a proposal, not measured].
4. A resend of an identical item writes nothing (`tpc_holds`, `maipai_packcache_core.h:323`), and `swap` writes only the directory.

## D. Language and font packs (decision 18)

### D1. How strings are held today

Strings are compiled tables, not data. First-run text is `words[MFR_LANG_COUNT]`, six languages of about 24 strings each, plain `const char*` in flash [`maipai_firstrun.cc:8-48`; count at `maipai_firstrun_core.h:17-23`]. Other screens pick between English and Spanish with an `s_es` flag [`maipai_more.cc:380`]. The language code list is fixed at six [`maipai_face_core.h:46,101`] and the native names are a fixed six-entry table [`maipai_apps.cc:964`]. The loadable language pack carries only 7 weekdays, 12 months and 2 chip words in plain ASCII, because the screen font "draws ASCII and the degree sign only" in that code's own words [`maipai_lang_core.h:18-19`]; whether the date and chip text can move to the basic Noto fonts, which carry Latin-1, is [measure: to read]. To make a language a pack, every user-visible string needs a stable id and one catalog: `maipai_tr(id)` returns the active table's string or the baked English one. The catalog is one definition (`schema/strings.json`, owned by the app track and shared with the dashboard) turned into an id header for the firmware. The six baked first-run tables stay: they are the built-in set decision 18 names.

### D2. Language pack format (body of an item of kind `language`)

Not a zip (no inflate, no zip walker for a 6 KB table). Fixed layout:

| Field | Size | Note |
|---|---|---|
| magic `MPLP1` | 8 | |
| string count N | 4 | u32 |
| catalog version | 4 | must equal the firmware's catalog version, else refused with a plain reason |
| font id | 8 | the script of the font item this language needs (`latin`, `cjk-sc`, `cjk-jp`, `cjk-kr`, ...), empty for the built-in Latin fonts |
| date order, weekday, month words | like `mlw_t` today | folded into the table as ids |
| offsets table | 4 bytes times N | offset of each string in the blob |
| UTF-8 blob | rest | each string zero-terminated |

The header (section B4) holds the code, flags (right-to-left, machine draft) and the signature. Completeness (complete, partial with English fallback, machine draft; decision 18d) is the percent of ids the table fills and a flag; the dashboard shows it. A table with an id missing is valid: that id falls back to English. Loaded into PSRAM by the same parse-into-idle-slot step as today [`maipai_lang.cc:21-22`]. Cost: about 6 KB flash and PSRAM per language [est], internal 0.

### D3. Font pack format (body of an item of kind `font`)

Format: the compact binary font the stock tree already loads in place [`xiaozhi-esp32/main/assets.cc:287-296`; loader `xiaozhi-fonts/src/cbin_font.c:33-80`; builder `xiaozhi-fonts/scripts/build.py`, `cbin_converter()` at line 60]. It is an LVGL 4-bit-per-pixel font produced by the font converter, then post-processed so every pointer is an offset from the start of the file. Loading allocates only the font struct, the descriptor and the character-map array; the glyph bitmaps and glyph descriptors are read from flash where they lie.

Why not the other loader in LVGL 9.5.0 (`lv_binfont_create_from_buffer`, `lvgl/src/font/binfont_loader/lv_binfont_loader.h:55`): it allocates and copies the whole glyph bitmap and the tables into the heap [`lv_binfont_loader.c:339,409-412`], so it costs the full pack size in RAM. For a 0.5 MB font that is not acceptable on internal RAM and wasteful in PSRAM.

Mapped in place from the slot (zero internal RAM beyond the 0.5 KB above, zero PSRAM) is the default. Copying to PSRAM is an option when draw rate from flash proves too slow [measure; the face redraws 20 times a second at best, `docs/design/picture-faces-2026-11-16.md`]. PSRAM is available (lowest above 6,000,000 bytes [gate]).

Compression: LVGL's compressed-bitmap path is off in this build (`# CONFIG_LV_USE_FONT_COMPRESSED is not set`, [`sdkconfig.fplain:5869`]) and the glyph cache is zero (`CONFIG_LV_CACHE_DEF_SIZE=0`, [`sdkconfig.fplain:5716`]). The stock fonts are built with `--no-compress` [header of `font_noto_sans_basic_16_4.c`]. Proposal: ship uncompressed; flash is cheaper than the added decoder code and the per-glyph decode. If a size problem appears, enabling compression is a config switch plus code size [measure both].

Glyph coverage and cost per pack (estimates; the playground builds the real packs and measures them):

- Measured anchor: the stock common font is 1,287,460 bytes for 6,845 glyphs at 20 px, 4 bpp, uncompressed. Latin glyphs average 114.8 bytes at 20 px and 75.3 at 16 px [measured from the basic `.c` files]. Han average about 210 bytes at 20 px [est: (1,287,460 minus 1,587 non-Han glyphs times 115) divided by 5,258] and about 134 at 16 px [est: times 0.64, the area ratio, and the Latin ratio 75.3 over 114.8 is 0.66].
- Chinese Simplified, 3,500 common characters: about 735 KB at 20 px, 470 KB at 16 px [est].
- Japanese, 2,136 jōyō kanji plus 147 kana: about 480 KB at 20 px, 307 KB at 16 px [est].
- Korean, 2,350 syllables: about 490 KB at 20 px, 316 KB at 16 px [est: the common set holds 464 Hangul].
- A UI-only subset (every character in the language's own strings plus the 2,500 most common): a few hundred KB [est].
- Flash: the sizes above, in one font slot (cap 800,000). PSRAM: 0 in place; the full size if copied. Internal about 0 (under 0.5 KB, freed on release).
- Two sizes (16 and 20 px) double the cost. Proposal: one size in the pack (20 px, the subtitle size [`maipai_subtitles.cc:20`]) and draw smaller text with the same font scaled by layout, not by a second font [to measure legibility on the panel].

### D4. What the LVGL in the tree supports

LVGL 9.5.0 [`managed_components/lvgl__lvgl/idf_component.yml:9`], UTF-8 text [`sdkconfig.fplain:5882`].

| Need | State | Cost |
|---|---|---|
| CJK line breaking | Works for Han, kana, full-width forms and CJK punctuation: each is treated as a breakable word [`lvgl/src/misc/lv_text_private.h:167-206`, `lv_text.c:286-288`]. Hangul is not in that list, which is right for Korean written with spaces. No line-start or line-end punctuation rules (kinsoku) exist in `lvgl/src` [read: grep found none], so a closing mark can start a line [measure on screen] | none |
| Hangul and kana drawing | Only a font question; the glyphs must be in the pack | in the font |
| Right-to-left ordering (`LV_USE_BIDI`) | Off [`sdkconfig.fplain:5892`]. Source is `lv_bidi.c`, 21,559 bytes of source | compiled flash [measure], plus a temporary buffer per label |
| Arabic and Persian letter forms (`LV_USE_ARABIC_PERSIAN_CHARS`) | Off [`sdkconfig.fplain:5894`]. `lv_text_ap.c`, 10,094 bytes of source, maps letters to presentation forms | compiled flash [measure]. The fonts in the tree do not carry those forms: the common font has 1 codepoint of U+FE70 to U+FEFF and none of U+FB50 to U+FDFF [measured from `charsets/common.json`], so an Arabic pack needs its own font with about 100 form glyphs [est] |
| Devanagari and other shaped scripts | No shaping code in `lvgl/src/misc` [read: grep of `lv_text.h` for shaping found none] | out for v1, as decision 18 allows |
| Hebrew | Needs BIDI on (or reversed storage) and glyphs: neither the basic nor the common font has U+0590 to U+05FF [measured] | tier 3 |
| Glyph cache | Zero [`sdkconfig.fplain:5716`] | none |

So tier 1 (Latin) needs no engine change, tier 2 (Chinese, Japanese, Korean) needs a font pack and no engine change, and tier 3 needs BIDI, Arabic forms and a font with those forms; Devanagari stays out.

### D5. The first-run screen before any pack is installed

The list must show each language in its own script with nothing installed. The first screen already prints a header line "Hello · Hola · Bonjour · Hallo · Olá · Ciao" [`maipai_firstrun.cc:30`], all Latin.

Proposed 12 languages for tiers 1: the six built in (English, Español, Français, Deutsch, Português, Italiano) plus Nederlands, Polski, Svenska, Dansk, Türkçe, Čeština. Tier 2 names: 中文, 日本語, 한국어.

- **The 12 Latin names need no new glyph.** Their 31 distinct letters are all in the basic 20 px font [measured against the glyph list of `font_noto_sans_basic_20_4.c`]. Cost: about 100 bytes of text.
- **The three CJK names need 8 distinct glyphs; 5 are missing from the basic font** (文, 日, 語, 국, 어; 中 and 한 are present) [measured against `charsets/basic.json`]. The stock common font has all 8, so the names would render today if that font stayed mapped, but it is the 1.29 MB item a font pack should replace, so do not rely on it.
- **Option 1, a baked subset of the missing glyphs only.** 5 glyphs at the common font's measured average of 188 bytes each is about 0.95 KB, plus tables about 100 bytes: **about 1 KB** [est]. It is one extra font object chained as a fallback of the label font (LVGL `fallback` pointer) and read in place.
- **Option 2, small bitmaps.** Each name as a 20 px high 4-bit alpha image: widths of about 40, 60 and 60 px for the three names give 400, 600 and 600 bytes, **about 1.6 KB** [est], not reusable, fixed size.
- **Verdict: option 1 is cheaper and reusable for the CJK names.** For the names that need shaping (Arabic, Hindi) there is no engine, so use a pre-rendered bitmap per name: a 50 by 20 px, 4-bit alpha image is about 500 bytes each, about 1 KB for the two [est]. A hybrid is the smallest. Real numbers are [measure] from the converter in the playground.

### D6. Latin Extended-A letters the current fonts lack

Method: parse the glyph lists of `font_noto_sans_basic_{16_4,20_4}.c` (890 glyphs each; the two sizes carry the same set; generated by the font converter from the `noto-sans-basic` source with the `basic` charset, `managed_components/78__xiaozhi-fonts/charsets/basic.json`, 24 characters of the request unavailable in the source font). The fonts that MaiPai screens draw with are those two [`maipai_ui_style.h:5-10`], not `font_noto_sans_common` (see section A).

Letters missing, by language (measured):

- Polish: Ą, Ć, Ę, Ń, ń, Ś, Ź, Ż (8). Present: ą ć ę ł Ł ó Ó ś ź ż.
- Czech: Ď, Ě, Ň, ň, Ř, Š, Ť, Ů, Ž (9). Present: Č and every other lowercase letter. The native name Čeština needs only Č and š, both present.
- Turkish: Ğ, İ (2). Present: ğ ı ş Ş ç Ç ö Ö ü Ü.
- Hungarian, not in the 12: Ő, Ű, ű (3).
- Swedish, Danish, Dutch, Norwegian: no missing letter (Latin-1).
- Total for Polish, Czech and Turkish: 19 letters (Hungarian would make 22).

Flash cost to add them to the two sizes: 19 glyphs at 114.8 bytes (20 px) and 75.3 bytes (16 px) averages is about 2.2 KB and 1.4 KB of bitmap, plus about 0.4 KB of glyph descriptors and one more character-map range: **about 4 KB in total** [est: averages from the measured glyph sizes]. With Hungarian, about 4.6 KB [est]. These are capital letters and a few lowercase, which are usually of average density, so the average is a fair guide. The playground measures this by running the font converter with the added codepoints and reading the compiled size. Cheaper than any pack, so the Latin-2 letters should be baked in for the tier-1 languages, not shipped per language.

## E. First two kinds, the app track, the playground

### E1. Implement first: languages and faces (styles)

Why these two: together they exercise every new part with the least risk. **Languages** exercise the header and signature, the multi-slot directory, the string catalog, the first-run screen and (later) the font hook, and they are the owner's example. **Face styles** exercise the same machinery with a 40-byte item, `swap` as a directory-only action, and a visible result on the face the person sees every day; the existing look pack (pictures) follows as the third kind with its trust rule.

Proposed slot counts: language **2** (cap 16,384 each), style **8** (cap 256 each), then look **2** (1,000,000 total), font **1** (cap 800,000), game **8** (16,384), sound **2** (400,000), phrase **1** (150,000). Overlays, personas and icons are not installed-set kinds in v1: overlays are code (a preset as data can follow, 256 bytes each [est]), personas are host-only, icons are baked and read in place.

Steps (each a lane with a Placement line and a verdict):

1. `maipai_assets_core.h` with the header parse (reuse `muh_*`), the directory with ring and slots, a RAM flash that cuts power at every step; host test. REBUILD on the pack cache (old code as spec and test).
2. Signature path and `self.assets.*` tools; error pairs.
3. Language consumer: catalog ids, `maipai_tr`, table load, the first-run list in own scripts. Unit tests plus the playground screen.
4. Style consumer: a style row from a slot, ids 16 and up beside the 11 existing style numbers [`maipai_face_core.h:29`], saved style by slot name.
5. Then look, then font (with the CJK pack and the fallback names), then game and sound.

Open questions for the owner (answers change nothing above until given):

1. Do owner-made pictures need a household signature, or is SHA-256 over the encrypted link enough (B4)? Recommendation: enough, once the link is encrypted by default.
2. Reclaim the stock common font (1.29 MB) and seven large icons (0.59 MB) to enlarge the pool by up to 1.9 MB? It needs the assets image reflashed over USB on units already out, so only after measuring that the pool is too small [measure; check first that no MaiPai screen draws with the stock font].

### E2. For the app track (host and dashboard)

- **Library and signer.** The host holds the library of installable items and signs catalog items with the release key at build time, producing `<name>.mab`, `.mah`, `.mah.sig` (B4). It never signs with a key the unit does not trust; owner-made packs (pictures) go unsigned under the trust rule above.
- **Dashboard.** One page per unit. Per kind: slots used out of slots available, each item with its flash and PSRAM cost (from the header fields, no unit call needed), the bytes free in the pool, and a plain warning when a choice does not fit, naming what to remove (decision 17). A "swap" is one action. Defaults fill the slots on first run: the person's language, the default style, a starter set of games.
- **Language rows** show completeness (complete, partial with English fallback, machine draft; decision 18d) and the script tier, and say when a font pack is required and its size.
- **Sync.** On hello the host reads `assets_state`, diffs it with the chosen set, and installs or swaps only the difference. On `asset_wanted` it installs the item if it holds it. On a unit with no host the dashboard shows the last known set as stale.
- **Transport.** Push pieces of 2,048 bytes in order; on a drop, call `self.assets.list` (the `got` offset of an install in flight is in it) and resume. A resend of an identical item writes nothing.
- The release signing key stays off the host that serves the unit; only signed files reach the host's library.

### E3. For the playground (virtual unit)

What it must fake, with the same JSON shapes as B5:

- The six tools above, answered from one shared table `schema/asset-kinds.json` (kinds, slot counts, caps, trust) so the real firmware, the host and the virtual unit cannot disagree.
- A **RAM flash** with the real geometry: 382 data sectors of 4,096 bytes, an 8-sector directory ring, erase-before-write, and a power cut injectable at every step of an install (the pattern of `packcache_core_test.c`).
- **Signature checking** with a test key pair and the real header layout: a bad signature, a wrong board id, a lower version, an oversize length, a wrong SHA-256, a wrong catalog version must each fail with the same code and the same `error` and `error_es` text as the unit.
- **Budgets enforced the way the memory table does** (decision 15g): pool bytes, per-kind caps, declared PSRAM when loaded (against the 6,000,000 byte floor), zero internal. A kind that would exceed refuses, so a feature cannot be designed past the budget.
- **Events:** `assets_state`, `asset_wanted`, `asset_progress` every 10 percent, `asset_done`, `asset_failed`, and the on-screen indicator.
- **Fallbacks:** a damaged slot shows the built-in item and `state:"damaged"` in the list.
- **Fonts:** a font item is a real converted pack; the virtual unit loads it with the same loader logic (offsets from the file start, in place) so glyph coverage and the first-run names can be rendered and judged in a picture, and the build measures the real flash cost of the Latin-2 letters and the CJK packs (section D, every [est] there becomes a measured number).

## Numbers still to measure

1. Compiled sizes: `LV_USE_BIDI`, Arabic forms, `LV_USE_FONT_COMPRESSED`.
2. Real pack sizes: a Chinese, a Japanese and a Korean pack at 20 px, with and without compression; the Latin-2 glyph additions; the first-run name glyphs.
3. Draw rate and PSRAM effect of a font read in place from flash against a copy in PSRAM.
4. Stack margin of the tool task during `esp_partition_write`; the internal block while a font object is loaded.
5. Install time per KB over the link (push) and the hash time of an in-place font at boot.
6. Whether any MaiPai screen draws with the stock common font; the flash part's real erase endurance.
7. The largest internal block during an install and the right refusal threshold.
