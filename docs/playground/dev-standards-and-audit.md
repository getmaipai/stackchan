# Standards and the audit

The physical screen standard is in `docs/design/screen-style.md`: targets 56 px (primary) and 48 px (secondary), 8 px gaps, text at least the 16 px font, on a panel of about 7.87 pixels a millimeter (assumed from the 2 inch diagonal until measured).

`scripts/virtual-unit/screen_audit.py` reads the unit's own click areas and line heights from the renderer, judges each screen and writes annotated frames to `docs/dev/screens/annotated/`. `host/tests/test_screen_audit.py` holds every screen to `docs/design/screen-audit-baseline.json`: failures may only shrink, and a new screen has none. The constants are in `scripts/virtual-unit/screen_standard.py`, one file, so a corrected panel size re-judges everything.

Back: [index](index.md).
