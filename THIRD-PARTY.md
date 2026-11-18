# Third-party notices

Listed here as code is vendored or patched. Each entry names the upstream, its license, the pinned version and where it is used.

| Upstream | License | Pin | Used in |
|---|---|---|---|
| Pollen Robotics recorded moves | Apache-2.0 | pinned dataset revision | Optional moves package, downloaded with checksum and never vendored |
| Chatterbox Turbo | Apache-2.0 | pinned catalog revision | Used to render offline voice clips; model not redistributed |
| TweetNaCl Ed25519 field and group arithmetic | Public domain | reference implementation, rewritten in C++ | Firmware update signature check (patch 155, `update_verify.cc`), verification only |
| Espressif ESP-SR (wake word, command recognizer, audio front end) | MIT text with the clause "for use on all ESPRESSIF SYSTEMS products"; model data terms to be confirmed | esp-sr 2.4.7, downloaded by the build from the component registry, never vendored in this repo | Wake word "Hi, Stack Chan" (`wn9l_histackchan_tts3`), stop word model (`mn5q8_en`), echo cancellation and voice activity in the firmware image. A prebuilt image that bundles the models waits for a license confirmation; the build recipe downloads them |
| LVGL | MIT | the version the pinned firmware base builds | Graphics library behind every screen on the robot; fetched by the build, never vendored here |
| ESP-IDF | Apache-2.0 | 6.1.1 | Firmware build framework and runtime; fetched by the build, never vendored here |
| Espressif ESP-DL | MIT | the version the face-detect patches pin | On-robot face detection model runtime (`FD01` patches); fetched by the build |
| Private-network client in the firmware | license to be confirmed before a release image ships it | not pinned in this repository | Optional away-from-home link. A release build carries neither this client nor any key until its license and pin are recorded here |

## Host dependencies

Installed by pip from `host/pyproject.toml` (exact versions in `host/uv.lock`); none is vendored here.

| Package | License | Used for |
|---|---|---|
| pydantic | MIT | Reading and checking `robot.toml` and records |
| websockets | BSD-3-Clause | The robot's voice link |
| aiohttp | Apache-2.0 | Vision uploads and notify audio |
| requests | Apache-2.0 | Calls to your model and speech servers |
| numpy | BSD-3-Clause | Audio samples |
| scipy | BSD-3-Clause | Audio resampling |
| pyserial | BSD-3-Clause | Serial link tools |
| av (PyAV) | BSD-3-Clause, bundling FFmpeg libraries under LGPL-2.1 or later | Audio decoding |
| onnxruntime | MIT | Face embedding and voice models |
| num2words | LGPL-2.1 | Spelling numbers out for speech, as the shared spec's normalizer expects; used as a dependency, never copied |
| esp-idf-nvs-partition-gen | Apache-2.0 | Building the robot's settings partition |
| openwakeword, sherpa-onnx (optional extras) | Apache-2.0 | Wake word scoring and offline command recognition |

## Licenses of this repository's own files

The repository is AGPL-3.0 (`LICENSE`). A source file without a notice is AGPL-3.0. New firmware source files added through patches in `firmware/patches` carry an MIT notice, because they are compiled into the MIT-licensed firmware base and can be offered upstream; the patches themselves are AGPL-3.0.

