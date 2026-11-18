# Illustrated character packs

A character pack is one ZIP file that holds `manifest.json` and the pictures for one illustrated character. The host reads the pack and sends its pictures to the robot.

## Manifest

The manifest is UTF-8 JSON. It has `format: 1`, a `name` of 1 to 40 characters, an `author` of 1 to 60 characters, a `license` with an SPDX ID or `own work`, a `mode`, and a `looks` object. The name and author must not contain email addresses, phone numbers, or street addresses.

`looks` maps expressions from the host picture face slots to lists of image paths. `neutral` is required. Picture and overlay packs use exactly one image in each listed slot. Sequence packs use up to six images in each listed slot and set `fps` from 1 to 12. Overlay packs set an `overlay` object with the eye and mouth placement values used by the host.

Images are PNG or JPEG. Each image may be at most 4 MB and 12,000,000 pixels. A ZIP may have at most 64 entries and expand to at most 16 MB. Paths must stay inside the ZIP folder. The validator reads images from the ZIP without extracting them.

## Build and check

Put files named `neutral.png`, `happy.jpg`, and so on in a folder, then run `stackchan character build SRC OUT.zip --name N --author A --license L`. Sequence files add a frame number, such as `neutral_1.png` and `neutral_2.png`; choose `--mode sequence` and optionally set `--fps`.

Run `stackchan character check PACK.zip` to see every problem. A valid pack prints `Pack is valid.`.
