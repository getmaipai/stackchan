# Third-party notices

Listed here as code is vendored or patched. Each entry names the upstream, its license, the pinned version and where it is used.

| Upstream | License | Pin | Used in |
|---|---|---|---|
| Pollen Robotics recorded moves | Apache-2.0 | pinned dataset revision | Optional moves package, downloaded with checksum and never vendored |
| Chatterbox Turbo | Apache-2.0 | pinned catalog revision | Used to render offline voice clips; model not redistributed |
| TweetNaCl Ed25519 field and group arithmetic | Public domain | reference implementation, rewritten in C++ | Firmware update signature check (patch 155, `update_verify.cc`), verification only |
| Espressif ESP-SR (wake word, command recognizer, audio front end) | MIT text with the clause "for use on all ESPRESSIF SYSTEMS products"; model data terms to be confirmed | esp-sr 2.4.7, downloaded by the build from the component registry, never vendored in this repo | Wake word "Hi, Stack Chan" (`wn9l_histackchan_tts3`), stop word model (`mn5q8_en`), echo cancellation and voice activity in the firmware image. A prebuilt image that bundles the models waits for a license confirmation; the build recipe downloads them |
