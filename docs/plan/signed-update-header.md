# Signed update header with a build number (agreement between host and firmware, 2026-11-18)

Status: host half built and tested; firmware half to be built against the vectors below. Replaces the detached signature over the whole image for new releases; the unit keeps accepting the old `.sig` only on units flashed before this exists.

## Why
A signature over the whole image forces the unit to buffer or re-read all of it, and says nothing about which release it is, so an older release signed with the right key installs. A signed 64-byte header fixes both: the unit streams the image through SHA-256 while writing it, checks the hash against the signed header, and refuses a build number that is not higher than the one it already runs.

## Format (big endian), 64 bytes
| Offset | Size | Field |
|---|---|---|
| 0 | 4 | magic `MPUH` |
| 4 | 1 | format, 1 |
| 5 | 3 | zero (must be zero) |
| 8 | 4 | build number, 1 and up, only ever goes up |
| 12 | 16 | version text, ASCII, padded with zero bytes |
| 28 | 4 | image size in bytes |
| 32 | 32 | SHA-256 of the image |

The package is `header (64) || Ed25519 signature over the header (64)` = 128 bytes, served beside the image at `<image>.mph`. The key is the release key; the public half is in the unit.

## What the unit does, in this order
1. Fetch the 128-byte package (refuse any other length).
2. Verify the Ed25519 signature over the first 64 bytes. Refuse on failure.
3. Check magic, format, the three zero bytes. Refuse otherwise.
4. Compare the build number with the highest build it has confirmed (NVS, `mp_update`, key `build`). Refuse unless the new number is **higher**. (No stored number yet: accept.)
5. Stream the image into the update slot while hashing; at the end the size and SHA-256 must equal the header's. Refuse otherwise and keep the old image.
6. After the new image boots and confirms (the existing first-boot trial), store its build number in NVS. A rolled-back trial never raises the stored number.

A deliberate downgrade (support only) needs the physical wipe, as for a factory reset.

## What the host does
- `scripts/release.sh --build-number N` writes `<image>.mph`, refuses a real release whose number is not higher than the last (`dist/last-build-number.txt`), and verifies what it wrote. A test key marks the folder TEST and never touches the last-number file.
- The Home-driven update path fetches `app.bin.mph` (falls back to `app.bin.sig` for old releases), checks the signed header against `[update] trusted_key`, requires the hash and size to match, requires the build number to be higher than the last one this host accepted (`update-builds.json` in the data folder) and than the unit's reported `fw_build` when the unit reports one, and serves the 128 bytes at the image address plus `.mph`.
- Verification code: `host/maipai_body/bodies/stackchan/firmware/update_header.py`.

## Vectors for the firmware test
`host/tests/fixtures/update-header-vectors.json` (made by `scripts/make-update-vectors.py` from the public test seed, same public key as `update-signature-vectors.json`): 11 cases, each with `package_hex`, `image_hex`, `installed_build` and `valid`. Valid: a good package with 16 installed, a good package with nothing installed. Refused: same number as installed, a higher installed number (rollback), the image, the signature, the build number, the version or the hash changed by one bit, a package one byte short, a header with no signature. The firmware C test should run every case and match `valid`.

## Asks of the firmware track
- Implement steps 1 to 6 behind the existing update switch; reuse `update_verify.cc` for Ed25519 over 64 bytes.
- Report the stored build number in the unit facts as `fw_build` (integer) so the host can refuse earlier.
- Tell me if a different field order or size is easier on the unit; the vectors are regenerated from the format in one place.
