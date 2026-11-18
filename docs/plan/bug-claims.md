# Bug claims

One line per claimed bug group. Whoever claims a group fixes it, failing test first (the tests are in `host/tests/test_cross_review_open_bugs*.py`; `python3 scripts/review-status.py` shows what is open). Others leave claimed groups alone. Add a line before starting; change the status when it lands.

| Claimed by | Group | Files | Status |
|---|---|---|---|
| playground (virtual unit session) | web flasher: manifest origin, manifest signature check, part paths, offsets and overlaps | `flasher/flasher-core.js`, `flasher/flasher.js`, `flasher/test/`, `host/tests/test_flasher_page.py` | fixed by the app track (commits e69624d, 133eaa8); post-download size checks added by playground 2026-11-18 |
| playground (virtual unit session) | memory notes credential words: pw and passwd, government ids without dashes, passport numbers, cloud key ids and signed tokens | `host/maipai_packages/memory_notes/admission.py`, `host/tests/test_memory_notes.py` | fixed by the app track (bbdefc2, 6ea5a4d); the red team found obfuscation gaps, now open in `test_cross_review_open_bugs_3.py` (owner app) |
| playground (virtual unit session) | first run name step: StackChan first and default, the host takes the picked name (owner request 2026-11-18) | `firmware/patches/UX11-first-run-name-stackchan-first.patch`, `host/maipai_body/first_run_name.py`, a few lines in `app.py`, `units.py`, `settings_page.py`, `companion.py` | landed with this commit |
