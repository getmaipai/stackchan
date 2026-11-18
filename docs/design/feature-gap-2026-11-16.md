# Feature gap: promised against built and flashed, 2026-11-16

Placement: audit note for the firmware and host lanes. Nothing was built, flashed or changed to write it.
Sources: `features.md`, `firmware-v1-cut.md` (CORE-V1 and HOME-PRESET rows), `decisions.md`, `core-extras-modules.md`, `firmware/patches/ORDER`, `host/maipai_body`, `host/tests`, the first-flash note (2026-11-15), the faces gate and status notes (2026-11-16).

## The short answer

The unit runs a rebased, trimmed build (image 0x2dfaf0 bytes after the security fixes, 42 percent of the smallest app slot free). It boots, joins Wi-Fi, holds the memory gate and answers the host's speech and reply self-tests. Almost every other feature is built into that image but was never called on the unit: the faces gate says so for faces, the first-flash note says so for timers, and nothing records a run for touch, privacy, sounds or dance. Four things the owner expects are not built at all: reset on the device, the over-the-air update, the hardened portal inside the firmware, and the day-to-day rules (hourly chime, low-battery ladder). The portal exists only as a page and C core tested on a PC.

Status words:
- BUILT-ON-UNIT-VERIFIED: in the flashed image and a real run on the unit showed it work.
- BUILT-NOT-VERIFIED: in the flashed image (or in the patch order) but no run on the unit showed the feature itself.
- HOST-ONLY: code and tests exist on the host, nothing of it is in the firmware yet.
- NOT-BUILT: no patch and no host code found.

Size: S is under a day, M is one to three days, L is more. Lane: FW is the firmware agent, HOST is the host agent. Priority 1 is highest user value.

## Memory room (from the gate reports)

| Measure | Last measured | Gate | Room |
|---|---|---|---|
| internal_free, steady | 58,000 bytes (faces build, 2026-11-16) | 25,000 | about 33 KB, but the rule says a step over 4 KB needs a reason |
| internal_min | 39,828 | 15,000 | about 24 KB |
| int_big | 31,744 | 16,000 | about 15 KB |
| psram_min | 7,824,012 | 6,000,000 | about 1.8 MB |
| App slot free | 2,164,000 bytes (42 percent, after the security fixes) | 20 percent (about 1,035,000) | about 1.1 MB of flash |

The security build (CA bundle cut, patches 155 to 158) was not re-measured for heap. The six faces were measured idle only, so their drawing cost is unknown. Plan on a spend of at most 8 KB steady internal RAM per train, everything new in PSRAM, and a heap line read after each train.

## One table, a row per core feature

| Feature | Promised where | Status | Evidence | Size to finish | Lane | Priority |
|---|---|---|---|---|---|---|
| Spoken turn over the paired link | features.md Voice; cut: 001, 003, 014, 016, 018 | BUILT-ON-UNIT-VERIFIED | Patches 003-persistent-websocket, 014, 016, 018; host self-test `speech` and `reply` pass after the plain flash | none, soak a longer turn | FW | 1 |
| Boot, Wi-Fi join, idle face, memory gate | build order step 1 | BUILT-ON-UNIT-VERIFIED | first-flash note (12 min clean, gate passed); faces gate (11.6 min, passed) | none | FW | 1 |
| Face styles, color, captions (big-eyes pack, minimal pack) | features.md Faces and look; decisions 22 | BUILT-NOT-VERIFIED | F01, F02; `host/maipai_body/faces.py`, `test_faces.py`; the face tools were never called on the unit | S (call it, look at the screen) | HOST, then FW | 1 |
| Time-of-day faces | Ideas after a market audit | BUILT-NOT-VERIFIED | F03 | S | FW | 2 |
| Clock face, works with no host | Faces and look | BUILT-NOT-VERIFIED | F04; `monitor_cue_begin` not in the tree, so the clock avoids cues by state only | S | FW | 1 |
| Thinking dots and quiet tone | decision 23 | BUILT-NOT-VERIFIED | F05; host `FaceService.thinking` wired to the turn sink in `app.py` | S | FW | 2 |
| Several named timers with live countdowns | Ideas after a market audit | BUILT-NOT-VERIFIED | F06, 090 to 094; timer tool registered, never called; a long caption is overdrawn by the chips | S | FW | 1 |
| Timers and alarms, snooze, stop by touch and voice | Voice and assistant | BUILT-NOT-VERIFIED | 090 to 094; `host/tests/firmware/timers_core_test.c`; host `timers.py`, `initiative/alarm.py` | S | FW | 1 |
| Quick-slider overlay from the head strip | Faces and look; decision 24 | BUILT-NOT-VERIFIED | C03-swipe-gestures-and-quick-settings; swipe up was the owner's open fault (decision 14) and no unit run is recorded | M | FW | 1 |
| Pickup, shake and tilt reactions | Always-on | BUILT-NOT-VERIFIED | C04 shake threshold; host `presence/carry_reaction.py`; the unit-side tap patch 081 (IMU tap) is not in ORDER | M | FW | 2 |
| Head-touch petting and tap | Always-on | BUILT-NOT-VERIFIED | 047, 048, 056, 080; `touch_core_test.c`; rub detection 052 is DEFER | S | FW | 2 |
| Speech wobble and breathing idle | Always-on | BUILT-NOT-VERIFIED | 047, 037; host `expression/idle.py` | S | FW | 3 |
| Free-roaming idle life | Always-on | BUILT-NOT-VERIFIED | 037-idle-motion-tool; the client called `set_idle_motion` 119 times on the old image and got "Unknown tool" | S (rerun on the new image) | HOST | 2 |
| Privacy sleep, hard mute, vision off, full quiet | Always-on; safety rules | BUILT-NOT-VERIFIED | 105, 106, 107, `maipai_touch_core.h`; the wake engine logged "muted or full quiet", the privacy states exist; the muted-mouth and closed-eyes looks (108, 122) are not built | M | FW | 1 |
| Camera-on cue that cannot be turned off | Always-on; cut: `monitor_cue_begin` stays core | NOT-BUILT | `monitor_cue_begin` is not in the tree (faces status note); camera patches are HOME-PRESET | M | FW | 2 |
| Quiet mode, quiet hours, light and tone per state | Always-on | BUILT-NOT-VERIFIED | 115, 116, 117; `sounds_core_test.c`; host `sounds.py`, `settings_keys.py` | S | FW | 2 |
| Hourly chime | Always-on | NOT-BUILT | no rule found in 115 to 117 or the host | S | FW | 3 |
| Wake feedback cue | Always-on | NOT-BUILT | no wake cue patch; 086 wake self-test and 083 are not ported | S | FW | 2 |
| Low-battery ladder: 20 percent chirp, 10 percent spoken, 5 percent sleep | Always-on | NOT-BUILT | battery reading is C01; the low-battery earcon exists in 115, no ladder | S | FW | 1 |
| Wake word on the unit, stop word | Voice and assistant | BUILT-NOT-VERIFIED | 049, 094; the engine logged that it stays off while muted; the stop word was not observed; the 25 KB model needs 34 KB free at creation | S | FW | 1 |
| Voice commands: stop, mute, volume, brightness, sleep, time, night mode | Voice and assistant; decision 15 | BUILT-NOT-VERIFIED | host `stop_phrases.py`, `volume.py`, `brightness.py`, `presence/night.py`; unit stop word 049 | S | HOST | 2 |
| Follow-up without the wake word, barge-in | Voice and assistant | HOST-ONLY | `speech/follow_up.py`, `speech/barge.py`, `test_followup.py`, `test_bargein_*` | S (unit run) | HOST | 2 |
| Offline phrases | Voice and assistant | HOST-ONLY | `speech/offline_clips.py`; the unit side is patch 118, DEFER and not ported | M | FW | 3 |
| Speech speed and pitch setting | Ideas after a market audit | HOST-ONLY | `speech/pitch.py` is a per-voice pitch offset; no speed setting anywhere | S | HOST | 3 |
| Cooking helper prompt pack | Ideas after a market audit | NOT-BUILT | no persona text or command set in the repo | S | HOST | 3 |
| Dance on request | core-extras-modules.md | BUILT-NOT-VERIFIED | 020-dance-mcp-tools; host `dance*.py`, `moves/`, `test_moves*` | S | FW | 2 |
| Music dance and mood faces | Touch and play | HOST-ONLY | host `music_dance.py`, `test_music_dance.py`, `beat_test.c`, `music_core_test.c`; unit patches 121, 124, 126 to 128, 130, 131 are DEFER, 100 to 101 HOME-PRESET | M | FW | 3 |
| Lights: ring and per-pixel tool | features.md | BUILT-NOT-VERIFIED | A01-per-pixel-led-tool, C02 boot ring; host `light*`, `ring*`; the ring-dark patches 050 and 114 are not ported | S | FW | 2 |
| Sleeping face | Faces and look | BUILT-NOT-VERIFIED | C05 | S | FW | 3 |
| Offline look, link screen, "waiting for approval" | cut: 111, 112, 113 | NOT-BUILT | patches not in ORDER; C02 has the connecting screen only | M | FW | 1 |
| Quiet reconnect, offline earcon after 3 minutes, "charged once" | cut: 119, 120, 141, 151 | NOT-BUILT | not in ORDER | S | FW | 2 |
| Self-restart guard and crash fixes | cut: 074-unit-crash-fixes, 085 | NOT-BUILT | not in ORDER; one boot abort (`ReadReg` 0x108) seen in five boots on the faces flash | M | FW | 1 |
| Pairing and security (token hand-off, no keys, no public CA, no vendor URLs) | decisions 12; security note | BUILT-NOT-VERIFIED | 018, 155 to 158, `scripts/check-no-keys.py`; image strings checked, no unit run of the tool removals | S | FW | 1 |
| Signed updates, wireless | features.md; release-and-updates.md | NOT-BUILT | 155 holds the Ed25519 check but nothing calls the vendor client, so a unit cannot install over the air; patch 133 is not ported; host `updater.py` and `test_stackchan_updating_route.py` exist | M | FW | 1 |
| Reset the device (two-step, atomic) | features.md "Reset the device" | NOT-BUILT | no patch, no handler | S | FW | 1 |
| Better Wi-Fi setup portal (protected, no saved-network list, timeout) | owner ask | HOST-ONLY | `host/tests/firmware/portal_core_test.c`, `test_portal_core.py`; no portal patch in ORDER; the interim fix is not applied | M | FW | 1 |
| Core settings page on the host | core-extras-modules.md | BUILT-NOT-VERIFIED | `settings_page.py`, face section, language; checked through routes, never in a browser; hub host is an older release | S | HOST | 1 |
| English and Spanish | decision 25; languages.md | BUILT-NOT-VERIFIED | host `i18n.py` catalog test; portal table both languages; screen text is ASCII only, no accents | S | HOST | 2 |
| Travel with the private network | features.md core list; Open | BUILT-NOT-VERIFIED | TN01 to TN06 (rebuilt from 147, 148, 153); behind MAIPAI_TAILNET; measured on the unit with a placeholder key, never joined a real network; see `travel-2026-11-16.md` | L | FW | 3 |
| Games on one engine (color memory, action, whack-a-mole) | features.md Touch and play | NOT-BUILT | no engine in the firmware or the host | L | FW | 3 |
| Mood that depends on care, saved across days | features.md Touch and play | NOT-BUILT | nothing found | M | FW | 3 |
| ESP-NOW pose mirroring | features.md Touch and play | NOT-BUILT | ESP-NOW was removed on purpose (097, S01) | M | FW | 3 |
| Photo-frame face | features.md Ideas | NOT-BUILT | deferred by the design until there is headroom | L | FW | 3 |

## Missing on the unit that the host expects

On the first-flash image the client called six tools the unit lacked. Three now have patches in ORDER (`set_idle_motion` 037, `set_sound_policy` 116, `keep_awake` 074) and still need a call on the unit to prove it. Two remain unknown in the latest log: `self.music.set` (44 calls) and `self.screen.set_face_background` (63 calls). Both belong to the Home preset or to the deferred face skins, so the cheapest fix is a host change: stop calling them on a core unit.

## Ranked build list, 15 items in three trains

A train is one firmware build and one unit load. Every item passes the memory gate. Rank inside a train is build order. All sizes are estimates.

### Train 1: make the flashed unit safe to live with (5 items)

1. Reset on the device (S, FW): the screen, the hold, the atomic clear. No resident cost.
2. Wireless update (M, FW): port patch 133 onto the new tree, call the vendor client so the Ed25519 check in 155 runs, set the public key from the build. About 2 to 4 KB flash code, little heap.
3. Wi-Fi portal into the firmware (M, FW): wire the tested page and core as patches, protected window of 5 to 10 minutes, generic network name, no saved-network list. The page lives in flash. It replaces the stock portal, so net flash falls.
4. Self-restart guard and crash fixes (M, FW): patches 085 and 074-unit-crash-fixes, plus the `ReadReg` retry. This protects every other item.
5. Offline look, link screen and "waiting for approval" (M, FW): patches 111 to 113 in the new face code. Drawn shapes, no new font.

Memory plan: about 4 KB steady internal at most (portal and update paths run only when needed). Gate check: boot, 10 minute idle, then one forced portal start and one update refusal.

### Train 2: daily rules and privacy looks (5 items)

6. Low-battery ladder: 20 percent chirp, 10 percent spoken request, 5 percent sleep (S, FW with a host spoken line).
7. Hourly chime and quiet hours rule on the unit (S, FW): extends the policy core in 115, which already carries the quiet window.
8. Wake feedback cue and wake self-test (S to M, FW): the cue from the sound policy, patch 086 for the self-repair.
9. Quiet reconnect, offline earcon after 3 minutes, charged once per session (S, FW): patches 119, 120, 141, 151 as one change.
10. Privacy looks: muted mouth, closed eyes when vision is off, and the cue path `monitor_cue_begin` the clock needs (M, FW): patches 108, 122 and the camera-on cue.

Memory plan: all small state and shared one-second timers. Expect under 3 KB steady. Gate check: add a battery sweep with the simulator and a mute and vision-off check by touch.

### Train 3: play and polish (5 items)

11. Speech speed with the existing pitch offset (S, HOST): one setting in the settings page and the speech output.
12. Cooking helper pack (S, HOST): persona text, "next step" command, per-step timers on the existing timer tool. No firmware.
13. Offline phrases, unit side (M, FW): patch 118, only after the wake and stop checks pass on the unit.
14. Mood that depends on care, saved across days (M, FW): a small record in saved settings, face shifts driven by the existing touch events.
15. First game on a built-in engine, color memory as a signed data pack (L, FW): PSRAM for the pack, no scripting runtime (firmware-memory.md). Build the engine once and ship one game.

Memory plan: 13 and 14 need about 4 KB steady internal each at most; 15 stays in PSRAM. Gate check: a full spoken turn with a game running and the heap line for 10 minutes.

## Not on the list, and why

- Travel with the private network (L): built 2026-11-16 (`travel-2026-11-16.md`); a real join needs a pairing key from the owner.
- ESP-NOW mirroring: removed to save memory and the attack surface; needs a second unit to test, which is the owner's call.
- Music dance on the unit (121 to 131): high value but heavy on the audio path; schedule after Train 3 and the heap line.
- Photo-frame face: the design says wait for headroom.
- Camera, live view, monitor modes, find my robot, remote control: tagged Home.

## Before anything new is built

1. Call every face, timer, sound-policy and idle-motion tool once on the unit and read the reply. This turns most BUILT-NOT-VERIFIED rows green and is cheaper than any new feature.
2. Update the host on the hub to the release that knows the face tools; until then the face rows stay unobserved.
3. Re-measure heap on the security build and add a permanent gate line to the firmware log (the first-flash note asks for it).
