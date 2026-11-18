# Offline audit: what the unit does with no host and with no internet (2026-11-18)

Placement: unit and host (design only, no code). Serves owner decision 24 (offline plan). Input to `docs/design/content-pantry.md` and `docs/design/model-games.md`.

## How to read this

Two cases, because they fail differently.

- **No host.** The unit has power, and Wi-Fi may be up or down, but nothing answers on the host address. The unit is on its own.
- **No internet.** The host is up on the home network and the internet is gone. Everything configured to run on the host works. Anything pointed at an outside address fails.

Tags: **works** (same as online), **degraded** (some of it works, the note says which part), **missing** (nothing happens, or only an error cue), **unknown** (the sources do not say; the note says what to read or measure).

The sources are the ledger (`docs/dev/feature-ledger.md`), the user page (`docs/user/features.md`) and the pages it links, the patch headers in `firmware/patches/`, and the host code named in each row. I did not run a unit. A row marked works means the sources say it runs on the unit with no call to the host, not that it was seen offline on a bench. The ledger has 874 rows. The everyday user rows (362) are audited as feature groups, because rows in one group share one answer (36 overlay rows, 32 motion rows, 25 light and tone rows). The 512 maker and tech rows are host modules, scripts, patches and tool protocol: they are not unit behavior, and section 4 gives the one answer for them.

The unit's design is a body on a talk loop: the wake word, the screen, the servos, timers and games run on the unit; hearing, thinking and speaking (speech to text, model, text to speech) run on the host (`docs/design/brain-seam.md`, `docs/design/own-llm-brain.md`).

## 1. Audit by feature

| # | Feature (ledger section) | No host | No internet | Note and source |
|---|---|---|---|---|
| 1 | Wake word (Voice) | works | works | The wake model runs on the unit. `docs/user/voice.md` "The wake word"; `docs/design/next-unit-voice-commands-2026-11-17.md` "What exists". |
| 2 | Spoken answer to a question (Voice) | missing | degraded | The host does speech to text, model and speech to speech. With no host the unit shows a calm "Can't reach Home" bubble, a doubtful face and a tone for 3 s (`075-offline-mode.patch`, intent 2). With no internet it works only when the model, speech to text and text to speech are local (`docs/design/own-llm-brain.md`, `stt_url`, `tts_url`, local engines); a cloud address fails with "I could not reach the model at <host>". |
| 3 | Follow-ups without the wake word (Voice) | missing | degraded | Host ends the follow-up window (`034-host-idle-command.patch`). Same internet note as row 2. |
| 4 | Voice commands: stop, mute, quiet, volume, brightness, sleep, time, night mode (Voice, 8 rows) | degraded | works | Only the stop word runs on the unit (patch 049; `next-unit-voice-commands-2026-11-17.md`). The rest go through the host's local command router, which needs the host awake, not the internet. Touch controls for the same actions work (row 20). |
| 5 | Offline phrases, 16 clips (Voice) | works | works | Sixteen clips for no Wi-Fi, connecting, no answer, refused, back (`V02-offline-phrases.patch`). 81,070 bytes in `host/maipai_body/bodies/stackchan/firmware/assets/phrases/`. A pack (`K12`) swaps in the household voice. Gap: one voice, English built in, English and Spanish packs (`docs/user/languages.md`). |
| 6 | "Offline" label, amber ring, offline tone, "I'm back" (Lights and sounds, Camera) | works | works | Label and ring after 45 s (`143`), tone after 3 min, quiet reconnect (`T04`). |
| 7 | Persona, speech speed and pitch (Voice) | missing | works | Prompt and speech settings live on the host (`docs/user/voice.md` "Persona"). |
| 8 | Custom and cloned voices, song naming, calendars, memories, companions (Home rows) | missing | unknown | MaiPai Home features. No host means no Home. With no internet, any that call an outside service fail; the sources do not list which. Read the Home contract (`docs/plan/home-contract.md`). |
| 9 | Moods, face styles, face colors, captions, banner (Faces and moods, 52 rows) | degraded | works | Drawing and idle breathing, blinks and gaze run on the unit (`docs/user/moves-and-moods.md` "Idle"). The mood to show comes from the host's reply tags, so with no host the face stays at neutral, the offline look and the tired look from the battery. Captions are off by default (decision 22) and have no text to show with no host. |
| 10 | Picture faces and character packs (Faces, Updates) | works | works | Stored in the unit's pack cache and drawn on the unit. Installing one needs the host. |
| 11 | Weather and mood overlays (Overlays, 36 rows) | degraded | works | Drawn on the unit. Triggered by the host's reply tags. No unit-side trigger is described. No outside weather service is involved. |
| 12 | Clock face, time-of-day faces, night mode (Time, Faces) | degraded | works | Network time is off by default (`004-configurable-sntp-empty.patch`, `docs/design/egress-audit.md`), so the clock needs the host once to learn the time (`docs/user/timers-and-alarms.md` "Offline"). Whether the time survives a reboot with no host is unknown: check for a hardware clock use in `firmware/main/hal/`. |
| 13 | Timers and named timers, ring, stop by touch (Time) | works | works | Run with no model (`090` to `094`). `docs/user/timers-and-alarms.md` "Offline". Setting one by voice needs the host. |
| 14 | Alarms and snooze (Time) | degraded | works | Same unit code, but an alarm needs a known time (row 12). |
| 15 | Hourly chime, quiet hours (Time) | degraded | works | Need a known time. `SF52-quiet-schedule-days-and-quiet-now.patch`. |
| 16 | Pickup, shake, tilt, petting, mood from care (Motion) | works | works | IMU and touch strip on the unit. `docs/user/moves-and-moods.md`. |
| 17 | Dances on request (Motion, 32 rows) | degraded | works | A named dance asked by voice needs the host. Sound-driven dancing runs on the unit, off until switched on, with a rest cap (`SF14-offline-dance-rest-cap.patch`). |
| 18 | Low-battery steps (Battery) | degraded | works | Chirp at 20 percent and sleep at 5 are unit logic (`T01-low-battery-ladder.patch`). The spoken ask at 10 percent: unknown whether it is a built-in clip or a host line. |
| 19 | Seven games: Color Memory, Whack-a-mole, Tic-Tac-Toe, Do It, Rock Paper Scissors, Magic 8-Ball, Dice and Coin (Games) | works | works | Declarative packs run by the unit's engine (`firmware/games/*.mpk`, `docs/plan/more-games-engine.md`), best five scores in the unit's storage. `docs/user/games-and-pet.md`: "work even when MaiPai Home is off". Starting by touch works; starting by voice needs the host (row 4). |
| 20 | Control sheet, swipe pages, Apps list, tabbed settings, quick actions (Screens) | works | works | Volume, brightness, mute, quiet, lock, apps, games, settings, time zone are unit screens (`docs/user/features.md` "Control sheet"). Settings that live on the host page (see row 28) are not reachable. |
| 21 | Mute, camera off, full quiet, passcode lock, no-stealth cues (Safety) | works | works | Unit state with unit cues. `docs/user/mute-and-camera-off.md`. |
| 22 | Talk games: 20 Questions, riddles, trivia, word chain, would you rather, bedtime stories (Games) | missing | degraded | `host/maipai_body/bodies/stackchan/talk_games.py` runs on the host and hands rules to the model. Needs host and model. Built, not flashed, not tested with a live model (`docs/user/games-and-pet.md`). Fixed by decision 24 and 27 (`docs/design/model-games.md`). |
| 23 | Wi-Fi setup page, reset button, pairing code (Updates, Screens) | works | works | The unit serves the setup page and shows the code. Pairing itself needs the host: missing with no host. |
| 24 | Away from home, private network (Link) | works | unknown | The unit joins by itself when it cannot reach the host (`docs/user/use-it-anywhere.md`). Whether the join needs the vendor's coordination server or can use a self-hosted one is not stated: read `firmware/tailnet/`. |
| 25 | Camera: photo, live view, watch, alerts, find my robot, remote control, parent view (Camera, 45 rows; Parent view, 5) | missing | works | The host stores and serves them. The unit keeps the cue path (purple cue, camera light) with no host. Face detection on the unit is an experiment, off and not flashed (`docs/user/features.md`). |
| 26 | Signed updates with rollback (Updates) | degraded | unknown | The unit verifies and rolls back by itself. The image arrives from the host. Whether a host with no internet can serve an update it already holds: read `docs/design/release-and-updates.md`. |
| 27 | Installed set: languages, faces, fonts, games, sounds, offline phrases (Updates, 7 rows) | degraded | works | Installed items stay and run. Installing, swapping and removing need the host (`docs/plan/installed-set.md` B6). |
| 28 | Settings page, dashboard (Screens, Settings) | missing | works | Served by the host. `docs/user/settings.md`. |
| 29 | Local API, event stream, MQTT, Home Assistant, coding companion, memory notes (Optional packages, Link) | missing | works | Host packages, off by default. They need only the LAN. |
| 30 | Languages: six first-run tables, language packs (Languages, 11 rows) | works | works | Compiled in or installed in the pack cache. Switching language by voice needs the host. |
| 31 | Several robots, one host (Link) | missing | works | Host feature. |
| 32 | Filler sounds while thinking (Lights and sounds) | missing | works | A thinking cue only happens while a turn is in flight. Not built to be heard by a person yet. |
| 33 | Planned rows: offline voice commands, more wake words, focus countdown, wake look-around, encrypted link, infrared and NFC, phone as host, outside games, reviewed translations (Wanted, 19 rows) | missing | missing | Not built. Offline voice commands is the one that changes this table. |

Totals for the 33 groups. No host: 12 works, 10 degraded, 11 missing. No internet: 26 works, 3 degraded (rows 2, 3, 22), 3 unknown (rows 8, 24, 26), 1 missing (row 33).

## 2. What is missing

With no host the unit cannot do these things, in order of how often a person meets them:

1. **It cannot say anything new.** Wake it and it plays one of 16 stored clips about being offline, then goes quiet. There is no joke, riddle, story or fact. Rows 2, 3, 22.
2. **No game by voice, no talk game.** Touch games work. Rows 4, 19, 22.
3. **Wrong or unknown time after a restart.** Alarms and the chime depend on it. Rows 12, 14, 15.
4. **The face does not react to anything.** No mood tags, no overlays, no captions. Rows 9, 11.
5. **Only the stop word works by voice.** Quiet, mute, volume by voice need the host. Row 4.
6. **No settings page and no installs.** Rows 27, 28.
7. **Offline phrases are one voice and two languages.** Row 5.
8. **No way to tell the person what is wrong beyond "offline".** The 16 clips say which state (no Wi-Fi, connecting, not answering, refused), but the screen shows one word.

With no internet and the host up, the gap is the configured model: a cloud address fails (row 2). The host should detect this and use the same pantry the unit holds (state S1 in `model-games.md`).

## 3. Ranked fix list

Rank = how many people meet it times how bad it feels, then cost. Owner of each fix in brackets.

| Rank | Fix | Closes | Cost and notes |
|---|---|---|---|
| 1 | **Content pantry on the unit** (jokes, riddles, trivia, stories as text) plus code-made mumble and captions, refilled by the host. Decision 24. Design: `content-pantry.md`. [firmware, app] | missing 1, rows 2, 3, 22 | About 200 KB of the 1.56 MB asset pool for two languages, no internal RAM. New asset kind. |
| 2 | **Touch tiles for pantry play**: tell, reveal, got it, not yet, another. Works with no microphone. Design: `model-games.md`. [firmware, playground] | missing 2 | Small: reuses the game-pack screens or the subtitle strip. |
| 3 | **Keep time across a restart with no host.** Check for a hardware clock use; if none, store the last time in storage on a schedule and mark the clock "approximate" on screen until the host confirms. Allow an owner-set address for network time (decision 12 permits addresses the owner configured). [firmware] | missing 3, rows 12, 14, 15 | Small. Needs a read of `firmware/main/hal/` first. |
| 4 | **Host answers when the model is down**: host up, model unreachable, host serves the pantry through the normal speech path. [app] | no-internet row 2, 22 | Small host change. |
| 5 | **Offline voice commands beyond stop** (pause, cancel, louder, quieter, mute, lock). Already designed in `next-unit-voice-commands-2026-11-17.md`. [firmware] | missing 5, row 4 | Recognizer is loaded, cost is the phrase list. English first. |
| 6 | **Idle face on its own**: a small set of unit-chosen moods (a slow look around, a yawn after a long quiet, a smile on a pet) so the face is not frozen with no host. [firmware] | missing 4 | Check the existing idle code first. |
| 7 | **Offline phrases per language**: build packs for every installed language, not English and Spanish only. [app] | missing 7 | Host job, 16 files per language. |
| 8 | **Screen says why** (no Wi-Fi, host not answering, refused) in the banner, not one word. [firmware] | missing 8 | The state is already known (V02). |
| 9 | **Settings on the unit for the five choices a person needs with no host**: language, volume, brightness, time zone, face style. [firmware] | missing 6 | Most exist on the control sheet. Confirm each. |
| 10 | Run the offline bench: power the host off, then Wi-Fi off, then internet off, and record each row of section 1 on the unit. Turns every works into a measured works. [bench] | all unknown | One bench window. |

## 4. Maker and tech rows (512)

Host modules (298), scripts and tools (82), tool protocol (35), the patch series (41) and the rest are code and tools. Host modules and scripts need the host by definition and need the internet only if they were pointed at an outside address; decision 12 says the host calls no address the owner did not configure, and `docs/design/egress-audit.md` is the evidence. The patch series is the unit side and is covered by the feature rows above. The tool protocol rows describe calls between the host and the unit: with no host they do not run. No row in these sections needs its own offline answer. The exception to check is the build and release scripts that download models or libraries; they need the internet at build time only.

## 5. Open points

- Rows 12, 18, 24, 26 are unknown until the files named in the note are read or the bench is run.
- This audit did not run a unit. Rank 10 turns it into measured results.
