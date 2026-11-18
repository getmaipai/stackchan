# Every unit screen against the UX13 standard (audit and fix list)

Made 2026-11-18 by the playground track from `docs/dev/screen-audit.json` (the audit reads the unit's own click areas and label sizes from the renderer) and the scenario list. The standard is `docs/design/screen-style.md` ("Physical standard"): primary targets 56 px, secondary 48 px, 8 px gaps and margins, text at least 16 px (20 px body), page dots and scroll cues where a list does not fit, the shared page indicator, a left tab column with a right pane where there are several sections (Settings). A target under 48 px or 8 px from its neighbor is a failure; a 56 px primary target under 56 px, or 16 px text, is a warning.

## Where each screen stands

| Screen | Audit | Patch | State |
|---|---|---|---|
| Face, banner row, captions (`screen-subtitles`) | clean | none needed | the banner is not a target |
| Control sheet, both pages, English and Spanish | 0 | UX13c | written, on `ux/unproven-games`, unit proof pending |
| Clock page (three styles, asleep, flip) | 0 | UX14, UX14b | written, unit proof pending |
| Timers page (none, one, two, three running) | 0 | UX13f | written, unit proof pending |
| Timers app (the Apps wall's Timers) | 0 | UX13f | written |
| Alarms app | drawn now (`screen-alarms-app`) | UX13f | written; the rows with alarms need a host stand-in for alarm items (not drawn yet) |
| Quick actions page | 0, warnings | none | tiles are 56 px or less; leave |
| Games page, walls (Apps, Games) | 0 | UX13e | written, unit proof pending |
| Settings (General, Network, Faces, Info) | 0, warnings | UX13a | on `main`, unit proof pending |
| More (menu, version, games) | 0 | UX13b with SF69 | on `main` |
| First run: language, name, brain, privacy, last, done (six languages each) | 0 | UX13d | written, unit proof pending; the two hint lines under the name and brain tiles are no longer drawn (they need two 16 px lines the glass has no room for; the last screen and the privacy step say the same): the owner may want them back in another place |
| Lock screen and keypad | not audited | batch 5 | drawn by its own program; the keypad keys need the standard |
| Link covers (Wi-Fi setup, connecting, waiting for approval, pairing, update) | not audited | batch 5 | drawn by `cover_render`; they have no targets, only text sizes |
| Data-pack games (Color Memory, Whack-a-Mole, Tic-Tac-Toe, Do It, RPS, Magic 8 Ball, Dice and Coin) | not audited | batch 6 | drawn by `games_render`; buttons and tiles need the standard |
| Grid games (Four in a Row, Match, Hangman, Mine Finder, 2048, Snake) | not audited | batch 6 | board cells are the targets; Hangman keys 31 x 32, Mines cells 24 px: needs a design decision (a board is allowed finer cells if a finger can place them) |
| Game over, Q and A games | core-tested | UX15, UX15b, UX17 | written; the core tests are their audit |
| Weather and overlays | none | none | no targets |

Totals today: zero failures in the audited frames after UX13d and UX13f (46 at the start of this audit); the warnings that remain are secondary targets under 56 px by design (the name tiles are 48 px high) and 16 px labels.

## The fix list, in batches (author on `ux/unproven-games`, one patch each, never in `main`)

1. **Done:** Settings (UX13a), More (UX13b), control sheet (UX13c), games page and walls (UX13e), clock (UX14), shared game over (UX15, UX15b).
2. **Batch 3, Timers and Alarms (UX13f, done):** the Timers app and page: rows 56 px high on an 8 px gap, the cancel target 56 x 56 at the right, a scroll cue when more than three timers, the three quick starts 56 px, one page indicator style. The Alarms app is drawn first (a scenario and a golden) because the renderer does not show it yet.
3. **Batch 4, Setup (UX13d, done):** first run. Skip 72 x 48 and Back 56 x 48 at the top (secondary targets 48 high), the language and brain tiles 56 px high on 8 px gaps (language tiles 96 x 56 in two rows of three; brain tiles 304 x 56 for the three ways), the name list as a scrolling column of 56 px rows, the last screen's Got it 148 x 56 8 px under its text. The renderer already shows every step in six languages: 42 goldens change.
4. **Batch 5, Lock and covers:** the keypad keys to 56 px with 8 px gaps (a 3 by 4 pad needs 3 x 56 + 16 across and 4 x 56 + 24 down: 184 x 248 does not fit 240, so the pad is 3 by 4 at 48 px keys with 8 px gaps (a secondary target) and the digits in the 20 px text; to be decided with the owner because a code is entered one key at a time), the covers checked for text under 16 px.
5. **Batch 6, Games:** the data-pack game tiles and buttons (Do It's big button already is; Tic-Tac-Toe cells are 93 x 52; RPS tiles), and a rule for boards: a board cell may be under 56 px when the board is the whole play field and a finger places one piece at a time, but never under 24 px and never with a target of a different kind closer than 8 px.

Each batch ends the same way: the patch, goldens redrawn and opened, `screen_audit.py --write`, the baseline lowered, the core test, and a message to the firmware track.

## What is not checkable here

The renderer draws the unit's code, so size and spacing are measured; the feel of a touch, the effect of a fingertip's width on a 2 inch panel and the glare are not. The millimeter figures assume 7.87 pixels a millimeter (the 2 inch diagonal) until a ruler check on the unit confirms it (`docs/design/screen-style.md`).
