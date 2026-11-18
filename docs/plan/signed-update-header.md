# Signed update header with a build number (agreed with the firmware track, 2026-11-18)

This note now only points at the agreed format. The proposal is `docs/plan/signed-update-anti-rollback.md` (firmware track); the app track adopted it as written, with one file-name detail.

## Format (little endian), 56 bytes
| Offset | Size | Field |
|---|---|---|
| 0 | 8 | magic `MPUH1` then three zero bytes |
| 8 | 4 | build number, u32, 1 and up, only ever goes up |
| 12 | 4 | image length, u32 |
| 16 | 32 | SHA-256 of the image |
| 48 | 8 | board id: ASCII, padded with zeros (CoreS3 StackChan: `m5cores3`); all zero is refused |

## Files
`<image>.hdr` (the 56 bytes) and `<image>.hdr.sig` (Ed25519 over those 56 bytes, 64 bytes). The old `<image>.sig` (a signature over the whole image) stays, unchanged, so a unit built before this still updates once; the new image carries the new verifier. The one detail that differs from the proposal: the header's signature is `.hdr.sig`, not `.sig`, so the two signatures cannot be confused.

## Unit steps
Fetch `.hdr` and `.hdr.sig`; verify the signature over the 56 bytes; check the magic and the board id (refuse a header whose id is all zero or is not this build's `CONFIG_MAIPAI_BOARD_ID`); refuse unless the build number is higher than the highest it has confirmed (NVS); stream the image while hashing; refuse unless length and SHA-256 equal the header's; store the new build number only after the first-boot trial confirms. The version text is not signed: the host sends it with the update call and the unit trusts only the signed build number.

## Host (built)
`update_header.py` builds, signs and verifies; `scripts/release.sh --build-number N` writes `.hdr` and `.hdr.sig` and refuses a real release whose number is not higher than the last; the Home-driven path fetches `.hdr` and `.hdr.sig` (falls back to `.sig`), checks signature, length, hash and a build number higher than the last this host accepted (`update-builds.json`) and than the unit's `fw_build` fact when it reports one, and serves `.hdr` and `.hdr.sig` at the image address.

## Vectors
`host/tests/fixtures/update-header-vectors.json` (from `scripts/make-update-vectors.py`, public test seed): 12 cases, each `package_hex` (header 56 then signature 64), `image_hex`, `installed_build`, `valid`: good with 16 installed, good with nothing installed; refused: same number, higher installed number (rollback), changed image, signature, build number, length, hash or board id byte, a package one byte short, a header with no signature, a header with a board id of all zero, a header for another board.

## Ask of the firmware track
Report the stored build number as the unit fact `fw_build` (integer).

## Board id (decision 2026-11-18, firmware track built, app track to follow)
The 8 bytes that were reserved now name the board the image is built for, so a signed image for another product or board cannot be installed by mistake or on purpose. The unit's own id is the Kconfig string `CONFIG_MAIPAI_BOARD_ID` (default `m5cores3`, 1 to 8 ASCII characters; an empty or longer value refuses every header). An all-zero id is refused from this version on, so releases built before it no longer install on a unit with this firmware.
- **Firmware (done):** `maipai_updatehdr_core.h` (`muh_parse` takes the board id; reasons "the header has no board id" and "the header is for another board"), `ota.cc`, Kconfig; the header signature check in `update_verify.cc` is unchanged (it signs and verifies the 56 bytes as a whole).
- **Host (minimal edit made with the firmware, app track to review):** `update_header.py` `build_header(..., board_id=BOARD_ID)`, `parse_header` refuses an all-zero id and returns `board_id`; `scripts/make-update-vectors.py` writes the vectors with the board id and adds three cases (one bit changed, all zero, another board). `scripts/release.sh` builds the header with the default board id; for another board pass it to `build_header`, and set the same string as `CONFIG_MAIPAI_BOARD_ID` when building that image. `verify_package` takes the expected `board_id` (default `m5cores3`) and refuses a package for another board before it is sent; `scripts/release.sh --board-id ID` names another board (default `m5cores3`) and verifies the header against it; tested in `test_cross_review_open_bugs_3.py`.
