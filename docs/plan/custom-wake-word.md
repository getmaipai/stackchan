# A wake word the family chooses (feature 8e): what the unit needs

Firmware track, 2026-11-18. A design note read from the code and the ESP-SR files in the build tree. No code is written; the numbers marked "to measure" need a bench run.

## What the unit has today

- The wake word is "Hi, StackChan", the WakeNet 9 model `wn9l_histackchan_tts3` (`CONFIG_SR_WN_WN9L_HISTACKCHAN_TTS3`), run by the AFE engine. A WakeNet model is trained for one phrase by the model's maker (a training service with text-to-speech data, a lead time of days and a license step): the family cannot make one on the unit or on the host.
- The base tree already has the second detector, `CustomWakeWord` (`xiaozhi-esp32/main/audio/wake_words/custom_wake_word.cc`, selected as `WakeDetector::kMultiNet`): MultiNet, the ESP-SR command recognizer, listens for a short phrase given as text and treats a hit as the wake word. The model in the build is `mn5q8_en` (English, 8-bit, single recognition; about 2.1 MB in the model files; other English and Chinese MultiNet models exist in the component).
- Its settings come from the `assets` partition (`index.json`, section `multinet_model`): `language`, `duration` (listen window, ms), `threshold` (0 to 1) and a list of `commands`, each `{command, text, action}` with `action: "wake"` for a wake phrase. `command` is the phrase in the model's phoneme notation, `text` is what is shown. The unit registers them with `esp_mn_commands_add` and `esp_mn_commands_update` at start, so a new phrase is a data change, not a new model.
- Partition table: `assets` is a 6.0 MB data partition at 0xA00000 (SPIFFS type) that holds the model package and `index.json`; the two app slots are 4.9 MB each.

## What a family phrase needs

1. **A phrase in MultiNet notation.** English MultiNet 5 takes phoneme strings (for example "hEY mi_sTk" style), made by ESP-SR's `multinet_g2p.py` from the spelled phrase. The host does this when the family types the phrase, and shows the phrase back as text. Limits to state in the page: 2 to 4 syllables work best, a name that sounds like common speech false-triggers more, and a phrase must be tested in the home (the page should offer a "say it three times" check that reads the unit's hit counter).
2. **A threshold.** The default threshold trades missed hits against false wakes; the page offers three steps (stricter, normal, easier) that map to three thresholds, kept in `index.json`.
3. **One active wake detector.** Either the shipped "Hi, StackChan" WakeNet or the MultiNet phrase, never both at once: the AFE engine starts exactly one (`wake_detector_`). Switching needs a restart of the audio path (not a reboot); the unit says which is active in `self.version.get`.
4. **The talk-over rule still holds.** The two-hit barge-in (`maipai_barge_core.h`) counts hits from whichever detector is active; a longer phrase than the phrase's length limit `MBG_TWO_HIT_MS` cannot be said twice in a second, so the rule must be re-measured for a family phrase before barge-in is promised with it.

## How it gets onto the unit

- **Data only (recommended, v1):** the host writes a new `index.json` into the assets package and the unit receives it through the existing assets update path (the same download and check as a firmware asset, over the paired host's address, TLS when the link is encrypted). It does not need a firmware image. What the unit must verify is the open point: the update path signs images (Ed25519 header, SHA-256 of the image); an asset bundle must be covered by the same kind of signed header (a second header file `<assets>.hdr` and `.hdr.sig`, board id as for images), or a family phrase file could be pushed by anyone on the network. Until assets are signed, the phrase file must not be installed from the network; a USB flash of the assets partition is the fallback.
- **A new model (not v1):** a different WakeNet or MultiNet model means a larger assets package (hundreds of KB to a few MB) and the same signed path. A true custom WakeNet word is a vendor service and is out of scope.

## Memory and flash (to measure with `self.bench.heap_info` and a bench run of the MultiNet detector)

| Where | What | Size |
|---|---|---|
| Flash (assets) | `mn5q8_en` model files | about 2.1 MB (already in the package when the detector is built) |
| Flash (assets) | `index.json` with a few phrases | under 2 KB |
| PSRAM | MultiNet model working memory and the command graph | to measure; the model loads from the partition and its buffers sit in PSRAM (AFE already uses `AFE_MEMORY_ALLOC_MORE_PSRAM`) |
| PSRAM | the wake audio cache (`CONFIG_SEND_WAKE_WORD_DATA`, 2 seconds of 16 kHz audio) | 64 KB, only when that option is on |
| Internal | the wake-word encode task stack (already a PSRAM static stack) and the detector's per-frame buffer | to measure; expected a few KB; the plain image must keep the largest free internal block at or above the gate floor (24,000 B median) |

## Privacy and safety

The phrase list lives on the unit and is never sent anywhere; the wake audio cache stays off unless the owner turns it on. A family phrase never changes what the unit does after the wake: mute, lock and child rules apply as before (the wake handler is unchanged). A phrase that matches a stop or safety word of the unit is refused by the host page.

## Decisions for the owner and the other tracks

1. v1 ships with "Hi, StackChan" only; the phrase page is an experiment behind a setting (recommended).
2. The host track writes the phoneme conversion, the three thresholds and the test counter; the firmware track adds the signed assets header check (feature 8e needs it first) and the `self.version.get` field for the active detector.
3. Before barge-in is allowed with a family phrase, measure how often a second hit lands inside `MBG_TWO_HIT_MS` for a phrase of two and of four syllables.
