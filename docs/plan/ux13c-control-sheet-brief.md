# UX13c brief: the control sheet at finger size (for a Codex lane, read by the playground track before it lands)

Placement: unit (display only: no safety, lock, cue, limiter or head-motion code). Files: `firmware/main/hal/maipai_pages_core.h` (layout), `maipai_pages.cc` (drawing, `build_sheet`, `sheet_refresh`), the host test `host/tests/firmware/pages_core_test.c`. Author the patch as `firmware/patches/UX13c-control-sheet-at-finger-size.patch` on the branch `ux/unproven`, never on main. Standard: `docs/design/screen-style.md` ("Physical standard"); audit: `scripts/virtual-unit/screen_audit.py` (today `screen-control-sheet` has 16 failures: the sliders' rows and tiles under 48 px, tiles 2 px apart, 16 px labels).

## What is wrong today
`mpg_sheet_layout` puts a status row, two slider rows of 44 px, and six icon tiles of 50 by 60 px (2 px apart, a 16 px label) into one sheet that covers the lower part of the glass. Tiles are under the 56 px primary size and 2 px apart; the sliders' grab area is 44 px; the labels are 16 px.

## Design
- The sheet becomes **two pages** with the shared page dots (8 px above the bottom edge, same component as the games wall once it exists; until then draw the dots with `MAC_WALL_DOT_*` values), a swipe left or right changes page, and a small next target at the right for those who do not swipe.
- **Page 1, sliders and status:** the status row (Wi-Fi bars, time, battery) as today (it is not a target); Volume and Brightness as two stacked rows: the 20 px label and value above, the slider below with a **56 px grab area** (16 px track, 20 px extended area each side), 8 px between the rows.
- **Page 2, tiles:** the tiles in two rows of three, each **at least 88 by 56 px**, 8 px apart (gap and margin 8), the icon above a 16 px label only where it fits, otherwise the 20 px label alone; the six items are Mute, Quiet now (decision 22), Lock, Apps, Vision off (replaces Games, decision 22) and More (the gear).
- The grabber handle and the swipe-down close stay. The sheet height is fixed (no change with the item count): two pages with six tiles and two sliders always fit.
- No tile or target overlaps another; the extended click area may exceed the drawn size but never overlaps a adjacent target.
- The strings in `MPG_SHEET_TITLE` stay English and Spanish; Quiet now and Vision off use the words of decision 22 (`docs/dev/unit-choices-audit.md`).

## Tests to change or add
`pages_core_test.c`: the layout invariants (every target at least 56 px high, 8 px gaps, nothing off the glass, the two pages hold every item, the page count), the swipe and next target hit boxes; keep the existing config parsing tests. Goldens: `screen-control-sheet`, a page-2 frame and the Spanish pair; then `screen_audit.py --write` and lower `docs/design/screen-audit-baseline.json` for the sheet frames to 0.

## Why not done yet
It rewrites a layout core and its drawing, a gesture (page swipe inside the sheet) and a host test: a day of careful work, and it must be read diff by diff. The playground track did the Settings batch (UX13a) and the More batch (UX13b with SF69) first.
