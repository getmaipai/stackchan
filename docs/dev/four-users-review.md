# Four users review of the robot's screens (2026-11-18)

Four people use the robot: a kid, a teen, an adult who is not technical, an adult who is. Method: every golden screen (`host/tests/golden/screens`, drawn by the unit's own screen code) and the parent view page, checked on four things. The three checks that a script can make are repeatable: `python3 scripts/virtual-unit/touch_targets.py` (target sizes), the palette math below (contrast) and the string tables (words). The rest was read by eye from the frames.

## Results in one table

| Check | Result | Where it stands |
|---|---|---|
| Touch targets of 40 px or more on the 320 by 240 panel | Every tile, key and button found is 44 px or more on its short side; smallest 44 by 44 (first-run Back, the settings tabs and Done 44 px high). The lock keypad keys are 100 by 46. No target under 40. The lock screen's padlock (36 by 36) is a picture: any touch on that screen opens the keypad. | pass |
| Contrast, text colors on the screen colors (WCAG ratio) | On black: white 21.0, muted 7.1, blue 8.6, green 8.9, amber 12.5, red 5.3, violet 4.9. On the card surface: white 16.2, muted 5.4, blue 6.6, green 6.8, amber 9.6, red 4.1, violet 3.8. All text colors pass 4.5 on black. Red and violet are under 4.5 on the card surface; they are used for shapes (the wrong-code dots, tile fills), not for text. | pass, with a rule: no red or violet text on a card |
| Words at grade 6 | The screens use short plain words (Apps, Games, Timers, Mute, Quiet, Volume, Bright, Lock, Settings, Save, Cancel). A reading-grade formula is meaningless for one-word labels, so the check is by list; see the jargon rows below. | 2 words to fix, 1 to watch |
| Error messages say what happened and what to do | The update screen said "Update refused, Nothing changed" and stopped. Fixed in patch UX09: it now adds "Try again later". The first-run, lock and pairing screens have no error text. | fixed |

## Findings by user

| User | Screen | Finding | Action |
|---|---|---|---|
| Kid | Face styles list | English "Stock" is not a word a child knows; the Spanish list says "Original". | Rename the English label to "Original" (a string-table change in the pages core and its tests; the app track's face docs say "Stock" and change with it). Not done here: it touches a core table with pinned tests. |
| Kid | Control sheet | "Games" is the longest tile label; it fills its 50 px tile edge to edge. | Watch on the glass; no overflow in the frame. |
| Teen | Lock screen and keypad | They carry no words by the owner's choice. A teen finds the keypad by touching the screen, but nothing says so. | None: owner decision (2026-11-17). The docs page for the lock says it. |
| Teen | First run, "What should I be called?" | Six persona names, 44 px Back, "You can change it later." Clear. | none |
| Non-technical adult | Control sheet tile "Private net" | Jargon. "Private network" (Info tab) is clearer; "Home link" says what it is for. | List for the owner: rename the tile in the pages core (Spanish "Red priv." too). |
| Non-technical adult | Update refused | Said what happened, not what to do. | Fixed, UX09 (patch UX09-update-refused-says-what-to-do). |
| Non-technical adult | Camera on | The camera cue on the screen is a 24 px icon in the status strip with no word. The ring light carries the strong cue. | List: a word next to the icon ("Camera on") when the banner has room, by the app and firmware tracks; the cue's rule (it cannot be hidden) is met. |
| Non-technical adult | Wi-Fi setup | Four lines: name, address, code. Plain. The address and code are not tappable, as they should not be. | none |
| Technical adult | Settings, Network | "Signal: Good (3/4)", "Wi-Fi network: Not connected" are right. No raw numbers hidden. | none |
| Technical adult | Info tab | Shows every row, no ten taps (NX02). | none |
| Parent | Parent view page (host page, `settings_ui_family.py`) | Words come from the `fam.*` catalog: Robot, Microphone, Camera, Lock, Online, Muted, Listening, Locked, "Who controlled the robot lately", "Valid for 10 minutes". Plain. The privacy sentence is the first-run one. Controls are buttons of the page's own size (not measured here: it needs a browser at phone width, which the app track owns). | The app track measures the page's buttons at 375 px; the review cannot from a frame. |

## Fixed in this review
- Patch UX09: the refused-update cover says "Try again later".

## Not drawable by the renderer (listed for the bench or later work)
- Alarm ringing (the clock page's ring style draws, but the ringing alarm's own look does not).
- "More" (no screen of that name exists in the pages core; the control sheet has the tiles listed above).
- The time zone picker (the renderer checks the zone list by text, `zonecheck`, and has no picture of it).
- The individual game screens (the games renderer is a separate program; its frames are not in the golden set yet).
- The Wi-Fi settings page itself (the Network tab's button is drawn; the page behind it is the system's).

## New golden frames
Camera on, subtitles, timers running, and the changed update-refused cover.
