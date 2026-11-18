# Build report: b33-plain

Made by `scripts/release-report.py` from `b33`. Numbers that were not measured say so.

## Images

| Build | App image bytes | OTA slot bytes | Used | Free | Room left before the 20 percent rule |
|---|---|---|---|---|---|
| plain (the image the owner runs) | 3,721,344 | 5,177,344 | 71.9 percent | 1,456,000 | 420,531 |
| gate (memory line on) | not found | | | | |
| bench (serial tools on) | not found | | | | |

Assets image `generated_assets.bin`: 4,463,226 bytes of the 6,225,920 byte assets partition (71.7 percent used, 1,762,694 free).

## Memory (internal RAM, bytes)

Not measured for this report: pass `--memory-log` with the log `scripts/fw-stress.py` wrote. The gate floors are in `docs/dev/gate-numbers.md`.

## Frame cost per screen (virtual unit baseline)

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
| first-run-started | 91 | 0 | 0.00 | 0.0 |

Source: `docs/dev/frame-cost-baseline-2026-11-18.md` (host renderer, dirty-area mode; pixels are exact, milliseconds are an estimate).

## Counts

- Firmware tools: 141 (7 user-only).
- Patches in ORDER: 282 (17 display patches named UX).
- Golden frames in `host/tests/golden`: 126.
