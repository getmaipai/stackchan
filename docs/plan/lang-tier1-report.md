# Tier 1 language report (machine drafts)

Branch `cloud/lang-tier1`. Seven languages: Dutch (nl), Polish (pl), Turkish (tr), Swedish (sv), Danish (da), Norwegian Bokmal (nb), Czech (cs). Every string is a machine draft that no native speaker has read; the completeness table says "machine draft, tier 1".

## What was added
- `host/maipai_body/i18n_tier1.py` and `host/maipai_body/i18n_tier1/<lang>_<n>.json`: 989 strings per language (876 settings page and message strings, 60 robot screen rows, 4 screen word rows, 49 user page titles), 6,923 in all. `i18n.ALL_LANGUAGES` lists them; `SUPPORTED` stays the six complete languages because other tests read per-module word tables for that tuple.
- Review pack: `docs/dev/translation-review/<lang>.csv` for each language (key, English, translation, context, max length, limit, status, note), and `STATUS.md` and `status.json` entries. `scripts/translation-pack.py` and `scripts/ledger_sources.py` register the languages in a few lines; the feature ledger lists them.
- `host/tests/test_i18n_tier1.py`: every key present, nothing empty, placeholders kept, no em dash, lengths within the pack limits (soft limits fail for page rows), robot screen rows drawable, screen word packs accepted by the pack builder, export in step with the data, importer round trip.
- `docs/plan/languages-tiers.md`: Tier 1 glyphs and the flash estimate.

## Checks run
Focused tests pass (41 in the new and fill tests; the other language tests show only missing-library errors in this container: `websockets`, `av`). Each batch also passed a length and placeholder check against the English before it was kept. `spelling-check`, `boundary-check`, `efuse-check` pass. `scripts/check.sh` stops at the hygiene word list, which is missing in this container. The full suite was not run.

## Needs a native reviewer
All seven, every row. Rows the drafters flagged: the native names on `unit.screen.050`; shortened robot screen rows (Polish 022 and 045, Turkish 021, 039 and 058, Czech 012, 013 and 039, Dutch 055); example strings with accents that had to be reworded (`settings.ui.pol.lang.ascii`, `settings.ui.pol.scene.help`, `settings.ui.pol.ov.help`); face names kept in English because people type them (`settings.react.help`); the masculine forms of Calm, High, Medium and Low in Polish; Czech "Licence" and AM/PM as "dop."/"odp.".

## Glyph findings
Dutch, Swedish, Danish and Norwegian need no new glyphs. Polish needs 16, Czech 18, Turkish 6 (40 together). Flash for a Latin-2 subset: about 47 KB for both sizes, about 28 KB for only what the robot rows use. Details in `docs/plan/languages-tiers.md`.

## Not done
Golden frames and contact sheets (the first-run screens are firmware code with six languages); adding the seven screen word packs to `language_packs.WORDS` (pack tests count five); a selectable list entry on the dashboard and the settings language picker.
