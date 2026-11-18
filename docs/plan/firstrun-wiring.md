# First-run flow: what the firmware track wires (2026-11-18)

Patches UX05a (rules, `hal/maipai_firstrun_core.h`) and UX05b (screens, `hal/maipai_firstrun.h/.cc`) are in `firmware/patches/ORDER`. They draw and decide; they save nothing and start nothing by themselves.

The firmware track must:
1. At boot, if no saved first-run record exists, call `maipai_firstrun_init(&host)` once and `maipai_firstrun_start()` under the LVGL lock (host struct: `wifi_set`, `hub_known`, `apply_language`, `open_wifi_setup`, `finished`).
2. In `open_wifi_setup`, hand over to the existing Wi-Fi setup cover and call `maipai_firstrun_wifi_done()` when Wi-Fi is joined.
3. In `finished(lang, name, mode)`: save the record (language, name index 0 to 5, mode 0 home or 1 own) so the flow never shows again; apply the language; tell the host the name and mode.
4. Resume: a unit that lost power mid-flow shows it again from the first unanswered step (`mfr_resume_step`); save answers as they are given if that is wanted.

Words and order: `docs/design/first-run-flow.md`. Golden frames: `host/tests/golden/screens/first-run-*.png`. Proof: `host/tests/test_virtual_unit.py::test_first_run_flow_by_taps_ends_with_the_answers`.
