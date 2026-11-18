# Screen audit against the physical standard


> Part of the [playground docs](../playground/index.md). This page is the full reference; the playground pages are the guide.

Made by `scripts/virtual-unit/screen_audit.py --write`. Panel 40.6 mm wide, 7.87 px a millimeter (assumed from the 2 inch diagonal). Targets under 48 px, targets closer than 8 px, labels under the 16 px font and clipped targets fail; targets under 56 px and 16 px labels warn. Annotated frames: `docs/dev/screens/annotated/`.

| Screen | Targets | Failures | Warnings | First failures |
|---|---:|---:|---:|---|
| es-more-menu | 6 | 0 | 1 |  |
| more-games | 3 | 0 | 1 |  |
| more-menu | 6 | 0 | 1 |  |
| more-version | 2 | 0 | 1 |  |

Total failures: 0 on 4 screens.
