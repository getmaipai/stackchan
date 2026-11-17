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
