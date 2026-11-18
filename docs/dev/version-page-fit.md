# Does the version page fit with the affiliation notice (patch SF69)? Measured 2026-11-18


> Part of the [playground docs](../playground/index.md). This page is the full reference; the playground pages are the guide.

`scripts/virtual-unit/version_page_fit.cc` builds the same root (padding 8, top 58, row gap 6, wrapping flex) and the same labels and fonts as `maipai_more.cc` `build_version()` and measures them with the real LVGL layout (b52 build tree). The notice is the one of `docs/legal/affiliation.json`; the detail lines are those of `maipai_version_core.h` with typical values. The More screens are not drawn by the screens renderer, so this is a measurement, not a golden frame; they are English and Spanish only (the notice is English in the firmware).

| Detail lines kept | Body font | Content bottom (panel ends at 239) | Result |
|---|---|---|---|
| 6 (today plus the notice) | 14 px (Montserrat, as the page uses) | 281 | **overflows by 42 px**: the last detail line wraps and the notice starts below the glass |
| 4 | 14 px | 221 | fits by 18 px |
| 3 | 14 px | 199 | fits by 40 px |
| 4 | 16 px (the secondary text minimum) | 270 | overflows by 31 px |
| 3 | 16 px | 241 | overflows by 2 px |

So the page overflows as SF69 is written, and the only layouts that fit use 14 px text, which is under the screen standard's 16 px minimum (`docs/design/screen-style.md`). The More screens (menu, time zone, network test, version) also have a 44 px Back or Done target and 44 px buttons: they are older than the standard and are not in the screen audit yet.

**Recommendation for the firmware track (never shorten the notice):** make the version page a scrolling pane: the root scrolls vertically, the title and the six detail lines at 16 px, the notice as the last row at 16 px, Back at 56 by 48; content is about 270 px in a 174 px viewport, so it scrolls, and a thin scroll bar shows there is more. The same pattern (a scrolling right pane) is the standard for any list that does not fit. Until that lands, drop Tag, Image and Slot from the page (keep Version, Memory free, Large memory free), which fits at 14 px.
