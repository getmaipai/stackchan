# Language tiers

Owner decision 18 (2026-11-18) adds languages in tiers. This page holds the facts each tier needs. Status of every language: `docs/dev/translation-review/STATUS.md`.

## Tier 1 glyphs

Tier 1 is Dutch, Polish, Turkish, Swedish, Danish, Norwegian (Bokmal) and Czech. The robot's screen font is Noto Sans basic at 16 and 20 px with the Latin-1 range (0x20 to 0x7E and 0xA0 to 0xFF). The font tool is not in this repository and no font file is vendored, so the cost below is an estimate from glyph counts, not a build.

| Language | Letters outside Latin-1 | Count |
|---|---|---|
| Dutch, Swedish, Danish, Norwegian | none (a, o, e, ae, oe, aa letters are all in Latin-1) | 0 |
| Polish | A-ogonek, a-ogonek, C-acute, c-acute, E-ogonek, e-ogonek, L-stroke, l-stroke, N-acute, n-acute, S-acute, s-acute, Z-acute, z-acute, Z-dot, z-dot | 16 (the Latin-1 letter o-acute is already in) |
| Czech | C-caron, c-caron, D-caron, d-caron, E-caron, e-caron, N-caron, n-caron, R-caron, r-caron, S-caron, s-caron, T-caron, t-caron, U-ring, u-ring, Z-caron, z-caron | 18 (the acute vowels are Latin-1) |
| Turkish | G-breve, g-breve, dotted capital I, dotless i, S-cedilla, s-cedilla | 6 (c-cedilla, o and u with diaeresis are Latin-1) |
| All three together | no letter is shared | 40 |

Letters the tier 1 drafts actually use today (all 989 strings): 29 glyphs. On the robot's own screen (the 60 `unit.screen.*` rows): 24 glyphs (Polish 10, Czech 9, Turkish 5).
Other letters wait for later languages and are not counted: Hungarian o-double-acute and u-double-acute (2 more glyphs), the rest of the Latin Extended-A block.

Cost estimate. The 16 px font is 87 KB of flash for about 190 glyphs (`docs/design/screen-style.md`), so about 0.46 KB per glyph at 16 px, and about 0.72 KB at 20 px (area ratio 1.56).

| Subset | Glyphs | 16 px | 20 px | Both |
|---|---|---|---|---|
| Letters used on today's robot screen rows | 24 | 11 KB | 17 KB | about 28 KB |
| Full tier 1 alphabets (Latin-2 subset) | 40 | 18 KB | 29 KB | about 47 KB |
| Whole Latin Extended-A block, for later tiers | 128 | 59 KB | 92 KB | about 150 KB |

Decision. Per decision 18 b, the subset is not in the base image. It ships inside the Polish, Czech and Turkish language packs (installed-set items, decision 17): flash or PSRAM is used only while one of those languages is installed. Until a pack carries the glyphs, the drafts keep a Latin-1 form for the robot screen (the `drawn` map in each `i18n_tier1/<lang>_<n>.json`, with the proper spelling in the review CSV `note` column). The settings page is drawn by the browser and needs no font from us.

## What tier 1 left undone

- The first-run language list and its golden frames are drawn by firmware code that holds six languages by index (`frun step N <index>`); the seven new languages need firmware work and a font pack first. The contact sheets and goldens were not extended.
- The language-pack words (`pack.*` rows) are drafted and tested against the pack builder but not yet added to `language_packs.WORDS`, because the pack tests count five shipped packs.
