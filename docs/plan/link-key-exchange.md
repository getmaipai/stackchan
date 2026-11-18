# Link key exchange for the encrypted link (design, 2026-11-18)

Placement: unit (firmware) and host. Replaces the key derivation in `docs/design/encrypted-link.md` (that note's derivation took the device token as input; this one takes nothing that travels on the network). Firmware half: patches follow this note behind their own switch. Host half: app track (HS-1, HS-2).

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
