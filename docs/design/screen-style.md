# Screen style standard

Status: standard for the 320 by 240 app screens (Apps wall, Timers, Alarms, Games wall, Settings, control sheet, pages). The face is not covered.

## Type ladder

Two sizes plus the clock digits, both from the Noto Sans basic font (it carries every Latin-1 letter, so accents and the Spanish opening marks draw): 16 px for labels and values, 20 px for titles, buttons and names; the clock page keeps its 48 px digits. Text that does not fit at 20 falls back to 16, never to a third size. Cost: the 16 px font adds 87 KB of flash (the 20 px font is already in the image for subtitles) and no internal RAM. Not in the font: oe ligature, euro sign, curly quotes (the unit maps them to plain letters and straight quotes).

## Palette

Eight roles, one color each, defined once in `hal/maipai_ui_style.h`; no screen file holds a color literal.

| Role | Use | Value |
|---|---|---|
| text | main words | 0xFFFFFF |
| muted | hints, labels, disabled | 0x8C96AA |
| bg | the glass behind every screen | 0x000000 |
| surface | buttons, cards | 0x202028 |
| accent | selected tab, slider, links | 0x5AAAFF |
| good | on, ok, charging | 0x46BE6E |
| warn | alarm, caution | 0xFABE32 |
| bad | stop, error, low battery | 0xE64646 |

Tile identity on the Apps wall uses accent, good, warn and a violet (0x965AE6); nothing else.

## Check

`scripts/virtual-unit/ui_style_check.py` lists the font sizes and color literals the screen sources use; the standard holds when it prints two sizes and no literal outside the header. Golden frames of every screen in `host/tests/golden/screens` show the result.
