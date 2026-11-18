# UX13: the screens at finger size, in batches (playground track)

Owner review of 2026-11-18, the standard in `docs/design/screen-style.md` ("Physical standard"), the audit in `docs/dev/screen-audit.md`. Display-only patches (no safety, lock, cue, limiter or head-motion code). One screen family per batch so a failure on the plain boot proof is easy to find.

| Batch | Patch | Screens | State |
|---|---|---|---|
| 1 | `UX13a-settings-at-finger-size.patch` | Settings (tabs, Done, rows, sliders, style tiles) | written, in ORDER, goldens redrawn, audit zero on the six settings frames, core test passes on the series replay; **not yet proven on a unit** |
| 1b | `UX13b-more-at-finger-size.patch` (with SF69, ONE group) | The More screen: menu, time zone, network test, version with the SF69 notice as the last row, games | on branch `ux/unproven`, goldens and audit zero on the four frames, not proven on a unit |
| 2 | UX13c | Control sheet (two sliders, tiles, status lines: pages, Quiet now and Vision off tiles of decision 22) | not started |
| 3 | UX13d | First-run (Skip 72 x 48, Back 56 x 48, brain tiles, last screen) | not started |
| 4 | `UX13e-games-page-at-finger-size.patch` | Games page (a scrolling grid of 148 x 64 tiles, 8 px gaps, name over best score, scroll bar, 13 games; no More paging) and the Apps and Games walls (150 x 86 tiles, 8 px gap) | written on a branch (not in main), goldens redrawn, audit zero on the four frames, core tests pass; **not yet proven on a unit** |
| 5 | UX13f | Timers and alarms (delete button, rows) | not started |

Notes for the firmware track: the repo's series has five face styles in `MPG_SET_STYLES` while the b49 tree has three (decision 22): UX13a derives the Faces rows from `MPG_SET_STYLES` and its core test follows it, so it works with either. The shared page-indicator component and the scroll affordances come with batches 2 and 4; the audit ratchet (`docs/design/screen-audit-baseline.json`) only lets failures shrink.
