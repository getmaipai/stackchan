# Integration 3 (2026-11-17)

Bottom line: patch O03 (governor hysteresis, grace period, staged unhide, floor) passes the gate and keeps the overlays on screen. The plain image of this build is on the unit. No further threshold tuning was needed.

## What was built

- Tree `~/esp/stackchan-rebase/final4`: a copy of final3 with patch O03 applied. The tree matches a clean replay of `firmware/patches/ORDER` (checked file by file against the replay tree; only the generated `dependencies.lock` differs).
- New bench-only patch FI06 (`firmware/patches/FI06-snapshot-includes-overlays-and-effects.patch`, added at the end of ORDER, not committed). The overlays and the screen effects are drawn on the pixels in the display flush hook, after LVGL. `self.face.snapshot` takes the LVGL picture only, so it never held them. That is why every overlay picture of integration 2 and the first run of this integration looked empty even though the status tool said the overlays were showing. FI06 runs the same two passes over the snapshot picture. It is guarded by the face bench option, so the plain image is unchanged by it.
- Builds: bench and plain, one at a time, `nice -n 15`, `-j2`. The generated assets partition is byte for byte the one on the unit.

## Gate (bench image, window 7, 605 s, plus the stress drive in the last 80 s)

Every overlay once (15 s normal, 40 s heavy for stormy, rainy, windy, party and celebrate), subtitles on, CRT on, glow on, the remote banner up, then a game and the listen test.

| Check | Result | Floor |
|---|---|---|
| internal_free steady (median) | 72623 | 40000 |
| internal_min | 33484 | 24000 |
| int_big steady | 27648 | 24000 |
| psram_min | 7018472 | 6000000 |
| panics, task_wdt, websocket drops | 0, 0, 0 | 0 |

GATE PASS. The first run (window 5, same image minus FI06, 666 s) passed the same way with the same memory numbers.

## What the governor does

Time at each level, from the unit's own governor log lines (level 0 is everything on; 4 is the 30 percent particle floor; 5 is the flat look):

| Level | Whole run (607 s) | Overlay phase (305 s) |
|---|---|---|
| 0 full | 53.0 percent | 33.7 percent |
| 1 glow off | 6.1 | 3.6 |
| 2 scanlines off | 5.6 | 5.7 |
| 3 particles 50 percent | 6.9 | 11.1 |
| 4 particles 30 percent (floor) | 27.1 | 45.3 |
| 5 flat | 1.3 | 0.7 |

The overlays were hidden in 3 of 135 status polls (2 percent), all three at the flat look, which the emergency rule reaches only after frames over 100 ms for five seconds. Integration 2 sat at the flat look 68 percent of the run.

Refreshes per second and 99th percentile gap, heavy overlays on (6 s each, CRT and glow on), from window 7:

| Overlay | Idle | Moving | Speaking |
|---|---|---|---|
| none (baseline) | 11.1, 100 ms | 33.7, 54 ms | 29.5, 93 ms |
| stormy heavy | 24.0, 91 ms | 19.8, 97 ms | 27.1, 96 ms |
| rainy heavy | 23.2, 96 ms | 17.4, 100 ms | 26.6, 98 ms |
| windy heavy | 17.9, 100 ms | 14.6, 100 ms | 23.5, 86 ms |
| party | 17.9, 89 ms | 16.3, 100 ms | 22.5, 85 ms |
| celebrate | 22.5, 100 ms | 23.0, 84 ms | 24.3, 92 ms |

Idle with an overlay refreshes more often than idle without one, because the particles move. A moving face with a heavy overlay drops from 34 refreshes a second to between 15 and 23; the 99th percentile gap stays at or under 100 ms.

## Pictures (all ten show the overlay)

Taken while each overlay ran, with CRT, glow and subtitles on. Opened and judged one by one: clouds and rain streaks for stormy and rainy, snow flakes and drifts for snowy, the sun and a cloud for sunny, a disco ball and balloons for party, confetti pieces for celebrate, hearts for love, drifting z letters for sleeping, clouds and gust lines with leaves for windy, the moon and stars for night. Scanlines show on the eyes. The eyes and mouth stay clear.

Folder `~/esp/stackchan-rebase/final4/logs/win7/`:

- `snap_stormy_heavy.png`, `snap_rainy_heavy.png`, `snap_snowy.png`, `snap_sunny.png`, `snap_party_heavy.png`
- `snap_celebrate_heavy.png`, `snap_love.png`, `snap_sleeping.png`, `snap_windy_heavy.png`, `snap_night.png`

The window 5 pictures in `logs/win5/` are empty of overlays for the snapshot reason above.

## Flash and unit state

- Windows: window 5 (11.7 min) and window 7 (11.9 min), each flashing the bench image, then returning the final3 plain image (read-back hash c1583752...) at the end. Lock file and `usb-queue.txt` were used and cleaned each time.
- Final: the final4 plain image, app partition 0x20000 only, read-back hash `c124069f1c6a105a388a5f5d63723d809f99f98135a42f83d9bcdecee87e88b7`, device-side hash verified. The unit reconnected (the host log shows its camera, orientation and reaction lines from 02:48:54 on).
- Preferences were put back as found (captions off, CRT off, glow off) by the gate at the end of window 7. In window 5 the restore step read the wrong key and left captions, CRT and glow on; window 7 fixed the script (`gate.py` reads the `values` object, and keeps the first saved copy) and restored them.

## Method notes

- The gate runs from `~/esp/stackchan-rebase/final4/gate.py` mode `int3` (int2 plus the extra overlays and snapshots, without the voice rounds and the scripted replies, to stay under 15 minutes). `govstat.py` there computes the level table from the serial log.
- Not measured: a full 12 minute window of the scripted stress drive with every overlay on; the drive ran for the last 80 s of each window after the overlay sequence.
