# Two new features: passcode lock and streaming radio (2026-11-17)

Placement: design note and backlog. Nothing here is built. Each item carries a placement line from the App Store test (`docs/dev/scope-core-vs-home.md`).

## 1. Passcode lock

**Placement:** unit firmware (the robot must enforce it alone, even with the host off) plus host settings page (set the code, the timeout, manual lock). Local. Home may later add per-person codes and policy (household identity is a Home matter); the basic lock is not Home.

**What it does (owner, 2026-11-17):** a code keeps other people from using the robot. A timeout locks it automatically (the owner sets it on the settings page, or turns auto lock off). It can be locked by hand from the settings page. While locked, the robot does not respond to the wake word, does not open settings, and shows only a lock screen with a keypad. No lockout after wrong tries for now (owner decision); see the risk below.

**Behavior**
- Lock state is stored on the unit and survives a reboot: a locked robot is still locked after power loss.
- Locking: manual (settings page, a lock tile on the control sheet, or the voice command "lock"), or automatic after N idle minutes (off, 1, 5, 15, 30, 60; idle means no touch, wake word or remote action).
- Locked screen: the sleeping face with a small padlock icon, dimmed to the night level. A touch shows a keypad (a 3 by 4 grid of 44 px keys, 4 to 6 digits, backspace, a cancel that returns to the lock screen). Unlock only by the keypad. A spoken code is never accepted (it can be overheard).
- While locked: the wake word engine is off (so no wake, and no listening for it), the stop word is off, the touch screen shows only the keypad, the control sheet, pages, games, settings and swipes are off, remote controllers are refused except "find my robot" (beep and flash, so a lost robot can be found), the camera and microphone cues keep working and nothing new turns them on.
- Still works while locked: timers and alarms keep ringing, and a ringing alarm or timer can be stopped with one tap without the code (safety); the clock runs; privacy cues; mute; low battery shows.
- The code: 4 to 6 digits, set on the settings page (changing it needs the current code if one is set). Stored as a salted, stretched hash in the unit's settings storage; the code itself is never stored, logged or sent. The host never holds the code; it asks the unit to set or clear it.
- Forgotten code: the existing two-step physical reset clears it (and everything else). The code protects against other people using the robot, not against the person who owns the host and the unit.
- The Home hub, when paired, may mirror the lock state and set a code; local operation does not need it.

**Risk to record (owner chose no lockout for now):** a short code with unlimited tries can be guessed at the keypad (a child could try 10,000 combinations). Recommended later, without calling it a lockout: a one-second pause between wrong tries, growing after five. Not built until the owner says so.

**Build size [estimate]:** a lock state, a hash and a keypad template; about 4 to 6 KB of flash, under 1 KB of RAM; the keypad is a display-list template once the template renderer exists, otherwise a small native screen.

**Tests:** wake word ignored while locked; touch limited to the keypad; the hash is salted and the code never appears in logs or the settings dump; auto lock after the idle time and not while an alarm rings; a reboot stays locked; alarms still ring; the lock cannot be cleared by any remote command; a wrong code never reveals the length.

## 2. Streaming radio and a player

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
