# Doc screenshots from the virtual unit

Owner of the pictures and `scripts/make-vu-screenshots.py`: the playground lane. Owner of every `docs/user/*.md` page: the app track. Rule: the app track adds the line below to its page; the playground lane never edits a user page.

Each picture is a golden frame of the unit's own screen code (320 by 240). `python3 scripts/make-vu-screenshots.py` refreshes them; `scripts/check.sh` fails when one is stale. The README says what `vu-` means.

| Picture | Page that should show it | Suggested line (alt text and caption) |
|---|---|---|
| `docs/images/vu-control-sheet.png` | `swipe-pages.md` (and `settings.md`) | `![The control sheet: volume and brightness sliders, the time, Wi-Fi and battery, and the buttons Mute, Sleep, Lock, Apps, Games and Setup.](../images/vu-control-sheet.png)` |
| `vu-first-run-language.png`, `vu-first-run-name.png`, `vu-first-run-mode.png`, `vu-first-run-done.png` | `getting-started.md`, "First start" | `![First start, step 1: pick a language.](../images/vu-first-run-language.png)` and the same for name, mode (home or your own model) and done |
| `vu-pairing.png` | `with-maipai-home.md` and `install-the-host.md` | `![The robot's screen while it waits for MaiPai Home to approve it: crossed-out signal bars and a key.](../images/vu-pairing.png)` |
| `vu-lock-screen.png`, `vu-lock-keypad.png`, `vu-lock-wrong.png` | no page yet: a `lock.md` page (passcode, auto lock, what the lock tools refuse) | `![The lock screen.](../images/vu-lock-screen.png)`, the keypad with three digits entered, and the red dots after a wrong code |
| `vu-clock.png` | `face-and-look.md`, "Clock face", and `swipe-pages.md` | `![The clock page.](../images/vu-clock.png)` |
| `vu-timers.png` | `timers-and-alarms.md` | `![The timers page with nothing running and three buttons to start a timer: plus 1, plus 5 and plus 10 minutes.](../images/vu-timers.png)` |
| `vu-games.png` | `games-and-pet.md` | `![The Games wall: a colored tile per game with its best score.](../images/vu-games.png)` |
| `vu-settings-general.png` | `settings.md` | `![The on-robot settings, General page.](../images/vu-settings-general.png)` |
| `vu-update.png` | `updates.md` | `![The update screen at 62 percent.](../images/vu-update.png)` |
| `vu-offline-line.png` | `playground/scenarios-and-recording.md` | `![The robot says "I can't reach Home. Still trying." as a subtitle, with its mouth open](../images/vu-offline-line.png)` |
| `vu-four-in-a-row.png` | `playground/games-and-sounds.md` | `![Four in a Row in play: yellow and red discs in a blue board](../images/vu-four-in-a-row.png)` |
| `vu-game-over.png` | `playground/games-and-sounds.md` | `![The end of a game: a smiling face, "You won!", the result and the new-best mark, and two buttons](../images/vu-game-over.png)` |
| `vu-question-game.png` | `playground/games-and-sounds.md` | `![A trivia question with four answers](../images/vu-question-game.png)` |

Captions above were checked against the frames for the control sheet and the timers page; check the rest by opening the picture.

The golden frame `cover-wifi-setup` now carries the real words (hotspot name, address, six-digit code) but draws them on the cover layout; the unit draws them as a caption line (patches P03, P05). Use it only if the page says the layout differs, or wait for a scenario on the caption path.
