# Packs for fillers, languages and offline phrases, 2026-11-17

Placement: unit firmware (patches `K10` to `K13`) and host (`packs.py`, `pack_auto.py`, `language_packs.py`, `phrase_packs.py`,
`unit_polish.py`, the settings page). Tree: `~/esp/stackchan-rebase/packs2` (a copy of `final3`, then K10 to K13). Nothing is
committed. The brief is the owner's list of 2026-11-16 ("one pack loader for every optional data set", "filler sounds", "While it
thinks") in `.runs/brief-faces-polish.md`.

Where it is: patches, host code, tests and this note are files in the working tree of this repo. The firmware is built (bench and
plain images) and was on the owned unit only as a bench image during the windows below; the unit is back on the integration 2
plain image. Nothing is on GitHub `main`, in a release or on the live hub.

## What was missing and what was built

| Item | State before | Built |
|---|---|---|
| 1 Filler pack, host push | The unit had the loader (TB02), the filler rule (TB03), and the host a generator and an explicit "use this pack" choice. Nothing chose or sent the pack by itself; changing "While it thinks" sent nothing. | `pack_auto.AutoPacks` works out the pack each unit should hold from its own settings. `PackService.sync` sends it on connect, `sync_types` sends or drops it when a setting that decides it changes (saved in the background so a save never waits on a push). The filler pack is held only while "While it thinks" is a phrase; a unit set to none or a tone holds none. |
| 2 Language packs | Six languages of screen words compiled into the image (U06). | English only stays built in. French, German, Portuguese, Italian and Spanish are language packs the host ships in its library and sends when the unit's screen language is set. Settings page: a Language card (install state, size, switch) and a Packs card with the real state. |
| 3 Offline phrases | Sixteen clips embedded in the image (V02), one voice and language. | A seventh pack type, `phrase`. The host renders the sixteen sentences with the household's own voice (the local speech server the replies use), encodes Ogg Opus like the image's clips, and sends the pack that matches the unit's language and voice. The clips in the image stay as the per-clip fallback. |
| 4 Sound and dance packs | Types exist in the loader and the cache. | Documented below; no consumer built. |
| 5 Tests | Core tests for the receiver, cache and zip walker (TB02). | New cores, the host against the firmware's own C code, damaged packs, a push cut at every call, power cuts at every flash operation, a reboot, a damaged cache. |

## Firmware patches

| Patch | What |
|---|---|
| `K10` | Pack type 7, `phrase` (gate 150,000 bytes). The cache directory is format 2; a format 1 directory (six types, written by units flashed with TB02) is still read, so a held pack survives the update. `maipai_inflate.h`: raw deflate with the decompressor state in PSRAM (see "A crash found on the unit"). |
| `K11` | Language pack: `maipai_lang_core.h` (the `words.txt` reader and English words), `maipai_lang.{h,cc}` (two 181 byte PSRAM slots, one atomic switch). The clock face date line and the timer chip words read the pack of the face's language, else English. |
| `K12` | Phrase pack: `maipai_phrasepack_core.h` (zip to one PSRAM block and a clip table), `maipai_phrasepack.{h,cc}`. The wake path says the pack's clip, else the image's clip, else the tone, per clip. `MAIPAI_OFFLINE_PHRASES_EMBED` (default y) keeps the clips in the image. |
| `K13` | The loader gives language and phrase packs to their users, applies a cached one at boot, and reports `lang` and `clips` in `self.pack.status`. The filler reader uses the K10 inflate helper. |

`ORDER` has K10 to K13 after `FI06`. Replay: all of ORDER from `O03` onward applies to a copy of the `final3` replay tree, and the
files these patches own are byte for byte the files of the work tree (`cmp`).

### The unit side of item 1 needed nothing new

TB03 already has the rule: `filler_mode` none, tone (default) or phrase, `filler_wait_s` 0.2 to 1.5 s (default 0.4), one filler per
turn, never while the robot speaks, silenced by the hard mute, "sounds off", quiet hours and full quiet, never the same sound
twice in a row. `filler_core_test.c` covers it. What was missing was the host half: choosing, sending and dropping the pack.

## Which pack a unit holds (host)

A person's explicit choice (`ActiveStore`) always wins. For the three managed types with no explicit choice:

- `language`: the screen-language pack of the face language; none for English.
- `filler`: the filler sounds of the language, only while "While it thinks" is a phrase; English sounds serve a language that has
  no set of its own (hmm and ah are not words).
- `phrase`: the pack made for the unit's language, preferring the household's voice; none when the library has no set for that
  language (the unit then says the clips in its image).

`PackService.sync` runs on connect: for each managed type it asks the unit what it holds (`self.pack.status`), sends the wanted
pack when the checksum differs, and removes a pack that is no longer wanted. `sync_types(kinds)` does the same for the types a
setting touches: the screen language (face save) moves language, phrase and filler; "While it thinks" moves filler. A unit that is
off or has no pack tools keeps the choice and gets it on connect; nothing raises. A pack the unit already holds (same SHA-256) is
not sent again, and the unit's cache does not rewrite a pack it already holds.

## Language packs

Format: a zip with one file, `words.txt`, of `key=value` lines: `lang`, `order` (dmy or mdy), `weekdays` (Sunday first, seven words),
`months` (twelve), `alarm`, `timer`. Unknown keys are ignored. The unit refuses the whole file for a missing key, a wrong count, a
bad code or a word over 7 letters (11 for the two chip words) and keeps the words it had.

Size: 223 to 228 bytes each, against the 200,000 byte gate.

### Font coverage: which accented letters render

None. The build's screen text is LVGL's built-in Montserrat 14, 16 and 20. Their character maps hold 0x20 to 0x7E (ASCII) and, from
0xB0, the degree sign and the symbol glyphs (`lv_font_montserrat_16.c`: one range of 95 characters at 32, then a sparse list that starts at 176). Latin-1
letters such as é, ñ, ü and ç are not in the maps, so a pack that carried one would draw a box. The pack reader therefore refuses
any byte outside ASCII, and the host folds accents before it builds a pack (`unit_extras.screen_text`; août reads "aou").
Spoken text keeps every accent; only the unit's own screen is plain. A Latin-1 glyph set (about 90 glyphs per size) would be
a font pack of its own, a later item.

### Flash and internal RAM saved by removing the compiled-in tables

Measured on the two plain builds (`final3` and this tree, both from `idf.py` ELF section sizes):

| | final3 plain | This tree plain | Change |
|---|---|---|---|
| `.rodata` of `maipai_face.cc.obj` (the only file that held the tables) | 5,461 bytes | 4,792 bytes | -669 bytes of flash |
| Static internal RAM, `.dram0.data` | 33,276 | 33,276 | 0 |
| Static internal RAM, `.dram0.bss` | 44,144 | 44,192 | +48 (state of the new readers) |
| Flash code, `.flash.text` | 2,410,004 | 2,415,264 | +5,260 |
| Flash data, `.flash.rodata` | 828,228 | 828,260 | +32 |
| App image | 3,445,184 bytes | 3,450,672 bytes | +5,488 (33.4 percent of the slot still free) |

The compiled-in tables were `static const`, so they sat in flash: removing them saves no internal RAM. The image grew, not
shrank, because the pack readers, the phrase table and the loader glue cost more than the 669 bytes of words they replace. Moving
the *words* out of the image was never going to save memory: they were under 700 bytes. The point is the mechanism (one loader, a
new language is data, not a flash), not the bytes. The larger saving is optional: `MAIPAI_OFFLINE_PHRASES_EMBED=n` removes the
sixteen image clips, 76,003 bytes of flash (the files' own size; this variant was not built), and leaves the phrase pack as the
only source.

Not moved: the word-reaction table (U02, about 1.1 KB of internal RAM) carries words in six languages and is not "screen words";
it is the next candidate for a pack type.

## Offline phrases

The pack is a zip of the image's sixteen file names, `ph_<group>_<n>.ogg` (groups `no_wifi` 4, `no_host` 4, `refused` 3,
`connecting` 3, `back` 2), stored with no further compression, plus an `index.json` the unit ignores. The host builds it from the
sentences of the image's clips (English, from `phrases.json`) or a Spanish set written for this module; a language with no set
has no pack. Encoding is `ffmpeg` with libopus, 16 kHz mono, 24 kbps, 60 ms frames, the same as the image's clips (the OpusHead
bytes match). A real run with the local speech server: English 78,194 bytes, Spanish 103,910 bytes, each 16 clips in under 4
seconds. The unit keeps the block in PSRAM (the clips are copied), saves the pack to the flash cache, and takes a clip from the
pack first, then from the image, then plays the tone.

## Sound and dance packs (item 4): interface only

The loader already has both types (`sound`, gate 400,000 bytes; `dance`, gate 100,000 bytes), stores them in the cache and reports
them in `self.pack.status`. Neither has a consumer on the unit, and neither is little work:

- A sound pack would be a zip of `.ogg` files and an `index.json` naming each sound. Playing one means `maipai_sounds.cc`
  (`play_named`) looking a name up after the five built-in ones, and giving it a policy class in `ms_sound_from_name` so night,
  "sounds off" and the mute decide it. That touches the policy core and its tests.
- A dance pack would be a zip with one step table in the format of `maipai_dances_core.h`. The unit would have to validate every
  angle and timing against the servo limits before it ran a table from outside the image, a safety-relevant reader of its own.

Both fit the loader as it is. The consumer is the work, so they were left.

## Settings page

- Packs: the library (import, export, delete, size meter) and one row per kind for this unit, with what it should hold, what the
  unit says it holds (from `self.pack.status`: held, name, size, "kept after a restart", damaged), and the choice (Automatic for
  language, filler and phrase). "Send to the robot now" runs `packs/sync`.
- Language: one row per language with the pack size ("built in" for English), whether it is on the robot, and the switch
  (it saves the face language, and the host sends the pack in the background). A damaged cache shows a notice.
- Offline phrases: "Make them with my voice" (progress bar, then it sends), what is made, how many clips the robot holds.
- Every new string exists in English and Spanish; French, German, Portuguese and Italian read English, as the other newer cards do.

New routes: `GET unit/<id>/phrases`, `POST unit/<id>/phrases/generate`, `POST unit/<id>/packs/sync`; `GET unit/<id>/packs` now
carries `wanted`, `unit` and `rows`.

## Tests

| File | What |
|---|---|
| `host/tests/firmware/lang_core_test.c` | The words reader: all five shipped files, every refusal leaves the target untouched, 40,000 damaged files, every truncation. |
| `host/tests/firmware/phrasepack_core_test.c` | Stored and deflated zips, missing clips, non-Ogg and too small or large clips, the size cap, 6,000 damaged zips. |
| `host/tests/firmware/packcache_k_test.c` | The phrase type and gate, a format 1 directory read and upgraded, a power cut at every flash operation replacing a phrase pack, a language pack, the first write and a remove, bit flips at boot. |
| `host/tests/firmware/pack_wire_driver.c` | The fake unit is now per type, runs the firmware's language and phrase consumers, and has `power_cycle` (cache applied at boot) and `damage_cache`. |
| `host/tests/test_packs_languages_phrases.py` | The host against that unit: every shipped pack accepted and shown, refusals, damaged packs with the checksum fixed up, a push cut at every call before and after the reply, power cycle, damaged cache, the choice logic, the generator, the page routes. |
| `host/tests/test_firmware_packs2.py` | Runs the cores under the address and undefined-behavior checkers and plain, and checks `ORDER`, header lines and that only English words stay in the image. |
| `host/tests/firmware_order_cores.py` | The pure headers as the whole of `ORDER` leaves them, shared by the tests that compile cores. |

## A crash found on the unit (and fixed in K10 and K13)

The first window (bench image, serial tool path) sent a French language pack. Its `commit` never answered and the unit rebooted
(`assert failed: xQueueSemaphoreTake queue.c:1713` in the pack writer's first log line, then a second panic inside the core dump). Sending the
filler pack did the same: `commit` answered "the robot cannot read that pack" and the unit panicked. The phrase pack, whose zip
entries are stored (not deflated), went through and stayed. The cause is the same in both: a deflated zip entry (Python's `zipfile` deflates
by default) is inflated with the ROM call `tinfl_decompress_mem_to_mem`, which keeps its whole decompressor, about 11 KB, on the
caller's stack. The tool task has 4 to 8 KB, so the inflate overflowed into the heap beside the stack, and the damage showed at the
next log call. The filler reader (TB03) has the same call, so a filler pack had never loaded on a real unit; the earlier windows only
read the empty cache.

Fix: `maipai_inflate_raw` (K10) runs the same ROM decompressor with its state in PSRAM; the language reader, the phrase reader and the
filler reader use it (K11, K12, K13). The picture-face reader (`maipai_picface.cc`, two `tinfl_decompress_mem_to_mem` calls) has the
same call on whatever stack it runs on; it was proven in earlier windows and was left alone, but it is the same risk and a
follow-up should move it to the helper. A deflated entry larger than the tool stack is now the case the tests must keep: the
language pack in `test_packs_languages_phrases.py` is deflated.

The first window also gave two results for free. With the face language set to French and no pack held, the clock face drew
the English date ("Tue Nov 17", picture `clock_fr_with_pack.png`): the fallback to English works. And after a hard reset the phrase
pack was back from the flash cache with 16 clips and cache state "ok", with no host involved.

## On the real unit (bench image, serial tool path)

Unit: the owned unit on the USB cable, bench image of this tree (4,049,168 bytes; the serial tool reader and the memory line on),
never the plain image of this tree. The unit's mute, quiet and vision-off state was turned off for each clock picture (the clock face
never covers those looks) and put back each time (`priv-orig.json` equals the state after). The plain image of integration 2
(`final3`, sha256 `c1583752...1104ec`) was flashed back after each window and read back equal. Logs: `~/esp/stackchan-rebase/packs2/logs/winpk*`.

Window 2 (after the inflate fix; the first window is the crash above):

| Check | Result |
|---|---|
| Language pack, deflated `words.txt`, 224 bytes | accepted in 3 calls; status held, `lang` fr, cached true |
| Clock face with the pack, face language French | date line "mar 17 nov" (picture `clock_fr_with_pack.png`), English "Tue Nov 17" without it |
| Phrase pack (78,194 bytes, the local voice) | accepted in 30 calls; `sound_info` `pack_clips` 16 |
| Offline phrase dry run, byte count per group | image: 4,030 / 5,248 / 4,236 / 5,264 / 2,264; pack: 3,873 / 6,211 / 4,599 / 4,362 / 1,610 (no_wifi, no_host, refused, connecting, back) |
| After `self.pack.remove` of all three | status held false, fallback true for every type; the dry run reads the image's clip again (5,248 for no_host) |
| Filler pack (5 sounds, 25,886 bytes, index deflated) | accepted in 12 calls; `self.filler.status` held true, sounds 5 |
| `self.filler.play` on the muted unit | `played false, why silenced`; the `silenced` counter went 0 to 1 |
| A push cut and a bad order | out of order answers code `order`; commit before all bytes answers code `short`; the held language, phrase and filler packs are unchanged |
| Hard reset (cache applied at boot, no host involved) | within 8 s: language held, lang fr, cache ok; phrase held, 16 clips, cache ok; filler held, cache ok |
| One bit flipped in the cached language pack's data sector (flash 0xE72000) and a reset | language held false, cache "damaged", fallback true, `lang` empty; phrase and filler unaffected and held |
| The same pack sent again | held true, lang fr |
| Cache directory on the unit | format 2 |
| After clean-up | every type held false, fallback true |

Window 3 (the same bench image; the face language is set again after each reset because a `self.face.set_config` over the serial
tool path did not survive a hard reset: the language read "en" after every reset; the host path sends the saved face settings on
connect, `FaceService.sync`):

| Step | Clock face date line (pictures in `logs/winpk3`) |
|---|---|
| French pack sent this boot, face language French | "mar 17 nov" (`a_french_pack_same_boot.png`) |
| Hard reset, all three packs applied from the cache, face language set to French again | "mar 17 nov" (`b_french_from_the_cache_after_reboot.png`): the words come from the flash cache with no host |
| One bit flipped in the cached language pack, reset, face language French | "Tue Nov 17" (`c_cache_damaged_face_french_words_english.png`): the face asks for French, the pack is damaged, the unit shows English; status `cache damaged`, `fallback true`; phrase and filler still held, cache ok |
| The pack sent again | "mar 17 nov" (`d_resent_french_again.png`) |

Memory at rest (the unit's own memory line, read when the next line appears, never during a snapshot):

| State | internal_free | int_big | psram_free |
|---|---|---|---|
| Boot, no packs | 80,535 | 32,768 | 7,927,916 |
| Language, phrase and filler packs sent and held | 80,475 | 32,768 | 7,809,204 |
| After a reset, the same three applied from the cache | 80,811 | 31,744 | 7,706,096 |
| For reference, integration 2 at boot, no packs | 78,619 to 80,643 | 31,744 to 36,864 | about 7,930,000 |

Internal RAM does not move beyond the noise between lines of the same boot (gate floors: internal_free 40,000, int_big 24,000). The
packs cost PSRAM only: about 119 KB when sent (the phrase block, the filler sounds) and about 222 KB when applied at boot. The
difference is a leftover of TB02: the boot task keeps the raw zip of each cached pack next to the copy its user made (the phrase
and filler packs, about 104 KB), while the commit path frees it. PSRAM has 7.7 MB free, so it was left; freeing the raw buffer at
boot for the types whose users copy is a small follow-up.

Sizes of the images of this tree: plain 3,450,672 bytes (sha256 `97e719ad...5c29b3a`), bench 4,049,168 bytes (`4d5451bc...2146e4`). Neither plain image
of this tree was put on the unit: the unit is on the integration 2 plain image (`final3`, `c1583752...1104ec`), read back equal.

## Not verified, and follow-ups

- No spoken turn was run: the unit is muted as saved, and `self.filler.play` on it answered `silenced` (the rule working). The
  filler sound playing after the wait, over a real answer, is covered by `filler_core_test.c` and not heard on the unit.
- The host half was run against the firmware's C code and the settings page against the simulated units; the page was not opened in
  a browser and the host process on the live hub was not restarted (it still runs the code from before this work).
- A format 1 cache directory on a real unit was not tried (the unit's cache was empty before this work); the C test covers it.
- The phrase pack was never played aloud: a dry run reads the clip; the Ogg files match the image's in every header field.
- The phrase pack voice label is "default": the host has no named voice setting yet, so the "prefer the active voice" rule works
  once the packs carry a voice name.
- Follow-ups: `maipai_picface.cc` still uses the ROM inflate on the caller's stack; free the raw pack at boot; sound and dance
  consumers; word reactions as a pack type; a Latin-1 font pack so accents render; `test_stackchan_train4.py::look_core_test.c`
  fails before and after this work (it needs patch O02 and its chain stops at FI04).
