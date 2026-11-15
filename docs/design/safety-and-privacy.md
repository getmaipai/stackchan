# Safety and privacy

Promise: private, local AI that is yours. Nothing leaves the home.

## Own-LLM safety floor (decision 13)

- No content filter of our own. Content safety is the responsibility of the connected language model and the owner's persona prompt.
- The docs, the first-run setup and the README say so in one plain sentence.
- An optional family-friendly persona preset may ship. It is labelled as a prompt, not a guarantee.
- A brain such as MaiPai Home may add its own age and household gates. Those belong to the brain and are not weakened by this repo.
- What stays in this repo:
  - Body safety: servo limits, slow eased moves, volume cap, thermal and wear limits, no hard shaking by games.
  - Privacy cues: the camera-on cue cannot be turned off while the camera streams. Mute and error cues cannot both be disabled.
  - No fast flashing in any light option (photosensitivity).
  - Pairing and token security. Voice commands never change safety settings, pairing or Wi-Fi.
  - Coding companion approvals: touch only by default, never by voice alone. Every approval is logged.
- Camera features are opt-in. Frames stay in the home, on the host or the Home hub, with a retention setting and delete-all.
- Mute has two kinds. Quiet keeps the wake word, so a voice unmute works. Hard mute powers the mic down and only touch, the web app or a button can undo it. The unit never claims a voice unmute works in hard mute.

## Zero phone-home

- The unit talks only to the host and the Wi-Fi it joined. The host talks only to addresses the owner put in the toml.
- No telemetry, no crash upload, no vendor account, no vendor cloud. Works fully offline once set up.
- The update check is one manifest request to the chosen source, sent by the host, carrying only the firmware version.
- The public privacy page lists every connection the unit may make, with a firewall rule sample.
- Optional private-network client: off by default, no key in any public build, started lazily, enrolled from the host with a one-off tagged expiring key.
- Presence comes from the network, a private-network client and the camera. No Bluetooth.

## Security audit outcomes (read of the dev image, 2026-11-15)

| # | Level | Finding | Fix |
|---|---|---|---|
| 1 | High | Host-controlled tools could install firmware or send data to any URL, with no check on who asks. Four tools plus a capabilities URL setter. | Patch 155: delete them or pin every URL to the paired host. Add an Ed25519 signature check on updates. First security patch, before the repo goes public. About 2 hours plus 1 day. |
| 2 | High | Voice and avatar links are plain `ws://` with a static token. The unit never checks who answers. Gateway fallback sends the token to the gateway on networks named by prefix. | Remove the gateway fallback now. Then TLS with a private CA, 1 to 2 days, after the pairing token exists. Until then the docs say the LAN link is plaintext. |
| 3 | High (dev only) | A live private-network auth key sat in a dev build tree and image. Not committed. Revoked and deleted. | Release and flash tools refuse any image containing a key. Secret scan in the build. Custom gitleaks rule. |
| 4 | Medium | The Wi-Fi portal is open and unauthenticated and leaks saved network names. It starts after a 60 s connect failure. | Redesign with a protected window and no saved-network list. Interim patch: drop the list and advanced route, add a 5 to 10 minute timeout, generic SSID. |
| 5 | Medium | The full public CA bundle is built in. | Custom bundle with only the roots we need. Frees 35 to 65 KB flash. |
| 6 | Medium | Flash is readable over USB: no secure boot, flash or NVS encryption. A dump yields the token and Wi-Fi passwords. | Keep erase-after-report for core dumps, no secrets in logs. Efuse hardening is the owner's call. |
| 7 | Low | Private-network client contacts its control plane, relay and STUN servers when on. | Expected. List them on the privacy page. Check the verify-off test path is never set. |
| 8 | Low | Dead code linked: MQTT, vendor OTA client, activation, SNTP client, modem code. The vendor OTA URL default points off-device. | One removal patch and an empty OTA URL default. |
| 9 | Low | Real addresses as Kconfig defaults in two patches. | Default both to empty, pass from the recipe. Must be done before the repo is public. |

Confirmed clean: Bluetooth, ESP-NOW, hard-coded DNS, DHCP NTP, audio debugger, insecure TLS flag, debug stub, HTTPS server,
telemetry strings, hard-coded tokens.

## Clock and time

Public time servers were removed on purpose. The host sends the time, zone and POSIX rule at hello and every 30 minutes.
The unit shows `--:--` until the time is valid. An optional local time server field is empty by default. No public default, ever.

## Build-time rules

- A secret-scan step in the firmware build and the release tools.
- Included code keeps its notice in LICENSE, NOTICE and THIRD-PARTY. A CI check refuses an unlicensed or incompatible import.
- No names, addresses or credentials of any household in code, docs or examples. Examples use reserved documentation addresses and names.
- The local API binds to the LAN, needs the token for reads and writes, and remote reach is a separate documented switch.

## Open

- TLS between unit and host: certificate pinned at pairing or a reverse proxy.
- Secure boot and flash encryption (burns eFuses, owner's call).
- Whether a remote camera view ever ships. It would be a separate opt-in feature with an on-robot cue, after patch 155 and TLS.
