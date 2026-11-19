# Face styles as recipes

Status: drawn and measured on the virtual unit; patch `UXF01-face-style-recipes.patch` waits on branch `ux/faces` for a unit build. Not flashed.

A face style is 44 bytes of numbers. The unit reads them into one writable style row and draws the face from that row, so a style you have not installed costs no memory. This is phases 1 and 2 of `docs/plan/face-parts.md`, built for the numbers and four eye designs rather than for a bank of parts.

## What a recipe holds

| Bytes | Field |
|---|---|
| 0 to 3 | `MPS1` |
| 4 | Version, 1 |
| 5 | Eye design: standard, pie, neon, slit, heart |
| 6 | Decoration: none, cat, robot, blush, hose, neon |
| 7 | Lid floor, 0 to 70 percent (a sleepy style never opens fully) |
| 8 to 13 | Mouth kind, roundness, pupil, brows, drift, brow thickness |
| 16 to 27 | Name, up to 12 letters, digits or underscores |
| 28 to 43 | Eight numbers: eye size, eye spacing, eye height, mouth place, mouth width, mouth thickness, eye width, eye height |

The reader (`ml_recipe_parse` in `maipai_look_core.h`) checks every number against what the face can draw: sizes 10 to 120, spacing 30 to 110, the top of the eyes below the face zone's top edge even when surprised, the mouth inside the zone. A bad recipe answers one plain sentence and changes nothing. The style asset kind holds 256 bytes; a recipe uses 44.

Sources are `firmware/styles/NAME.json`. `python3 scripts/face-recipe.py build` writes `NAME.rcp`; `check` (part of `scripts/check.sh`) fails when they differ.

## The ten recipes

Classic and Eyes only were base rows before; they are recipes now. Round, Cat, Robot, Sleepy, Pixel and Heart eyes come back from the set-aside list. Rubber hose and Neon anime are new, with original shapes only.

- **Rubber hose:** a tall oval eye with a big dark middle and a wedge cut out of it, a wide grin, two round cheeks and a three-hair tuft.
- **Neon anime:** a hollow ring eye with a soft glow, a bright iris that follows the gaze, a dark middle and a spark; four small sparkles at the sides. Big eyes stays the filled-eye anime look.

## How it draws

Eyes are drawn from a shape list, as for the base styles; the new eye designs add shapes to that list (a wedge, a ring, a slit, a heart). Decorations are a short fixed list drawn by one LVGL object that exists only while the style has any. Colors, backgrounds, moods, speech and the privacy marks work as for the base styles. A style change redraws the screen once (about 56 to 65 ms).

## Five more moods

Patch `UXF02-extended-moods.patch` adds joy, excited, shocked, curious and worried to the twelve moods (the owner-approved expressive set). Each is a table row and a pose, so every style draws it with the same shapes and no new memory. Nothing on the unit picks them yet; the host's face vocabulary names them.

## Memory

| State | Cost |
|---|---|
| No recipe installed | Nothing new. The writable row is built the first time a style asks for it (about 70 bytes of internal RAM). |
| One installed | 44 bytes in an asset slot (flash; 8 slots at most). |
| Active, with decorations | One object, about 160 bytes of internal RAM, deleted when the style changes. |
| Flash for the reader and the eye designs | About 2 KB. |

The unit gate (internal free median 40,000, lowest 24,000) is not touched. The numbers above come from the patch and the host build; they have not been read on a unit.

## Checks

- `host/tests/firmware/face_recipe_core_test.c`: the reader on every recipe and on bad ones, every emotion and blink fitting the shape list, every decoration inside the face zone, and the base styles unchanged (the existing `look_core_test.c` runs against the patched header).
- `host/tests/test_face_styles_golden.py`: a digest of 13 moods for every style, four face colors and three backgrounds.
- `scripts/virtual-unit/face_matrix.py` writes the contact sheet and the pictures in `docs/images`. `scripts/virtual-unit/face_style_cost.py` writes the frame cost.
