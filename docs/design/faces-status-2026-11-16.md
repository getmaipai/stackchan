# Faces and always-on behaviours, status 2026-11-16

Placement: unit firmware plus a host module (`host/maipai_body/faces.py`). Nothing is flashed; no USB was touched.
"Faces and always-on behaviours" in the design is `features.md` (Faces and look, Always-on behaviour), build-order steps 6 and 8, and decisions 22 to 24.

## Built (six firmware patches, one build after each, all on `firmware/patches/ORDER`)

The patches are numbered F01 to F06 because 151 to 154 are taken by legacy patch ids in the cut list.

| Patch | What | Kconfig switch (default y) |
|---|---|---|
| F01 face-config | Neutral white-on-black default. Style (classic, big_eyes, minimal) and colour (none, seven names, or `#rrggbb`) saved in the unit's flash; a colour too dark to see is refused. Tools `self.face.set_config` (one JSON object, all-or-nothing) and `self.face.get_config` (settings plus the features this build has). | `MAIPAI_FACE_CONFIG` |
| F02 face-captions | Captions off by default; a person turns them on. Turning them off clears one on screen. Status words and link screens are not captions. | `MAIPAI_FACE_CAPTIONS` |
| F03 face-time-of-day | Four bands (morning, day, evening, night) from saved hours; the lid opens less (90, 70 percent) and the colour softens (85, 55 percent) late in the day. One shared one-second LVGL timer. Clock never set: day look. | `MAIPAI_FACE_TOD` |
| F04 face-clock | Clock face from drawn bars (no big font): big digits or digits inside a seconds ring, 12 or 24 hour, date line in English or Spanish, dimmed at night. Shows on `self.face.show_clock` or after `clock_idle_s` idle seconds (0 by default). Never covers a mute, vision-off or quiet look or a ringing timer. A touch ends it and is only a wake. | `MAIPAI_FACE_CLOCK` |
| F05 face-thinking-cue | Three animated dots plus the quiet shipped tone (decision 23), on the thinking emotion or `self.face.thinking`. The dots always show; the tone follows the setting, the sound policy and the hard mute. Ends on any other emotion, any status change, or after 45 s. | `MAIPAI_FACE_THINKING` |
| F06 face-timer-countdowns | Up to four chips along the bottom (soonest first, name and live countdown), three plus "+N" when more. Reads a copy the timer task publishes under its own leaf lock, because the timer task takes the timer lock and then the display lock. Works with the host off. | `MAIPAI_FACE_TIMERS` |

Host: `faces.py` holds a per-unit `FaceConfig` (file `~/.config/maipai/stackchan-faces.json`), checks every field with the firmware's rules (English and Spanish messages that say what to do), and sends it through `call_device_tool`. `FaceService.update`, `push`, `sync` (call on connect: it pushes only when the unit differs), `reset`, `show_clock`, `thinking`; `settings_view` and `apply_settings` are the two calls for the settings page. A unit that is offline keeps the saved setting and gets it on `sync`. Old firmware without the tools is named in plain words.

## Evidence

- Build after every patch passed. Final image 0x2f32d0 bytes (baseline before this work 0x2ee870, so +19,040 bytes). Smallest slot 0x4f0000, free 0x1fcd30 (2,084,144 bytes, 40 percent). DIRAM 161,163 used, 180,597 free (static; runtime heap not measured).
- Switch off: with `MAIPAI_FACE_CONFIG` off (every dependent switch goes with it) the image is 0x2ee690, 480 bytes smaller than the baseline, so an off feature costs nothing.
- Replay: the six patches applied in ORDER onto the pre-work tree (`8bdaf21`) match the branch tip exactly.
- Host: `host/tests/test_faces.py` (43 tests) and `test_stackchan_face_cores.py` (compiles `face_cores_test.c` with `-Wall -Wextra -Werror` against the headers taken from the patches). `scripts/check.sh` passes.

## Not done, and why

- Not run on a unit (no flash, by instruction). Every patch has a "Check after a flash" line.
- The mint skin faces (013, 108, 110) stay deferred in the cut list; the thinking emotion draws the doubtful face of the default skin plus the dots.
- The thinking tone reuses the shipped vibration sound. A dedicated quiet earcon needs an asset and is a later choice.
- `monitor_cue_begin` is not in this tree yet, so the clock avoids every cue it can know (privacy bits, a ringing timer, any non-idle state). When the cue path lands, add its state to the clock's blocked test.
- Spanish day and month names are plain ASCII (the screen font has no accents); the language pack adds the accents.
- With captions on and a long caption showing, the timer chips draw over the lower part of the bubble.
- Nothing calls `FaceService.sync` or `thinking` yet: wiring them to the link connect event and the turn loop belongs to `cli.py` and the settings page, which another agent owns.
- `docs/design/unit-protocol.md` does not list `self.face.set_config`, `get_config`, `show_clock` and `thinking` yet.
- Home-preset items: none of these six is tagged home-preset, so no body-half-only work was needed.

## Where it is

Only in the build tree `~/esp/stackchan-rebase/main`, branch `ours` (commits a7121d6 to 16fd45c), and as uncommitted files in this repo (patches, `faces.py`, tests, this note). Not on GitHub, not in a release, not on the unit.
