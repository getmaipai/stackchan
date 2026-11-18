# Screen audit against the physical standard

Made by `scripts/virtual-unit/screen_audit.py --write`. Panel 40.6 mm wide, 7.87 px a millimeter (assumed from the 2 inch diagonal). Targets under 48 px, targets closer than 8 px, labels under the 16 px font and clipped targets fail; targets under 56 px and 16 px labels warn. Annotated frames: `docs/dev/screens/annotated/`.

| Screen | Targets | Failures | Warnings | First failures |
|---|---:|---:|---:|---|
| es-apps-wall | 4 | 4 | 0 | targets at 4,28 and 162,28 are 4 px apart (under 8); targets at 4,28 and 4,122 are 4 px apart (under 8) |
| es-page-actions | 4 | 0 | 4 |  |
| es-page-timers | 3 | 0 | 0 |  |
| es-settings-general | 11 | 16 | 0 | target 76x44 px (9.7 x 5.6 mm) at 4,32: under 48 px; target 76x44 px (9.7 x 5.6 mm) at 4,80: under 48 px |
| es-settings-info | 6 | 9 | 0 | target 76x44 px (9.7 x 5.6 mm) at 4,32: under 48 px; target 76x44 px (9.7 x 5.6 mm) at 4,80: under 48 px |
| first-run-1 | 7 | 5 | 0 | target 64x36 px (8.1 x 4.6 mm) at 252,4: under 48 px; targets at 8,62 and 110,62 are 6 px apart (under 8) |
| first-run-2 | 9 | 20 | 0 | target 44x44 px (5.6 x 5.6 mm) at 4,4: under 48 px; target 64x36 px (8.1 x 4.6 mm) at 252,4: under 48 px |
| first-run-4 | 5 | 8 | 0 | target 44x44 px (5.6 x 5.6 mm) at 4,4: under 48 px; target 64x36 px (8.1 x 4.6 mm) at 252,4: under 48 px |
| first-run-5 | 2 | 1 | 1 | target 44x44 px (5.6 x 5.6 mm) at 4,4: under 48 px |
| first-run-6 | 0 | 0 | 0 |  |
| first-run-next | 2 | 2 | 0 | target 140x42 px (17.8 x 5.3 mm) at 90,192: under 48 px; targets at 8,34 and 90,192 are 6 px apart (under 8) |
| screen-apps-wall | 4 | 4 | 0 | targets at 4,28 and 162,28 are 4 px apart (under 8); targets at 4,28 and 4,122 are 4 px apart (under 8) |
| screen-camera-on | 0 | 0 | 0 |  |
| screen-control-sheet | 8 | 16 | 6 | target 156x44 px (19.8 x 5.6 mm) at 2,140: under 48 px; target 156x44 px (19.8 x 5.6 mm) at 162,140: under 48 px |
| screen-games-wall | 4 | 4 | 0 | targets at 4,28 and 162,28 are 4 px apart (under 8); targets at 4,28 and 4,122 are 4 px apart (under 8) |
| screen-page-actions | 4 | 0 | 4 |  |
| screen-page-clock | 1 | 0 | 0 |  |
| screen-page-games | 6 | 13 | 0 | target 150x44 px (19.1 x 5.6 mm) at 8,38: under 48 px; target 150x44 px (19.1 x 5.6 mm) at 162,38: under 48 px |
| screen-page-timers | 3 | 0 | 0 |  |
| screen-page-timers-running | 2 | 3 | 0 | target 58x44 px (7.4 x 5.6 mm) at 254,52: under 48 px; target 58x44 px (7.4 x 5.6 mm) at 254,98: under 48 px |
| screen-settings-faces | 8 | 14 | 0 | target 76x44 px (9.7 x 5.6 mm) at 4,32: under 48 px; target 76x44 px (9.7 x 5.6 mm) at 4,80: under 48 px |
| screen-settings-general | 11 | 16 | 0 | target 76x44 px (9.7 x 5.6 mm) at 4,32: under 48 px; target 76x44 px (9.7 x 5.6 mm) at 4,80: under 48 px |
| screen-settings-info | 6 | 9 | 0 | target 76x44 px (9.7 x 5.6 mm) at 4,32: under 48 px; target 76x44 px (9.7 x 5.6 mm) at 4,80: under 48 px |
| screen-settings-network | 6 | 10 | 0 | target 76x44 px (9.7 x 5.6 mm) at 4,32: under 48 px; target 76x44 px (9.7 x 5.6 mm) at 4,80: under 48 px |
| screen-subtitles | 0 | 0 | 0 |  |
| screen-timers-app | 9 | 7 | 0 | targets at 4,36 and 4,96 are 4 px apart (under 8); targets at 4,96 and 4,156 are 4 px apart (under 8) |

Total failures: 161 on 26 screens.
