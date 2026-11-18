# Signed update header with a build number (agreed with the firmware track, 2026-11-18)

This note now only points at the agreed format. The proposal is `docs/plan/signed-update-anti-rollback.md` (firmware track); the app track adopted it as written, with one file-name detail.

## Format (little endian), 56 bytes
| Offset | Size | Field |
|---|---|---|
| 0 | 8 | magic `MPUH1` then three zero bytes |
| 8 | 4 | build number, u32, 1 and up, only ever goes up |
| 12 | 4 | image length, u32 |
| 16 | 32 | SHA-256 of the image |
| 48 | 8 | reserved, zero |

## Files
`<image>.hdr` (the 56 bytes) and `<image>.hdr.sig` (Ed25519 over those 56 bytes, 64 bytes). The old `<image>.sig` (a signature over the whole image) stays, unchanged, so a unit built before this still updates once; the new image carries the new verifier. The one detail that differs from the proposal: the header's signature is `.hdr.sig`, not `.sig`, so the two signatures cannot be confused.

## Unit steps
Fetch `.hdr` and `.hdr.sig`; verify the signature over the 56 bytes; check magic and the reserved bytes; refuse unless the build number is higher than the highest it has confirmed (NVS); stream the image while hashing; refuse unless length and SHA-256 equal the header's; store the new build number only after the first-boot trial confirms. The version text is not signed: the host sends it with the update call and the unit trusts only the signed build number.

## Host (built)
`update_header.py` builds, signs and verifies; `scripts/release.sh --build-number N` writes `.hdr` and `.hdr.sig` and refuses a real release whose number is not higher than the last; the Home-driven path fetches `.hdr` and `.hdr.sig` (falls back to `.sig`), checks signature, length, hash and a build number higher than the last this host accepted (`update-builds.json`) and than the unit's `fw_build` fact when it reports one, and serves `.hdr` and `.hdr.sig` at the image address.

## Vectors
`host/tests/fixtures/update-header-vectors.json` (from `scripts/make-update-vectors.py`, public test seed): 12 cases, each `package_hex` (header 56 then signature 64), `image_hex`, `installed_build`, `valid`: good with 16 installed, good with nothing installed; refused: same number, higher installed number (rollback), changed image, signature, build number, length, hash or reserved byte, a package one byte short, a header with no signature.

## Ask of the firmware track
Report the stored build number as the unit fact `fw_build` (integer).
