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

- Goldens: `clock-classic`, `clock-ring`, `clock-datetime`, each awake and `-asleep` (six frames), `clock-datetime-12h`, and `clock-tap-to-datetime` (four taps, back to classic).
- `host/tests/test_clock_styles.py`: a tap cycles three different styles and wraps; a tap on a sleeping unit changes nothing.
- `pages_core_test.c`: every style fits above the page dots, the sign has room, the cycle wraps.
- Not yet proven on a unit: the touch feel of a tap on the page, the sleeping dimming against a real backlight, the saved style after a restart.

## Open questions for the firmware track

1. Which flag is `asleep()`? The spec assumes the sleeping face state. If the unit also dims the screen when idle without sleeping, say so and the sign follows that flag instead.
2. Does the page swipe consume a tap that starts as a short drag? The renderer cannot tell; the unit proof can.
