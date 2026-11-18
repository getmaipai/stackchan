# Owner round NX (patches NX01 to NX09), 2026-11-17

Nine firmware patches after MF01 and the host changes that go with them. Each patch header says what to check after a flash.

| Patch | What it does |
|---|---|
| NX01 | The quick sheet's Light tile becomes a Lock tile with a drawn padlock (Mute, Quiet, Lock, Apps, Games, Settings: still one row of six). With a code set a tap locks now; with none the banner row says "Set a code on the settings page" and the sheet stays. The listening light switch moves to a "Listening light" row in Settings, General; the settings page keeps its own. |
| NX02 | The ten-tap gesture is gone. The Settings Info tab shows eight rows at once (firmware tag, image, slot, memory, host name, Wi-Fi network, signal, uptime) and the old More, Version screen shows its detail lines at once. `mv_tap` stays in the version core, unused, with a note. |
| NX03 | One rule for everything on the glass (`maipai_screens_core.h`): a sheet may sit over the face or a swipe page, every other surface is exclusive, and opening any surface closes what may not stay. Fixes the Apps wall opening over the games page. |
| NX04 | The bench snapshot also lays the system layer over the screen, where the lock screen is drawn. |
| NX05 | A face glyph in the banner strip next to the mic glyph, set by `self.banner.face_seen {seconds}` (default 3, at most 10) from the host's face model or the unit's own detector. Only while "Status icons" is on; reports under half a second apart are ignored. |
| NX06 | The seeker's default mode is "always" and it is gated for lock, carry and night. |
| NX07 | The z letters of the sleeping face no longer float over the unlock keypad (overlays stay off while it is up). |
| NX08 | The Apps and Games walls: tiles fill the zone (154 by 90 px), each with its own accent color, a large picture drawn from LVGL shapes and the title in the 24 px font on a dark plate. Shapes exist only while the wall is open. |
| NX09 | The Timers app: a scrolling column of presets on the left (1, 5, 10, 15, 30, 45, 60 min and Custom), tall running-timer rows on the right with a progress bar and a big Cancel; the words Timer and Alarm are no longer written. |

## Saved sheet keys

The sheet item saved as `light` is read as `lock`, in the same place, and never twice (unit: `mpg_sheet_by_name`, host: `swipe_pages.migrate`). New saves write `lock`.

## Face turning (`turn_to_faces`)

- `off`: the head never turns toward a face.
- `talk`: only after the wake word and during a talk (the old default).
- `always`: also an idle watch, one camera frame a second with the camera cue, a turn when something moves, at most four turns a minute (the new default).

The seeker runs nothing while the unit is asleep, muted, in full quiet, with vision off, locked or carried, or while a host holds the look lease. The idle watch also waits for day (night mode); a wake word at night still turns the head, slowly. On the host, `effective_turn_to_faces` decides what the unit is sent: the owner "off" first, a person's own "off", then the "Look for faces" switch once used (on is `always`, off is `talk`), then the person's choice, then the default.

## Overlay rule test

`host/tests/firmware/screens_core_test.c` opens every named screen (sheet, the six swipe pages, Apps, games wall, Timers, Alarms, Settings, quick settings, Wi-Fi, More, lock keypad) after every other, in pairs, in triples and in a 50,000 step random walk, and checks the drawn set against the rule after each step.
