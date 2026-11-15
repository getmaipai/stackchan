# Firmware v1 cut

Verdict: **REBUILD** the core subset from the new base. Patch-map PORT rows are still assessed against the current design; where they fall in the core they remain small eligible carries. Rows classified UPSTREAM are dropped by naming the matching upstream change. The intent and patch-map decide scope; if the scope is uncertain, the row is DEFER.

## Patch inventory

Every patch file in the patch directory is listed below, including recipe patches, the three known replay orphans, and the extra MicroLink patch. Reasons are specific to release scope. The inventory has 130 files: 126 recipe patches plus four orphans.

| Patch | Tag | Reason |
|---|---|---|
| `001-server-url-empty` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: leave the M5 avatar server unset unless a local installer configures it. |
| `002-nvs-websocket-no-ota` | **CORE-V1** | Required for private paired-host setup, secure operation, or signed updates. Intent: skip xiaozhi OTA and activation, use the already provisioned NVS websocket settings. |
| `003-persistent-websocket` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: No Intent header; see patch-map status. |
| `003-stackchan-kconfig` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: No Intent header; see patch-map status. |
| `004-configurable-sntp-empty` | **CORE-V1** | Required for local touch or reaction behavior. Intent: make SNTP host configurable and disabled by default to prevent public time calls. |
| `005-disable-m5-registry-mqtt` | **CORE-V1** | Required for private paired-host setup, secure operation, or signed updates. Intent: stop starting M5 EzData registry and MQTT, and remove its service URL from the device UI. |
| `007-unique-firmware-identity` | **CORE-V1** | Required for private paired-host setup, secure operation, or signed updates. Intent: give local firmware a distinct project and version identity. |
| `008-additional-ca-bundle` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: No Intent header; see patch-map status. |
| `009-axp2101-charging-timeout` | **UPSTREAM** | Retire because the new base already supplies this behavior: M5 65193e8 safe power-chip reads; no old timeout patch is needed. Intent: No Intent header; see patch-map status. |
| `010-battery-status` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: No Intent header; see patch-map status. |
| `011-avatar-auth-headers` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: use the provisioned identity and bearer token on M5's avatar channel. |
| `012-per-pixel-led-tool` | **CORE-V1** | Required for hardware-truth privacy controls and hard mute. Intent: add an atomic MCP operation for all twelve independently addressable RGB pixels. |
| `013-mint-face-skin` | **DEFER** | Useful refinement, but the minimal core purpose does not depend on it; defer. Intent: draw a softer face (mint skin) with surprised and wink faces; the default avatar stays for other apps. |
| `014-wifi-awake-while-speaking` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: keep Wi-Fi out of modem sleep while the robot speaks; MAX_MODEM delayed audio packets by seconds and the voice stuttered. |
| `015-speech-edges` | **DROP** | Diagnostic-only work is outside the first firmware cut. Intent: count and log audio frames lost at the start and end of a spoken line (dropped before speaking, cleared on a state change, playback gaps). |
| `016-speech-open-at-tts-start` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: accept a spoken line's audio from tts start and keep the decode queue on a reset while the line is open, so the speaking-state entry no longer cuts th |
| `017-face-palette-idle-light` | **DEFER** | Useful refinement, but the minimal core purpose does not depend on it; defer. Intent: add MCP tools to recolor the mint face (palettes and a night face, palette saved in NVS), gate idle head movement at runtime, and read the LTR-553 amb |
| `018-hello-token-handoff` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: save a long-lived token from the server hello and reconnect with it. |
| `019-avatar-nvs-config` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: have the avatar channel use the saved websocket token and avatar URL. |
| `020-dance-mcp-tools` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: expose the firmware built-in dances (Happy, Robot, Panic, LookAround) as MCP tools so the host can start and stop a dance. |
| `021-device-events-tool` | **CORE-V1** | Required for local touch or reaction behavior. Intent: queue head touch, head swipe and shake events on the robot and let the host read and clear them with one MCP tool (the host polls; the robot cannot pu |
| `023-wifi-saved-networks-tools` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: list, add, forget and switch saved Wi-Fi networks through MCP tools backed by the robot SsidManager (NVS); passwords are never returned or logged. |
| `030-load-local-assets` | **CORE-V1** | Required for local wake, interruption, or stop behavior. Intent: load the wake word model. Patch 002 skips CheckAssetsVersion(), the only caller of Assets::Apply(), so the srmodels never reach the audio service and  |
| `032-wake-word-with-persistent-socket` | **CORE-V1** | Required for local wake, interruption, or stop behavior. Intent: act on the wake word with the persistent websocket. The channel is always open, so HandleWakeWordDetectedEvent() and WakeWordInvoke() took the "alread |
| `033-connecting-screen-and-boot-ring` | **CORE-V1** | Required for the always-on cue and sound policy. Intent: a plain connecting screen and the ring the firmware owns before the host connects. The face stays hidden under a black cover until the first Standby:  |
| `034-host-idle-command` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: let the host end a silent follow-up. In auto mode the firmware goes straight back to Listening after every reply and only the server could end the utt |
| `036-swipe-gestures-and-quick-settings` | **CORE-V1** | Required for local touch or reaction behavior. Intent: swipe gestures on the face and a quick-settings screen (owner request 2026-10-20). Swipe left lowers the volume by 10, right raises it by 10 (20 to 10 |
| `037-idle-motion-off-by-default` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: stillness is the default (owner request 2026-10-20: "it is constantly moving"). The idle head movement now starts OFF at boot and the host choice (sel |
| `038-head-move-cap` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: a last-resort limit on the host's head moves (owner request 2026-10-20: servo wear from constant movement). self.robot.set_head_angles refuses more th |
| `039-mcp-timing-log` | **DROP** | Diagnostic-only work is outside the first firmware cut. Intent: log-only timing diagnostic for the slow MCP replies (>5 s) seen while audio streams. Logs one warning line, at most one a second per kind, when an MCP |
| `044-strongest-wifi-ap` | **UPSTREAM** | Retire because the new base already supplies this behavior: M5 94856a7 strongest saved-network access-point selection. Intent: join the strongest access point of the saved network (Jesse's unit, 2026-10-20: it joined a -80 dBm channel-1 mesh node although a -37 dBm node on cha |
| `045-control-panel` | **DROP** | Orphan outside the replay recipe; omit from the release. Intent: a control panel that drops from the top of the screen (owner request 2026-10-21). A swipe down that begins in the top 30 px opens a sheet with the vol |
| `046-touch-diagnostics` | **DROP** | Diagnostic-only work is outside the first firmware cut. Intent: diagnostics for the face screen's touch path (2026-10-21; swipes and taps did nothing on the unit). Each finger down (with x and y) and up, and each L |
| `047-tap-handling` | **CORE-V1** | Required for local touch or reaction behavior. Intent: taps on the face (owner report 2026-10-21). (1) A swipe that starts on the top bezel reports a touch at y 0 to 16 and loses the point at the edge, whi |
| `048-head-touch-filter` | **CORE-V1** | Required for local touch or reaction behavior. Intent: stop the head touch strip's phantom pets (owner report 2026-10-21: the unit showed its petted heart and open-mouthed happy face at random with nobody  |
| `049-stop-word` | **CORE-V1** | Required for local wake, interruption, or stop behavior. Intent: a stop word that works while the robot is speaking (owner request 2026-10-21: he said "stop" mid-sentence and it kept talking). A small MultiNet comma |
| `050-ring-dark-with-screen` | **CORE-V1** | Required for the always-on cue and sound policy. Intent: the LED ring goes dark with the screen and before a power off (owner report 2026-10-21: holding the power button turned the screen off but left the ri |
| `051-internal-ram-budget` | **CORE-V1** | Required for local wake, interruption, or stop behavior. Intent: free internal RAM so the stop word can run (host log 2026-10-21: the model costs 10,752 bytes of internal RAM and turned itself off against a 6 KB lim |
| `052-rub-detection` | **DEFER** | Useful refinement, but the minimal core purpose does not depend on it; defer. Intent: make a real rub register without bringing the phantom pets back (owner report 2026-10-21: after 048 "I don't see rubbing registering"). The host log s |
| `053-stable-stacks` | **CORE-V1** | Required for the always-on cue and sound policy. Intent: a stable build after 0.2.24 (owner report 2026-10-21: the unit stopped answering MCP calls for 30 to 45 s and then reset, repeatedly; a spoken volume  |
| `054-avatar-channel-in-agent-mode` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: open the camera and avatar socket in AI-agent mode (owner report 2026-10-21: the unit cannot say what it sees; the host log shows "StackChan camera st |
| `055-opus-stack-in-psram-experiment` | **DROP** | Obsolete, superseded, rejected, or diagnostic work has no v1 requirement. Intent: EXPERIMENT, in the 0.2.28 recipe to settle whether the stalls of 0.2.24 came from this stack or from the stop word. The opus codec task's 24 KB stack  |
| `056-pet-by-peak-reading` | **CORE-V1** | Required for local touch or reaction behavior. Intent: pets that register, from the host log of the petting minutes (2026-10-21). With nobody there the strip reads 1 on 60 to 90 samples a minute, in runs u |
| `057-shake-threshold` | **CORE-V1** | Required for local touch or reaction behavior. Intent: tune the shake (host log 2026-10-21: a lift-and-shake by hand produced no event). The shake detector sums the change in the three axes between samples |
| `058-internal-ram-trims` | **CORE-V1** | Required by the memory gate, flash budget, or stable core. Intent: give back internal RAM without moving any stack to PSRAM (the unit stalled in 0.2.24 and the PSRAM stack was the prime suspect; 055 tests that separat |
| `059-wake-and-tap-visibility` | **DROP** | Diagnostic-only work is outside the first firmware cut. Intent: make the wake word and taps reliable and visible (owner report 2026-10-21: the robot does not listen, taps do not start or stop listening, and the wak |
| `060-avatar-socket-credentials` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: let the hub accept the unit's avatar socket (host log 2026-10-21: the avatar worker of patch 054 connects every 5 s and the hub refuses it: "not autho |
| `061-stop-while-speaking` | **CORE-V1** | Required for local wake, interruption, or stop behavior. Intent: stopping a reply that is already playing (owner report 2026-10-21: tapping or saying "Hi, StackChan" while the robot speaks does not stop it). Three p |
| `062-firmware-version-report` | **DROP** | Diagnostic-only work is outside the first firmware cut. Intent: tell the hub which firmware the unit runs and how strong its Wi-Fi is. The unit reported M5's own 1.5.1 (or nothing) and Home's Software card read "No |
| `063-avatar-device-id-and-barge-in` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: (1) let the hub accept the unit's avatar socket: 0.2.30 still logged "token present, device missing" because Kconfig defaults STACKCHAN_DEVICE_ID and  |
| `064-camera-stream-stats` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: show why the camera sends no frames (host log 2026-10-21: "0 frames and 0 KB from the unit in 1.0 min" on a connected avatar socket). The body's start |
| `065-barge-stats-and-light-channels` | **DROP** | Obsolete, superseded, rejected, or diagnostic work has no v1 requirement. Intent: (1) measure whether barge-in can work (owner test 2026-10-21: "Hi, StackChan" over a reply never woke the unit). While the robot speaks, each echo-can |
| `066-camera-failure-stages` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: tell apart the ways the camera can fail to send (host log 2026-10-21: the avatar socket connects and the host asks for a camera stream, yet no frame a |
| `067-orientation-event-and-screen-rotation` | **DROP** | Obsolete, superseded, rejected, or diagnostic work has no v1 requirement. Intent: the robot knows when it is on its side or upside down (owner request 2026-10-21). (1) hal_imu.cpp now also tracks which way gravity points: a low-pass |
| `068-state-guard-and-listen-restart` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: stop the unit leaving a turn half done (owner report 2026-10-22: "it answered one question and stopped responding"; host log: the state guard of patch |
| `069-stall-watch-and-camera-pause` | **DROP** | Diagnostic-only work is outside the first firmware cut. Intent: find and avoid the freeze (owner report 2026-10-22, host log on 0.2.41: a turn starts, then every tool call times out for a minute with the socket sti |
| `070-playback-report` | **DROP** | Diagnostic-only work is outside the first firmware cut. Intent: show whether the unit stutters and why (owner report 2026-10-22: speech stuttery and slow for a minute or two; the host's own playback numbers are cle |
| `071-orientation-signed-pull` | **DROP** | Diagnostic-only work is outside the first firmware cut. Intent: the orientation tracker of patch 067 stopped reporting after its first change (host log 2026-10-22, pose test: upright to right ear down was reported, |
| `072-faster-tilt` | **DROP** | Diagnostic-only work is outside the first firmware cut. Intent: a tilt shows up faster (owner report 2026-10-22: "tipping over is slow and unreliable"). The orientation tracker of patch 067 filtered the vector at 0 |
| `073-sleeping-face` | **DEFER** | Useful refinement, but the minimal core purpose does not depend on it; defer. Intent: a real sleeping face for the idle sleep (owner request 2026-10-23: "I see the face dimmed, but no sleepy or sleeping"). The host used the avatar socke |
| `074-unit-crash-fixes` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: stop the unit rebooting itself on every stall, boot into the AI agent by default, and let the host keep the unit awake (owner decision 2026-10-23). (1 |
| `075-offline-mode` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: the unit stays usable and reachable when the hub is not (owner decision 2026-10-23: "even with no hub or Wi-Fi the unit must keep responding"). (1) Wi |
| `076-weak-pet` | **DROP** | Diagnostic-only work is outside the first firmware cut. Intent: rubbing the head reacts even when the strip only reads 1 (owner report 2026-10-23: "rubbing did not work at all"). The recogniser needed a sample at r |
| `077-silent-link-closes` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: a hub link that goes silent no longer freezes the unit for minutes. The reconnect task waited forever for a disconnect event, so when a weak access po |
| `078-quick-tap-counts` | **DROP** | Diagnostic-only work is outside the first firmware cut. Intent: a quick firm tap on the head counts as a pet (owner report 2026-11-12: tap did nothing). A tap lasts one to three samples at the strip's 16 Hz; a run  |
| `079-dev-server-override` | **DEFER** | Useful refinement, but the minimal core purpose does not depend on it; defer. Intent: let a development build point the unit at a Bot app on another port without touching the pairing saved in NVS (2026-11-12: the vision work needed the  |
| `079-dev-voice-url` | **DEFER** | Useful refinement, but the minimal core purpose does not depend on it; defer. Intent: the voice websocket half of 079-dev-server-override.patch: when CONFIG_STACKCHAN_DEV_VOICE_URL or CONFIG_STACKCHAN_DEV_TOKEN is not empty (a developme |
| `080-weak-runs-are-maybes` | **CORE-V1** | Required for local touch or reaction behavior. Intent: stop the phantom pets (owner report 2026-11-12, "it keeps smiling"). With nobody touching the unit the strip read 1 on 277 of 979 samples a minute in  |
| `081-imu-tap` | **CORE-V1** | Required for local touch or reaction behavior. Intent: a light tap on the head counts, and the strip's idle noise never makes a touch by itself (owner mission 2026-11-12, "IMU-assisted head tap"). The owne |
| `082-sound-direction` | **DROP** | Orphan outside the replay recipe; omit from the release. Intent: tell which side a sound comes from (owner mission 2026-11-12, "can the StackChan hear direction"). The CoreS3 has two front microphones on the ES7210  |
| `082-sound-tap` | **DROP** | Orphan outside the replay recipe; omit from the release. Intent: hand every chunk the audio input task reads from the codec (24 kHz, two channels, before the 16 kHz resampler) to the StackChan sound-direction tap (p |
| `083-wake-no-echo-reference` | **DEFER** | Useful refinement, but the minimal core purpose does not depend on it; defer. Intent: the wake word stopped hearing the owner after hours of room sound (owner report 2026-11-13, "stackchan is not listening to me"; design note docs/dev/s |
| `084-core-dump-report` | **DROP** | Diagnostic-only work is outside the first firmware cut. Intent: know why the unit panics (host log 2026-11-13: boot reason 4, a panic, four times in 15 hours, with no message or backtrace, because core dumps were o |
| `085-self-restart-guard` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: the unit gets itself out of a freeze, and can never reboot-loop (owner approval 2026-11-13, "implement everything we discussed and planned"; design no |
| `086-wake-selftest-and-rebuild` | **CORE-V1** | Required for local wake, interruption, or stop behavior. Intent: a unit that cannot hear the wake word finds out and repairs itself (owner report 2026-11-13, "stackchan is not listening to me ... It should be self h |
| `090-timers-core` | **CORE-V1** | Required for alarms that ring with the host off. Intent: the pure logic of on-unit timers and alarms (owner decision 2026-11-13: on-device timers, no Bluetooth): up to 8 active, a timer of 1 s to 24 h, an al |
| `091-timers-device` | **CORE-V1** | Required for alarms that ring with the host off. Intent: the device side of on-unit timers and alarms (owner decision 2026-11-13: on-device timers, no Bluetooth, hub down must still work). The schedule is ke |
| `092-timer-tools` | **CORE-V1** | Required for alarms that ring with the host off. Intent: the MCP tools the host uses to drive the on-unit timers (patch 091): self.timer.set(seconds 1..86400, label, silent), self.timer.alarm(hour, minute, l |
| `093-timer-touch-stop` | **CORE-V1** | Required for alarms that ring with the host off. Intent: a ringing timer or alarm (patches 091, 092) ends on a touch: a press on the face (the screen) or a press on the head strip calls maipai_timers_request |
| `094-timer-stop-word` | **CORE-V1** | Required for alarms that ring with the host off. Intent: the stop word ends a ringing timer or alarm (patches 091 to 093). The stop-word callback in the xiaozhi application (patch 049) first asks maipai_time |
| `095-grow-assets-partition` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: No Intent header; see patch-map status. |
| `096-drop-cjk-font-and-emoji` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: No Intent header; see patch-map status. |
| `097-remove-mooncake-apps` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: No Intent header; see patch-map status. |
| `098-bluetooth-off` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: No Intent header; see patch-map status. |
| `099-no-jpeg-decoder` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: No Intent header; see patch-map status. |
| `099-wifi-only-and-fewer-sounds` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: No Intent header; see patch-map status. |
| `100-music-features` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: the unit measures a few numbers about the room's sound so the host can tell clear music from speech and noise (owner request 2026-11-13: the robot hea |
| `101-music-tap` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: hand every chunk the audio input task reads from the codec (24 kHz, two channels, before the 16 kHz resampler) to the music features (patch 100, hal/h |
| `105-face-touch-toggles` | **CORE-V1** | Required for hardware-truth privacy controls and hard mute. Intent: touches on the face of the screen toggle mute, vision off and full quiet (owner design 2026-11-13): HOLD the mouth 0.5 s = mute on or off, TAP an eye  |
| `106-privacy-core` | **CORE-V1** | Required for hardware-truth privacy controls and hard mute. Intent: the unit's mute, vision off and full quiet (owner design 2026-11-13, hard mute note). State is three independent bits saved in a NEW NVS namespace mai |
| `107-mic-guards` | **CORE-V1** | Required for hardware-truth privacy controls and hard mute. Intent: the xiaozhi side of the hard mute (maipai_privacy.h, patch 106): while muted or in full quiet AudioService::ReadAudioData reads nothing (so nothing is |
| `108-mint-muted-and-lidded` | **CORE-V1** | Required for hardware-truth privacy controls and hard mute. Intent: the mint face's two privacy looks (owner: a muted mouth looks different, no-vision eyes look different, never an X because it looks dead). MintMouth:: |
| `110-listening-thinking-faces` | **CORE-V1** | Required for face, setup, clock, or link-state behavior. Intent: two new faces in the mint skin, `listening` (the eyes a little wider and rounder, the mouth a short closed line) and `thinking` (the eyes up and to th |
| `111-shared-link-screen` | **CORE-V1** | Required for face, setup, clock, or link-state behavior. Intent: one link screen for every state where the unit is not yet linked (owner, 2026-11-13). A black cover with a glyph slot (the shipped Wi-Fi icons, drawn  |
| `112-offline-look` | **CORE-V1** | Required for face, setup, clock, or link-state behavior. Intent: the standing offline look (owner, 2026-11-13), driven by the firmware's own link state. While Home is out of reach the normal face stays and reacts lo |
| `113-waiting-for-approval` | **CORE-V1** | Required for face, setup, clock, or link-state behavior. Intent: the "refused" state, so a unit Home has not approved says so instead of looking offline (owner, 2026-11-13). Home accepts the websocket and closes it  |
| `114-power-key-ring-dark` | **CORE-V1** | Required for the always-on cue and sound policy. Intent: the ring is dark and the eyes are shut when the power key switches the unit off (owner, 2026-11-13). The PMIC cuts power with no warning about 4 s aft |
| `115-sounds-core` | **CORE-V1** | Required for the always-on cue and sound policy. Intent: the pure logic of the unit's own sounds (owner approved the sound plan on 2026-11-13, docs/dev/stackchan-lights-audit-and-plan-2026-11-13.md sections  |
| `116-sounds-device` | **CORE-V1** | Required for the always-on cue and sound policy. Intent: the device side of the unit's own sounds (owner approved 2026-11-13). (1) The seven new earcons (Ogg Opus mono 16 kHz 24 kbps, 0.4 to 1.0 s, 0.5 to 3  |
| `117-sound-events` | **CORE-V1** | Required for the always-on cue and sound policy. Intent: the firmware plays the right earcon itself for the events only it sees (owner approved 2026-11-13; plan rows 2, 30 to 33, 35). Charger: the 1 s power  |
| `118-offline-phrases` | **DEFER** | Tier 2 offline phrase support is optional; defer until wake, stop, and paired turns are stable. Intent: tier 2 of the local offline voice (owner approved 2026-11-13; plan section 17): when the wake word or a tap fires and there is no link to Home, the un |
| `119-quiet-reconnect-errors` | **CORE-V1** | Required for face, setup, clock, or link-state behavior. Intent: stop the error chime and the error face on every failed reconnect (owner 2026-11-13: "it keeps playing this melody", heard each time Home restarted fo |
| `120-offline-earcon-after-3-minutes` | **CORE-V1** | Required for the always-on cue and sound policy. Intent: the offline earcon and the "I'm back" chime are for a real outage, not for every Home restart (owner 2026-11-13: "omg this beeping is annoying" while  |
| `121-offline-music-dance` | **DEFER** | Optional local music detection and dance can follow the core behavior set. Intent: with no link to Home, the unit nods and dances to music by itself (owner 2026-11-13: "when its offline, it could still listen to music and dance, righ |
| `122-vision-off-closes-the-eyes` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: tapping an eye closes the eyes fully (owner 2026-11-13: "tapping eyes should close them, not half close"). Vision off used the calm half-lidded eye of |
| `123-music-notes-and-song-title` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: music notes and the song name on the face (owner 2026-11-13, preview approved: "maybe the face should have a musical note on it, of something in diffe |
| `124-offline-music-cycles` | **DEFER** | Long running music dance cycles are an optional refinement after v1. Intent: the unit's own music session runs in cycles for hours, like the host's (owner 2026-11-13: "i could be listening to music for hours and it should dance |
| `125-keyframe-size-zero` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: the eyes are the same size after a dance (owner 2026-11-13, three times: "one eye is bigger than the other", "i still see the one large eye and one sm |
| `126-slow-mood-and-pause` | **DEFER** | Music dance mood transitions are an optional refinement after v1. Intent: the break between dance blocks is a slow mood, not a stop (owner 2026-11-13: "a 90 second break is crazy ... you can have it go into slow mood for 90  |
| `127-pause-faster-resume-mood` | **DEFER** | Music dance pause and resume tuning is optional after v1. Intent: no music for 4.5 s pauses the unit's own dance (was 9 s) and clear music takes it right back to the mood it was in (owner 2026-11-13: "cut that 9 seco |
| `128-beat-sway` | **DEFER** | Beat tracking and sway are optional music dance refinements after v1. Intent: the head sways on the beat of the song (owner 2026-11-13: "any way to have StackChan dance to the beat of the song"; "sometimes it dances slow and the |
| `129-music-clip-capture` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: the unit captures a short clip of the room's audio for song naming (owner 2026-11-13: when the robot hears music it names the song through Home and sh |
| `130-steady-beat-and-quick-start` | **DEFER** | Faster beat detection and timing are optional music dance refinements after v1. Intent: start head bobbing on the beat sooner, stop sooner, and hold the beat (owner 2026-11-13: "i feel like it takes too long to start dancing, ideally it w |
| `131-bob-first` | **DEFER** | A separate bob phase is an optional music dance refinement after v1. Intent: a music session starts with the head nodding up and down on the beat, for a while, before the full dance (owner 2026-11-14: "nodding is up and down an |
| `132-expressive-faces` | **DEFER** | An expanded expression pack is a nice face refinement after the essential face states ship. Intent: seven new faces for the owner-approved expressive set (2026-11-14, preview judged): joy, content, excited, shocked, curious, love, worried. New Emotio |
| `133-wireless-update` | **CORE-V1** | Required for private paired-host setup, secure operation, or signed updates. Intent: wireless firmware update (owner 2026-11-14: the unit is on battery and off USB, "hopefully you can update wirelessly", plus "a special animated icon t |
| `140-song-title-bar` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: the song title on the face is a white, bolder, slightly larger text on a solid black bar, close to the bottom edge (owner 2026-11-14: "text aligned to |
| `141-power-reading-and-sound-gate` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: stop the robot's repeating plug-in/unplug beeps and make every cue attributable (owner 2026-11-14: "it never did that before"). A Fable review found p |
| `142-stock-tones-gated` | **CORE-V1** | Required for the always-on cue and sound policy. Intent: the stock xiaozhi tones that bypassed the unit's sound gate are gone or gated (owner 2026-11-14: a chime is for something a person must notice or that |
| `143-offline-label-after-45-s` | **CORE-V1** | Required for face, setup, clock, or link-state behavior. Intent: the word "Offline" in the upper left shows after 45 s without the hub, not 10 s (owner 2026-11-14: the hub installs and restarts every few minutes and |
| `144-fallback-hub-endpoint` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: a fallback hub endpoint for both channels so the robot works away from home without any public address (owner 2026-11-14: Jesse takes the robot to a f |
| `145-app-version-from-release` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: the app description version is the release version (a fix for patch 133). The image's esp_app_desc version was the fixed "1.5.1-maipai.1" while the up |
| `146-fallback-gateway-and-ssid-gate` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: the away-from-home fallback must work whatever Wi-Fi the friend has and must never hand the pairing token to a stranger's network (owner 2026-11-14: ' |
| `147-tailnet-client` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: the robot's own tailnet client (owner 2026-11-14: "register it to a tailscale network and then just give it any WiFi"). The unit joins the household's |
| `148-tailnet-endpoint` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: the connection order with the tailnet (patch 147): while the tailnet is up, the hub's tailnet address is the first fallback after the home address (en |
| `149-microlink-psram-stacks` | **DROP** | Orphan outside the replay recipe; omit from the release. Intent: the library patch for the pinned MicroLink (applied by recipe.sh to the downloaded copy in the build root, not to the StackChan tree): the net_io, der |
| `151-charged-once-per-session` | **CORE-V1** | Required for the paired voice turn and core robot behavior. Intent: the "charged" cue plays once per charge and never repeats (owner 2026-11-14: a beep came every few minutes while the robot sat on a cable with a full  |
| `152-gateway-fallback-kconfig-flag` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: the laptop/Wi-Fi-gateway fallback (patches 144 and 146) sits behind a Kconfig flag, CONFIG_STACKCHAN_FALLBACK_GATEWAY (default y). The trip-candidate  |
| `153-prefer-tailnet-hook` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: a test hook so the tailnet path can be proven at home (owner 2026-11-14): the device command self.network.prefer_tailnet(minutes) makes the voice and  |
| `154-wifi-use-now` | **HOME-PRESET** | Needed by a feature assigned to the Home preset; compile behind its Kconfig gate. Intent: "Use this network now" for a real away test without carrying the unit out of range of the home Wi-Fi (owner 2026-11-14): self.wifi.use_now(index) leav |

## CORE-V1 order, size, dependencies, and ownership

Size estimates mean strong-model active engineering time, excluding target-unit runtime and review. All CORE-V1 items rebuild when the map says REBUILD; PORT-eligible items can carry with the fewest edits. File lists are from the patch map. `-` means a recipe row has no file list in the map.

| Order | Patch | Size | Depends on | Files touched |
|---:|---|:---:|---|---|
| 1 | `002-nvs-websocket-no-ota` | M | base pairing settings | firmware/main/Kconfig.projbuild,firmware/xiaozhi-esp32/main/Kconfig.projbuild,firmware/xiaozhi-esp32/main/application.cc |
| 2 | `005-disable-m5-registry-mqtt` | M | none declared; base source only | firmware/main/apps/app_ezdata/view/view.h,firmware/main/hal/hal_ezdata.cpp |
| 3 | `008-additional-ca-bundle` | S | none declared; base source only | firmware/main/Kconfig.projbuild |
| 4 | `098-bluetooth-off` | S | none declared; base source only | firmware/main/CMakeLists.txt |
| 5 | `003-stackchan-kconfig` | M | 002 | firmware/main/Kconfig.projbuild |
| 6 | `007-unique-firmware-identity` | M | 003 | firmware/CMakeLists.txt |
| 7 | `001-server-url-empty` | M | 003 | firmware/main/Kconfig.projbuild |
| 8 | `004-configurable-sntp-empty` | S | 003 | firmware/main/Kconfig.projbuild,firmware/main/hal/hal_network.cpp |
| 9 | `003-persistent-websocket` | L | 002, 007 | main/protocols/protocol.cc,main/protocols/protocol.h,main/protocols/websocket_protocol.cc,main/protocols/websocket_protocol.h |
| 10 | `018-hello-token-handoff` | S | 003-persistent-websocket | main/protocols/websocket_protocol.cc |
| 11 | `030-load-local-assets` | M | 003-persistent-websocket | firmware/xiaozhi-esp32/main/application.cc |
| 12 | `032-wake-word-with-persistent-socket` | M | 003-persistent-websocket, 030 | firmware/xiaozhi-esp32/main/application.cc |
| 13 | `014-wifi-awake-while-speaking` | S | audio baseline | firmware/xiaozhi-esp32/main/application.cc |
| 14 | `016-speech-open-at-tts-start` | M | voice transport | firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/audio/audio_service.cc,firmware/xiaozhi-esp32/main/audio/audio_service.h |
| 15 | `061-stop-while-speaking` | M | 003-persistent-websocket | firmware/main/hal/board/stackchan.cc,firmware/main/hal/device_events.h,firmware/main/hal/hal.cpp,firmware/main/hal/hal_head_touch.cpp,firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc |
| 16 | `049-stop-word` | L | 030, 051, 061 | firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/audio/audio_service.cc,firmware/xiaozhi-esp32/main/audio/audio_service.h,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.h,firmware/xiaozhi-esp32/scripts/build_default_assets.py |
| 17 | `034-host-idle-command` | S | 003-persistent-websocket | firmware/xiaozhi-esp32/main/application.cc |
| 18 | `068-state-guard-and-listen-restart` | M | 034 | firmware/xiaozhi-esp32/main/application.cc |
| 19 | `074-unit-crash-fixes` | L | 068 | firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan.cc,firmware/main/hal/hal.h,firmware/main/hal/hal_imu.cpp,firmware/main/hal/hal_mcp.cpp |
| 20 | `077-silent-link-closes` | M | 003-persistent-websocket | firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc |
| 21 | `085-self-restart-guard` | L | 074 | firmware/main/hal/heal_guard.cpp,firmware/main/hal/device_events.h,firmware/xiaozhi-esp32/main/application.cc,firmware/main/hal/hal_imu.cpp,firmware/main/hal/hal_head_touch.cpp |
| 22 | `086-wake-selftest-and-rebuild` | L | 030, 032 | firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.h,firmware/xiaozhi-esp32/main/application.cc,firmware/main/hal/device_events.h |
| 23 | `023-wifi-saved-networks-tools` | M | 003-stackchan-kconfig | firmware/main/hal/hal_mcp.cpp |
| 24 | `033-connecting-screen-and-boot-ring` | M | display base | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h |
| 25 | `036-swipe-gestures-and-quick-settings` | M | 033 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h |
| 26 | `047-tap-handling` | M | 036 | firmware/main/hal/board/stackchan_display.cc,firmware/xiaozhi-esp32/main/application.cc |
| 27 | `021-device-events-tool` | M | 003-stackchan-kconfig | firmware/main/hal/hal_mcp.cpp |
| 28 | `048-head-touch-filter` | M | 021 | firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/stackchan/modifiers/head_pet.h |
| 29 | `056-pet-by-peak-reading` | M | 048 | firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_mcp.cpp |
| 30 | `080-weak-runs-are-maybes` | M | 048 | firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_mcp.cpp |
| 31 | `081-imu-tap` | M | 021 | firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_imu.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/hal/hal_servo.cpp |
| 32 | `057-shake-threshold` | S | 021 | firmware/main/hal/hal_imu.cpp,firmware/main/hal/utils/motion_detector/motion_detector.h |
| 33 | `037-idle-motion-off-by-default` | M | 003-stackchan-kconfig | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h |
| 34 | `038-head-move-cap` | S | 003-stackchan-kconfig | firmware/main/hal/hal_mcp.cpp |
| 35 | `106-privacy-core` | L | 003-stackchan-kconfig | firmware/main/hal/board/cores3_audio_codec.cc,firmware/main/hal/board/cores3_audio_codec.h,firmware/main/hal/board/hal_bridge.cc,firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan_camera.cc,firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/hal/hal_ws_avatar.cpp,firmware/main/hal/maipai_privacy.cpp,firmware/main/hal/maipai_privacy.h,firmware/main/stackchan/motion/servo.cpp |
| 36 | `107-mic-guards` | L | 106 | main/application.cc,main/audio/audio_service.cc |
| 37 | `105-face-touch-toggles` | M | 106, 047 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h,firmware/main/hal/maipai_touch_core.h |
| 38 | `108-mint-muted-and-lidded` | M | 106 | firmware/main/stackchan/avatar/skins/mint/mint.cpp,firmware/main/stackchan/avatar/skins/mint/mint.h |
| 39 | `050-ring-dark-with-screen` | M | 003-stackchan-kconfig | firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan.cc,firmware/main/hal/hal_io_expander.cpp |
| 40 | `114-power-key-ring-dark` | M | 050 | firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan.cc,firmware/main/hal/hal_io_expander.cpp |
| 41 | `141-power-reading-and-sound-gate` | M | 115, 116, 117 | firmware/main/hal/board/stackchan.cc,firmware/main/hal/maipai_sounds.cc,firmware/main/hal/maipai_sounds.h,firmware/main/hal/maipai_sounds_core.h |
| 42 | `090-timers-core` | S | none | firmware/main/hal/maipai_timers_core.h |
| 43 | `091-timers-device` | L | 090 | firmware/main/hal/device_events.h,firmware/main/hal/hal.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/hal/maipai_timers.cc,firmware/main/hal/maipai_timers.h |
| 44 | `092-timer-tools` | S | 091 | firmware/main/hal/hal_mcp.cpp |
| 45 | `093-timer-touch-stop` | M | 091, 092, 047 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/hal_mcp.cpp |
| 46 | `094-timer-stop-word` | M | 091, 092, 049 | main/application.cc |
| 47 | `111-shared-link-screen` | M | 033 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h |
| 48 | `112-offline-look` | M | 111, 003-persistent-websocket | firmware/main/hal/board/hal_bridge.cc,firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan.cc,firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h,firmware/main/stackchan/avatar/skins/mint/mint.cpp,firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc |
| 49 | `113-waiting-for-approval` | M | 111, 003-persistent-websocket | firmware/main/hal/board/stackchan_display.cc,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.h |
| 50 | `110-listening-thinking-faces` | M | face renderer | firmware/main/hal/board/stackchan_display.cc,firmware/main/stackchan/avatar/avatar/elements/emotion.h,firmware/main/stackchan/avatar/skins/mint/mint.cpp |
| 51 | `122-vision-off-closes-the-eyes` | S | 108 | firmware/main/stackchan/avatar/skins/mint/mint.cpp |
| 52 | `115-sounds-core` | S | none | firmware/main/hal/maipai_sounds_core.h |
| 53 | `116-sounds-device` | L | 115 | firmware/main/CMakeLists.txt,firmware/main/hal/hal.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/hal/maipai_sounds.cc,firmware/main/hal/maipai_sounds.h |
| 54 | `117-sound-events` | M | 115, 116 | firmware/main/hal/board/stackchan.cc,firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc |
| 55 | `119-quiet-reconnect-errors` | S | 115, 116 | firmware/xiaozhi-esp32/main/application.cc |
| 56 | `120-offline-earcon-after-3-minutes` | M | 112, 115, 116 | firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc |
| 57 | `151-charged-once-per-session` | M | 115, 116, 141 | firmware/main/hal/maipai_sounds_core.h |
| 58 | `142-stock-tones-gated` | M | 115, 116, 117 | firmware/main/hal/board/stackchan_camera.cc,firmware/main/hal/board/stackchan_camera.cc,firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/display/lvgl_display/lvgl_display.cc |
| 59 | `133-wireless-update` | L | 002, 007; signed manifest and security review | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h,firmware/main/hal/hal.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/hal/maipai_update.cc,firmware/main/hal/maipai_update.h |
| 60 | `145-app-version-from-release` | S | 133 | firmware/CMakeLists.txt |
| 61 | `010-battery-status` | S | base power service | firmware/main/hal/hal_mcp.cpp |
| 62 | `012-per-pixel-led-tool` | S | MCP base | firmware/main/hal/hal_mcp.cpp |
| 63 | `020-dance-mcp-tools` | M | MCP and motion base | firmware/main/hal/hal_mcp.cpp |
| 64 | `095-grow-assets-partition` | S | partition baseline | firmware/partitions.csv |
| 65 | `096-drop-cjk-font-and-emoji` | S | display budget | firmware/main/CMakeLists.txt,firmware/main/hal/board/stackchan_display.cc |
| 66 | `099-wifi-only-and-fewer-sounds` | M | build config | firmware/main/CMakeLists.txt |
| 67 | `099-no-jpeg-decoder` | M | Home camera cut | firmware/main/CMakeLists.txt,firmware/main/hal/hal_ws_avatar.cpp |
| 68 | `097-remove-mooncake-apps` | M | Home feature cut | firmware/main/CMakeLists.txt,firmware/main/hal/hal.cpp,firmware/main/main.cpp |
| 69 | `125-keyframe-size-zero` | S | animation base | firmware/main/stackchan/animation/animation.h |
| 70 | `051-internal-ram-budget` | L | none declared; base source only | firmware/main/hal/hal_head_touch.cpp,firmware/xiaozhi-esp32/main/audio/audio_service.cc,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc |
| 71 | `053-stable-stacks` | L | none declared; base source only | firmware/main/hal/hal_head_touch.cpp,firmware/xiaozhi-esp32/main/audio/audio_service.cc,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc |
| 72 | `058-internal-ram-trims` | L | none declared; base source only | firmware/main/hal/board/stackchan_display.cc,firmware/xiaozhi-esp32/main/audio/audio_service.cc,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc |
| 73 | `075-offline-mode` | M | none declared; base source only | firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan.cc,firmware/main/hal/hal_io_expander.cpp,firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/application.h,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.h |
| 74 | `143-offline-label-after-45-s` | M | none declared; base source only | firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc |

### Parallel lanes

Start only when the listed file sets are disjoint in the new-base worktree. Each lane owns its listed paths; integration order remains the CORE-V1 order above. Groups have at most four lanes. Dependencies list only direct patch prerequisites found in the intent or design; `none` means the new-base source is the only prerequisite.

| Group | Parallel lanes with disjoint files |
|---|---|
| A | Timers logic `090` (`firmware/main/hal/maipai_timers_core.h`); sound logic `115` (`firmware/main/hal/maipai_sounds_core.h`); animation fix `125` (`firmware/main/stackchan/animation/animation.h`); partition sizing `095` (`firmware/partitions.csv`). These four path sets are disjoint and can be developed in parallel. |

Only group A is confirmed disjoint from the patch map file lists. All other CORE-V1 work is serialized until its exact file ownership is checked; the microphone, MCP, display, and sound integration paths are shared.

## Totals and cut effect

- CORE-V1: 74 patches: 19 S, 42 M, 13 L.
- HOME-PRESET: 19; DEFER: 16; UPSTREAM: 2; DROP: 19. Total inventory: 130.
- The old map reports 89 REBUILD verdicts among 126 recipe patches. The cut puts only CORE-V1 rows into first-release scope; HOME-PRESET, DEFER, UPSTREAM, and DROP stay out of the core v1 build. That removes 37 old REBUILD items from the immediate core backlog, reducing the first-release rebuild queue from 89 to 52 mapped REBUILD items. PORT-eligible core items are not counted as rebuilds.

## Minimum shippable firmware

The minimum shippable image is the CORE-V1 subset that compiles into a small paired voice robot: provisioned Wi-Fi and host identity, a working paired voice turn, local wake and stop, hard mute and privacy cues, face and clock, timers that ring without the host, touch and basic reactions, controlled lights and sounds, reset/setup, signed updates, and the memory and security removals needed to pass the gate. Defer optional face packs, richer dances, and every Home preset module until their own memory checks pass. The first real-unit test verifies pairing and reconnect on the owner network, a full wake to spoken reply with barge-in/stop, hard mute at the microphone hardware, touch stop for an alarm with the host disconnected, setup/reset, the camera/mic privacy cues, no public network calls, and a 10-minute memory run meeting `internal_free >= 25 KB`, minimum `>= 15 KB`, and `int_big >= 16 KB` without resets, stalls, or watchdogs.
