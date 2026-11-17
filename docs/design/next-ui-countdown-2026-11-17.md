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
