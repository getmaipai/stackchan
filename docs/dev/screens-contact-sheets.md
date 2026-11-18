# Screens contact sheets

One PNG per language, built from the golden frames drawn by the unit's own code (`python3 scripts/virtual-unit/scenarios.py`). Frames run left to right, top to bottom, at half size.

## en  ([sheet-en.png](screens/sheet-en.png))

1 cover-connecting-home, 2 cover-connecting-wifi, 3 cover-pairing, 4 cover-update-0, 5 cover-update-62, 6 cover-update-installed, 7 cover-update-refused, 8 cover-wifi-setup, 9 first-run-1, 10 first-run-1-en, 11 first-run-2, 12 first-run-2-en, 13 first-run-4, 14 first-run-4-en, 15 first-run-5, 16 first-run-5-en, 17 first-run-6, 18 first-run-6-en, 19 lock-keypad-empty, 20 lock-keypad-three, 21 lock-keypad-wrong, 22 lock-screen, 23 screen-apps-wall, 24 screen-charging, 25 screen-control-sheet, 26 screen-eyes-only-muted, 27 screen-games-wall, 28 screen-listening, 29 screen-low-battery, 30 screen-muted, 31 screen-offline, 32 screen-page-actions, 33 screen-page-clock, 34 screen-page-games, 35 screen-page-timers, 36 screen-settings-faces, 37 screen-settings-general, 38 screen-settings-info, 39 screen-settings-network, 40 screen-status-normal, 41 screen-timers-app, 42 screen-wifi-flag

## es  ([sheet-es.png](screens/sheet-es.png))

1 es-apps-wall, 2 es-page-actions, 3 es-page-timers, 4 es-settings-general, 5 es-settings-info, 6 es-sheet, 7 first-run-1-es, 8 first-run-2-es, 9 first-run-4-es, 10 first-run-5-es, 11 first-run-6-es, 12 lock-keypad-wrong-es

## fr  ([sheet-fr.png](screens/sheet-fr.png))

1 first-run-1-fr, 2 first-run-2-fr, 3 first-run-4-fr, 4 first-run-5-fr, 5 first-run-6-fr

## de  ([sheet-de.png](screens/sheet-de.png))

1 first-run-1-de, 2 first-run-2-de, 3 first-run-4-de, 4 first-run-5-de, 5 first-run-6-de

## pt  ([sheet-pt.png](screens/sheet-pt.png))

1 first-run-1-pt, 2 first-run-2-pt, 3 first-run-4-pt, 4 first-run-5-pt, 5 first-run-6-pt

## it  ([sheet-it.png](screens/sheet-it.png))

1 first-run-1-it, 2 first-run-2-it, 3 first-run-4-it, 4 first-run-5-it, 5 first-run-6-it

## What the sheets show (read 2026-11-18, after UX07a to UX07c)

- Accents and the opening question and exclamation marks draw in every language (the screens use the Noto Sans basic fonts: 16 and 20 px). Not in the font: the oe ligature, the euro sign and curly quotes; the unit already maps those to plain letters and straight quotes.
- The back arrow and the close mark are symbol glyphs and keep Montserrat; the first version of the font change left them as empty boxes, found on these sheets.
- First-run titles drop from 20 to 16 px when a longer title does not fit, so the size changes from step to step; acceptable, listed for the style pass.
- All first-run steps fit with no clipping in all six languages.

## Not covered

French, German, Portuguese and Italian have only the first-run steps: the unit's app screens (sheet, Settings, Apps and Games walls, pages) carry English and Spanish words only. Translating them into the other four needs the unit's word tables extended (the font now draws the letters).
