# Offline lines on the screen

The playground's mock of owner decision 24, extension (`docs/design/content-pantry.md`, "Lines by situation"; the sound is `docs/design/offline-mumble.md`). With no host and no model the unit picks a canned line for the situation, shows it in the subtitle strip and plays the code-made mumble while the mouth follows it. Nothing here needs a firmware patch: the subtitle strip and the mouth exist on the unit already; the pantry reader that picks the line is the firmware track's (`docs/plan/pantry-reader-firmware.md`).

## What the frame shows

The face with the mouth open at the mumble's level, and the line in the subtitle strip under it: one line of 16 px text, at most about 36 characters. The lines are written to fit one strip line in all six languages; a longer line wraps to a second row and touches the panel edge, which the layout check of the scenarios fails. The real records may be up to 100 bytes (the record's limit), so the unit's reader should show a longer line the way it shows any long subtitle (two rows, scrolling), and the pantry's built-in set keeps its lines short for this strip.

## The six mocked situations

`wake_heard_offline`, `cannot_reach_home`, `back_online`, `touch_head`, `pick_up`, `goodnight`, one line each in English, Spanish, French, German, Portuguese and Italian (`scripts/virtual-unit/offline_lines.py`). They are 6 of the 20 tags of `record.SITUATIONS`; the test checks that each is a real tag. The mouth level of a still frame is the loudest of the first half of the mumble's levels (`mumble.blips`, the same reference the unit's core is tested against).

Frames: `offline-line-<situation>-<language>` (36 scenarios, goldens in `host/tests/golden/screens/`). `host/tests/test_offline_lines.py` checks the limits, the plain voice (no exclamation points), translation, and the mouth.
