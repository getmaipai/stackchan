# Frame cost baseline from the virtual unit (2026-11-18)

Lane P baseline. Measured with `python3 scripts/virtual-unit/frame_cost.py --write` on the host renderer in dirty-area mode (only changed areas drawn and flushed, as on the unit), 3 s of each screen after it settled.

| Scenario | Frames in 3 s | Pixels flushed per frame | Host ms per frame | Estimated unit flush ms per frame |
|---|---|---|---|---|
| face-neutral | 91 | 3200 | 0.01 | 1.2 |
| face-happy | 91 | 3432 | 0.01 | 1.3 |
| speak-90 | 91 | 2688 | 0.01 | 1.1 |
| face-thinking | 91 | 3200 | 0.01 | 1.2 |
| face-sleeping | 91 | 0 | 0.00 | 0.0 |
| screen-status-normal | 91 | 3200 | 0.01 | 1.2 |
| screen-page-clock | 91 | 2707 | 0.01 | 1.1 |
| screen-page-timers | 91 | 2698 | 0.01 | 1.1 |
| screen-control-sheet | 91 | 2698 | 0.01 | 1.1 |
| screen-apps-wall | 91 | 2688 | 0.01 | 1.1 |
| screen-games-wall | 91 | 2688 | 0.01 | 1.1 |
| screen-settings-general | 91 | 2609 | 0.01 | 1.0 |
| screen-eyes-only-muted | 91 | 2200 | 0.00 | 0.9 |
| first-run-1 | 91 | 2437 | 0.01 | 1.0 |

## How to read it

- Pixels flushed per frame is exact for the unit's own drawing code: it does not depend on the Mac. A static screen flushes 0 pixels.
- Host ms per frame is the time of the same drawing on this Mac: use it to compare screens with each other, not as unit time.
- The estimated unit flush time uses the one measured number we have (a full-screen flush of 153,600 bytes takes 26 to 35 ms on the unit, `docs/design/picture-faces-2026-11-16.md`), taken as 30 ms. It covers the flush only, not the drawing, so the real frame is longer.
- Finding: full-screen screens (pages, the Apps and Games walls, Settings, first run) flush 2,600 to 2,700 pixels per frame, the same order as the face itself (2,700 to 3,400), although nothing on them moves. The face behind a cover keeps its gaze drift and blink going and LVGL redraws the covered area each time. Pausing the face update while a full-screen screen is up would take those screens to 0 pixels per frame (about 1 ms of flush per frame saved on the unit). A sleeping face already flushes 0.
- Lane P target: when a change raises pixels flushed per frame of a screen, say so here.
