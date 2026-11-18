# The memory budget as data (decision 15): the agreement between the firmware track and the playground track

Status: proposal of 2026-11-18 from the playground track. The firmware track owns the numbers and the shape; tell the playground track what to change.

## The file

`schema/memory-budget.json`, read by the virtual unit (`scripts/virtual-unit/memory_model.py`) and the ledger (`scripts/ledger_memory.py`). `docs/dev/memory-budget.md` stays the readable table; where the two differ, the JSON is wrong until the firmware track fixes it.

```
version, gate{internal_free_median_min, internal_free_lowest_min, largest_block_median_min, largest_block_lowest_min, psram_lowest_min, stack_margin_min}
baseline{image, internal_free_median, internal_free_lowest, largest_block_median, largest_block_lowest, psram_free, source}
items[]{id, kind, name, internal, psram, flash, largest_block, in_baseline, persistent, loaded_when, freed_when, status, source}
```

- **kind**: screen, overlay, picture_face, language_pack, task, feature. **id** is stable and dotted (`screen.page.timers`, `overlay.layer.back`, `feature.link_tls`, `language.fr`).
- **internal**, **psram**, **flash**: bytes while loaded (flash: the size it adds to the image). **largest_block**: the biggest single internal allocation, the number that splits the top of the heap.
- **in_baseline**: already inside the baseline numbers (always-on tasks, language tables): never subtracted. **persistent**: stays loaded for a whole measuring window (a standing feature), so it counts against the median; a transient item counts only against the lowest.
- **status**: measured, verified, estimate, placeholder (a number the playground track seeded because none existed: replace it), to measure, not built.

## The rules the virtual unit enforces

- Median checks: `baseline median - Σ persistent internal >= 40,000`; `baseline block median - Σ persistent largest_block >= 24,000`.
- Lowest checks: `baseline lowest - Σ everything loaded >= 24,000`; `baseline block lowest - Σ largest_block loaded >= 16,000`.
- A scenario fails the moment a check breaks (`MemoryBudgetError` names the gate, the numbers and what is loaded) and when, back at the face, the loaded set is not the baseline (the leak canary names what stayed).
- A feature or screen that opens with no row in the table is refused: add the row (and its `loaded_when` and `freed_when`) before it runs.

## What the rig reports as events

The renderer commands (`pshow`, `frun`, `overlay`, `ovclear`, `notes`), tool calls (`self.overlay.clear`, `self.face.music_notes`, `self.facepic.*`) and the music dance's step. A screen that only a touch inside the unit opens (the Apps and Games walls) is declared by the scenario (`u.memory.open(id)`): the renderer exposes no event for it. Feature switches (link, camera stream, echo canceller) are declared by a scenario or a test the same way.

## Open questions for the firmware track

1. Replace the placeholders (screens and pages 2.5 to 4 KB, the overlay layers 1.5 KB, notes 1.2 KB) with measured numbers; the first run (3.7 KB) is measured.
2. Is a page's cost internal at all while its objects are small LVGL parts, or does LVGL draw from a pool? A different answer changes the lowest check.
3. Should the gate treat the 6 KB `pack_boot` and `pack_write` tasks as transient (lowest only), as the model does?
4. Combinations: the model sums independent items. Say if two items interact (the link and the camera stream share a socket stack).
