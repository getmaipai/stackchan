# Offline audit, the unit half (firmware track, 2026-11-18)

Rows for the app track's `docs/plan/offline-audit.md`. "No host" means the Wi-Fi is up and the home host cannot be reached; "no Wi-Fi" means neither. Each row says what the unit does on its own, read from the code (the patch is named where one decides it). "Works" means it needs nothing from the host.

| Feature | No host | No Wi-Fi | Basis |
|---|---|---|---|
| Face, emotions, blink, gaze, idle behavior | works | works | local avatar and look tables |
| Wake word | works (heard locally) | works | esp-sr models in the assets partition (2.47 MB) |
| A conversation turn (speech to a reply) | **does not work**: the unit answers with an offline phrase (16 recorded clips, one per state) or the tone, never the same clip twice, at most one in 10 s and three a minute | same | `MAIPAI_OFFLINE_PHRASES`, patch 075 |
| Captions of a reply | none (the reply comes from the host) | none | host text |
| Timers, alarms, the hourly chime | works (the clock chip keeps time; the time itself is set by the host and never fetched from the internet) | works | `maipai_timers`, `maipai_tz` |
| Clock page and clock face | works; shows the last time set; a unit that never had its time set shows the digits without a date | works | the host sets the time (`self.clock.set`) |
| Time zone | works from the saved zone; the unit's own picker shows only while no host address is saved | works | SF57 |
| Quiet hours, Quiet now, mute, full quiet, lock, auto lock | works | works | local policy cores, saved in flash |
| Sounds, notification tones, volume | works | works | tones made in code and shipped chimes |
| Games (all of them), scores | works, scores saved on the unit | works | the grid engine and the data-pack player are local |
| Music dance, dance, sound-reactive nod | works (the unit measures the room's sound itself) | works | `maipai_music`, SF51 |
| Turning toward a person | works (frames are compared on the unit; nothing is sent) | works | the seeker (SF55 schedule) |
| Camera snapshot or stream to the host | **does not work** (nothing to send to) | same | host link |
| Face tracking by the host (the lease) | does not work; the unit's own seeker runs instead | same | lease rule |
| Settings screens, More (version, games), quick settings, control sheet | works | works | local screens |
| Wi-Fi setup | works (the unit's own access point and page) | works | portal |
| Pages: clock, timers, games, actions | works | works | local |
| Page: tiles (dashboard) | shows the last tiles received, dimmed after an hour with their age | same | `MPG_TILES_STALE_S` |
| Page: picture frame, picture faces | works from the pictures held on the unit | works | the pack cache |
| Language and style packs | the packs held keep working; a new one cannot be installed | same | installed set |
| Firmware update | **does not work** (signed images come only from the paired host) | same | `maipai_update` |
| Installing packs, asset swaps | the installed ones swap locally; a new one needs the host | same | installed set |
| Sound policy and its schedule | works | works | local |
| Link state shown to a person | "Connecting..." from 3 s, "Offline" with the slashed bars from 45 s, the sleepy face and the amber ring from 3 min, the words "Can't reach Home..." on the banner at 10 min (20 s) and every 30 min | "no Wi-Fi" phrase and the same looks | SF49, SF73 |
| Reconnect | every 0.5 to 5 s for 2 min, 15 s to 5 min, 30 s to 10 min, 120 s after; the first success resets the delay; a host that comes back is found within the current wait plus one connect | same, after Wi-Fi returns | SF64, SF71 |
| Watchdog and self-restart | works; at most three self-restarts an hour, then a wait | works | patch 085, SF49 |
| Battery and the movement limiter | works | works | local |
| Mouth and mumble voice (decision 24) | planned: tones from the caption text, see `docs/plan/offline-mumble-firmware.md` | planned | not built |
| Content pantry (decision 25) | planned: the unit reads its own typed records, see `docs/plan/pantry-reader-firmware.md` | planned | not built |

## Gaps the audit shows

1. The unit says **nothing useful** in a conversation with no host beyond the offline phrases. The mumble voice and the pantry are the planned answers.
2. A unit that **never had its time set** has no date (the host sets it; there is no time source of its own by design: nothing leaves the home). The first-run flow could ask the person to set the time on the unit when no host is paired (a screen, not built).
3. **New packs cannot be installed** with no host (by design: signed over the paired host only). A pantry of records that the unit already holds keeps working.
4. The 10-minute notice was invisible before SF73 (it queued behind the steady Offline look); it now takes the banner row.
