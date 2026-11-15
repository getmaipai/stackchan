# Upstream firmware review

Compared our pins, M5 StackChan `1b57655` through `28b9f0c8`, and xiaozhi-esp32 `v2.2.4` through `v2.6.0`. M5's current dependency is xiaozhi `v2.5.2`; the local xiaozhi clone also contains `v2.6.0`. No network used. Cost figures are only listed when visible in the source study or dependency change; no full build size or RAM measurements exist for the new base.

## Notable changes

| Change | Commit or version | Area | RAM or flash cost visible | Verdict and why |
|---|---|---|---|---|
| LAN-preferred avatar transport with cloud fallback, local avatar client and diagnostics | M5 `94856a7`, `0808a47` | Wi-Fi, protocol | Not measured; adds networking code | TAKE: matches local-first host pairing and resilience needs. |
| Wi-Fi station and provisioning flow rewritten; app-based setup and network test | M5 `94856a7` | Wi-Fi | Not measured | TAKE: use the tested setup path, then retain our pairing behavior. |
| Camera now subclasses shared EspVideo path | M5 `0808a47` | drivers | Removes 1,158 lines in camera implementation; cost not measured | TAKE: reduces board-specific camera code and aligns with updated camera stack. |
| Audio codec implementation moved to shared xiaozhi component | M5 `0808a47` | audio, drivers | Removes 246 lines locally; cost not measured | TAKE: fewer local codec forks, subject to hardware audio check. |
| ESP-NOW wrapped in EspNowRadio class | M5 `0808a47` | drivers, protocol | Not measured | LATER: useful for pose mirroring, not required for first local voice release. |
| Wi-Fi password no longer logged over serial | M5 `febcfdb` | security | Negligible; one-line change | TAKE: prevents credential disclosure. |
| BLE setWifi rejects missing SSID or password instead of aborting | M5 `d2e9548` | security, Wi-Fi | Negligible; six added lines | TAKE: removes malformed-input crash path. |
| Guard invalid servo position reads | M5 `65193e8` | drivers, power | Negligible; 32 lines added | TAKE: prevents invalid position handling; retain our servo wear limits too. |
| Y-axis current monitoring and stall protection; touch debounce adjustment | M5 `893ee38` | drivers, power | Not measured; adds current/stall logic | TAKE: stall protection matches safe motion goals; review thresholds against our limits. |
| Support for ILI9342E display | M5 `8743e2b` | display, drivers | Not measured; board-specific | SKIP: current unit display is unchanged. |
| Fragmented BLE JSON transfer | M5 `7d82315` | protocol | Not measured; 275 lines added | SKIP: Bluetooth is disabled in our profile. |
| Launcher and setup feature toggles | M5 `1c629b8` | build | Not measured | SKIP: our optional-feature rule requires disabled features to compile out with no memory cost. |
| ESP-IDF 6.1 and xiaozhi v2.5.2; C++23 and Newlib config changes | M5 `0808a47` | build | HTTP client/server mbedTLS growth about 37/41 KB per study; firmware total not measured | TAKE: required base; remeasure the complete memory baseline before trimming. |
| Shared AFE replaces old wake/audio processors; esp-sr 2.4.7 and WN9L model | xiaozhi `v2.5.0` and M5 `0808a47` | audio, wake | AFE stack and LVGL pool moved to PSRAM (`7aa9266`); S3 totals not published | TAKE: use the shared engine and new wake model, then re-port custom wake behavior. |
| Streamed notify playback | xiaozhi `bb9122a` (`v2.5.0`) | audio, protocol | Not measured | TAKE: supports idle spoken alerts and future host events. |
| Glyph push and text-font hello capability | xiaozhi `v2.5.0` | display, protocol | Not measured | LATER: enables rare-script captions when a font pack is selected. |
| MCP input validation, max string lengths and JSON-RPC error codes | xiaozhi `acb2fc7` | security, protocol | Not measured | TAKE: safer tool boundary; keep our own tool allowlist and authorization. |
| OTA URL validation and invalid saved-URL fallback | xiaozhi `#2408`, `5d863f5` | OTA, security | Not measured | TAKE: reduces unsafe update destinations; still port signature verification. |
| Unsafe eFuse serial handling fixed | xiaozhi `f05adce` | security | Negligible | TAKE: avoids unsafe device identity input. |
| WebSocket hello transport null guard | xiaozhi `d436097` | protocol, crash | Negligible | TAKE: prevents null dereference on malformed hello. |
| JSON parse length, MCP error escaping/string limits and Ogg end-lace fixes | xiaozhi `358819bf`, `aef2ab0c`, `acb2fc7`, `eeae329b` | protocol, security, audio | Negligible or not measured | TAKE: input safety and demux correctness fixes. |
| Camera DMA disabled by default on ESP32-S3; bounce buffer capped at 16 KiB | xiaozhi `3556a28`, `3556a283` | drivers, power | 16 KiB cap visible; exact RAM reduction not published | TAKE: bounded camera DMA pressure fits our RAM constraints. |
| LAN/cloud avatar, camera, and WebSocket implementation rewrites | M5 `94856a7`, `0808a47` | Wi-Fi, protocol, drivers | Not measured; substantial code movement | HAVE: keep our host integration but drop/rework patches replaced by these implementations. |
| xiaozhi 2.6 adds MCP 2026-07-28 beside legacy version | `69f22bf` | protocol | Not measured | TAKE: preserve backward compatibility and adopt once host negotiation is checked. |
| Authenticated MQTT/UDP health probes and reset reason in device status | xiaozhi `5b1dbe0`, v2.6.0 | protocol, diagnostics | Not measured | SKIP: MQTT is excluded; reset reason can be revisited with host diagnostics. |
| New locales and updated font/assets support | xiaozhi v2.5.0-v2.6.0 | display, build | No board-specific size published | LATER: language packs are useful, but select fonts only after partition budget review. |
| v2.6.0 WebSocket protocol/header additions | xiaozhi `v2.6.0` | protocol | Not measured; M5 patch has three rejected esp_video hunks | TAKE: required target version; land after the M5 v2.5.2 hop and reconcile hello fields. |

## Fixes we get for free

- `d4360977`: guard a missing hello `transport` before string comparison.
- `358819bf`: bound JSON parsing by the supplied input length.
- `aef2ab0c`, `acb2fc73`: validate MCP strings and escape/limit error content.
- `f05adce2`: reject unsafe eFuse serial values in OTA identity handling.
- `#2408`, `5d863f5`: validate OTA URLs and fall back from an invalid saved URL.
- `eeae329b`: emit an Ogg packet whose final lace has zero length.
- M5 `febcfdbc`: stop printing Wi-Fi passwords; `d2e95488`: reject incomplete BLE Wi-Fi credentials without aborting.
- `153e19b`: free cJSON text after printing a custom message; `3556a283`: bound camera DMA bounce allocation.

## Features worth building on

- LAN-first avatar path can become the local host transport, with the feature hidden when its brain adapter is absent.
- Streamed notify can carry local timer, alert and coding-companion events without waiting for a full turn.
- The shared AFE and wake engine are the base for our local wake word and barge-in, after custom stop-word and echo handling are rewritten.
- Glyph push and font blocks can support optional non-Latin caption packs while keeping the default screen compact.
- Servo current/stall feedback supports safe motion and future pose recording, subject to measured thresholds and a disabled-feature memory check.
- Camera migration gives the host snapshot and face-alert work a current driver seam; frames remain host-side per our design.
- ESP-NOW radio abstraction can support pose mirroring later without making it part of the resident core.

## Upstream removals and patch breakage

The audio engine replaces the old wake processor files, so patches `049`, `059`, `061`, `065`, `083`, `086`, and dependent `094` need a rewrite. `stackchan_camera.cc`, avatar socket/transport, `wifi_station.cc`, `hal_ws_avatar.cpp`, `application.cc`, and `websocket_protocol.cc` are rewritten or moved; the conflict map and patch ids are in `firmware-base.md`. Legacy I2S, ADC, RMT and `wifi_provisioning` APIs are removed under IDF 6; migrate to the new drivers and `network_provisioning`. Upstream now selects the strongest Wi-Fi AP and adds safe power-chip reads, so retire patches `044` and `009`. M5's v2.5.2 patch does not apply cleanly to v2.6.0: three `esp_video.cc` hunks need resolution.

## Open questions

- Does the M5 v2.5.2 image pass our memory gate? Check one full spoken turn while recording `internal_free`, `int_big`, and `psram_min` for ten minutes.
- Does v2.6 hello negotiation preserve our host handshake? Run a captured hello exchange against the updated protocol and host.
- Can the shared AFE host our stop-word without raising internal heap use? Measure the model and stack placement on the target unit.
- Does the local avatar route remain available without cloud fallback? Disable cloud reachability and verify pairing, voice and reconnect.
- Are Y-axis stall current thresholds safe for this unit? Measure current at rest, normal motion and a controlled obstruction.
- Do removed IDF drivers affect our camera/audio setup? Build the StackChan target with warnings-as-errors and exercise camera, playback and capture.
- Does BLE fragmented transfer matter to any enabled workflow? Confirm Bluetooth stays disabled in the selected configuration.
- Can v2.6 MCP coexist with the host's tool schema? Capture registration and one call against both supported protocol versions.
