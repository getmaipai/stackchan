# Third-party notices

Listed here as code is vendored or patched. Each entry names the upstream, its license, the pinned version and where it is used.

| Upstream | License | Pin | Used in |
|---|---|---|---|
| Pollen Robotics recorded moves | Apache-2.0 | pinned dataset revision | Optional moves package, downloaded with checksum and never vendored |
| Chatterbox Turbo | Apache-2.0 | pinned catalog revision | Used to render offline voice clips; model not redistributed |
| TweetNaCl Ed25519 field and group arithmetic | Public domain | reference implementation, rewritten in C++ | Firmware update signature check (patch 155, `update_verify.cc`), verification only |
| Espressif ESP-SR (wake word, command recognizer, audio front end) | MIT text with the clause "for use on all ESPRESSIF SYSTEMS products"; model data terms to be confirmed | esp-sr 2.4.7, downloaded by the build from the component registry, never vendored in this repo | Wake word "Hi, Stack Chan" (`wn9l_histackchan_tts3`), stop word model (`mn5q8_en`), echo cancellation and voice activity in the firmware image. A prebuilt image that bundles the models waits for a license confirmation; the build recipe downloads them |
| LVGL | MIT | the version the pinned firmware base builds | Graphics library behind every screen on the robot; fetched by the build, never vendored here |
| esptool-js | Apache-2.0 | 0.7.0, one file copied unchanged into `flasher/vendor/` (license beside it) | The web flasher writes the robot over USB (Web Serial) with it |
| ESP-IDF | Apache-2.0 | 6.1.1 | Firmware build framework and runtime; fetched by the build, never vendored here |
| Espressif ESP-DL | MIT | the version the face-detect patches pin | On-robot face detection model runtime (`FD01` patches); fetched by the build |
| MuJoCo | Apache-2.0 | 4.0.1, the WebAssembly build (`mujoco.js`, `mujoco.wasm`) of npm package `@mujoco/mujoco`, SHA-512 `vLuwD6biiyo2D2LG1fwpwJUfWSDZhBIr6aUd3AuPJR8P7FAIeSHgofGC+0XgIpZ0vYi0EOyju+Kv7zPJepX7wA==` (the package's published integrity). The native viewer loads it from the pinned address in `scripts/virtual-unit/physics/THIRD-PARTY-physics-engine.json`; the browser site build (`scripts/virtual-unit/wasm/site-build.sh physics`) downloads it from the npm registry, checks the hash and puts it in the site's `vendor/mujoco-4.0.1/` with the Apache-2.0 text (`docs-site/vendor/mujoco/LICENSE-Apache-2.0.txt`). Never committed (11 MB), never in the firmware or the host program | Optional physics mode of the virtual unit (off by default, loaded on demand) |
| Private-network client in the firmware | license to be confirmed before a release image ships it | not pinned in this repository | Optional away-from-home link. A release build carries neither this client nor any key until its license and pin are recorded here |
| M5Stack StackChan structure files (K151), from m5stack/M5_Hardware | MIT, Copyright (c) 2021 M5Stack (text in `scripts/virtual-unit/model/source/LICENSE`) | commit 70fb127275ef0e2da21218d1f01cd305754d35fa, ten STL files copied unchanged, hashes in `scripts/virtual-unit/model/SOURCE.md` | Geometry of the virtual unit 3D model (`scripts/virtual-unit/model/stackchan.glb`) |
| Khronos glTF Validator (`gltf-validator` on npm) | Apache-2.0 | 2.0.0-dev.3.10, installed on demand into the git-ignored `.runs/gltf-validator/`, never vendored | Development check only: `scripts/virtual-unit/model/validate.sh` reads `stackchan.glb` on this machine. Not a runtime dependency of the host or the firmware |
| three.js | MIT, Copyright (c) 2010-2021 three.js authors (text in `docs-site/vendor/three-r128/LICENSE`) | r128 (npm package 0.128.0), `build/three.min.js` copied unchanged, sha256 `9274bbcec8d96168626c732b5d31c775aa8cfb7eaa0599bec0c175908a2c1ce2` | The 3D model viewer page of the documentation site (`docs-site/viewer.html`), served from the site itself. The same release the virtual unit view loads. Never in the firmware or the host program |

## Host dependencies

The packages these pull in are listed, with the license each declares, in [docs/dev/third-party-indirect.md](docs/dev/third-party-indirect.md). A few of them (the Reachy simulator and its GStreamer parts) arrive only through a development dependency and are not part of a release export; their licenses are marked "to confirm upstream" in that table until checked.

Installed by pip from `host/pyproject.toml` (exact versions in `host/uv.lock`); none is vendored here.

| Package | License | Used for |
|---|---|---|
| pydantic | MIT | Reading and checking `robot.toml` and records |
| websockets | BSD-3-Clause | The robot's voice link |
| aiohttp | Apache-2.0 | Vision uploads and notify audio |
| requests | Apache-2.0 | Calls to your model and speech servers |
| certifi | MPL-2.0 | The list of trusted certificate authorities used by requests and aiohttp (kept current so a known advisory does not apply) |
| numpy | BSD-3-Clause | Audio samples |
| scipy | BSD-3-Clause | Audio resampling |
| pyserial | BSD-3-Clause | Serial link tools |
| av (PyAV) | BSD-3-Clause, bundling FFmpeg libraries under LGPL-2.1 or later | Audio decoding |
| onnxruntime | MIT | Face embedding and voice models |
| num2words | LGPL-2.1 | Spelling numbers out for speech, as the shared spec's normalizer expects; used as a dependency, never copied |
| segno | BSD-3-Clause | The QR code that logs a phone in to the settings page |
| reachy-mini (optional extra) | Apache-2.0 | The Reachy Mini body daemon client; only for the Reachy body code that is leaving this repository |
| esp-idf-nvs-partition-gen | Apache-2.0 | Building the robot's settings partition |
| llama.cpp `llama-server` (downloaded at install, not shipped) | MIT | Runs the small local language model |
| Qwen2.5 0.5B and 1.5B Instruct GGUF (downloaded at install, not shipped) | Apache-2.0 | The small local language model |
| Moonshine tiny English (sherpa-onnx package, downloaded at install, not shipped) | MIT | The small local speech-to-text model |
| Piper `en_US-ljspeech-medium` (sherpa-onnx package, downloaded at install, not shipped) | MIT code; voice data from the public-domain LJ Speech set | The small local text-to-speech voice |
| openwakeword, sherpa-onnx (optional extras) | Apache-2.0 | Wake word scoring and offline command recognition |

## Licenses of this repository's own files

The repository is AGPL-3.0 (`LICENSE`). A source file without a notice is AGPL-3.0. New firmware source files added through patches in `firmware/patches` carry an MIT notice, because they are compiled into the MIT-licensed firmware base and can be offered upstream; the patches themselves are AGPL-3.0.

