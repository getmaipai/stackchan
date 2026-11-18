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

Captions above were checked against the frames for the control sheet and the timers page; check the rest by opening the picture.

No picture of the Wi-Fi setup screen yet: the golden frame `cover-wifi-setup` shows text the firmware does not produce (the real screen is the hint line `Wi-Fi setup: stackchan-XXXX  http://192.168.4.1` plus the six-digit code, patches P03 and P05). It needs a scenario that draws that line the way the unit does; until then `getting-started.md` should stay text only for that step.
