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

## Physical standard (owner review of 2026-11-18)

Measured in millimeters of glass, from one number: the panel is a 2 inch 320 by 240 screen, 40.6 mm wide, **7.87 pixels a millimeter (assumed from the diagonal until a ruler is put on the glass)**. The constants live in one file, `scripts/virtual-unit/screen_standard.py`; the audit is `scripts/virtual-unit/screen_audit.py` (the unit's own click areas and line heights, drawn on annotated frames in `docs/dev/screens/annotated/`, summary in `docs/dev/screen-audit.md`).

| Thing | Minimum |
|---|---|
| Primary target (the one thing a screen is for) | 56 x 56 px (7 mm) |
| Secondary target (tabs, list rows, a second action) | 48 px a side (6 mm); tab rows and content rows 56 px high |
| Skip, back, close | 48 x 48 hit area even when drawn smaller (LVGL extended click area); never overlapping another target |
| Gap between adjacent targets | 8 px |
| Screen margin, label to control | 16 px, 12 px; everything on an 8 px grid |
| Body text | the 20 px font (line height 23) |
| Secondary text | the 16 px font (line height 19), nothing smaller |
| Contrast | unchanged (the palette above) |

Failing today: see `docs/dev/screen-audit.md`. `host/tests/test_screen_audit.py` holds each screen to its baseline in `docs/design/screen-audit-baseline.json` (failures may only shrink) and gives a new screen no failures.

### Which pattern for which screen

| Content | Pattern | Rule |
|---|---|---|
| A few big choices | **Pages** of tiles | 4 tiles a page, 2 by 2; never clip or shrink below the minimum; more tiles mean more pages |
| Many sections (more than about 5 items or groups) | **Master-detail** (as in settings) | left column of tabs that scrolls, 56 px tab rows, the active tab clearly marked; right pane scrolls, rows at least 56 px with 8 px gaps; a thin scrollbar or an edge fade shows there is more |
| One long list | **Scrolling list** | rows at least 56 px, 8 px gaps, a sticky header when it helps, the scroll affordance as above |
| Steps toward one result | **Wizard** | one primary action a step, dots show the step, Skip or default on every step |

One **page indicator** everywhere (swipe pages, wizard steps, games wall pages): the same dots at the bottom center, fixed size and spacing, accent for the active one, muted for the others, inside a safe area no content may enter. A swipe left or right changes the page; where a swipe is not obvious there are also next and previous targets. The Done or back control sits in the same place on every screen. Content that does not fit one page goes to more pages: it is never clipped, shrunk below the minimums or allowed to overflow. The host dashboard web pages use the same structure (left tabs, right scrolling pane) so the two feel alike (`docs/plan/dashboard-structure.md`).

## Documented exceptions (owner, 2026-11-18)

- **The lock keypad is no longer an exception.** It is four columns and three rows of 70 by 56 px keys with 8 px gaps (patch UX13g; three columns by four rows of 56 px keys did not fit under the dots row, and the owner chose the 4 by 3 pad that meets the standard).
- **Boards.** A game board cell may be under 56 px when the board fills the play field and a finger places one piece at a time, never under 24 px and never with a different kind of target closer than 8 px (`docs/plan/screen-standards-audit.md`, batch 6).
