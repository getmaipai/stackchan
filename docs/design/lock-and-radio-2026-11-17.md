# Two new features: passcode lock and streaming radio (2026-11-17)

Placement: design note and backlog. The passcode lock (section 1) is built in firmware patches LK01 to LK03 and in the host settings page; it is not flashed on the owner's unit until the memory gate result below is filled in. Radio (section 2) is not built. Each item carries a placement line from the App Store test (`docs/dev/scope-core-vs-home.md`).

## 1. Passcode lock

**Placement:** unit firmware (the robot must enforce it alone, even with the host off) plus host settings page (set the code, the timeout, manual lock). Local. Home may later add per-person codes and policy (household identity is a Home matter); the basic lock is not Home.

**What it does (owner, 2026-11-17):** a code keeps other people from using the robot. A timeout locks it automatically (the owner sets it on the settings page, or turns auto lock off). It can be locked by hand from the settings page. While locked, the robot does not respond to the wake word, does not open settings, and shows only a lock screen with a keypad. No lockout after wrong tries for now (owner decision); see the risk below.

**Behavior**
- Lock state is stored on the unit and survives a reboot: a locked robot is still locked after power loss.
- Locking: manual (settings page, the More screen, or the voice command "lock"), or automatic after N idle minutes (off, 1, 5, 15, 30, 60; idle means no touch, wake word or remote action).
- Locked screen: the sleeping face with a small padlock icon, dimmed to the night level. A touch shows a keypad (twelve large keys, 100 by 44 px, three across and four down, 4 to 6 digits, backspace, a cancel that returns to the lock screen; no words: entry dots and keys only; a wrong code shakes the dots and flashes them red). Unlock only by the keypad. A spoken code is never accepted (it can be overheard).
- While locked: the wake word engine is off (so no wake, and no listening for it), the stop word is off, the touch screen shows only the keypad, the control sheet, pages, games, settings and swipes are off, remote controllers are refused except "find my robot" (beep and flash, so a lost robot can be found), the camera and microphone cues keep working and nothing new turns them on.
- Still works while locked: timers and alarms keep ringing, and a ringing alarm or timer can be stopped with one tap without the code (safety); the clock runs; privacy cues; mute; low battery shows.
- The code: 4 to 6 digits, set on the settings page (changing it needs the current code if one is set). Stored as a salted, stretched hash in the unit's settings storage; the code itself is never stored, logged or sent. The host never holds the code; it asks the unit to set or clear it.
- Forgotten code: the existing two-step physical reset clears it (and everything else). The code protects against other people using the robot, not against the person who owns the host and the unit.
- The Home hub, when paired, may mirror the lock state and set a code; local operation does not need it.

**Risk to record (owner chose no lockout for now):** a short code with unlimited tries can be guessed at the keypad (a child could try 10,000 combinations). Recommended later, without calling it a lockout: a one-second pause between wrong tries, growing after five. Not built until the owner says so.

**Build size [estimate]:** a lock state, a hash and a keypad template; about 4 to 6 KB of flash, under 1 KB of RAM; the keypad is a display-list template once the template renderer exists, otherwise a small native screen.

**Tests:** wake word ignored while locked; touch limited to the keypad; the hash is salted and the code never appears in logs or the settings dump; auto lock after the idle time and not while an alarm rings; a reboot stays locked; alarms still ring; the lock cannot be cleared by any remote command; a wrong code never reveals the length.

**Built (2026-11-17), what the patches do beyond the text above**
- `LK01` is the pure C core (`maipai_lock_core.h`, host test `lock_core_test.c`). The hash is PBKDF2 with HMAC-SHA-256, 2000 rounds, a 16 byte random salt; it uses the core's own SHA-256, not the chip's hash block, because the rounds need the raw compression function that the SDK's hash API does not expose. `LK_WRONG_DELAY_MS` is 0 (owner decision, no lockout); it is the one place to raise.
- There is no "enter" key: every digit from the fourth on is checked, so the screen never shows how long the code is. Six wrong digits clear the entry and show one wording.
- `LK02` is the unit module (state in settings namespace `mp_lock`, the tools `self.lock.status`, `set`, `clear`, `now`, `config`, the lock screen and keypad). A locked unit answers `set`, `clear` and `config` with reason `locked`, and no tool unlocks.
- `LK03` is the enforcement (wake word, voice processing, stop word, swipes, pages, sheet, settings, Wi-Fi, quick settings, games, remote controllers except find) and a Lock button on the More screen (shown only while a code is set). Owner decision, 2026-11-17: the control sheet keeps its one row of six tiles and has no lock tile; the Apps list and Settings, General are the planned homes for Lock.
- The physical two-step reset erases the namespace with everything else (a test keeps `mp_lock` out of the reset's keep list).

## 2. Streaming radio and a player (REMOVED 2026-11-17: tried on the unit and dropped)

**Outcome (owner, 2026-11-17):** a host-side player was built and played real streams and a local file through the unit. The unit's small speaker is weak and music sounded thin and distorted even with a richer encoder, a level control and a soft limiter; the robot also answered the music through its own microphone. The owner asked to remove the feature. The code, tests, settings card and saved stations were deleted. If revisited, the first step is a firmware music decode path and a bench echo test, not more host code. The design below is kept as a record.


**Placement:** split.
- **The player is a host package (local).** The host fetches a stream the owner names, turns it into the same Opus audio the unit already plays for speech, and sends it over the existing audio channel. The unit needs no new codec. Volume, mute, quiet hours and the stop word work as for speech. A "now playing" card shows the station. It plays through the same small speaker: chiptunes and spoken-word stations suit it; full-range music will sound thin.
- **A stream the owner types or picks is an owner-enabled integration,** like the owner's own model address. It is off by default; when on, the host connects to exactly the addresses the owner chose, only when asked to play, and the egress list says so. The owner's own stream on the home network (an Icecast server, a media server) is fully local and needs nothing outside.
- **Station directories, search, curated lists and anything that needs an outside service to discover music are Home tools.** In local mode the owner keeps their own short list on the settings page. The host does not fetch a directory by itself.

**Voice:** "play chiptunes", "play my jazz station", "stop the music", "louder", "next station". These start the player with no model call. Volume and stop are local commands.

**Fit with the rest:**
- **Wake word while playing:** the unit's speaker leaks into its microphone. The wake word must still work: the host ducks the music (lowers it) on wake, and the unit's echo control must be tested with music at the common volumes. This is the main technical risk and needs a bench test.
- **Dance:** the dance to music feature listens through the microphone; the robot's own music will make it dance. This is a nice default (it dances to the radio) and can be switched off.
- **Resources:** audio playback adds no firmware; the host does the decoding. Network jitter needs a buffer of about two seconds; lost packets are skipped, never retransmitted.
- **Licensing:** the owner connects to public streams as any player would. The project ships no music and no list of stations; any starter list is data the owner edits.
- **Privacy:** no listening history leaves the host. In Home mode, Home may keep presets and history under its own policy.

**Build order:** (1) host player package with a URL list, play, stop, volume, now-playing card; (2) the wake word and echo test with music; (3) dance to the radio; (4) Home directory integration (a Home tool).
