# WebAssembly port: the virtual robot in a browser, no server

Status: built and checked 2026-11-18. Code: `scripts/virtual-unit/wasm/` (build, adapter layer, parity driver). Output: `docs-site/playground/` (build output, git-ignored, never committed). Placement: host-side development tool. Follows `docs/plan/wasm-spike-report.md`.

## Verdict

The whole virtual unit now runs from a static folder with no server and no outside request: the unit's own screens code (every screen the native screens renderer draws), the lock keypad and the link covers as WebAssembly, the unit's C cores as one WebAssembly module, and the virtual unit's Python (`vunit.py`, `hw.py`, `tools/*.py`, `dance_sim.py`, `scenarios.py`, `assets_sim.py`, `memory_model.py`, `host_away.py`, and the viewer's own `view.py` handlers) unchanged, in Pyodide 0.27.7. The 3D viewer (`view.html`, `view3d.js`) runs on top of it as it is.

Parity against the native virtual unit, run in headless Chromium: all 287 cases give the same result as the native run. Frames are pixel identical (same SHA-256 of the decoded pixels, no tolerance needed). Tool results, the dance sessions, the quiet schedule, the memory walk, the reconnect core and nine C cores are equal.

## What was built

| Piece | Files (all new, none of the originals edited) |
|---|---|
| Build | `site-build.sh` (targets `screens`, `cores`, `pyodide`, `site`, `all`), `gen_sdkconfig.py`, `shim_main.py`, `gen_cores.py`, `cores_all.c`, `bundle.py`, `make_page.py` |
| Adapter layer | `page/py/wasm_shim.py` (renderer pipe, core libraries), `page/py/api.py` (the viewer server's requests), `page/engine.js`, `page/bridge.js`, `page/boot.js`, `page/app.js` |
| Parity | `page/py/parity_cases.py`, `run_native.py`, `parity.js`, `page/test.html` and `page/test.js` (a harness page without the viewer) |

How each outside reach of the Python was replaced, from outside, with no edit to the original files:

- **Renderer.** `vunit.py` starts the native renderer with `subprocess.Popen` and talks to it in command lines. `wasm_shim.py` replaces `subprocess.Popen` and `subprocess.run` for the programs `render`, `lock_render` and `cover_render`: each command line goes to a fresh WebAssembly instance of that program, the lines the program prints come back, and a PNG the program writes (`snap`, `lock`, `pad`) is copied into Python's file system. The native `main()` loops read stdin until the end; `shim_main.py` makes a copy of each source in which `main()` is split into `vu_init()` and `vu_cmd(line)` (the loop body, unchanged), plus `vu_fb()` for the frame buffer. The command set, the drawing code and the output lines are the program's own.
- **Cores.** `dance_core.py` and `host_away.py` load a compiled library with `ctypes.CDLL`. `ctypes.CDLL` is replaced by a class whose functions call `cores.wasm` through the bridge; ctypes arrays and `byref` values are copied in and out. The compile steps those modules run first (`cc`, `patch`) are skipped because the cores are already built.
- **Viewer server.** `view.py`'s real `Handler` class answers `/state`, `/tools`, `/log`, `/scenarios`, `/call`, `/touch`, `/hw`, `/imu`, `/record` and `/scenario`: `api.py` builds the object the HTTP server would have built and calls `do_GET` or `do_POST`. The pump loop is `view.pump` with its `sleep` turned into a stop (one iteration per call). `/scenario` is played by a stepper on the page's clock instead of a thread. `app.js` answers the viewer's `fetch` calls and gives `view3d.js` the unit's frame wherever it asks for `/frame.png`.
- **Host code the dance session imports.** `dance_sim.py` imports `maipai_body.bodies.stackchan.dance_ladder` from `host/`. The bundle includes that file and the three small ones it needs. The real `profile.py` imports numpy and pydantic for one constant, so the bundle carries a two-line stand-in with `LED_CHANNEL_MAX` read from the real file at build time (the build stops if the constant moves).

Changes to the viewer page, all by documented text swaps in `make_page.py` that must each match exactly once: three.js from the site's own `vendor/three-r128` (self-hosted, unchanged, license kept), absolute script paths made relative, the physics switch disabled with a plain note, the "three.js did not load" message without an outside address, the link to `/about` pointing at `about.html`, and a banner. The banner says "Simulation in your browser: nothing leaves this page", shows the short affiliation wording from `docs/legal/affiliation.json` (the full wording is on `about.html` and in the banner's tooltip), and holds a language switch (English, Spanish). The page has no other choice to make before it works (owner decision 20); it is simulation only (decision 21 names live as a separate mode, not built here).

C cores in `cores.wasm` (66,515 bytes): the Python virtual unit's own wrappers (`dance/ladder_sim.c`, `dance/reconnect_sim.c`, included not copied), the spike's lock and limiter wrappers, one hand wrapper for the signed update header, and 112 generated wrappers over the headers `lock`, `motion_limit`, `listen_guard`, `update` (first-boot trial), `updatehdr`, `link_quiet`, `remote` (the remote safety rules), `sounds` (the quiet schedule), `hourly`, `touch` and `reconnect`. The generator wraps every `static inline` function whose parameters are numbers, strings, a struct held in the module, or an out value; the 20 it cannot wrap (byte buffers, struct returns) are listed in `wasm/cores.sigs.json` under `skipped`.

## Parity

Run: `bash scripts/virtual-unit/wasm/site-build.sh all`, then `python3 scripts/virtual-unit/wasm/run_native.py .runs/wasm/native-results.json` (the same cases natively, with the real ctypes libraries and renderers), then `node scripts/virtual-unit/wasm/parity.js`. Exit 0 means every case equals the native result, no request left the page and the page logged no error.

| Group | Cases | Browser equals native |
|---|---|---|
| Golden frames: 15 face and speech frames, 89 screen frames (23 status bar, pages and settings, 43 first run in 6 languages, 10 dance steps and dance session steps, 7 host-away notices, 6 Spanish screens), 5 lock screen and keypad frames, 8 link covers | 117 | 117 of 117, pixel identical |
| Committed goldens in `host/tests/golden` | 117 | 113 identical; 4 differ (see below) |
| Tool calls: every tool in `schema/tools.json` called on a fresh unit (the tool parity list), result compared whole | 154 | 154 of 154 |
| Dance: loud song in Home mode (40 s), fast and quiet songs on the unit alone (30 s each), the hand-chosen dance session (20 s); the stage every half second, a hash of every 100 ms sample of lights, overlays, notes and head | 4 | 4 of 4 |
| Quiet schedule: the tool's rule against the unit's C core on 6 windows by 96 minutes, plus the default window | 1 | 1 of 1 (and the tool and the core agree on all 576 points) |
| Memory model: the memory walk (every page, sheet, settings, overlays, music dance, first run, back to baseline each time) | 1 | 1 of 1 |
| Reconnect core through `host_away` | 1 | 1 of 1 |
| C cores called directly: lock (set, lock, keypad, wrong and right code), limiter, listen guard, first-boot trial, signed update header, remote rules, link quiet, sounds and hourly, touch | 9 | 9 of 9 |

Also checked in the page: a tool call, a tap and a swipe on the screen (the control sheet and the games wall open, as natively), a hardware control (battery to 30 percent gives `battery_limited`), the Wi-Fi button, a scenario started by name, the language switch. Python 3.12 (Pyodide) and Python 3.13 (native) give the same results.

The 4 goldens that differ from the committed files are `dance-session-4-full`, `host-away-notice-fr`, `host-away-notice-de` and `host-away-notice-pt`. The native renderer built in the same container differs from them in the same way, and the browser equals the native frame, so these goldens are out of date against the replayed firmware tree; they are not a browser difference. Whoever owns the goldens should look at them. This container's native build also needed one thing the spike did not: `gen_sdkconfig.py` writes the `CONFIG_MAIPAI_*` defaults from `main/Kconfig.projbuild` into `sdkconfig.h`, because a plain defaults file leaves the unit's lock, time zone, network test and version screens compiled out.

## Sizes

Measured on what the page fetches on its first visit, each file compressed with gzip level 6 as a static host would send it (Brotli would save about another 10 to 15 percent):

| Part | Raw | Gzip |
|---|---|---|
| Pyodide (runtime wasm 10.1 MB, Python standard library zip, loader, package list) | 13.7 MB | 5.84 MB |
| Screens renderer (`screens.wasm` 1.16 MB and its loader) | 1.23 MB | 0.50 MB |
| Unit's Python, data files and adapter (`vu-py.zip`) | 0.13 MB | 0.13 MB |
| C cores (`cores.wasm` and table) | 0.11 MB | 0.04 MB |
| 3D model (the small `stackchan.web.glb`) | 1.35 MB | 0.63 MB |
| three.js r128 | 0.60 MB | 0.15 MB |
| Viewer and page scripts, HTML | 0.20 MB | 0.06 MB |
| First-visit total | 17.5 MB | 7.0 MiB (7,362,234 bytes) |
| Lock keypad and cover renderers (`lock.wasm` 0.63 MB, `cover.wasm` 0.72 MB), fetched after the page is up | 1.35 MB | 0.53 MB |

The whole folder is 18.5 MB on disk. The Pyodide share is 79 percent of the transfer; the spike's estimate of 4 to 5 MB for Pyodide was low by about 1 MB because the standard library zip does not compress further. Trimming it is the first lever (see the estimate).

Memory in the running page: Pyodide heap 24 MB, the screens renderer 16 MB (its declared start; it can grow), `cores.wasm` 2 MB fixed, each extra renderer instance 16 MB while it exists (a unit holds one; the cover and lock instances are made when needed and dropped after use). JS heap about 25 MB. The unit-side memory gate is simulated by the memory model as before; the page does not claim anything about the unit's real RAM.

## Time

Headless Chromium 1243 in this cloud container (a shared CPU, software WebGL): an order of magnitude, not a benchmark.

| Measure | Result |
|---|---|
| Cold, page to unit ready (local server, gzip on) | 7.2 to 7.7 s in the full viewer page; the same code on the harness page without the 3D drawing is ready in 2.0 s (Pyodide 1.9 s, then 0.1 s for the cores, the renderer and the unit's Python) |
| Cached (browser keeps the files) | 7.8 to 9.1 s locally: the files are not fetched again, but the browser compiles the WebAssembly again. The time is compile and the 3D scene, not network |
| Over a real link | add the download: 7 MiB is about 6 s at 10 Mbit/s |
| Frame time, one pump step (50 ms of the unit's clock: the renderer's frames, the tools' tickers, state) | 0.85 to 1.0 ms average, 1.8 ms worst, 24 steps; painting the frame into the 3D texture is extra and not in this number |
| Fresh renderer instance (a new native-program state, module already compiled) | a few ms |
| All 287 parity cases in the page | 3.3 s |

The spike measured 37 ms for the face alone; the difference now is Pyodide (about 1.9 s here) and the viewer's 3D drawing, which is the slow part of the full page in a headless browser without a GPU. No outside request was made (0 of the page's requests left its origin, checked on every page the test opened), and there is no analytics and no font or script from another site.

## What is missing against the native playground, and what blocks each

| Missing | Blocks | Days |
|---|---|---|
| The real host (`host/maipai_body`, about 25,000 lines: asyncio, sockets, threads, subprocess) and a brain on the other end | The host is a network program. Not a candidate for the browser; a brain stays a separate peer the page could reach over a WebSocket | out of scope; WebSocket client for a brain: 1.5 |
| Voice (wake word, listening, speaking, the Talk panel) | The voice bridge is not part of the native server either; the Talk panel answers with its plain "not running" message. Browser audio and a speech engine are a separate piece and a decision | 2 to 3 plus a decision |
| The physics engine (physics mode) | `physics.js` loads an 11 MB engine from an outside address named in `THIRD-PARTY-physics-engine.json`. The page may not fetch from outside. Needs the engine vendored under its license into the site, then the same page code works | 1 |
| Live mode (the page driving a real robot) | Decision 21 keeps it a separate mode. A page served over https cannot open a plain `ws://` socket to a robot on the home network (mixed content); needs a link design | 1.5 to 3 plus a decision |
| Game boards (`games_render`) and the standalone apps program | Not linked. The games wall, timers and settings are drawn (they are in the screens renderer); the per-game boards need `.mpk` packs fetched or bundled and one more small module | 0.5 |
| Recordings saved by the Record button | They are written to the page's in-memory file system and lost on reload; no download button yet | 0.25 |
| First-load size | Pyodide's standard library and package list are loaded whole. Dropping unused standard library modules, Brotli, and a service worker cache would take the first visit well under 6 MB and make repeat visits skip compile work with the browser's code cache | 1 |
| The face profile | The page uses the screens renderer for everything. Natively, `profile="face"` uses a separate bare-face build. The screens renderer draws the same face pixel for pixel on 100 of the 104 frames the face scenarios cover (the other 4 are the stale goldens above), so nothing is lost, but the two builds are not the same program | 0 |
| Build in CI | `parity.js` needs Emscripten 3.1.74, the replayed firmware tree, LVGL 9.5.0 and the font package from GitHub, and Playwright. Not yet a step of `scripts/test-all.sh` | 0.5 |

Estimate for everything in the table that is in scope for a first public page (physics vendored, game boards, recording download, size trim, CI step): about 3.25 days. With a brain connection over WebSocket and voice: about 7 to 8 days. Live mode adds 1.5 to 3 once decision 21's link design is made.

## Risks

- **Drift in the glue, not the rules.** The renderer and the cores are the unit's own sources, built from the same files; what can drift is `shim_main.py` (it matches the shape of each program's `main()` and stops the build with a message if the shape changes), `make_page.py` (each swap must match exactly once), `api.py` (it uses `view.py`'s names: `Handler`, `pump`, `play`, `PLAYING`, `LOCK`, `UNIT`, `HW`) and `parity_cases.py`. A change to those names stops the build or the parity run, it does not pass silently.
- **Toolchain pins.** Emscripten 3.1.74, LVGL 9.5.0 (commit `85aa60d1`), the font package (commit `d45dbc64`, from its GitHub repository), zlib 1.3.1, Pyodide 0.27.7 (SHA-256 `9bc8f127...41be8`, checked by the build). The IDF component registry is not reachable from the cloud container, so the build depends on GitHub for LVGL, the fonts and zlib.
- **Pyodide 0.27.7 is Python 3.12; the native playground runs 3.13.** No difference showed in 287 cases. Move Pyodide when a 3.13 release is pinned.
- **Time passes only while a command runs in this container.** Long checks here must run in the foreground (`parity.js` takes about 3 minutes); a background copy appeared to hang for that reason. Not a property of the build.
