# Firmware patch map

Replay target: new base at `28b9f0c8`. Statuses are from sequential application in recipe order. Conflict hunk counts count patch hunk headers when the check fails, so they are an upper bound; inspect the patch and affected files before porting.

## A: avatar, skin, sound

| Patch | Purpose | Status | Hunks | Files | Verdict |
|---|---|---:|---:|---|---|
| `011-avatar-auth-headers` | use the provisioned identity and bearer token on M5's avatar channel. | CONFLICT | 4 | firmware/main/hal/hal_ws_avatar.cpp,firmware/main/hal/utils/secret_logic/secret_logic.cpp | REBUILD |
| `012-per-pixel-led-tool` | add an atomic MCP operation for all twelve independently addressable RGB pixels. | FUZZY | 0 | firmware/main/hal/hal_mcp.cpp | PORT |
| `013-mint-face-skin` | draw a softer face (mint skin) with surprised and wink faces; the default avatar stays for other app | CONFLICT | 9 | firmware/main/hal/board/stackchan_display.cc,firmware/main/stackchan/avatar/avatar.h,firmware/main/stackchan/avatar/avatar/elements/emotion.h,firmware/main/stackchan/avatar/skins/mint/mint.cpp,firmware/main/stackchan/avatar/skins/mint/mint.h | REBUILD |
| `017-face-palette-idle-light` | add MCP tools to recolor the mint face (palettes and a night face, palette saved in NVS), gate idle  | CONFLICT | 28 | firmware/main/hal/board/hal_bridge.cc,firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h,firmware/main/hal/hal_mcp.cpp,firmware/main/stackchan/avatar/skins/mint/mint.cpp,firmware/main/stackchan/avatar/skins/mint/mint.h | REBUILD |
| `018-hello-token-handoff` | save a long-lived token from the server hello and reconnect with it. | CONFLICT | 1 | main/protocols/websocket_protocol.cc | REBUILD |
| `019-avatar-nvs-config` | have the avatar channel use the saved websocket token and avatar URL. | CONFLICT | 3 | firmware/main/hal/utils/secret_logic/secret_logic.cpp | PORT |
| `054-avatar-channel-in-agent-mode` | open the camera and avatar socket in AI-agent mode (owner report 2026-10-21: the unit cannot say wha | CONFLICT | 9 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/hal.h,firmware/main/hal/hal_ws_avatar.cpp | REBUILD |
| `060-avatar-socket-credentials` | let the hub accept the unit's avatar socket (host log 2026-10-21: the avatar worker of patch 054 con | CONFLICT | 3 | firmware/main/hal/hal_ws_avatar.cpp | REBUILD |
| `063-avatar-device-id-and-barge-in` | (1) let the hub accept the unit's avatar socket: 0.2.30 still logged "token present, device missing" | CONFLICT | 4 | firmware/main/hal/hal_ws_avatar.cpp,firmware/xiaozhi-esp32/main/application.cc | REBUILD |
| `095-grow-assets-partition` | Patch has no Intent header. | CLEAN | 0 | firmware/partitions.csv | PORT |
| `100-music-features` | the unit measures a few numbers about the room's sound so the host can tell clear music from speech  | CONFLICT | 5 | firmware/main/hal/maipai_music_core.h,firmware/main/hal/hal_music.cpp,firmware/main/hal/hal.cpp,firmware/main/hal/hal_mcp.cpp | REBUILD |
| `101-music-tap` | hand every chunk the audio input task reads from the codec (24 kHz, two channels, before the 16 kHz  | CONFLICT | 3 | main/audio/audio_service.cc | REBUILD |
| `108-mint-muted-and-lidded` | the mint face's two privacy looks (owner: a muted mouth looks different, no-vision eyes look differe | CONFLICT | 20 | firmware/main/stackchan/avatar/skins/mint/mint.cpp,firmware/main/stackchan/avatar/skins/mint/mint.h | REBUILD |
| `110-listening-thinking-faces` | two new faces in the mint skin, `listening` (the eyes a little wider and rounder, the mouth a short  | CONFLICT | 12 | firmware/main/hal/board/stackchan_display.cc,firmware/main/stackchan/avatar/avatar/elements/emotion.h,firmware/main/stackchan/avatar/skins/mint/mint.cpp | REBUILD |
| `111-shared-link-screen` | one link screen for every state where the unit is not yet linked (owner, 2026-11-13). A black cover  | CONFLICT | 16 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h | REBUILD |
| `112-offline-look` | the standing offline look (owner, 2026-11-13), driven by the firmware's own link state. While Home i | CONFLICT | 46 | firmware/main/hal/board/hal_bridge.cc,firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan.cc,firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h,firmware/main/stackchan/avatar/skins/mint/mint.cpp,firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc | REBUILD |
| `113-waiting-for-approval` | the "refused" state, so a unit Home has not approved says so instead of looking offline (owner, 2026 | CONFLICT | 12 | firmware/main/hal/board/stackchan_display.cc,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.h | REBUILD |
| `115-sounds-core` | the pure logic of the unit's own sounds (owner approved the sound plan on 2026-11-13, docs/dev/stack | CONFLICT | 1 | firmware/main/hal/maipai_sounds_core.h | PORT |
| `116-sounds-device` | the device side of the unit's own sounds (owner approved 2026-11-13). (1) The seven new earcons (Ogg | CONFLICT | 13 | firmware/main/CMakeLists.txt,firmware/main/hal/hal.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/hal/maipai_sounds.cc,firmware/main/hal/maipai_sounds.h | REBUILD |
| `121-offline-music-dance` | with no link to Home, the unit nods and dances to music by itself (owner 2026-11-13: "when its offli | CONFLICT | 6 | firmware/main/hal/hal_mcp.cpp,firmware/main/hal/hal_music.cpp,firmware/main/hal/maipai_music_judge.h | REBUILD |
| `122-vision-off-closes-the-eyes` | tapping an eye closes the eyes fully (owner 2026-11-13: "tapping eyes should close them, not half cl | CONFLICT | 1 | firmware/main/stackchan/avatar/skins/mint/mint.cpp | PORT |
| `123-music-notes-and-song-title` | music notes and the song name on the face (owner 2026-11-13, preview approved: "maybe the face shoul | CONFLICT | 15 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h,firmware/main/hal/hal_mcp.cpp,firmware/main/hal/hal_music.cpp | REBUILD |
| `124-offline-music-cycles` | the unit's own music session runs in cycles for hours, like the host's (owner 2026-11-13: "i could b | MISSING_FILE | 0 | firmware/main/hal/hal_music.cpp,firmware/main/hal/maipai_music_judge.h | REBUILD |
| `125-keyframe-size-zero` | the eyes are the same size after a dance (owner 2026-11-13, three times: "one eye is bigger than the | CLEAN | 0 | firmware/main/stackchan/animation/animation.h | PORT |
| `126-slow-mood-and-pause` | the break between dance blocks is a slow mood, not a stop (owner 2026-11-13: "a 90 second break is c | MISSING_FILE | 0 | firmware/main/hal/hal_music.cpp,firmware/main/hal/maipai_music_judge.h | REBUILD |
| `127-pause-faster-resume-mood` | no music for 4.5 s pauses the unit's own dance (was 9 s) and clear music takes it right back to the  | MISSING_FILE | 0 | firmware/main/hal/hal_music.cpp,firmware/main/hal/maipai_music_judge.h | REBUILD |
| `128-beat-sway` | the head sways on the beat of the song (owner 2026-11-13: "any way to have StackChan dance to the be | CONFLICT | 10 | firmware/main/hal/hal_music.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/hal/maipai_beat.h,firmware/main/stackchan/modifiers/beat_sway.h | REBUILD |
| `129-music-clip-capture` | the unit captures a short clip of the room's audio for song naming (owner 2026-11-13: when the robot | CONFLICT | 10 | firmware/main/hal/hal_music.cpp,firmware/xiaozhi-esp32/main/application.cc | REBUILD |
| `130-steady-beat-and-quick-start` | start head bobbing on the beat sooner, stop sooner, and hold the beat (owner 2026-11-13: "i feel lik | MISSING_FILE | 0 | firmware/main/hal/hal_music.cpp,firmware/main/hal/maipai_music_judge.h | REBUILD |
| `131-bob-first` | a music session starts with the head nodding up and down on the beat, for a while, before the full d | MISSING_FILE | 0 | firmware/main/hal/hal_music.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/stackchan/modifiers/beat_sway.h,firmware/main/hal/maipai_music_judge.h | REBUILD |
| `132-expressive-faces` | seven new faces for the owner-approved expressive set (2026-11-14, preview judged): joy, content, ex | CONFLICT | 18 | firmware/main/hal/board/stackchan_display.cc,firmware/main/stackchan/avatar/avatar/elements/emotion.h,firmware/main/stackchan/avatar/skins/mint/mint.cpp | REBUILD |
| `140-song-title-bar` | the song title on the face is a white, bolder, slightly larger text on a solid black bar, close to t | CONFLICT | 10 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h | REBUILD |
| `142-stock-tones-gated` | the stock xiaozhi tones that bypassed the unit's sound gate are gone or gated (owner 2026-11-14: a c | CONFLICT | 10 | firmware/main/hal/board/stackchan_camera.cc,firmware/main/hal/board/stackchan_camera.cc,firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/display/lvgl_display/lvgl_display.cc | REBUILD |
| `143-offline-label-after-45-s` | the word "Offline" in the upper left shows after 45 s without the hub, not 10 s (owner 2026-11-14: t | CONFLICT | 2 | firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc | REBUILD |
| `045` | Orphan patch outside the recipe. | ORPHAN | 0 | - | SKIP |
| `082-sound-direction` | Orphan patch outside the recipe. | ORPHAN | 0 | - | SKIP |
| `082-sound-tap` | Orphan patch outside the recipe. | ORPHAN | 0 | - | SKIP |

## B: MCP tools and timers

| Patch | Purpose | Status | Hunks | Files | Verdict |
|---|---|---:|---:|---|---|
| `020-dance-mcp-tools` | expose the firmware built-in dances (Happy, Robot, Panic, LookAround) as MCP tools so the host can s | CONFLICT | 5 | firmware/main/hal/hal_mcp.cpp | REBUILD |
| `021-device-events-tool` | queue head touch, head swipe and shake events on the robot and let the host read and clear them with | CONFLICT | 7 | firmware/main/hal/hal_mcp.cpp | REBUILD |
| `023-wifi-saved-networks-tools` | list, add, forget and switch saved Wi-Fi networks through MCP tools backed by the robot SsidManager  | CONFLICT | 5 | firmware/main/hal/hal_mcp.cpp | REBUILD |
| `090-timers-core` | the pure logic of on-unit timers and alarms (owner decision 2026-11-13: on-device timers, no Bluetoo | CONFLICT | 1 | firmware/main/hal/maipai_timers_core.h | PORT |
| `091-timers-device` | the device side of on-unit timers and alarms (owner decision 2026-11-13: on-device timers, no Blueto | CONFLICT | 11 | firmware/main/hal/device_events.h,firmware/main/hal/hal.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/hal/maipai_timers.cc,firmware/main/hal/maipai_timers.h | REBUILD |
| `092-timer-tools` | the MCP tools the host uses to drive the on-unit timers (patch 091): self.timer.set(seconds 1..86400 | CONFLICT | 3 | firmware/main/hal/hal_mcp.cpp | PORT |
| `093-timer-touch-stop` | a ringing timer or alarm (patches 091, 092) ends on a touch: a press on the face (the screen) or a p | CONFLICT | 5 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/hal_mcp.cpp | REBUILD |
| `094-timer-stop-word` | the stop word ends a ringing timer or alarm (patches 091 to 093). The stop-word callback in the xiao | CONFLICT | 3 | main/application.cc | REBUILD |

## C: power, ring, sensors

| Patch | Purpose | Status | Hunks | Files | Verdict |
|---|---|---:|---:|---|---|
| `009-axp2101-charging-timeout` | Patch has no Intent header. | OBSOLETE | 0 | main/boards/common/i2c_device.cc | SKIP |
| `010-battery-status` | Patch has no Intent header. | FUZZY | 0 | firmware/main/hal/hal_mcp.cpp | PORT |
| `033-connecting-screen-and-boot-ring` | a plain connecting screen and the ring the firmware owns before the host connects. The face stays hi | FUZZY | 0 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h | PORT |
| `036-swipe-gestures-and-quick-settings` | swipe gestures on the face and a quick-settings screen (owner request 2026-10-20). Swipe left lowers | CLEAN | 0 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h | PORT |
| `037-idle-motion-off-by-default` | stillness is the default (owner request 2026-10-20: "it is constantly moving"). The idle head moveme | CONFLICT | 6 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h | REBUILD |
| `038-head-move-cap` | a last-resort limit on the host's head moves (owner request 2026-10-20: servo wear from constant mov | FUZZY | 0 | firmware/main/hal/hal_mcp.cpp | PORT |
| `039-mcp-timing-log` | log-only timing diagnostic for the slow MCP replies (>5 s) seen while audio streams. Logs one warnin | CONFLICT | 13 | firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/mcp_server.cc | SKIP |
| `044-strongest-wifi-ap` | join the strongest access point of the saved network (Jesse's unit, 2026-10-20: it joined a -80 dBm  | OBSOLETE | 0 | firmware/main/hal/hal.cpp | SKIP |
| `046-touch-diagnostics` | diagnostics for the face screen's touch path (2026-10-21; swipes and taps did nothing on the unit).  | CONFLICT | 22 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h,firmware/main/hal/device_events.h,firmware/main/hal/hal.cpp,firmware/main/hal/hal_mcp.cpp | SKIP |
| `047-tap-handling` | taps on the face (owner report 2026-10-21). (1) A swipe that starts on the top bezel reports a touch | CONFLICT | 8 | firmware/main/hal/board/stackchan_display.cc,firmware/xiaozhi-esp32/main/application.cc | REBUILD |
| `048-head-touch-filter` | stop the head touch strip's phantom pets (owner report 2026-10-21: the unit showed its petted heart  | CONFLICT | 17 | firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/stackchan/modifiers/head_pet.h | REBUILD |
| `050-ring-dark-with-screen` | the LED ring goes dark with the screen and before a power off (owner report 2026-10-21: holding the  | CONFLICT | 8 | firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan.cc,firmware/main/hal/hal_io_expander.cpp | REBUILD |
| `051-internal-ram-budget` | free internal RAM so the stop word can run (host log 2026-10-21: the model costs 10,752 bytes of int | MISSING_FILE | 0 | firmware/main/hal/hal_head_touch.cpp,firmware/xiaozhi-esp32/main/audio/audio_service.cc,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc | REBUILD |
| `052-rub-detection` | make a real rub register without bringing the phantom pets back (owner report 2026-10-21: after 048  | CONFLICT | 13 | firmware/main/hal/hal_head_touch.cpp | REBUILD |
| `053-stable-stacks` | a stable build after 0.2.24 (owner report 2026-10-21: the unit stopped answering MCP calls for 30 to | MISSING_FILE | 0 | firmware/main/hal/hal_head_touch.cpp,firmware/xiaozhi-esp32/main/audio/audio_service.cc,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc | REBUILD |
| `055-opus-stack-in-psram-experiment` | EXPERIMENT, in the 0.2.28 recipe to settle whether the stalls of 0.2.24 came from this stack or from | CONFLICT | 2 | firmware/xiaozhi-esp32/main/audio/audio_service.cc | REBUILD |
| `056-pet-by-peak-reading` | pets that register, from the host log of the petting minutes (2026-10-21). With nobody there the str | CONFLICT | 19 | firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_mcp.cpp | REBUILD |
| `057-shake-threshold` | tune the shake (host log 2026-10-21: a lift-and-shake by hand produced no event). The shake detector | CLEAN | 0 | firmware/main/hal/hal_imu.cpp,firmware/main/hal/utils/motion_detector/motion_detector.h | PORT |
| `058-internal-ram-trims` | give back internal RAM without moving any stack to PSRAM (the unit stalled in 0.2.24 and the PSRAM s | CONFLICT | 6 | firmware/main/hal/board/stackchan_display.cc,firmware/xiaozhi-esp32/main/audio/audio_service.cc,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc | REBUILD |
| `059-wake-and-tap-visibility` | make the wake word and taps reliable and visible (owner report 2026-10-21: the robot does not listen | MISSING_FILE | 0 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/device_events.h,firmware/main/hal/hal_head_touch.cpp,firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/application.h,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc | SKIP |
| `064-camera-stream-stats` | show why the camera sends no frames (host log 2026-10-21: "0 frames and 0 KB from the unit in 1.0 mi | CONFLICT | 11 | firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_ws_avatar.cpp | SKIP |
| `066-camera-failure-stages` | tell apart the ways the camera can fail to send (host log 2026-10-21: the avatar socket connects and | CONFLICT | 11 | firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_ws_avatar.cpp | SKIP |
| `067-orientation-event-and-screen-rotation` | the robot knows when it is on its side or upside down (owner request 2026-10-21). (1) hal_imu.cpp no | CONFLICT | 16 | firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan.cc,firmware/main/hal/hal_imu.cpp,firmware/main/hal/hal_mcp.cpp | REBUILD |
| `069-stall-watch-and-camera-pause` | find and avoid the freeze (owner report 2026-10-22, host log on 0.2.41: a turn starts, then every to | CONFLICT | 20 | firmware/main/hal/board/stackchan.cc,firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_imu.cpp,firmware/main/hal/hal_ws_avatar.cpp,firmware/xiaozhi-esp32/main/application.cc | REBUILD |
| `070-playback-report` | show whether the unit stutters and why (owner report 2026-10-22: speech stuttery and slow for a minu | CONFLICT | 2 | firmware/xiaozhi-esp32/main/application.cc | SKIP |
| `071-orientation-signed-pull` | the orientation tracker of patch 067 stopped reporting after its first change (host log 2026-10-22,  | CONFLICT | 2 | firmware/main/hal/hal_imu.cpp | PORT |
| `072-faster-tilt` | a tilt shows up faster (owner report 2026-10-22: "tipping over is slow and unreliable"). The orienta | CONFLICT | 2 | firmware/main/hal/hal_imu.cpp | PORT |
| `073-sleeping-face` | a real sleeping face for the idle sleep (owner request 2026-10-23: "I see the face dimmed, but no sl | FUZZY | 0 | firmware/main/hal/board/stackchan_display.cc | PORT |
| `074-unit-crash-fixes` | stop the unit rebooting itself on every stall, boot into the AI agent by default, and let the host k | CONFLICT | 7 | firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan.cc,firmware/main/hal/hal.h,firmware/main/hal/hal_imu.cpp,firmware/main/hal/hal_mcp.cpp | REBUILD |
| `076-weak-pet` | rubbing the head reacts even when the strip only reads 1 (owner report 2026-10-23: "rubbing did not  | CONFLICT | 2 | firmware/main/hal/hal_head_touch.cpp | PORT |
| `078-quick-tap-counts` | a quick firm tap on the head counts as a pet (owner report 2026-11-12: tap did nothing). A tap lasts | CONFLICT | 2 | firmware/main/hal/hal_head_touch.cpp | PORT |
| `080-weak-runs-are-maybes` | stop the phantom pets (owner report 2026-11-12, "it keeps smiling"). With nobody touching the unit t | CONFLICT | 8 | firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_mcp.cpp | REBUILD |
| `081-imu-tap` | a light tap on the head counts, and the strip's idle noise never makes a touch by itself (owner miss | CONFLICT | 63 | firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_imu.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/hal/hal_servo.cpp | REBUILD |
| `084-core-dump-report` | know why the unit panics (host log 2026-11-13: boot reason 4, a panic, four times in 15 hours, with  | CONFLICT | 6 | firmware/main/hal/hal_head_touch.cpp,firmware/main/CMakeLists.txt | REBUILD |
| `085-self-restart-guard` | the unit gets itself out of a freeze, and can never reboot-loop (owner approval 2026-11-13, "impleme | CONFLICT | 14 | firmware/main/hal/heal_guard.cpp,firmware/main/hal/device_events.h,firmware/xiaozhi-esp32/main/application.cc,firmware/main/hal/hal_imu.cpp,firmware/main/hal/hal_head_touch.cpp | REBUILD |
| `114-power-key-ring-dark` | the ring is dark and the eyes are shut when the power key switches the unit off (owner, 2026-11-13). | CONFLICT | 16 | firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan.cc,firmware/main/hal/hal_io_expander.cpp | REBUILD |
| `141-power-reading-and-sound-gate` | stop the robot's repeating plug-in/unplug beeps and make every cue attributable (owner 2026-11-14: " | MISSING_FILE | 0 | firmware/main/hal/board/stackchan.cc,firmware/main/hal/maipai_sounds.cc,firmware/main/hal/maipai_sounds.h,firmware/main/hal/maipai_sounds_core.h | REBUILD |

## D: audio and wake

| Patch | Purpose | Status | Hunks | Files | Verdict |
|---|---|---:|---:|---|---|
| `014-wifi-awake-while-speaking` | keep Wi-Fi out of modem sleep while the robot speaks; MAX_MODEM delayed audio packets by seconds and | CONFLICT | 2 | firmware/xiaozhi-esp32/main/application.cc | REBUILD |
| `015-speech-edges` | count and log audio frames lost at the start and end of a spoken line (dropped before speaking, clea | CONFLICT | 20 | firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/application.h,firmware/xiaozhi-esp32/main/audio/audio_service.cc,firmware/xiaozhi-esp32/main/audio/audio_service.h | REBUILD |
| `016-speech-open-at-tts-start` | accept a spoken line's audio from tts start and keep the decode queue on a reset while the line is o | CONFLICT | 16 | firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/audio/audio_service.cc,firmware/xiaozhi-esp32/main/audio/audio_service.h | REBUILD |
| `032-wake-word-with-persistent-socket` | act on the wake word with the persistent websocket. The channel is always open, so HandleWakeWordDet | CONFLICT | 4 | firmware/xiaozhi-esp32/main/application.cc | REBUILD |
| `049-stop-word` | a stop word that works while the robot is speaking (owner request 2026-10-21: he said "stop" mid-sen | MISSING_FILE | 0 | firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/audio/audio_service.cc,firmware/xiaozhi-esp32/main/audio/audio_service.h,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.h,firmware/xiaozhi-esp32/scripts/build_default_assets.py | REBUILD |
| `061-stop-while-speaking` | stopping a reply that is already playing (owner report 2026-10-21: tapping or saying "Hi, StackChan" | MISSING_FILE | 0 | firmware/main/hal/board/stackchan.cc,firmware/main/hal/device_events.h,firmware/main/hal/hal.cpp,firmware/main/hal/hal_head_touch.cpp,firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc | REBUILD |
| `065-barge-stats-and-light-channels` | (1) measure whether barge-in can work (owner test 2026-10-21: "Hi, StackChan" over a reply never wok | MISSING_FILE | 0 | firmware/main/hal/device_events.h,firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_mcp.cpp,firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc | REBUILD |
| `083-wake-no-echo-reference` | the wake word stopped hearing the owner after hours of room sound (owner report 2026-11-13, "stackch | MISSING_FILE | 0 | firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc | REBUILD |
| `086-wake-selftest-and-rebuild` | a unit that cannot hear the wake word finds out and repairs itself (owner report 2026-11-13, "stackc | MISSING_FILE | 0 | firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc,firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.h,firmware/xiaozhi-esp32/main/application.cc,firmware/main/hal/device_events.h | REBUILD |
| `107-mic-guards` | the xiaozhi side of the hard mute (maipai_privacy.h, patch 106): while muted or in full quiet AudioS | CONFLICT | 14 | main/application.cc,main/audio/audio_service.cc | REBUILD |

## E: application, persistent socket, offline logic

| Patch | Purpose | Status | Hunks | Files | Verdict |
|---|---|---:|---:|---|---|
| `001-server-url-empty` | leave the M5 avatar server unset unless a local installer configures it. | CLEAN | 0 | firmware/main/Kconfig.projbuild | PORT |
| `002-nvs-websocket-no-ota` | skip xiaozhi OTA and activation, use the already provisioned NVS websocket settings. | CONFLICT | 14 | firmware/main/Kconfig.projbuild,firmware/xiaozhi-esp32/main/Kconfig.projbuild,firmware/xiaozhi-esp32/main/application.cc | REBUILD |
| `003-stackchan-kconfig` | Patch has no Intent header. | CLEAN | 0 | firmware/main/Kconfig.projbuild | PORT |
| `003-persistent-websocket` | Patch has no Intent header. | CONFLICT | 23 | main/protocols/protocol.cc,main/protocols/protocol.h,main/protocols/websocket_protocol.cc,main/protocols/websocket_protocol.h | REBUILD |
| `004-configurable-sntp-empty` | make SNTP host configurable and disabled by default to prevent public time calls. | FUZZY | 0 | firmware/main/Kconfig.projbuild,firmware/main/hal/hal_network.cpp | PORT |
| `005-disable-m5-registry-mqtt` | stop starting M5 EzData registry and MQTT, and remove its service URL from the device UI. | FUZZY | 0 | firmware/main/apps/app_ezdata/view/view.h,firmware/main/hal/hal_ezdata.cpp | PORT |
| `007-unique-firmware-identity` | give local firmware a distinct project and version identity. | CONFLICT | 4 | firmware/CMakeLists.txt | REBUILD |
| `030-load-local-assets` | load the wake word model. Patch 002 skips CheckAssetsVersion(), the only caller of Assets::Apply(),  | CLEAN | 0 | firmware/xiaozhi-esp32/main/application.cc | PORT |
| `034-host-idle-command` | let the host end a silent follow-up. In auto mode the firmware goes straight back to Listening after | CLEAN | 0 | firmware/xiaozhi-esp32/main/application.cc | PORT |
| `062-firmware-version-report` | tell the hub which firmware the unit runs and how strong its Wi-Fi is. The unit reported M5's own 1. | CONFLICT | 3 | firmware/main/hal/hal_head_touch.cpp | PORT |
| `068-state-guard-and-listen-restart` | stop the unit leaving a turn half done (owner report 2026-10-22: "it answered one question and stopp | CONFLICT | 6 | firmware/xiaozhi-esp32/main/application.cc | REBUILD |
| `075-offline-mode` | the unit stays usable and reachable when the hub is not (owner decision 2026-10-23: "even with no hu | CONFLICT | 19 | firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan.cc,firmware/main/hal/hal_io_expander.cpp,firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/application.h,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.h | REBUILD |
| `077-silent-link-closes` | a hub link that goes silent no longer freezes the unit for minutes. The reconnect task waited foreve | CONFLICT | 1 | firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc | REBUILD |
| `079-dev-server-override` | let a development build point the unit at a Bot app on another port without touching the pairing sav | CONFLICT | 6 | firmware/main/Kconfig.projbuild,firmware/main/hal/utils/secret_logic/secret_logic.cpp | REBUILD |
| `079-dev-voice-url` | the voice websocket half of 079-dev-server-override.patch: when CONFIG_STACKCHAN_DEV_VOICE_URL or CO | CONFLICT | 2 | main/protocols/websocket_protocol.cc | REBUILD |
| `096-drop-cjk-font-and-emoji` | Patch has no Intent header. | CONFLICT | 10 | firmware/main/CMakeLists.txt,firmware/main/hal/board/stackchan_display.cc | REBUILD |
| `099-wifi-only-and-fewer-sounds` | Patch has no Intent header. | FUZZY | 0 | firmware/main/CMakeLists.txt | PORT |
| `099-no-jpeg-decoder` | Patch has no Intent header. | CONFLICT | 7 | firmware/main/CMakeLists.txt,firmware/main/hal/hal_ws_avatar.cpp | REBUILD |
| `117-sound-events` | the firmware plays the right earcon itself for the events only it sees (owner approved 2026-11-13; p | CONFLICT | 10 | firmware/main/hal/board/stackchan.cc,firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc | REBUILD |
| `118-offline-phrases` | tier 2 of the local offline voice (owner approved 2026-11-13; plan section 17): when the wake word o | CONFLICT | 2 | firmware/xiaozhi-esp32/main/application.cc,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc | REBUILD |
| `119-quiet-reconnect-errors` | stop the error chime and the error face on every failed reconnect (owner 2026-11-13: "it keeps playi | CONFLICT | 1 | firmware/xiaozhi-esp32/main/application.cc | REBUILD |
| `120-offline-earcon-after-3-minutes` | the offline earcon and the "I'm back" chime are for a real outage, not for every Home restart (owner | CONFLICT | 3 | firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc | REBUILD |
| `144-fallback-hub-endpoint` | a fallback hub endpoint for both channels so the robot works away from home without any public addre | CONFLICT | 20 | firmware/main/Kconfig.projbuild,firmware/main/Kconfig.projbuild,firmware/main/hal/hal_ws_avatar.cpp,firmware/main/hal/maipai_fallback.cc,firmware/main/hal/maipai_fallback.h,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc | REBUILD |
| `146-fallback-gateway-and-ssid-gate` | the away-from-home fallback must work whatever Wi-Fi the friend has and must never hand the pairing  | MISSING_FILE | 0 | firmware/main/Kconfig.projbuild,firmware/main/hal/maipai_fallback.h,firmware/main/hal/maipai_fallback.cc,firmware/main/hal/hal_ws_avatar.cpp,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc,firmware/main/hal/maipai_fallback_core.h | REBUILD |
| `151-charged-once-per-session` | the "charged" cue plays once per charge and never repeats (owner 2026-11-14: a beep came every few m | CONFLICT | 4 | firmware/main/hal/maipai_sounds_core.h | REBUILD |

## F: update path, security, portal, clock

| Patch | Purpose | Status | Hunks | Files | Verdict |
|---|---|---:|---:|---|---|
| `008-additional-ca-bundle` | Patch has no Intent header. | CLEAN | 0 | firmware/main/Kconfig.projbuild | PORT |
| `097-remove-mooncake-apps` | Patch has no Intent header. | CONFLICT | 7 | firmware/main/CMakeLists.txt,firmware/main/hal/hal.cpp,firmware/main/main.cpp | REBUILD |
| `098-bluetooth-off` | Patch has no Intent header. | CONFLICT | 2 | firmware/main/CMakeLists.txt | PORT |
| `105-face-touch-toggles` | touches on the face of the screen toggle mute, vision off and full quiet (owner design 2026-11-13):  | CONFLICT | 20 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h,firmware/main/hal/maipai_touch_core.h | REBUILD |
| `106-privacy-core` | the unit's mute, vision off and full quiet (owner design 2026-11-13, hard mute note). State is three | MISSING_FILE | 0 | firmware/main/hal/board/cores3_audio_codec.cc,firmware/main/hal/board/cores3_audio_codec.h,firmware/main/hal/board/hal_bridge.cc,firmware/main/hal/board/hal_bridge.h,firmware/main/hal/board/stackchan_camera.cc,firmware/main/hal/hal_head_touch.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/hal/hal_ws_avatar.cpp,firmware/main/hal/maipai_privacy.cpp,firmware/main/hal/maipai_privacy.h,firmware/main/stackchan/motion/servo.cpp | REBUILD |
| `133-wireless-update` | wireless firmware update (owner 2026-11-14: the unit is on battery and off USB, "hopefully you can u | CONFLICT | 19 | firmware/main/hal/board/stackchan_display.cc,firmware/main/hal/board/stackchan_display.h,firmware/main/hal/hal.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/hal/maipai_update.cc,firmware/main/hal/maipai_update.h | REBUILD |
| `145-app-version-from-release` | the app description version is the release version (a fix for patch 133). The image's esp_app_desc v | CONFLICT | 1 | firmware/CMakeLists.txt | PORT |
| `147-tailnet-client` | the robot's own tailnet client (owner 2026-11-14: "register it to a tailscale network and then just  | CONFLICT | 16 | firmware/CMakeLists.txt,firmware/main/CMakeLists.txt,firmware/main/Kconfig.projbuild,firmware/main/hal/hal.cpp,firmware/main/hal/hal_mcp.cpp,firmware/main/hal/maipai_tailnet.cc,firmware/main/hal/maipai_tailnet.h,firmware/main/hal/maipai_tailnet_core.h | REBUILD |
| `148-tailnet-endpoint` | the connection order with the tailnet (patch 147): while the tailnet is up, the hub's tailnet addres | MISSING_FILE | 0 | firmware/main/hal/maipai_fallback.cc | REBUILD |
| `152-gateway-fallback-kconfig-flag` | the laptop/Wi-Fi-gateway fallback (patches 144 and 146) sits behind a Kconfig flag, CONFIG_STACKCHAN | MISSING_FILE | 0 | firmware/main/Kconfig.projbuild,firmware/main/hal/maipai_fallback.cc | REBUILD |
| `153-prefer-tailnet-hook` | a test hook so the tailnet path can be proven at home (owner 2026-11-14): the device command self.ne | MISSING_FILE | 0 | firmware/main/hal/hal_ws_avatar.cpp,firmware/main/hal/maipai_fallback.cc,firmware/main/hal/maipai_tailnet.cc,firmware/main/hal/maipai_tailnet.h,firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc | REBUILD |
| `154-wifi-use-now` | "Use this network now" for a real away test without carrying the unit out of range of the home Wi-Fi | CONFLICT | 11 | firmware/main/hal/hal_mcp.cpp,firmware/main/hal/maipai_wifi_use.cc,firmware/main/hal/maipai_wifi_use.h | REBUILD |

## Totals by layer and verdict

| Layer | PORT | REBUILD | SKIP |
|---|---:|---:|---:|
| A | 6 | 28 | 3 |
| B | 2 | 6 | 0 |
| C | 10 | 19 | 8 |
| D | 0 | 10 | 0 |
| E | 8 | 17 | 0 |
| F | 3 | 9 | 0 |

## Squash chains

- Head touch: 047, 048, 052, 056, 076, 078, 080, 081.
- Avatar credentials: 011, 018, 019, 060, 063.
- Offline behaviour: 075, 112, 118, 119, 120, 121, 124, 143.
- Music: 100, 101, 121, 123, 124, 126-132, 140.

## Lane ownership

Each lane owns the listed patches and edits the union of their listed files. Recipe patches with common files across lanes are called out below. Files are base-relative as printed by the replay.

### A lane

Patches: 011, 012, 013, 017, 018, 019, 054, 060, 063, 095, 100, 101, 108, 110, 111, 112, 113, 115, 116, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 140, 142, 143, 045, 082, 082

Files: firmware/main/CMakeLists.txt, firmware/main/hal/board/hal_bridge.cc, firmware/main/hal/board/hal_bridge.h, firmware/main/hal/board/stackchan.cc, firmware/main/hal/board/stackchan_camera.cc, firmware/main/hal/board/stackchan_display.cc, firmware/main/hal/board/stackchan_display.h, firmware/main/hal/hal.cpp, firmware/main/hal/hal.h, firmware/main/hal/hal_mcp.cpp, firmware/main/hal/hal_music.cpp, firmware/main/hal/hal_ws_avatar.cpp, firmware/main/hal/maipai_beat.h, firmware/main/hal/maipai_music_core.h, firmware/main/hal/maipai_music_judge.h, firmware/main/hal/maipai_sounds.cc, firmware/main/hal/maipai_sounds.h, firmware/main/hal/maipai_sounds_core.h, firmware/main/hal/utils/secret_logic/secret_logic.cpp, firmware/main/stackchan/animation/animation.h, firmware/main/stackchan/avatar/avatar.h, firmware/main/stackchan/avatar/avatar/elements/emotion.h, firmware/main/stackchan/avatar/skins/mint/mint.cpp, firmware/main/stackchan/avatar/skins/mint/mint.h, firmware/main/stackchan/modifiers/beat_sway.h, firmware/partitions.csv, firmware/xiaozhi-esp32/main/application.cc, firmware/xiaozhi-esp32/main/display/lvgl_display/lvgl_display.cc, firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc, firmware/xiaozhi-esp32/main/protocols/websocket_protocol.h, main/audio/audio_service.cc, main/protocols/websocket_protocol.cc

### B lane

Patches: 020, 021, 023, 090, 091, 092, 093, 094

Files: firmware/main/hal/board/stackchan_display.cc, firmware/main/hal/device_events.h, firmware/main/hal/hal.cpp, firmware/main/hal/hal_mcp.cpp, firmware/main/hal/maipai_timers.cc, firmware/main/hal/maipai_timers.h, firmware/main/hal/maipai_timers_core.h, main/application.cc

### C lane

Patches: 009, 010, 033, 036, 037, 038, 039, 044, 046, 047, 048, 050, 051, 052, 053, 055, 056, 057, 058, 059, 064, 066, 067, 069, 070, 071, 072, 073, 074, 076, 078, 080, 081, 084, 085, 114, 141

Files: firmware/main/CMakeLists.txt, firmware/main/hal/board/hal_bridge.h, firmware/main/hal/board/stackchan.cc, firmware/main/hal/board/stackchan_display.cc, firmware/main/hal/board/stackchan_display.h, firmware/main/hal/device_events.h, firmware/main/hal/hal.cpp, firmware/main/hal/hal.h, firmware/main/hal/hal_head_touch.cpp, firmware/main/hal/hal_imu.cpp, firmware/main/hal/hal_io_expander.cpp, firmware/main/hal/hal_mcp.cpp, firmware/main/hal/hal_servo.cpp, firmware/main/hal/hal_ws_avatar.cpp, firmware/main/hal/heal_guard.cpp, firmware/main/hal/maipai_sounds.cc, firmware/main/hal/maipai_sounds.h, firmware/main/hal/maipai_sounds_core.h, firmware/main/hal/utils/motion_detector/motion_detector.h, firmware/main/stackchan/modifiers/head_pet.h, firmware/xiaozhi-esp32/main/application.cc, firmware/xiaozhi-esp32/main/application.h, firmware/xiaozhi-esp32/main/audio/audio_service.cc, firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc, firmware/xiaozhi-esp32/main/mcp_server.cc, firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc, main/boards/common/i2c_device.cc

### D lane

Patches: 014, 015, 016, 032, 049, 061, 065, 083, 086, 107

Files: firmware/main/hal/board/stackchan.cc, firmware/main/hal/device_events.h, firmware/main/hal/hal.cpp, firmware/main/hal/hal_head_touch.cpp, firmware/main/hal/hal_mcp.cpp, firmware/xiaozhi-esp32/main/application.cc, firmware/xiaozhi-esp32/main/application.h, firmware/xiaozhi-esp32/main/audio/audio_service.cc, firmware/xiaozhi-esp32/main/audio/audio_service.h, firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc, firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.h, firmware/xiaozhi-esp32/scripts/build_default_assets.py, main/application.cc, main/audio/audio_service.cc

### E lane

Patches: 001, 002, 003, 003, 004, 005, 007, 030, 034, 062, 068, 075, 077, 079, 079, 096, 099, 099, 117, 118, 119, 120, 144, 146, 151

Files: firmware/CMakeLists.txt, firmware/main/CMakeLists.txt, firmware/main/Kconfig.projbuild, firmware/main/apps/app_ezdata/view/view.h, firmware/main/hal/board/hal_bridge.h, firmware/main/hal/board/stackchan.cc, firmware/main/hal/board/stackchan_display.cc, firmware/main/hal/hal_ezdata.cpp, firmware/main/hal/hal_head_touch.cpp, firmware/main/hal/hal_io_expander.cpp, firmware/main/hal/hal_network.cpp, firmware/main/hal/hal_ws_avatar.cpp, firmware/main/hal/maipai_fallback.cc, firmware/main/hal/maipai_fallback.h, firmware/main/hal/maipai_fallback_core.h, firmware/main/hal/maipai_sounds_core.h, firmware/main/hal/utils/secret_logic/secret_logic.cpp, firmware/xiaozhi-esp32/main/Kconfig.projbuild, firmware/xiaozhi-esp32/main/application.cc, firmware/xiaozhi-esp32/main/application.h, firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc, firmware/xiaozhi-esp32/main/protocols/websocket_protocol.h, main/protocols/protocol.cc, main/protocols/protocol.h, main/protocols/websocket_protocol.cc, main/protocols/websocket_protocol.h

### F lane

Patches: 008, 097, 098, 105, 106, 133, 145, 147, 148, 152, 153, 154

Files: firmware/CMakeLists.txt, firmware/main/CMakeLists.txt, firmware/main/Kconfig.projbuild, firmware/main/hal/board/cores3_audio_codec.cc, firmware/main/hal/board/cores3_audio_codec.h, firmware/main/hal/board/hal_bridge.cc, firmware/main/hal/board/hal_bridge.h, firmware/main/hal/board/stackchan_camera.cc, firmware/main/hal/board/stackchan_display.cc, firmware/main/hal/board/stackchan_display.h, firmware/main/hal/hal.cpp, firmware/main/hal/hal_head_touch.cpp, firmware/main/hal/hal_mcp.cpp, firmware/main/hal/hal_ws_avatar.cpp, firmware/main/hal/maipai_fallback.cc, firmware/main/hal/maipai_privacy.cpp, firmware/main/hal/maipai_privacy.h, firmware/main/hal/maipai_tailnet.cc, firmware/main/hal/maipai_tailnet.h, firmware/main/hal/maipai_tailnet_core.h, firmware/main/hal/maipai_touch_core.h, firmware/main/hal/maipai_update.cc, firmware/main/hal/maipai_update.h, firmware/main/hal/maipai_wifi_use.cc, firmware/main/hal/maipai_wifi_use.h, firmware/main/main.cpp, firmware/main/stackchan/motion/servo.cpp, firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc

### Cross-layer shared files

- `firmware/CMakeLists.txt`: layers E, F
- `firmware/main/CMakeLists.txt`: layers A, C, E, F
- `firmware/main/Kconfig.projbuild`: layers E, F
- `firmware/main/hal/board/hal_bridge.cc`: layers A, F
- `firmware/main/hal/board/hal_bridge.h`: layers A, C, E, F
- `firmware/main/hal/board/stackchan.cc`: layers A, C, D, E
- `firmware/main/hal/board/stackchan_camera.cc`: layers A, F
- `firmware/main/hal/board/stackchan_display.cc`: layers A, B, C, E, F
- `firmware/main/hal/board/stackchan_display.h`: layers A, C, F
- `firmware/main/hal/device_events.h`: layers B, C, D
- `firmware/main/hal/hal.cpp`: layers A, B, C, D, F
- `firmware/main/hal/hal.h`: layers A, C
- `firmware/main/hal/hal_head_touch.cpp`: layers C, D, E, F
- `firmware/main/hal/hal_io_expander.cpp`: layers C, E
- `firmware/main/hal/hal_mcp.cpp`: layers A, B, C, D, F
- `firmware/main/hal/hal_ws_avatar.cpp`: layers A, C, E, F
- `firmware/main/hal/maipai_fallback.cc`: layers E, F
- `firmware/main/hal/maipai_sounds.cc`: layers A, C
- `firmware/main/hal/maipai_sounds.h`: layers A, C
- `firmware/main/hal/maipai_sounds_core.h`: layers A, C, E
- `firmware/main/hal/utils/secret_logic/secret_logic.cpp`: layers A, E
- `firmware/xiaozhi-esp32/main/application.cc`: layers A, C, D, E
- `firmware/xiaozhi-esp32/main/application.h`: layers C, D, E
- `firmware/xiaozhi-esp32/main/audio/audio_service.cc`: layers C, D
- `firmware/xiaozhi-esp32/main/audio/wake_words/afe_wake_word.cc`: layers C, D
- `firmware/xiaozhi-esp32/main/protocols/websocket_protocol.cc`: layers A, C, E, F
- `firmware/xiaozhi-esp32/main/protocols/websocket_protocol.h`: layers A, E
- `main/application.cc`: layers B, D
- `main/audio/audio_service.cc`: layers A, D
- `main/protocols/websocket_protocol.cc`: layers A, E

## Scope note (2026-11-15)

Patches for features tagged [Home] in `features.md` (camera capture and streaming, music detector, monitor and remote body halves) are ported or rebuilt as usual but each is gated by its own Kconfig switch, default off in the `core` preset, on in the `home` preset. The merge step adds the gating after layers A to C land.
