# Link key exchange for the encrypted link (design, 2026-11-18)

Placement: unit (firmware) and host. Supersedes the key derivation section of `docs/design/encrypted-link.md`. Firmware half: patches follow this note behind their own switch. Host half: app track.

## What is encrypted

The voice socket, the avatar and camera socket, and the host HTTP route (photos, notification audio, firmware file) run over TLS 1.2 with a pre-shared key (the suites in `encrypted-link.md`). Policy per unit: `required` (plain refused), `allowed` (both), `off`. A unit paired with this exchange starts `required`. "allowed" exists only for units paired before the exchange existed and for debugging; the Security section shows it.

## Pairing exchange (X25519 plus a code the owner types on the host)

Messages are JSON on the existing pairing WebSocket, before any credential exists:
1. unit to host: `pair_start {device_id, pk_u}` (32-byte X25519 public key, new for each attempt, base64).
2. host to unit: `{pk_h, c}` with `c = SHA-256("mp-commit" || pk_h || pk_u || n_h)`; `n_h` is 16 random bytes the host keeps.
3. unit to host: `{n_u}` (16 random bytes).
4. host to unit: `{n_h}`. The unit checks `c` and aborts on a mismatch.
5. Both sides compute `sas = uint32_be(SHA-256("mp-sas" || pk_u || pk_h || n_u || n_h)[0:4]) mod 1000000`, six digits with leading zeros. The unit shows it on its screen. The owner types it on the host page and approves. A wrong code aborts, counts against the existing attempt limits, and the unit drops its keys.
6. host to unit: `paired {}`.

## Link key

- `z = X25519(sk, peer_pk)` (32 bytes).
- `K = HKDF-SHA256(ikm = z, salt = SHA-256(pk_u || pk_h || n_u || n_h), info = "maipai-stackchan-link-key-v2" || 0x00 || device_id lower case, L = 32)`.
- `PSK = HKDF-SHA256(ikm = K, salt = empty, info = "maipai-stackchan-link-psk-v2" || 0x00 || identity, L = 32)`; identity is the device id, lower case, as before.
- The device token is not an input anywhere. If a token stays as an app credential it is sent only inside TLS.

Reference vectors: `scripts/link-key-vector.py` (standard library; X25519 per RFC 7748), checked by `host/tests/firmware/linkkey_core_test.c` through the unit's core `maipai_linkkey_core.h`.

## Storage

Unit (NVS, namespace `mp_link`): `K`, 32 bytes. Ephemeral keys and nonces are freed after pairing. Host (pairing file, mode 600): `K` for each unit; `token_sha256` is not kept for units paired this way.

## Migration

No unit uses the old derivation yet (the firmware half was not started), so it is replaced, not kept. A unit paired before this exchange re-pairs once (its record and settings stay): the exchange runs on its next connection and the owner's typed code authorizes it. Home-paired units: Home runs the exchange and keeps `K`.

## Host interface for the app track

- Pairing WebSocket messages as above (new `pair_start` on the plain port, 18775 and 8765 stay the pairing entry).
- Host page: a six-digit field and an Approve button in the pairing card; a mismatch shows "The code did not match. Nothing was paired." and counts as a failed try.
- Pairing record fields: `link_key_hex` (K), `link_encryption`.
- PSK derivation for the TLS callbacks: from `K` as above (replace the token-digest step in `link_security.py`).

## Cost (estimates, measure with the memory gate)

Flash 2 to 8 KB. Internal RAM at pairing only (about 1 to 2 KB stack); afterwards 32 bytes. PSA has X25519, SHA-256 and HKDF. The firmware switch: `CONFIG_MAIPAI_LINK_PSK` (default n), off costs nothing.

## Not covered

The owner approving without reading the unit's screen, and the key at rest on the host or on the unit (flash encryption is a separate decision).

## Host half as built (app track, 2026-11-18): details the firmware half needs

- **Socket framing.** The unit opens the plain pairing port (8765) with `Device-Id`, `Client-Id` and the new header `Pair-Exchange: 1`, no `Authorization`. The host speaks JSON text frames: unit `{"type":"pair_start","pk_u":<base64 32 bytes>}`; host `{"type":"pair_host","pk_h":<base64>,"c":<base64 32 bytes>}`; unit `{"type":"pair_nonce","n_u":<base64 16 bytes>}`; host `{"type":"pair_reveal","n_h":<base64 16 bytes>}`; then the host waits up to 5 minutes for the owner's six digits and answers `{"type":"paired"}` or `{"type":"pair_failed","reason":<plain words>}` and closes. Messages out of order, wrong sizes or an unusable key (all-zero shared secret) end the exchange with `pair_failed`. Without the header the old refusal is unchanged.
- **Limits.** Three wrong codes for one unit make it wait 10 minutes; another unit is not held back; one live exchange per unit; the per-address pairing-request limit applies.
- **After pairing.** The host keeps `link_key_hex` (K), `client_id` and `link_encryption: "required"` and no token digest. On the encrypted ports such a unit is authorized by the PSK handshake plus its `Client-Id` header (no token). A paired unit therefore needs the Client-Id to stay secret: it travels only inside TLS.
- **Identity check.** The TLS library does not tell the handler which PSK identity a connection used, so the host checks the `Device-Id` and `Client-Id` headers against the record. Firmware may add a first-frame proof (an HMAC of the session id keyed with K); the host would then verify it.
- **Vectors.** `host/tests/test_link_exchange.py` checks the host key schedule against `scripts/link-key-vector.py` (X25519 per RFC 7748, commitment, six digits, K, PSK).
- **Host page.** The pairing card on the Home page lists a unit that is showing six digits and takes the digits (`GET /api/stackchan/pairings/waiting`, `POST /api/stackchan/pairings/code-entry`, host computer only; a phone token cannot approve).

## Unit half as built (firmware track, 2026-11-18)

- **Start.** The MCP tool `self.link.pair {url}` (default: the saved server address, which must be a plain `ws://` address) opens the pairing socket with the headers above. It refuses on a locked unit and on a unit that already holds a link key (the owner erases the key on the unit first), so a stolen host connection cannot replace a key.
- **Screen.** At the reveal the unit shows "Type 123456 on the host to pair" as a notice and repeats nothing: the host card should show the waiting unit for the full five minutes. The unit gives up after 330 seconds, on `pair_failed` or `pair_abort`, on a closed socket, and on any message out of order.
- **After "paired".** The unit computes `K` and saves it in NVS (`mp_link`); the voice and avatar connections then use the encrypted ports with the PSK handshake (a saved plain address is rewritten, and never used in the clear while a key is stored).
- **Switch.** All of it is under `CONFIG_MAIPAI_LINK_PSK` (default off); the `linkpsk` build overlay turns it on.

## Wrong codes are counted per source (2026-11-18)
A wrong code counts against the source address that sent it (three a unit every ten minutes each). Only the owner's side, this host's loopback or a signed-in settings session, can end the exchange with a wrong code; any other source's wrong code only counts against that source, and all such sources together get twelve a unit. A second start for a unit that is already waiting for its digits is refused. So a stranger's guesses never lock the owner out or end the owner's pairing.

## The owner confirms on the unit, and what plain-link pairing assumes (2026-11-18)
After the host says `paired`, the unit does not keep the key yet. It derives it, shows "Keep this host?" with the six digits, and keeps the key only when the owner taps **Keep** within a minute. Cancel, or no tap, wipes the key and the unit tells the host (`pair_abort`). The unit also refuses an all-zero or small-order host key and an all-zero shared secret. Pairing over the plain link still assumes **nobody interfering with the link** during the few seconds the owner is at the host: someone relaying the whole exchange can show the owner a code too. The tap on the unit and the code typed on the host together are what the owner checks.
