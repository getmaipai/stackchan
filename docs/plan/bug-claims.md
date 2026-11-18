# Bug claims

One line per claimed bug group. Whoever claims a group fixes it, failing test first (the tests are in `host/tests/test_cross_review_open_bugs*.py`; `python3 scripts/review-status.py` shows what is open). Others leave claimed groups alone. Add a line before starting; change the status when it lands.

| Claimed by | Group | Files | Status |
|---|---|---|---|
| playground (virtual unit session) | web flasher: manifest origin, manifest signature check, part paths, offsets and overlaps | `flasher/flasher-core.js`, `flasher/flasher.js`, `flasher/test/`, `host/tests/test_flasher_page.py` | claimed 2026-11-18 |
| playground (virtual unit session) | memory notes credential words: pw and passwd, government ids without dashes, passport numbers, cloud key ids and signed tokens | `host/maipai_packages/memory_notes/admission.py`, `host/tests/test_memory_notes.py` | claimed 2026-11-18 |
