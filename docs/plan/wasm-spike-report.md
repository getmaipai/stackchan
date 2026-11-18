# WebAssembly spike: the virtual robot in a browser, no server

Status: spike done 2026-11-18. Code: `scripts/virtual-unit/wasm/` (`build.sh`, `face_api.cc`, `cores_api.c`, `index.html`, `page.js`, `check.js`). Placement: host-side development tool.

## Verdict

Feasible, and cheaper than expected. The unit's real face code and three real C cores run in Chromium from a static folder, with a tap changing the face. Nothing in the firmware tree had to change. Recommended path for the full port: Pyodide for the Python virtual unit, not a TypeScript port (Spike C).

## Environment

- Emscripten 3.1.74 (emsdk, `./emsdk install 3.1.74`). Not preinstalled; installs in about 1 minute from `storage.googleapis.com`.
- Firmware tree: `scripts/fw-rebuild.sh` replayed all 301 patches onto the pinned bases in this cloud container (`git clone` of the base repositories works). Its final ESP-IDF build step fails, as expected without ESP-IDF; the tree is complete before that step.
- Missing from the replay and fetched another way: the IDF component manager's `managed_components` (its registry returns 403 here). LVGL v9.5.0 came from a shallow `git clone` of its tag (the version `dependencies.lock` pins) and the font package from its GitHub repository. `sdkconfig.h` is generated from the firmware's own `sdkconfig.defaults` and `sdkconfig.bench.defaults` (`CONFIG_LV_*` lines). `build.sh` does all of this on a first run.
- Headless browser: Playwright's Chromium is present; `check.js` serves the folder, opens the page, taps the face, drives the cores, and prints JSON.

## Spike A: the face

Built from the replayed tree's own `eyes.cpp`, `mouth.cpp`, `default.cpp`, `speech_bubble.cpp`, `maipai_facefx.cc`, `hooks_new.cc` plus LVGL (about 350 C files). A 90-line C API in `face_api.cc`: `vu_init`, `vu_tick(ms)`, `vu_touch(x, y, type)`, `vu_fb` and `vu_fb_size` (RGB565), `vu_rgba` (canvas-ready), `vu_set_emotion`, `vu_speak`. The page is self-hosted, no outside script or font.

| Measure | Result |
|---|---|
| face.wasm | 557,414 bytes (221,340 gzip -9) |
| face.js loader | 16,301 bytes (5,238 gzip) |
| Cold build, LVGL plus face, 16 cores | about 40 s; face link alone 14 s |
| Fetch plus instantiate both modules (local server, headless Chromium) | 37 ms |
| Page ready after navigation | 162 ms |
| Avatar init | a few ms |
| Frame cost, `vu_tick` per 33 ms frame | 0.16 ms average, 6 ms worst (173 frames, idle face with a tap) |
| Tap | pointer events become `vu_touch`; the page showed the next emotion and the eyes turned toward the tap (`check.js`: taps 0 to 1, emotion neutral to happy, screenshot confirms) |
| External requests | none |

Frame time is the LVGL full-frame mode with a software canvas copy; the unit's partial-redraw mode is available and would cut it further. The numbers are headless Chromium on a shared container CPU, so treat them as an order of magnitude.

Beyond the face: the banner, subtitles, pages, apps and first-run sources (`maipai_banner.cc`, `maipai_subtitles.cc`, `maipai_pages.cc`, `maipai_apps.cc`, `maipai_firstrun.cc`, `hooks_banner.cc`) plus the two screen fonts compile under emcc with no change and link with the face. Trial link, not wired to the page: 910,173 bytes wasm (386,092 gzip). So the whole screens renderer is under 1 MB on the wire, as one module. The lock and cover programs (`lock_render.cc`, `cover_render.cc`, `cover_gen.py` output) were not built; they use the same LVGL and the same stubs and should follow the same pattern.

## Spike B: C cores

`cores_api.c` includes the firmware's own `maipai_lock_core.h` and `maipai_motion_limit_core.h` from the replayed tree and the existing dance wrapper `scripts/virtual-unit/dance/ladder_sim.c` (included, not copied), all behind one module: `cores.wasm` is 36,253 bytes (18,413 gzip), `cores.js` 16,267 bytes. Build time 1 s. Every function takes the time as an argument, so the page runs a fake clock.

Checked in the browser by `check.js`: lock (set code 1234, lock, keypad, four digits give `UNLOCK`; status JSON identical in shape to the unit's), movement limiter (battery 10 percent gives `battery_limited`, scale 25, speed cap 500, dance max 0), dance ladder (60 simulated seconds). PBKDF2 for the lock code (2000 rounds) ran without a noticeable pause.

Note on the ladder demo: with level 80 and no beat time constant the stage stays at 1; the climb needs the beat conditions the Python sim feeds (`dance_sim.py` SONGS). That is a page input choice, not a core problem.

The other 74 `*_core.h` headers follow the same shape (plain C, `static inline`, time passed in). A generator that wraps each header's public functions would be a small script, and `scripts/test-all.sh` already has the native harness style to compare against.

## Spike C: Python virtual unit in Pyodide (analysis, no build)

What there is: `vunit.py` 336 lines, `hw.py` 303, `tools/*.py` 1,808 lines (129 `@tool` handlers), plus `dance_core.py`, `posixtz.py`, `scenarios.py`. All standard library: `json`, `re`, `base64`, `zlib`, `hashlib`, `binascii`, `ipaddress`, `datetime`, `pathlib`, `tempfile`, `importlib`. No threads, no asyncio, no sockets, no numpy or PIL in this layer (the word "socket" in `hw.py` is a USB socket).

What breaks, with a count:

| Use | Where | Fix |
|---|---|---|
| `subprocess.Popen` of the native renderer on stdin and stdout | `vunit.py` line 77 (1 place; `scenarios.py` has 2 more in dev scenarios) | Replace the pipe with calls into the wasm face through a JS proxy (`from js import ...`). The command set (`emotion`, `speak`, `advance`, `snap`) maps one to one on `face_api.cc` plus a small PNG encode in JS or `zlib` in Python |
| `ctypes.CDLL` of a `.dylib` | `dance_core.py` | Pyodide cannot load a native library. Call `cores.wasm` through the JS proxy instead |
| Reading firmware patch files at run time to cut a header out | `dance_core.py` | Not needed once the core is wasm |
| `tempfile`, `pathlib`, `open` | 1 temp dir, 8 `Path` uses | Work on Pyodide's in-memory filesystem; bundle any data files |
| Dynamic `__import__("tools.x")` loop over a glob | `vunit.py` line 24 | Works if the `tools/` folder is unpacked into the Pyodide filesystem; or replace the glob with a generated list |
| Stdin and stdout JSON-lines server (`vunit.py serve`) | `vunit.py` | Replaced by page JS calling `call(tool, args)` directly |

The host program under `host/maipai_body` (about 25,000 lines, 121 files that use asyncio, sockets, threads or subprocess) is not part of this and should stay out of the browser. The virtual unit is the unit's side only; a brain (own LLM or Home) stays a separate network peer. If the page needs a brain, the browser can reach one by WebSocket from JS; that is a separate decision.

Pyodide cost (from its published releases, not measured here): about 8 to 10 MB of wasm plus standard library, about 4 to 5 MB over the wire with gzip, first load 2 to 5 seconds on a laptop, cached afterward. It must be self-hosted (no CDN), which the org rule requires anyway.

Work estimate for Pyodide: about 3 days (swap the renderer bridge and ctypes, unpack and import the handlers, a loader page, run the existing parity tests against the browser build).

TypeScript port of the handlers: 129 handlers and about 2,700 lines of Python (`vunit`, `hw`, `tools`, `dance_sim` logic) to rewrite and test: about 8 to 10 days, then a standing drift risk against the Python handlers that the host tests and `host/tests/test_virtual_unit_parity.py` guard today. Smaller payload (tens of KB instead of 4 to 5 MB), faster start.

Recommendation: Pyodide. One implementation of the handlers (Python), the existing parity and scenario tests stay the acceptance suite, and the 4 to 5 MB is a one-time cached download on a site that is already shipping a roughly 1 MB wasm. Choose TypeScript only if first-load size becomes the limiting factor (for example on a phone over cellular); decide that from a measured Pyodide load, which is the first thing to measure in the next step.

## What blocked, and what did not

- Nothing blocked the toolchain. Needed: Emscripten, the replayed firmware tree, LVGL and the font package from GitHub.
- The firmware replay needs network to the pinned base repositories and takes a few minutes; `build.sh` caches it in `.runs/wasm/`.
- No existing file was edited. The firmware sources compiled as they are, using the existing stubs in `scripts/fw-face-render/stub/`.

## Estimate for the full port

| Piece | Days |
|---|---|
| One renderer module for face, banner, pages, apps, lock, covers, games and overlays, with an API per screen and the unit's tap targets (`touch_shim.c`) | 3 to 4 |
| Cores: a generator for the 77 core headers, wrappers for the ones the handlers call, wasm parity against the native test harness | 2 |
| Pyodide host for the virtual unit (Spike C) | 3 |
| Static site: viewer (`view.html`, `view3d.js`) wired to the wasm and Pyodide modules, fake clock controls, scenarios | 2 |
| Build and CI: pinned emsdk, size budget, Playwright check in `scripts/test-all.sh`, golden-frame compare against the native renderer | 2 |
| Total | 12 to 13 days |

## Risks

- Drift: the wasm renderer is built from the same sources as the native one, so the risk is in the glue (stubs, API wrappers). Mitigation: a golden-frame diff of wasm against native in CI.
- First-load weight with Pyodide (4 to 5 MB). Mitigation: lazy-load Pyodide only when a scenario or tool call needs it; the face and cores alone start in under 1 MB.
- Toolchain pins: Emscripten 3.1.74, LVGL 9.5.0, fonts from a GitHub clone (record the commit in the build). The IDF component registry is not reachable from the cloud container, so the build depends on GitHub for LVGL and fonts.
- Rendering parity: wasm uses the same LVGL software renderer, so pixels should match; float behavior in wasm is IEEE and deterministic, but compare to be sure.
- Memory: face module starts at 16 MB with growth on; the unit-side memory gate is not simulated here.
- Real firmware features that need hardware (camera, audio, servo physics) are out of reach by design; the virtual unit already marks them as gaps.
