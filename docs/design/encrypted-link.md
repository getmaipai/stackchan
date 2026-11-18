# Encrypted link between the unit and the host

Status: design and host half built (2026-11-17). The unit half is a firmware patch that follows this note.

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
