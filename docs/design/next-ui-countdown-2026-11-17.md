# Next UI: full-screen countdown (owner idea, 2026-11-17)

Placement: unit firmware (it reads the unit's own timer core, so it works with no host) plus a host voice command. Local. A countdown to a calendar date is a data source: the owner's own date works locally; a household calendar is a Home tool.

**What it is:** a timer shown as a full-screen countdown. Big digits fill the content zone, with a ring that shrinks as time runs out. Any running timer can be shown this way.

**Behavior**
- Start: "start a 10 minute countdown" (voice, no model), the Timers app (a Countdown button next to Start), or a tap on a running timer in the list.
- Layout: the time in the largest digits that fit (minutes and seconds, or hours and minutes when long), a ring or bar around it, the label in small text, a drag bar to dismiss, Pause and Cancel buttons at least 44 px high.
- Color: calm color while plenty of time remains, amber under one minute, red under ten seconds. Color never carries the meaning alone: the digits and the ring also change.
- Last ten seconds: the digits pulse, a quiet tick each second (follows the system volume, off in quiet hours), a distinct ending sound and a short celebration when it reaches zero. A ringing timer is stopped with one tap.
- Dismissing the screen does not cancel the timer; it keeps running and the Timers app still lists it.
- The face is not hidden by it forever: after a configurable time (default off) the screen returns to the face with the remaining time in the banner.
- Date countdowns ("days until the trip"): a card with big days, then hours under a day. The date comes from the owner or from Home.

**Rules:** inside y 28 to 224 with the drag bar, 44 px targets, one overlay screen at a time, cues and the banner never covered, sounds follow the system volume, cost estimated at under 3 KB of flash and no steady internal RAM (drawn with a few shapes, in PSRAM while shown).

**Build order:** the full-screen timer view, then the voice command, then the date countdown card.

## Focus presets, pictures and interruptions (owner idea, 2026-11-17)

Placement: unit firmware (the countdown view, the drawn icon set, the mini chip) plus data packs (presets) plus host voice. Local. The same screens can later be drawn from display lists (`llm-display-control-2026-11-17.md` 8.2b), which would let Home or a package send any picture; the built-in set below needs no host.

**Preset ("Focus") = a small data record:** name, picture, color token, default length, ending sound, an optional scene (for example a dimmed face with a soft ring), and an optional halfway nudge. Examples: Lunch break (a burger and a drink), Coffee, Focus (a target), Reading, Workout, Stretch (the 20-20-20 eye rest), Phone down, Nap, Laundry, Meeting, Walk. The owner edits names and picks a picture on the settings page; custom titles are free text with a default picture.

**Screen:** the picture drawn large from shapes (about 90 px), the title under it, then the countdown digits and the shrinking ring. If the picture is not built in, the preset uses the closest one or a plain ring. Picture and title together stay inside y 28 to 224 with the drag bar. Voice: "start a lunch break for 30 minutes", "focus for 25 minutes", "start a coffee break" (a preset's default length). Plain "countdown for 10 minutes" uses the default picture. A Pomodoro option chains focus and break (25 and 5, four rounds, then a long break).

**Interruptions (state machine, one countdown screen at most):**
1. **Foreground:** the full-screen countdown.
2. **Interrupted:** the wake word fires, the person asks, the robot answers (face, subtitles, the usual turn). The countdown keeps running underneath, and its time is shown in the mini chip (below). When the turn ends and a short quiet period passes (default 4 seconds), the screen returns to the countdown by itself, with no sound.
3. **Away:** the person leaves the countdown on purpose (swipe down, opens a game, the sheet, a call, a modal). The countdown runs. The mini chip stays until the timer ends or is canceled. A tap on the chip reopens the full screen.
4. **Alerts:** a higher-priority alert (alarm ringing, a modal from Home) covers the countdown; the countdown continues and returns after the alert is dismissed.
5. **Finished:** the ending sound and a short celebration; one tap stops it; the screen returns to the face and the chip clears.
A game screen opened while a countdown runs does not stop it. Pausing is explicit (a Pause button or "pause the timer"). The countdown survives a host disconnect because it lives in the unit's timer core.

**Mini chip (the "always see it" rule):** the remaining time as a small pill at the right end of the banner row, shown whenever a countdown runs and the full screen is not up. Priority inside the banner row: privacy, the remote chip, the camera and microphone cues, and the lock come first; then an alarm ringing; then the mini chip; then notices and captions. If two timers run, the nearest shows with a small count ("+1"). The chip turns amber under a minute and red under ten seconds, with the digits changing too. A tap opens the countdown. With the face on screen the chip never covers the eyes (the banner zone is above the face zone). It is off for owners who prefer a clean banner (a setting).

**Quiet and privacy:** ticks and ending sounds follow the system volume and quiet hours; the wake word still answers during a countdown; nothing is sent anywhere.

**Build order:** (1) the full-screen countdown view with title and ring, (2) the drawn picture set and presets data, (3) the mini chip and the return-after-a-turn behavior, (4) voice phrases and the Pomodoro chain, (5) display-list pictures later.
