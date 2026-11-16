# Third-party notices

Listed here as code is vendored or patched. Each entry names the upstream, its license, the pinned version and where it is used.

| Upstream | License | Pin | Used in |
|---|---|---|---|
| Pollen Robotics recorded moves | Apache-2.0 | pinned dataset revision | Optional moves package, downloaded with checksum and never vendored |
| Chatterbox Turbo | Apache-2.0 | pinned catalog revision | Used to render offline voice clips; model not redistributed |
| TweetNaCl Ed25519 field and group arithmetic | Public domain | reference implementation, rewritten in C++ | Firmware update signature check (patch 155, `update_verify.cc`), verification only |
