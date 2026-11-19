# Screen audit against the physical standard

Made by `scripts/virtual-unit/screen_audit.py --write`. Panel 40.6 mm wide, 7.87 px a millimeter (assumed from the 2 inch diagonal). Targets under 48 px, targets closer than 8 px, labels under the 16 px font and clipped targets fail; targets under 56 px and 16 px labels warn. Annotated frames: `docs/dev/screens/annotated/`.

| Screen | Targets | Failures | Warnings | First failures |
|---|---:|---:|---:|---|
| clock-classic | 1 | 0 | 0 |  |
| clock-classic-asleep | 1 | 0 | 0 |  |
| clock-datetime | 1 | 0 | 0 |  |
| clock-datetime-12h | 1 | 0 | 0 |  |
| clock-datetime-asleep | 1 | 0 | 0 |  |
| clock-ring | 1 | 0 | 0 |  |
| clock-ring-asleep | 1 | 0 | 0 |  |
| clock-tap-to-datetime | 1 | 0 | 0 |  |
| es-apps-wall | 4 | 0 | 0 |  |
| es-control-sheet | 3 | 0 | 1 |  |
| es-control-sheet-tiles | 7 | 0 | 1 |  |
| es-more-menu | 6 | 0 | 1 |  |
| es-page-actions | 4 | 0 | 4 |  |
| es-page-timers | 3 | 0 | 0 |  |
| es-settings-general | 11 | 0 | 1 |  |
| es-settings-info | 6 | 0 | 1 |  |
| first-run-1 | 7 | 0 | 1 |  |
| first-run-2 | 9 | 0 | 9 |  |
| first-run-4 | 5 | 0 | 5 |  |
| first-run-5 | 2 | 0 | 1 |  |
| first-run-6 | 0 | 0 | 0 |  |
| first-run-next | 2 | 0 | 0 |  |
| more-games | 3 | 0 | 1 |  |
| more-menu | 6 | 0 | 1 |  |
| more-version | 2 | 0 | 1 |  |
| screen-alarms-app | 2 | 0 | 0 |  |
| screen-apps-wall | 4 | 0 | 0 |  |
| screen-camera-on | 0 | 0 | 0 |  |
| screen-control-sheet | 3 | 0 | 1 |  |
| screen-control-sheet-tiles | 7 | 0 | 1 |  |
| screen-games-wall | 4 | 0 | 0 |  |
| screen-page-actions | 4 | 0 | 4 |  |
| screen-page-clock | 1 | 0 | 0 |  |
| screen-page-games | 13 | 0 | 0 |  |
| screen-page-games-end | 13 | 0 | 0 |  |
| screen-page-games-scrolled | 13 | 0 | 0 |  |
| screen-page-timers | 3 | 0 | 0 |  |
| screen-page-timers-more | 2 | 0 | 0 |  |
| screen-page-timers-one | 4 | 0 | 0 |  |
| screen-page-timers-running | 2 | 0 | 0 |  |
| screen-settings-faces | 8 | 0 | 1 |  |
| screen-settings-general | 11 | 0 | 1 |  |
| screen-settings-info | 6 | 0 | 1 |  |
| screen-settings-network | 6 | 0 | 1 |  |
| screen-subtitles | 0 | 0 | 0 |  |
| screen-timers-app | 9 | 0 | 0 |  |

Total failures: 0 on 46 screens.
