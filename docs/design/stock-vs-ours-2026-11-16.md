# Stock firmware against ours, 2026-11-16

Placement: audit note. Source: a read-only comparison of the stock base (`28b9f0c8`) with `firmware/patches/ORDER`, `feature-gap-2026-11-16.md` and `firmware-v1-cut.md`.
Status words: BUILT, PLANNED (decided, no patch), HOME-ONLY (needs the hub), REMOVED ON PURPOSE (reason given), MISSING (no decision recorded).

| # | Stock feature | Ours | Basis |
|---|---|---|---|
| 1 | Voice chat with an AI agent | BUILT, to the paired host's own model; cloud removed | 003, 014, 016, 018 |
| 2 | Wake word on the unit | BUILT, no unit run | 030 |
| 3 | Six emotions | BUILT, no unit run | F01, F02 |
| 4 | Decorators (heart, sweat, shy, angry, dizzy) | BUILT as nine drawn extras (sweat, shy, dizzy, heart, anger, tears, sparkles, stars, zzz), flashed, draw path run on the unit, not seen | U01 |
| 5 | Blink, breathing, speech wobble | BUILT, no unit run | F01, 047 |
| 6 | Idle head motion | BUILT, off by default | 037 |
| 7 | Word reactions ("hello" shows happy, "love" dances) | BUILT as a table the settings page edits, six languages, flashed, matching run on the unit | U02 |
| 8 | Head pet and shake reactions | BUILT, no unit run | 047, 048, 056, 080, C04 |
| 9 | Pickup and tilt reactions | PLANNED (pickup, host only); tilt DROP in the v1 cut | v1 cut |
| 10 | Screensaver | REMOVED ON PURPOSE, replaced by sleeping face and clock | 097, C05, F04 |
| 11 | Built-in dances | BUILT | 020, 125 |
| 12 | Phone-app choreography over Bluetooth | REMOVED ON PURPOSE (Bluetooth off) | 098 |
| 13 | Music dance | PLANNED, host code exists, unit patches not in ORDER | gap doc |
| 14 | Head move and angle tools | BUILT, with move cap | 038 |
| 15 | LED ring and colour tool | BUILT, no unit run | A01, C02 |
| 16 | Ring dark with screen | PLANNED | 050, 114 |
| 17 | Status bar | BUILT | C01 |
| 18 | Launcher, home button | REMOVED ON PURPOSE, swipe gestures replace them | 097, C03 |
| 19 | Quick settings swipe | BUILT, no unit run | C03 |
| 20 | Notification sounds | BUILT | 115 to 117, T05 |
| 21 | Timers and reminders | BUILT; repeating reminders not decided | 090 to 094 |
| 22 | Photo, live stream, monitoring, gallery | HOME-ONLY | features.md |
| 23 | Video call, camera upload to a URL | REMOVED ON PURPOSE (vendor cloud, egress) | 001, 155 |
| 24 | Phone pairing, Bluetooth services | REMOVED ON PURPOSE; host pairing BUILT | decisions 19, 21; 018 |
| 25 | ESP-NOW remote | REMOVED ON PURPOSE (memory, attack surface) | S01 |
| 26 | App Center, vendor registry, MQTT, cloud accounts | REMOVED ON PURPOSE (egress) | 001, 002, 005, 155 |
| 27 | Vendor firmware update | REMOVED ON PURPOSE; signed update from the paired host BUILT | 158 to 160 |
| 28 | Public network time | REMOVED ON PURPOSE | 004 |
| 29 | Time zone picker | BUILT (31 zones with summer time; unit screen, tools, settings page; the host sets the clock) | U03 |
| 30 | Wi-Fi setup portal | BUILT, new protected portal; saved-network tools (023) conflict with it | P01 to P05 |
| 31 | Network test | BUILT, reads only what the unit holds, plain words and the fix | U04 |
| 32 | Radio power saving | PLANNED, test first | decision 16 |
| 33 | Firmware version screen | BUILT (ten taps for tag, image state, slot, memory) | U05 |
| 34 | Account unbind and reset | BUILT, two-step reset | R01 |
| 35 | Servo, microphone and RGB test screens | REMOVED ON PURPOSE (setup app not built); bench serial path covers some | 097, V01 |
| 36 | English | BUILT, with Spanish | decision 25 |
| 37 | Other languages, CJK font, emoji | CJK and emoji REMOVED ON PURPOSE; French, German, Portuguese and Italian screen words and page BUILT in plain ASCII | 096, U06 |
| 38 | NFC and infrared | SKIPPED: hardware is in the body, but the tree has no stock code and no pin map; finding in train4-2026-11-16.md | U07 note |

## MISSING rows to build

None left except NFC and infrared (skipped with a finding; see `train4-2026-11-16.md`). The six other rows were built in Train 4.

## Notes found

- `strip-results.md` says setup, launcher and dance apps are kept, but patch 097 filters every `apps/app_*` directory out of the build. One of the two is wrong.
- `feature-gap-2026-11-16.md` predates Trains 1 to 3, so reset, portal, update, battery ladder, chime, wake cue and reconnect now have patches and that note is stale.
- The gap doc promises tilt reactions; the v1 cut drops patch 072.
- IMU tap 081 is CORE-V1 but not in ORDER.
