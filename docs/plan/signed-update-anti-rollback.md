# Signed update with a build number (proposal for the app track, 2026-11-18)

Placement: release script and host (app track), unit verifier (firmware track).

Today the detached signature (64 bytes, Ed25519) covers the image bytes only, so any older signed image installs, and the version text the host sends is not signed. Proposal:

1. A header file next to the image, `<image>.hdr`, 56 bytes: magic `MPUH1\0\0\0` (8), `build` u32 little endian (4), `image_len` u32 (4), `sha256(image)` (32), `reserved` u64 zero (8).
2. The signature covers the 56 header bytes, not the image. The unit streams the image through SHA-256 while it writes it and refuses the install unless the hash and length equal the header's.
3. `build` is a counter the release script raises on every release (it is also compiled into the image, shown on the version screen). The unit refuses a header whose `build` is not greater than the running build, and records the highest build it has accepted in NVS so a rollback through a second route fails too.
4. The host sends `version` and `build` with the start call (`self.robot.update` or the current update tool); the unit checks both against the signed header, never the other way round.
5. The wireless update asks for `<image>.hdr` and `<image>.sig` (the signature of the header) in place of the single `.sig`. A unit built before this keeps the old check until it is updated once by cable or by the old path (the new image carries the new verifier).

Release script: write the header, sign it with the release key, publish the three files; the test key and the host test (`test_stackchan_firmware_update.py` family) cover a lower `build`, a wrong hash, a wrong length and a bad signature. Firmware: the verifier change follows once the header format is agreed.

## Unit half as built (firmware track, 2026-11-18)

- The image carries its own build number: `CONFIG_MAIPAI_FW_BUILD` (0 to 2147483647, default 0). `FW_BUILD=<n> bash scripts/fw-build.sh TREE KIND` sets it. The floor a new header must beat is the higher of that number and the confirmed number kept in flash (`minbuild`), so a unit flashed over USB, or with its settings erased, still refuses an older signed release.
- `self.version.get` reports `fw_build` as that floor.
- A header build above 2147483647 is refused; a new image whose boot partition cannot be set leaves no pending build number behind.
- The release script (app track) passes the same number it writes into the signed header as `FW_BUILD`.
