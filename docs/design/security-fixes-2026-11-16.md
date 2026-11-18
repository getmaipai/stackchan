# Security fixes, 2026-11-16

Source: the findings table in `safety-and-privacy.md`. Tree: the rebased firmware tree, built with ESP-IDF 6.1.1. Nothing was flashed and no USB port was touched.
New patches are on `firmware/patches/ORDER` after F06. Replay of 155 to 158 onto the pre-155 files reproduces the tree byte for byte.

## Result per finding

| # | Finding | Status | Patch or file | App image after it | Free in smallest slot (0x4f0000) |
|---|---|---|---|---|---|
| 1 | Host-controlled install and send tools, camera URL setter | Fixed in source | `155-host-url-tools-removed-and-signed-updates` | 0x2efcc0 (3,079,360 B) | 0x200340 (41%) |
| 1 | Ed25519 check on updates | Built and host-tested; not linked yet (see below) | same patch | same | same |
| 2 | Gateway fallback | Fixed by absence | patches 144, 146, 152 never ported (decision 17) | n/a | n/a |
| 2 | TLS to the host | Not started, as asked | later item | | |
| 3 | Key in an image or tree | Fixed | `156-refuse-keys-in-images`, `scripts/check-no-keys.py`, `.gitleaks.toml` | 0x2efcc0 | 0x200340 |
| 5 | Full public CA bundle | Fixed | `157-ca-bundle-no-public-roots` plus 4 lines in `firmware/sdkconfig.core.defaults` | 0x2dfaf0 (-66,000 B) | 0x210510 (42%) |
| 7 | Private-network client contacts | Listed below, client not changed | this file | | |
| 8 | Dead code, vendor update URL | Partly fixed | `158-vendor-update-url-empty-and-dead-modem-dependency` | 0x2dfaf0 | 0x210510 (42%) |
| 4, 6, 9 | Portal, flash encryption, address defaults | Not in this task | | | |

Final build: app image 0x2dfaf0 bytes, smallest app slot 0x4f0000, free 0x210510 bytes (42%). Static internal RAM was not re-measured (the build prints no summary).

## 1. Tools and updates (patch 155)

Removed from `mcp_server.cc`: `self.upgrade_firmware` (install from any URL), `self.screen.snapshot` (POST to any URL), `self.screen.preview_image` (fetch from any URL) and `self.assets.set_download_url`.
The camera address in the host's capabilities message is now accepted only when its host part equals the host of the unit's own saved link (`websocket` url). Any other address is ignored with a log line; user info in the address is refused.

Update signature: plain Ed25519 (RFC 8032) over the whole image. The signature is a detached 64-byte file at the image address plus `.sig`, fetched first; the image is hashed as it streams in (R, key, image) and the install stops before the boot slot is switched when the check fails. Log lines say what is wrong and what to do ("Update refused: ..."). The public key is `STACKCHAN_UPDATE_PUBKEY` (64 hex characters, empty by default, which accepts no update). `STACKCHAN_UPDATE_ALLOW_UNSIGNED` is the developer override, off, with a warning line when on.
Tested on a PC against the RFC 8032 vector and a random 100 KB message signed with a standard tool: valid signature passes; one flipped signature bit or one flipped message bit fails.
Limit to know: the vendor update client (`Ota::Upgrade`) is in the source with the check, but nothing in this firmware calls it any more, so the linker drops it. The wireless update patch (old 133, with its security review) must call it; until then a unit cannot install over the air at all. Not exercised on a unit.
Key custody (who signs, what a fork signs with) is still open in `release-and-updates.md`; no key is in this repo.

## 2. Gateway fallback

The tree has no gateway fallback: patches 144, 146 and 152 were never ported and `grep` finds no fallback code or gateway address in `firmware/main` or the base. Keep them off the port list; the patch map rows for them should read SKIP (decision 17). Nothing to revert. The pairing token is sent only to the saved host.

## 3. Keys

`scripts/check-no-keys.py PATH...` scans files (as bytes) and folders for private-network auth keys, private key blocks (header plus encoded body, so the bare header text in crypto libraries does not trip it), code host tokens, cloud key ids and chat or model API keys. It prints the file, the kind and the byte offset, never the value, and exits 1. Run against the current five images and 1,876 source files: clean. A planted fake key and a fake private key block are both refused.
Where it runs: the firmware build (post-build step in `firmware/CMakeLists.txt`, patch 156; `scripts/fw-env.sh` exports `MAIPAI_KEY_CHECK`; a build without it stops with "run source scripts/fw-env.sh"), and `scripts/build-stackchan-firmware-asset.sh` before it packs a release folder.
Gitleaks note: `.gitleaks.toml` extends the default rules with the private-network auth key prefix.

## 5. CA bundle

The core needs no public root: the unit speaks plain WebSocket to the host on the private network, and the later TLS link will pin a private CA. The bundle is now a custom bundle holding one placeholder root (`firmware/ca/no-public-roots.pem`) whose key was destroyed at creation, so nothing chains to it. Measured: the bundle was 66,137 B; the image shrank by 66,000 B.
What remains and why: nothing public. When the TLS item lands, its private CA goes in that folder. An https connection to a public site now fails with a certificate error, by design.

## 7. Private-network client contacts, for the privacy page

The client is patch 147 in the old recipe and is not in this tree. When enabled (off by default, compiled in only by the tailnet recipe option) it contacts, besides the home host:
- the control plane named in the build (coordination and key exchange);
- relay servers (the client's DERP setting is on) over HTTPS;
- STUN servers over UDP 3478 to learn its public address;
- other devices on the same private network, directly.
The addresses come from the client library's defaults or the owner's own control plane; read them from the pinned client when it is ported and list them with the firewall sample. In the old patches 147 and 153 there is no flag that turns certificate checking off; recheck at port time. The old Kconfig default peer address (a private network address) is finding 9 and must be emptied at port time.

## 8. Dead code

Done: `CONFIG_OTA_URL` default is empty (outer and base Kconfig); the vendor address is no longer in the image (no match for it in the image strings). `uart-eth-modem` dropped from the manifest. Already out before this task: mqtt_protocol, ezdata and registry, account, app center, espnow, 4G and dual-network boards, RNDIS board, Bluetooth.
Left, with the reason:
- The network component (`esp-ml307`) is needed for the WebSocket and HTTP classes and carries an MQTT client (about 12.8 KB). It cannot be dropped without editing that component, which our patch layout does not cover. Option: a patch target for managed components, or a different network layer.
- The lwIP time client (94 B) stays: the core uses it for the configured time server value, which is empty by default.
- Activation task and handler (about 0.5 KB) are linked but never reach a server with an empty update address.
`dependencies.lock` in the tree regenerated (uart-eth-modem entries gone); it is tree state, not a patch.

## Checks

`bash scripts/hygiene-check.sh`, `bash scripts/boundary-check.sh`, `bash scripts/check.sh`: see `.runs/security-fixes.result.md`.

## Sniffing and man in the middle: decision (owner question, 2026-11-17)

Yes, protect the robot-to-host link, before the first public release. Today the unit speaks plain WebSocket to the host on the home network, so anyone who can see traffic on that network (a guest on the Wi-Fi, a compromised device) could read what the robot sends (its microphone audio while a turn runs, commands, camera frames when the camera is on) or inject commands by posing as the host. What protects us now: the pairing key, signed firmware updates, hash-pinned model downloads, the remote controls that are off by default with cues that cannot be hidden, the host's settings page bound to this computer only, and the private network (WireGuard) path when it is used.

**Design (TLS item, now scheduled)**
1. **TLS with a pinned private certificate authority.** At pairing the host makes a private CA and a host certificate; the unit stores the CA's fingerprint (not a public root), and every connection is `wss` to the host, checked against that pin. A stranger on the network cannot present a valid certificate, so a man in the middle fails at the handshake.
2. **Authenticated both ways.** The unit also proves itself with its device key and a short-lived token (a nonce per session, already carried as a session id), so a stranger cannot pose as the robot.
3. **Same for the other channels:** the audio and camera channels, and the host's small HTTP route for photos and notification sounds (https with the same pin).
4. **No downgrade:** once paired for TLS, the unit refuses plain `ws`. A "trusted home network, no encryption" option exists only as an explicit setting for debugging, off by default and shown in the Security check screen.
5. **Setup hotspot:** the setup code stays on the screen; the credentials sent in setup go over the robot's own temporary network, and the page says to do setup at home. The hotspot is closed after setup.
6. **Cost on the unit [estimate, to be measured]:** the stock firmware already speaks `wss` to its vendor's cloud, so the TLS client exists; the work is the pin, the private CA and keeping the TLS buffers in PSRAM so internal RAM keeps its floors (handshake peak is the number to measure). A few KB of flash.
7. **Tests:** a host that presents a different certificate is refused; a replayed session id is refused; tampered frames are refused; a wake and a turn still work with the TLS link (latency measured, handshake once per connection); the memory gate with an active TLS session.

**Other exposure to check in the Security check screen:** the host's HTTP port 8767 (photos, notification audio) is plain http on the LAN until item 3 lands; the settings page is loopback only; the Tailscale key is never in a release.

**Order:** after the current firmware round: (1) the TLS link with the pinned private CA, (2) the Tools app (`next-network-tools-2026-11-17.md`) beginning with the Wi-Fi scan, signal meter and the Security check screen.

**Comparison and the lighter option (owner question, 2026-11-17).** The stock firmware speaks `wss` (TLS) to its vendor's server and checks it against the public certificate bundle (`esp_crt_bundle`, in its OTA and network diagnostics code); it has no special protection for a self-hosted server on the home network, where community setups usually run plain `ws`. Other ESP32 voice and smart home projects range from plain WebSocket on the LAN to authenticated, encrypted links; for example the ESPHome native API offers encryption with a shared 32 byte key (a Noise protocol handshake) [from memory, unverified here]. The ESP-IDF TLS stack supports certificate pinning and also pre-shared key cipher suites, which need no certificates at all [unverified for our build: check the mbedTLS config].
Appropriateness: for a microphone and camera robot in a public privacy-first project, defense in depth on the LAN is proportionate but not urgent for private use; it is not overkill if it is cheap. The cheaper design is **TLS with the pairing secret as the pre-shared key** (both sides prove they hold it, no private CA, no certificate handling, smaller code and RAM). A pinned private CA is the alternative if PSK suites are not in the build. Either way: measure the handshake RAM, keep buffers in PSRAM, refuse downgrade once paired, and do it after the current firmware round.

## Built so far: encrypted link, host half (2026-11-17)

Python 3.13 with OpenSSL 3.5 does TLS-PSK (`SSLContext.set_psk_server_callback`), so the pinned private CA alternative was not needed. Firmware half: not started. Host code: `xiaozhi/link_security.py`, `xiaozhi/pairing.py` (link fields), the two servers, `settings_ui_link.py`.

**Ports (constants in `link_security.py`, env overrides `MAIPAI_LINK_VOICE_PORT`, `_AVATAR_PORT`, `_HTTP_PORT`, `MAIPAI_LINK_BIND`):** voice WebSocket 18775 (plain 8765), avatar and camera WebSocket 18776 (plain 8766), HTTP route 8777 (plain 8767: photos, notification audio, firmware file). Same paths and headers as the plain ports, scheme `wss` and `https`. The encrypted listeners bind to every interface (`0.0.0.0`), so the LAN address, loopback and a Tailscale address (100.x or a MagicDNS name) all reach them with identical behavior.

**Choice per unit, `link_encryption` (in the pairing file, never in the unit settings dump):** `required` (plain refused, close code 1008 with a plain-words reason), `allowed` (both ports; the default for an existing unit), `off` (plain only; the encrypted port refuses that unit; the Security section shows a warning). A unit paired after this change starts `allowed` and becomes `required` the first time its hello says `"features": {"tls_psk": true}` while no choice was made. A hello without the flag changes nothing. The first connection over an encrypted port sets `seen_encrypted`; with `required` a plain connection is then refused (no downgrade). Link state in the Security section: encrypted, plain allowed, plain, never seen encrypted.

**Replays:** the host issues one session id per connection (hello reply). A JSON frame that names any other id, including the id of an earlier connection, closes the socket (1008); a frame with no id is tolerated. An avatar hello that carries a session id is refused. TLS adds fresh randoms per handshake, so recorded traffic cannot be replayed into a new connection either. Logs name a unit by the last five characters of its id.

### Key derivation (for the firmware and for Home; no host code needed to follow it)

Inputs: the unit's **device token** (the string the unit already holds and sends as `Authorization: Bearer <token>`) and its **device id** (the MAC address text, for example `02:00:5e:00:53:01`).
1. `ikm = SHA-256(token as UTF-8 bytes)`: 32 raw bytes. The host stores exactly this digest (`token_sha256`) and never the token, so both sides have the same input without a second secret.
2. `identity = device id, lower case` (this is also the **TLS PSK identity** string).
3. `PSK = HKDF-SHA256(ikm, salt = empty, info = "maipai-stackchan-link-psk-v1" || 0x00 || identity (ASCII), L = 32)`, RFC 5869. An empty salt means 32 zero bytes (HMAC key) as the RFC says.
4. The PSK is 32 raw bytes, used as the TLS pre-shared key as is. It is never the digest, never the token, never logged, never stored.

Test vectors (fake token `test-token-not-a-secret-0123456789abcdefghijklmnopq`, digest `0a58fbd7c218e7b6e0c0cb253a90dd6fed0bc0d56486681c0417ba46f58422d1`):
- identity `02:00:5e:00:53:01`: PSK `1d45f16f0548601ad8c4d97eca15889af3732d4660128bac45ebb00c46214926`
- identity `AA:BB:CC:DD:EE:FF` (lower-cased first): PSK `9f8bb521a3077108311d155761ff66cf7ca3b45b209aa706c64b8fa660a6b373`
- RFC 5869 case 1 checks the HKDF itself (the host test runs it).
`python3 scripts/link-psk-vector.py --self-test` prints these; `DEVICE_ID --digest HEX64` or `--token-stdin` prints the PSK for real inputs (run it yourself, never paste a real token into a doc or a shell history).

### TLS parameters the unit must use
TLS 1.2 only (OpenSSL's PSK support in TLS 1.3 is not used). No certificate, no server name or certificate check (so any address works). Cipher suites the host offers, best first: `ECDHE-PSK-CHACHA20-POLY1305` (RFC 7905), `ECDHE-PSK-AES128-CBC-SHA256` (RFC 5489), `PSK-AES128-GCM-SHA256` (0x00A8), `PSK-AES256-GCM-SHA384`. Give the unit at least one of the first three; ECDHE ones add forward secrecy. The PSK identity hint from the server is empty. The unit needs mbedTLS `MBEDTLS_KEY_EXCHANGE_PSK_ENABLED` (plus ECDHE_PSK for the first two) and `esp_tls` with `psk_hint_key`, and must send the hello flag `tls_psk: true` in its `features` once it can. Order for the unit: try the encrypted port first; fall back to the plain port only when the choice is not `required` (the host refuses it anyway when it is).

### Home (Home is a separate codebase)
Home pairs a unit with a one-time enrollment code; the unit redeems it and receives a device token, so Home already holds that token's digest or the token. Home derives the same PSK with the steps above (HKDF-SHA256 exists in Node `crypto.hkdfSync("sha256", ikm, Buffer.alloc(0), info, 32)` and Python `hashlib`/`hmac`; an empty salt is accepted by both and equals 32 zero bytes). When Home is the unit's host it runs its own TLS-PSK listener with these parameters (Node: `tls.createServer({ pskCallback: (socket, identity) => psk, ciphers, minVersion: "TLSv1.2", maxVersion: "TLSv1.2" })`). When the Python host is the unit's host and Home paired the unit, Home hands the host `(device id, client id, SHA-256 of the token)`; the host registers it with `PairingStore.adopt_device(device_id, client_id, token_sha256)` and uses it exactly like a unit it paired itself (the digest is the same secret the token check already uses, not a new one). Nothing else is exchanged. Re-pairing issues a new token, which changes the PSK and resets `seen_encrypted` and the choice.

### Three setups, same code
- **Local:** the unit connects to the host's LAN address on 18775, 18776, 8777.
- **Through Home:** the hub's address as the unit's host (Home runs the same listener spec), or Home's digest adopted by the Python host as above.
- **Tailscale:** the unit uses the host's tailnet address; PSK checks no name, so nothing changes. Traffic on that path is already inside WireGuard, so the TLS layer is defense in depth. It stays on by default. A setting to skip it on the tailnet only is not added: the measured cost is small (below).
A test connects to the same listener over loopback and over the machine's LAN address and requires identical results (hello, and refusal of a wrong key).

### Measured (fake unit on loopback, Python client, this Mac)
Connect plus handshake: 7.4 ms plain, 5.0 ms TLS-PSK (noise; both are a few milliseconds). Small-frame round trips on the voice socket: about 2,360 per second plain, about 2,300 per second with TLS-PSK. The host side is not the limit; the unit's handshake RAM and time are still to be measured on a unit.

### Tests
`host/tests/test_stackchan_link_psk.py` (23 tests): HKDF RFC vector, fixed PSK vectors, the reference script, frames on all three encrypted listeners, wrong key and wrong identity refused at the handshake, a plain client refused on the encrypted port, required, allowed and off, the downgrade rule, the hello flag, stale and foreign session ids, loopback and LAN address, the PSK and digest never in logs or the settings dump, the settings route, Home's adopted digest, a performance note.
Security check screen data: none exists in the host yet, so the link state is in the Security section only.
