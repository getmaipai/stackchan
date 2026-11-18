# Clock styles, the tap and the sleep sign

Owner idea of 2026-11-18. The clock page (the first swipe page) shows when the unit sleeps, and a tap on it cycles through its styles. The choice is kept across restarts. Display patch: `firmware/patches/UX14-clock-styles-tap-and-sleep-sign.patch`. The renderer draws the screens from the unit's own page code, so the pictures below are the unit's pictures: `host/tests/golden/screens/clock-*.png`.

## The styles

| Number | Name | What it shows |
|---|---|---|
| 0 | Classic | The big seven-segment digits, white on the black card, the short date under them (today's clock, unchanged). |
| 1 | Ring | Smaller digits inside the seconds ring (today's ring style, unchanged). |
| 2 | Date and time | Medium digits (40 px wide, 76 px tall) with the full date line in the 20 px body text under them. |

Only styles that exist are in the cycle. A new style is added by raising `MPG_CLOCK_STYLES` in `maipai_pages_core.h` and giving it a layout; nothing else changes. A tap moves 0, 1, 2, then back to 0.

## The sleep sign

When the unit is asleep the clock page shows a moon and "Zz" and is dimmed to 40 percent (`MPG_ASLEEP_DIM_PCT`). The sign is a steady dim white that the dimming does not touch, so it stays readable. The colon stops blinking while asleep. Places: left of the date line in the classic style, top left in the ring and date and time styles; the digits never touch it (checked in `pages_core_test.c`).

"Asleep" is the host call `asleep()`: true while the unit is in its sleeping state (the sleeping face, the dim idle screen). Waking the unit repaints the page at full brightness and removes the sign within one page tick.

## The tap

- Awake: a tap on the page (anywhere that is not a button) calls `clock_set_style(next)` and redraws the page in the new style.
- Asleep: the tap only wakes the screen. The style does not change. The unit's own wake on touch runs first; the page ignores the tap while `asleep()` was true when it arrived.
- A swipe is not a tap. Page swipes, the sheet swipe and the grabber keep working as before.

## The flip

When the style changes on a tap, the page plays a card flip of 240 ms: it closes to its middle line in the first 120 ms, the new style is built at that moment, and it opens again in the next 120 ms. Patch: `UX14b-clock-flip-on-the-card-tween.patch` (on top of UX14).

- **Same tween as the Match card flip.** The width comes from `gan_flip_width()` and the middle from `gan_flip_new_face()` in `maipai_grid_anim_core.h` (patch SF74); no new engine. A 30 ms timer runs only during the flip.
- **No buffer.** Nothing is rendered to a surface. Every box of the page (the digit bars, the colon, the page dots) moves its x and width toward the middle line; the labels and the ring are hidden while the card is under 90 percent wide, because text and an arc cannot be squeezed without a buffer.
- **Memory.** About 1 KB of heap (the tween list and 56 object records) exists only for the 240 ms; nothing is held at rest. If the allocation fails the style still changes, without the flip.
- **Rules.** A tap during a flip is ignored. Swiping away during a flip leaves nothing behind: the timer notices the page is gone and frees its state without touching the page's objects. The style is saved as in "Keeping the choice", once, when the tap changes it (not per frame).
- **A tap on a sleeping unit** starts no flip.
- **Pictures:** `clock-flip-classic-to-ring.png` and `clock-flip-ring-to-datetime.png` are filmstrips of nine frames, 33 ms apart (the frame before the tap, then eight): narrowing, the line, opening on the new style. Tests: `test_clock_styles.py` (it closes and opens; a second tap in the flip is ignored).

## Keeping the choice

- Stored as the clock style in the face configuration (`clock_style`, today 0 digits or 1 ring). The firmware track extends the range to 0 to 2 (`maipai_face_core.h`: the check `clock_style > 1` becomes `> 2`; the tool text gets the name `date_time`) and the saved byte keeps its place, so an older saved 0 or 1 reads the same.
- Written only when the value changed (the same rule as the existing config save), and not on every tap: the unit waits 700 ms after the last tap (the slider-save pattern in `maipai_pages_unit.cc`), so three quick taps are one write.
- The write runs on the application task (`Application::Schedule`), never from a task that has its stack in PSRAM and never from the LVGL display task itself. The page only calls `clock_set_style()`; the unit's implementation of that call stores the value in memory at once (so the redraw and `clock_style()` agree) and arms the debounced save.
- Restart: the page reads `clock_style()` when it is built, so the saved style shows from the first frame.

## Host interface (additive, safe defaults)

```
virtual int  clock_style()          // 0 to 2; the default maps clock_ring() to 1, else 0
virtual void clock_set_style(int)   // the unit stores it in memory at once and saves it debounced
virtual bool asleep()               // true while the unit sleeps
```

The virtual unit keeps the style in the stand-in host (`pset cstyle N`, `pset asleep 1`).

## Proof on the virtual unit

- Goldens: the two flip filmstrips (see "The flip"), `clock-classic`, `clock-ring`, `clock-datetime`, each awake and `-asleep` (six frames), `clock-datetime-12h`, and `clock-tap-to-datetime` (four taps, back to classic).
- `host/tests/test_clock_styles.py`: a tap cycles three different styles and wraps; a tap on a sleeping unit changes nothing.
- `pages_core_test.c`: every style fits above the page dots, the sign has room, the cycle wraps.
- Not yet proven on a unit: the touch feel of a tap on the page, the sleeping dimming against a real backlight, the saved style after a restart.

## Answers from the firmware track (2026-11-18, patch SF81)

1. **What `asleep()` is.** The unit has no sleep state of its own. A host that puts it to sleep dims the screen: the live backlight level falls below the level the person saved (`maipai_screen_levels`). So `asleep()` is true while the screen is dimmed below the saved level (live less than saved, saved above 0). A touch restores the level (`maipai_screen_wake`) and that press is flagged `MGS_F_WOKE`, so the page's tap does nothing. A screen that is fully off (privacy sleep) shows nothing, so there is no sign. The face's "sleepy" emotion is a different thing and does not count.
2. **Tap against swipe.** A tap is a touch that stays within 12 px and under 450 ms (500 ms at most). A swipe is at least 36 px, within 900 ms and at least 60 px a second, mostly one direction. A move of 12 to 36 px is neither: the gesture layer gives the page no tap for it. The unit proof will show whether the LVGL click still fires for such a short drag; if it does not, the page's tap tolerance is widened (a firmware change).
3. **Saving.** The style is saved 700 ms after the last tap, on the application task, only when it changed. The face configuration keeps the same byte; the tool names are `digits`, `ring` and `date_time`.
