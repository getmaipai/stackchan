# Fixed zones, the banner row and the subtitle strip (patches N01 to N04)

Owner decisions, 2026-11-16: information never sits over the mouth, nothing moves when a message appears, and the bottom of the
screen is for subtitles. The screen has three fixed zones. Each is laid out once.

| Zone | Rows (y) | What lives there |
|---|---|---|
| Banner | 0 to 28 | the banner row, reserved even when empty |
| Face | 28 to 184 | eyes, brows, mouth (156 px), clipped to the zone |
| Subtitles | 184 to 240 | what the robot is saying (56 px) |

## The banner row (N01, N02)

ONE rectangle for every message: x 4, y 1, 312 by 26, radius 13. Only the content inside changes (icon on the left, text, icon
strip on the right). A short message never shrinks the row; a text longer than its text area scrolls (marquee). The row fades in
and out over 150 ms at full width. There is no second height: a long text scrolls instead of growing a second line.

| Part | Rule |
|---|---|
| Priority | privacy and remote cues first, then notices, then captions |
| Minimum time | 1.5 s on screen; a more urgent message waits for it, the displaced notice is queued again |
| Replace in place | a message with the same tag and priority replaces the old one (Volume, Here I am, captions) |
| Remote session | a violet chip inside the row: "Remote connected", then ": label" only when the controller has a name; steady, never blinking; the lowest priority, so a cue replaces it and it comes back |
| Heartbeat | the host repeats the session call about every 10 s; a repeat with the same state and label changes nothing and does not redraw (core test) |
| Remote say | the exact words in the row, sticky until spoken or canceled; when spoken they continue as subtitles |
| Strip | microphone live, camera on and remote always; battery under 20 percent and Wi-Fi or hub link lost only when wrong |

For information only: remote cues and session, "Here I am!", game score, offline, battery, volume. Never the robot's spoken words,
unless the owner chooses Captions: banner.

## The subtitle strip (N01, N02)

No box. The build's own 20 px text font (Noto Sans, accented Latin included, already in the image) in the face color with a
dark outline, at most two lines centered, one line in the vertical middle of the zone. A sentence is one speech message; a long
sentence is paged (about 55 ms a character, 1.6 to 3.5 s a page); a new sentence fades in over 150 ms; the last page leaves
0.8 s after the robot stops talking. Word timing from the host is not sent today, so there is no karaoke highlight. The Wi-Fi
setup hint shows as still subtitles. Settings, Captions: off, subtitles (default when on), banner. The old bottom speech bubble is
gone; the Stock style uses the subtitles too.

## The face zone (N04)

The default skin's panel is the face zone and clips what leaves it. Style offsets are from the middle of the zone (screen y 106).
Big eyes is the approved design at 0.82 (eyes 79 by 85); the other styles keep their sizes. Every eye top is at y 32 or lower, every
mouth is centered at y 162 (the stock bar at 152) and its tallest open shape ends by y 180. The gaze range is 10 px, the mouth's
own offset 2 px, the brows are pushed down so they never reach above the eye line, and an eye's vertical offset (pose, gaze and
drift together) is clamped. Tests: `face_zone_core_test.c` checks 47,000 shape boxes over every style, emotion, lid, blink, voice
level and gaze extreme; the host renderer zone check lights nothing in the banner or subtitle zone over 240 style, emotion, voice
and thinking combinations (lit rows 32 to 174).

## Settings

- `captions_mode`: off, subtitles (default), banner.
- `top_bar`: hidden (default), or always show battery and Wi-Fi.

The settings page has a Captions card and a Top bar card; its preview draws the same zones from `banner_table.json` (what
`hal/maipai_banner_core.h` prints) and clips the face to its zone; `tests/test_banner_preview_parity.py` checks the table and the
page's functions against the core.

## The stock status bar (N03)

The vendor's green bar (time, battery, Wi-Fi) was created in `hal.cpp` once the unit was ready and updated every pass of the
update task. It is behind `MAIPAI_STOCK_STATUS_BAR` (default n) and `apps/common/status_bar` is left out of the build. Linked size
of that object before: 6068 bytes of code, 1669 bytes of read-only data, 4 bytes of RAM, plus about ten LVGL objects at run time
and a per-pass update with an animation step. The banner row and subtitles cost about the same code (flash net about zero) but no
LVGL objects when idle.
