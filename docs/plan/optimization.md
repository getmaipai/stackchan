# Optimization: the image diet, the patch series cleanup, and the host side

Firmware track, 2026-11-18. Measure first, trim later. Part 1 is measured on the b49 build (SF48 to SF56 applied, plain image); every row says **measured** or **estimate**. Part 2 runs last, before release. Part 3 is for the app track and the playground to fill in.

## Part 1: the image diet audit (firmware)

### Where the bytes are now (measured, b49 plain)

| Region | Size | Limit | Left |
|---|---:|---:|---:|
| App image (`maipai-stackchan.bin`) | 3,746,624 B | slot 5,177,344 B | 28% |
| App image under the 20% rule | | 4,141,875 B | about 395 KB |
| Assets partition, used | 4,463,226 B | 6,225,920 B (0x5F0000) | 1,762,694 B |
| Bench image | 4,386,928 B | | 15% |

App image by archive (measured, `esp_idf_size`, flash code plus flash data): `libmain` (our code and the stock app) 868,133; LVGL 332,874; `libesp_stdio` 253,733 (one object, `stdio_vfs.c.obj`, looks mis-attributed: to inspect in the map before anything is claimed); the stock fonts library 248,167 (two Noto "basic" LVGL fonts, 122,896 and 87,786, in app flash); the deep-learning library 189,391 (102,930 in one convolution object); C++ runtime 185,142; audio codecs 170,867; Wi-Fi core 161,422; crypto 120,631; audio processing 83,153; supplicant 70,467; the TCP stack 66,116; our link library 54,835; image effects 50,998.

Assets partition by item (measured): wake-word models 2,469,827; the stock Noto "common 20" font 1,287,460; seven stock app icons 84,612 each (592,284 together); setup front view 58,980; app-center background 29,218; small icons (wifi, battery, indicators, bell) about 25,000.

### Items, in order (cheap and safe first)

| # | Item | Saves | Basis | Risk | Test | Order |
|---|---|---:|---|---|---|---|
| 1 | Reclaim the stock "common 20" font if no screen uses it | 1,287,460 B of the assets partition | measured size; use **unconfirmed** (our screens set fonts from the compiled-in LVGL fonts; the font is loaded by the stock text path) | low | probe: log every font object the display and the screens load for a full walk of every screen (the virtual unit's screen walk lists the font each screen sets); if nothing loads it, drop it from `index.json` and rebuild the assets image | 1 |
| 2 | Drop the unused stock app icons (ai_agent, app_center, controller, ezdata, sentinel, setup; dance if the Apps wall draws its own) | up to 592,284 B of the assets partition | measured size; use to confirm with the same probe | low | screen walk: every Apps wall tile shows its icon | 2 |
| 3 | Same probe for the small icons and the front view | about 85,000 B | measured size | low | same | 2 |
| 4 | Sounds: which stock sounds ship, mono, bitrate | small (two sfx files, 16 KB of source in `main/assets/sfx`; the notification sounds listed in the build are about 20 KB) | measured sources | very low | listen test by the owner (sound tests wait for the owner) | 3 |
| 5 | The two Noto "basic" fonts in app flash (210,682 B) | up to 210 KB of app flash | measured size; use unconfirmed | medium (text could fall back to a missing glyph) | the screen walk in all six languages; a glyph-coverage check against `symbols.txt` | 4 |
| 6 | Unused glyph ranges in the fonts we keep | estimate 10 to 30 percent of each font; **not measured** | estimate | medium | glyph coverage over every string table, all languages | 4 |
| 7 | Log levels and asserts | the default level is already warning and the maximum equals it (measured in the config); asserts are enabled at level 2. Disabling asserts saves an estimate of 20 to 40 KB; it removes crash information the coredump flow uses | estimate | medium: keep asserts | memory gate and a crash test | 5 |
| 8 | Compiler flags | the optimization is already size (`-Os`, measured in the config). Per-component `-O2` for hot paths would add size; no saving there. LTO: feasible for our own `main` component only, estimate 3 to 8 percent of `libmain` (30 to 70 KB), a risk to the PSRAM-stack lint and to the function sections the lint reads | estimate | medium | full replay, memory gate, the PSRAM review test | 6 |
| 9 | sdkconfig trimming: unused components of the stock app (the cellular module support, unused display and touch drivers, the stock OTA server path, unused protocol code, the many board drivers in `managed_components`) | not measurable by reading: the linker already drops unreferenced code. Real savings come from Kconfig switches that remove a feature; candidates are listed by `scripts/off-cost.sh` (landed): run it per switch for the exact bytes | measure with `off-cost.sh` | low per switch | gate plus the plain boot proof | 3 |
| 10 | Duplicate string literals and tables (language tables, tool descriptions) | estimate 5 to 20 KB; the tool descriptions are the longest strings in `hal_mcp.cpp` | estimate | low | `strings` diff before and after, the tools-schema check | 5 |
| 11 | Image and sprite compression (indexed colors, dedupe): the seven app icons are identical in size (84,612 B), so they are raw 16-bit; indexing would cut each to about a third | about 390,000 B if they are kept | measured size; ratio estimate | medium (colors) | golden screens | only if item 2 keeps them |
| 12 | Partition table: app slot 5.1 MB (two OTA slots of 0x4F0000), assets 6.1 MB, coredump 64 KB | after items 1 and 2 the assets partition needs about 2.5 MB plus installed-set packs; the OTA slots cannot shrink below the 20 percent rule of the image | no saving without a layout change; a layout change needs a USB flash (never over the air), so it is a once-only decision | high | boot proof, update test | last, with the installed-set design |
| 13 | The wake-word models (2,469,827 B) | none unless we ship fewer wake words | measured size | n/a | n/a | not now |

Nothing in 1 to 3 changes the app image: it frees the **assets partition** for installed-set packs (decision 20). Items 5 to 8 and 10 shrink the app image and widen the margin under the 20 percent rule.

### Measurement before any trim

1. A **font and asset probe** (bench tool, to build): lists every assets-partition item and the font objects the screens create, so items 1 to 3 are decided by the unit, not by reading code.
2. `scripts/off-cost.sh` for each switch in item 9 (already built).
3. A map-file diff for `stdio_vfs.c.obj` before any claim about it.
4. Record the numbers in `docs/dev/memory-budget.md` and the flash rows of `schema/memory-budget.json` (the flash column), in the same commit as the change.

## Part 2: patch series cleanup (last, before release)

Today: 310 entries in `firmware/patches/ORDER`; three patches are stored with hunks in the wrong place and are repaired by a later patch (`firmware/patches/MISPLACED`: 075, 106, 107, each repaired by the base adaptation patch); several repair and revert patches exist next to the patches they repair.

Plan:

1. **Acceptance first:** `scripts/series-equal.sh OLD_ORDER NEW_ORDER` (to write): replays both series into two trees from the same pinned base and diffs the trees; the result must be byte-identical. All host tests, the plain boot proof on the unit and an unchanged or smaller image size follow.
2. **Branch and tag:** do it in a branch of the series; the old series is kept as a tag for history. The public squashed history is made at release (a decision on history, not made here).
3. **Folds:** merge each repair patch into the patch it repairs; drop reverted patches together with the patch they revert (the pair collapses to nothing); drop dead patches (code no later patch uses; found by `scripts/series-equal.sh` plus a call-graph check on the replayed tree).
4. **Misplaced hunks:** fix the three stored in the wrong place by moving each hunk into the patch where it belongs (the base adaptation patch), so the tree compiles after every patch; then `MISPLACED` is empty and the compile-every-patch bisect works again.
5. **Regroup by feature family** (face, voice, motion, lock and privacy, update, bench, apps) and give clear names and Intent lines. An Intent line says what the patch does and why, in plain words; it never describes a flaw or a mistake of an earlier version (decision rule).
6. **Order of work:** safe folds first (a fold changes no content), then regroup (changes order, so each move is re-checked), last the renames. Never during an open landing batch.

Risk: low for content (the equality script proves it), medium for the schedule: every open lane works against the series, so this runs only when no lane has unlanded patches.

## Part 3: the host side (for the app track and the playground to fill in)

Each owner adds measured numbers here, same format as Part 1.

| Item | Owner | To measure |
|---|---|---|
| Web app assets and bundle | app track | gzip size per route, unused components, fonts |
| Thumbnails and screenshots | playground and app track | total bytes of `host/tests/golden` and docs images; `oxipng` and `zopfli` ratios |
| The 3D model file (glb) | model session | filled in below (2026-11-18) |
| Python wheel and install size | app track | installed size of the host environment; unused dependencies |
| Docs images | playground | `oxipng` over `docs/` images |

### The 3D model file (measured 2026-11-18, model session)

`scripts/virtual-unit/model/stackchan.glb`, built by `make_body.py`: **2,127,368 B** on disk, **763,030 B** with gzip (what a static host sends). 65,258 triangles, 89 nodes, 51 materials, no pictures inside. Where the bytes are (measured): positions 814,224; normals 814,224; indices 391,548; the JSON part 107,312. By mesh: head 770,448; base 638,244; holder 281,556; every drawn detail together under 200,000. So the maker's structure meshes are 80 percent of the file; the details added since are a small part.

| # | Option | Size after | Basis | Cost | Verdict |
|---|---|---:|---|---|---|
| 1 | Send as is, gzip on the host | 763,030 B on the wire | measured | none; about 0.6 s at 10 Mbit/s | fine for the local viewer, which reads it from disk |
| 2 | Quantize: positions as 16-bit, normals as 8-bit (`KHR_mesh_quantization`) | 1,313,144 B on disk, 527,759 B gzip | measured on a prototype built in memory, not shipped | no decoder script: the view has its own small reader and would read the two smaller number types (about 10 lines). Steps of about 1.2 micrometers on an 80 mm part: no visible change | **take this for the web copy** |
| 3 | meshopt compression | estimate 300,000 to 400,000 B | estimate, not built | needs its decoder, one self-hosted script of about 30 KB; the view's reader would have to hand buffers to it | not worth a second script for one file |
| 4 | Draco compression | estimate 250,000 B | estimate, not built | its decoder is about 300 KB and, for three.js r128, an example script that would have to be self-hosted; the decoder outweighs the saving | no |
| 5 | Thin the structure meshes (fewer triangles in the shell, base and holder) | not measured; they are 80 percent of the file | estimate | needs a mesh simplifier (none in the standard library) and a new check that holes and openings survive | only if 2 is not enough |
| 6 | Leave the inside parts out of a web copy | under 60,000 B saved | measured (sum of the inside nodes) | Show inside would have nothing to show | no |
| 7 | Share materials, drop unused nodes | under 20,000 B | measured: no node is unused; the 12 light materials are needed one each | none | no gain |

**Target for the static Pages viewer:** at most 600,000 B on the wire. Option 2 meets it (527,759 B) with no decoder and no visible change. Keep the full file for the local viewer and tests; build the web copy from the same generator (`make_body.py --lite`, to write, deterministic like the full one) so the two cannot drift. Not built yet: this section is the measurement only.

### Host rows filled by the app track (2026-11-18, measured on the development Mac with `scripts/host-footprint.py --run`)

Numbers come from a clean install of the host package (what a friend gets: `.runs/e2e-venv`), not the development environment (which also holds the Reachy and GStreamer extras, 1.4 GB, and is not shipped).

| Item | Measured now | Proposed saving | Risk | Test |
|---|---|---|---|---|
| Installed Python size (clean install) | 266.7 MB: onnxruntime 78.2, scipy 70.2, av 54.6, numpy 20.6, cryptography 10.9, our code 6.3 | scipy is used for audio resampling only (check with a grep): replace with numpy or `av`'s resampler and drop up to 70 MB; onnxruntime is needed only by the wake word, face models and voice models: make it an extra loaded when one is on (already lazy where a package is off) | medium: resampling quality must stay the same | a golden test of the resampled audio before and after; the e2e spoken turn |
| Import time | `maipai_body.config` 0.14 s, `maipai_body.app` 2.2 s | find the top five slow imports with `-X importtime`; make heavy modules (numpy, av, onnxruntime, scipy) lazy where a feature is off | low | a test that importing `maipai_body.app` does not import `onnxruntime` or `scipy` when no model is configured |
| Idle host, no robot connected | RSS 194 MB, CPU 0.0 percent average over 10 s, ready in under 10 s | the same lazy imports bring RSS down; the number with 1, 2 and 10 units is not measured here (needs the virtual rig with many instances) | low | `host-footprint.py --run` in the release report with a ceiling |
| Settings page | 246,166 bytes of HTML, CSS and JS in one response, 72,568 bytes gzipped | serve it with `Content-Encoding: gzip` (and a long cache for the immutable parts): saves 173 KB per load, the biggest win on a phone | low: the server must still serve a client that does not accept gzip | a route test with and without `Accept-Encoding` |
| Other pages | Brain 7.9 KB, On my robot 6.2 KB, Health 0.8 KB | none needed | none | n/a |
| Docs images | 1,724,027 bytes (1,643,837 of them PNG); golden frames 575,937 bytes | lossless recompression with `oxipng -o4` or `zopflipng`: the tool is not installed on this Mac, so no ratio is measured here; typical 10 to 30 percent | none if lossless; a script must refuse a lossy tool | a test that every recompressed PNG decodes to identical pixels |
| Web flasher assets | 347,329 bytes, of which the vendored esptool-js is 324,536 | already minified; serve gzip | low | none beyond the gzip route test |
| Asset service cache | no cache: each request reads the pack from the library; peak memory is one pack (at most 1 MB) | none | n/a | n/a |
| Local stack downloads | small 637,373,182 bytes (runtime, 0.5B model, Moonshine, Piper); better 1,263,293,886 | the small model is already the smallest that holds a conversation; no further saving | n/a | the catalog test pins the sizes |
| Logs and databases | the log rotates (5 files of 5 MB, 25 MB at most); the host's JSON files (pairing, installed sets, update builds, notes) are each a few KB and grow only with people and units | cap the notes file count already enforced (200 per person); nothing else grows without bound | none | `test_rotating_log` |
| Release report | none yet | `scripts/host-footprint.py` prints every number above (`--json` for the report; `--run` starts the host for 10 s); add it to `scripts/release-report.py` | none | the script runs in `scripts/check.sh --docs`? no: it runs in the release step only |
