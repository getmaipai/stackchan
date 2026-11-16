# Firmware egress audit

Status (2026-11-15): this audits the OLD base (M5 pin 1b57655). Patch 155 and the removal patch are rebuilt on the new base during the rebase (layer F), then this audit is re-run against the new tree and the egress proof is captured on a real unit. Until then the privacy claim reads "built so, until a capture proves it".

Scope: pinned firmware source after the recipe patch sequence, inspected 2026-11-15. The recipe restores that source after check-only. `yes` means the path can initiate a network request in the ordinary firmware profile, without a tool or user selecting an external URL.

| Path | File and line | Reachable by default | Fix |
|---|---|---:|---|
| Backend base URL default points at a fixed public IPv4 address; account, app list and avatar websocket compose paths from it | `firmware/main/Kconfig.projbuild:3-10`; `firmware/main/hal/hal_account.cpp:20-32,72,116,209`; `firmware/main/hal/hal_app_center.cpp:16-18,40`; `firmware/main/hal/hal_ws_avatar.cpp:66` | yes when those features are used | Keep `CONFIG_STACKCHAN_SERVER_URL` empty unless recipe supplies the paired host; remove account and app-center calls for a local-only build. No paired-host value is present in the checked-in recipe by default. |
| OTA metadata and image download client | `firmware/main/Kconfig.projbuild:16-20`; `firmware/main/hal/hal_ota.cpp:20-50`; `firmware/main/hal/utils/ota/ota.c:127-182` | yes when update is requested; vendor URL is default | Set `CONFIG_OTA_URL=""`; compile vendor OTA and its entry points out. Require a signed update manifest before accepting an image. |
| App-center firmware URL from server response, then arbitrary URL download | `firmware/main/hal/hal_app_center.cpp:99-125`; `firmware/main/apps/app_app_center/app_app_center.cpp:72`; `firmware/main/hal/utils/ota/ota.c:127` | no until app-center is opened and an item launched | Remove app-center launch path or enforce paired-host origin and signature verification. |
| Camera explain URL HTTP POST, including image data and token | `firmware/main/hal/board/stackchan_camera.h:51`; `firmware/main/hal/board/stackchan_camera.cc:389-391,1029,1085` | no until a caller sets the URL and requests explain | Remove URL setter or accept only paired-host URLs; no URL-taking MCP registration was found in `hal_mcp.cpp`. |
| EzData activation/registration and MQTT | `firmware/main/hal/hal_ezdata.cpp:158-179,214-257`; endpoint `ezdata2.m5stack.com`, broker `uiflow2.m5stack.com:1883` | no until EzData is used | Compile `hal_ezdata.cpp` feature out and remove its activation and MQTT dependencies. |
| SNTP public time lookups | `firmware/main/hal/hal_network.cpp:33-43`; `firmware/components/esp-now/src/utils/src/espnow_timesync.c:23` | yes when network time initialization runs; ESP-NOW component's time helper is not the normal StackChan clock path | Disable SNTP initialization and ESP-NOW timesync; unit receives time from paired host. |
| Modem/cellular event handling | `firmware/main/hal/hal_network.cpp:96-99`; `firmware/main/idf_component.yml:27` | no evidence of a default modem connection | Exclude modem component and event handling from this target. |
| HTTP client callers | `firmware/main/hal/hal_account.cpp:49,209`; `firmware/main/hal/hal_app_center.cpp:40`; `firmware/main/hal/board/stackchan_camera.cc:1085`; `firmware/main/hal/hal_ezdata.cpp:179`; OTA client above | conditional on each caller; OTA is user-triggered | Keep only host-bound calls, remove the callers that accept arbitrary URLs, and disable unused HTTP clients in component configuration. |
| DNS lookups | Runtime URL clients resolve their URL hostnames through the network stack; source references above | yes for requests that use hostnames | Restrict all retained destinations to paired-host configuration. No standalone hard-coded DNS resolver was found in the app sources. |
| Captive connectivity checks | No captive-check URL or connectivity probe found in `firmware/main` | no | None identified in the inspected application sources. |
| Wi-Fi setup portal and AP | `firmware/main/hal/hal_network.cpp:86-94`; upstream Wi-Fi board setup is invoked after connect failure | yes after Wi-Fi connection failure | Existing setup route is a local AP, not an outbound request. It is open and exposes setup on the LAN; protect the setup window and remove saved-network disclosure as specified in privacy audit row 4. |
| Cloud avatar fallback | `firmware/main/hal/hal_ws_avatar.cpp:66`; patched fallback behavior is controlled by patches 144, 146, 152 | no in the recipe's no-gateway-fallback profile; yes if fallback is enabled | Keep `--no-gateway-fallback`; provide only paired-host URL and disable that option for no-phone-home builds. |

## Configuration switches and defaults

- `CONFIG_STACKCHAN_SERVER_URL`: base URL for backend/account, app-center and avatar requests. The pinned Kconfig default is a public IP. `recipe.sh` does not currently set this value.
- `CONFIG_OTA_URL`: vendor update metadata URL. The pinned Kconfig default is a vendor HTTPS URL. Set it empty.
- `CONFIG_STACKCHAN_PERSISTENT_WEBSOCKET`: enabled by default in the recipe; `--no-persistent-websocket` disables it. This is the paired-host voice link, not an external fallback.
- `CONFIG_STACKCHAN_GATEWAY_FALLBACK`: enabled unless `--no-gateway-fallback` is supplied. No-phone-home builds must disable it.
- `CONFIG_STACKCHAN_TAILNET`: off unless `--tailnet` is supplied. When enabled, this intentionally contacts the configured private-network control plane, relay and STUN endpoints; it does not meet the strict home-only promise.
- `CONFIG_STACKCHAN_CA_PEM`: empty unless `--ca-file` is supplied.
- `CONFIG_MQTT`: component-level setting should be disabled with EzData excluded. No project-level Kconfig switch was found for the EzData registration path.
- No application-level switch was found for SNTP initialization or modem handling in the inspected source. Those paths need a compile-time guard or source removal.

## Audit boundary

The pinned tree's `firmware/main/hal/hal_mcp.cpp` contains robot motion, reminder, Wi-Fi and local device tools, but no four URL-taking tools or capabilities URL setter. The repository also contains no release public-key PEM or raw Ed25519 public key asset. Therefore this audit does not assert those symbols or a shipped release key exist in this source revision.

## Travel with the private network (added 2026-11-16, patch TN01)

When the unit cannot reach the hub three times in a row, and a one-time key was entered on the setup page, the client contacts the private-network coordination service over TLS to join. At home it never starts. This is the one outbound connection to a public service the firmware can make, it is off unless a person enters a key, and the egress proof (`scripts/stackchan-egress-proof.sh`) must list it. Wording stays "built so, until a capture proves it".
