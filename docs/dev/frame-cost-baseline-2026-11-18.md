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
| screen-page-clock | 91 | 9 | 0.00 | 0.0 |
| screen-page-timers | 91 | 0 | 0.00 | 0.0 |
| screen-control-sheet | 91 | 2698 | 0.01 | 1.1 |
| screen-apps-wall | 91 | 0 | 0.00 | 0.0 |
| screen-games-wall | 91 | 0 | 0.00 | 0.0 |
| screen-settings-general | 91 | 0 | 0.00 | 0.0 |
| screen-eyes-only-muted | 91 | 2200 | 0.00 | 0.9 |
| first-run-1 | 91 | 2437 | 0.01 | 1.0 |

## How to read it

- Pixels flushed per frame is exact for the unit's own drawing code: it does not depend on the Mac. A static screen flushes 0 pixels.
- Host ms per frame is the time of the same drawing on this Mac: use it to compare screens with each other, not as unit time.
- The estimated unit flush time uses the one measured number we have (a full-screen flush of 153,600 bytes takes 26 to 35 ms on the unit, `docs/design/picture-faces-2026-11-16.md`), taken as 30 ms. It covers the flush only, not the drawing, so the real frame is longer.
- Finding (fixed by patch UX06): before it, full-screen screens flushed 2,600 to 2,700 pixels per frame, as much as the face, because the face behind a cover kept its gaze drift and blink going. With UX06 the face update rests while a full-screen screen is up: pages, the Apps and Games walls and Settings flush 0 pixels per frame (the clock page 9, its seconds). The half-height control sheet keeps the face live, so it still flushes about 2,700. The first-run screens are not registered as screens yet and still flush about 2,400 per frame during first run only. A sleeping face flushes 0.
- Lane P target: when a change raises pixels flushed per frame of a screen, say so here.
