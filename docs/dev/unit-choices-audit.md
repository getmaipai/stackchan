# Unit choices audit (decision 20 of 2026-11-18)

Bottom line: the unit and its host page offer about 75 settings and screen choices. About 30 can disappear or become automatic with host code or small firmware patches, about 25 can move behind one collapsed Advanced section, and about 20 stay visible. Everything about privacy and safety (mute, vision off, full quiet, the lock code, the listening cues, the camera cue) stays visible and simple. The biggest clutter is not on the unit screen. It is four overlapping ways to put words on the screen, three ways to say "quiet", seven color effects, five face styles that differ a little, and a stock Setup app that still carries vendor pages. Most fixes are host only or touch one small firmware family.

How to read this: "unit" paths are in the replayed firmware tree (`main/...`), host and doc paths are in this repo. Patch families named in the last column are the prefixes in `firmware/patches/` (UI screens, UX first run, NX unit rules, SF safety and fixes). "Host only" needs no firmware change. Defaults come from the code named in the "where" column; where I did not read a default, the cell says "not checked".

Verdicts: keep (stays visible), automatic (the unit or host decides, the choice disappears), remove (the choice is dropped and one default is fixed), Advanced (moves behind one collapsed section on the host settings page; the unit screen shows none of these).

## Privacy and safety (all stay)

| Setting or choice | Where | Default | Verdict | Reason | Cost |
|---|---|---|---|---|---|
| Mute (no listening, microphone chip off) | tool `self.privacy.set` in `main/hal/hal_mcp.cpp`, `main/hal/maipai_privacy.cpp`; quick sheet tile "mute" (`main/hal/maipai_pages_core.h`); host settings key `mute` | off | keep | A privacy control must be one tap away and plainly visible. | none |
| Vision off (camera not read) | `self.privacy.set` (`vision_off`); host settings key `vision_off`; not a quick sheet tile in the replay | off | keep | A privacy control. Add it as a sheet tile in place of a rarely used one (see owner questions). | UI family, small |
| Full quiet (no movement, no sound, no listening) | `self.privacy.set` (`quiet`); sheet tile "quiet" | off | keep | A privacy and comfort control with one clear meaning. | none |
| Unmute from the unit itself | sheet "mute" tile and the face tap; I did not trace the exact path (not checked) | n/a | keep | A muted robot must be unmutable by a person standing at it. | none |
| Lock code: set, change, clear (4 to 6 digits) | keypad on the unit `main/hal/maipai_lock*.cc`; host `host/maipai_body/settings_ui_lock.py`, `unit_lock.py` | no code | keep | A safety control. Already simple. | none |
| Lock now | Settings > General, sheet "lock" tile, tool `self.lock.now` | n/a | keep | One tap, no choice. Two entry points are enough. | none |
| Auto lock minutes | Settings > General row `MAC_R_AUTOLOCK` (`main/hal/maipai_apps_core.h`); choices 0, 1, 5, 15, 30, 60 (`main/hal/maipai_lock_core.h`) | 0 (off) | keep, trim | Six values where three do the job: off, 1, 15 minutes. Keeps the control, drops the clutter. | NX family, small |
| Listening cues: sound, light, face (at least one must stay on) | `self.prefs.set` in `main/hal/maipai_fx.cc`; rule in `host/maipai_body/unit_prefs.py` | all on | keep the rule, Advanced the switches | The people near the robot must always be able to tell it listens. The three switches themselves are for makers. | host only |
| Camera cue cannot be switched off | `docs/dev/feature-ledger.md` row "The camera cue cannot be switched off" | fixed | keep | Not a choice already. | none |
| Remote control | host `[remote]` in `host/robot.example.toml`, settings page | off | keep | Off by default and a privacy control. Already one switch. | none |
| Phone on the LAN may open the settings page | `[settings] lan` in `host/robot.example.toml` | off | Advanced | Needs a token and a reason; most people never need it. | host only |
| Encrypted link, plain link opt-out | decision 13 in `docs/design/decisions.md` | encrypted | Advanced | Safe default; the opt-out is a rare, explicit act. | host only |
| USB movement limit (limited or off) | `self.motion.set` in `main/hal/maipai_motion_limit.cc`; host settings | limited | Advanced | A protection for the cable and the servos. The unit already decides from the cable, the lift and the battery; the override is for makers. | host only |

## Sound

| Setting or choice | Where | Default | Verdict | Reason | Cost |
|---|---|---|---|---|---|
| Volume slider | sheet slider, Settings > General `MAC_R_VOLUME`, host `volume` | 70 (host default) | keep | A person changes this daily. Keep the sheet slider and the Settings row; one stored value. | none |
| Volume cap per unit | host `volume_cap` in `host/robot.example.toml`, `host/maipai_body/unit_settings.py` | not set | Advanced | A household rule, rarely used. | host only |
| Sounds enabled (sound policy `enabled`) | `self.audio.set_sound_policy` in `main/hal/maipai_sounds.cc` | on | remove | Same effect as mute or volume 0; a third way to say quiet. | SF family, small |
| Sounds at night (`night_ok`) | same tool | off | automatic | Quiet hours and the light sensor already decide. Fixed rule: no own sounds at night unless an alarm rings. | SF family, small |
| Quiet hours (from, to) | same tool (`quiet_from`, `quiet_to`) | none set; the hourly chime assumes 22:00 to 07:00 (`main/Kconfig.projbuild`) | automatic with an Advanced edit | Start with 22:00 to 07:00 on; one Advanced row to change the hours. | host only |
| Dark flag from the host (`dark`) | same tool, set by the host from the light sensor | host decides | automatic | Already automatic. | none |
| Hourly chime | tool named in `main/Kconfig.projbuild` (`MAIPAI_HOURLY_CHIME`); the tool is not in the replay's tool list (not checked) | off | Advanced | A person who wants it will look for it. | host only |
| Listening sound (off, chime, mm) | `listen_sound` in `main/hal/maipai_prefs_core.h`; `host/maipai_body/unit_prefs.py` | chime | Advanced | Three options where one is right for nearly everyone. | host only |
| Thinking tone | face config `thinking_tone` (`main/hal/maipai_face_core.h`); tool `self.face.set_config` | on | remove | Two switches for the same cue (tone and dots). Fold into the filler choice below. | UI family, small |
| Filler mode (none, tone, phrase) | `filler_mode` in `unit_prefs.py`; `self.filler.*` | tone | Advanced | One real choice (a spoken phrase while it thinks); the rest is automatic. | host only |
| Filler wait (0.2 to 1.5 s) | `filler_wait_s` | 0.4 s | remove | Nobody can judge 0.4 against 0.6. The unit can measure its own reply time and choose. | NX family, small |
| Pickup reaction (off, face, face with sound) | `pickup_reaction` in `main/hal/maipai_prefs_core.h` | face with sound | automatic | The sound part follows quiet hours; the reaction itself is a feature, not a setting. | NX family, small |
| Sound packs and play sound | tool `self.audio.play_sound`; dashboard installed set (decision 17) | starter set | automatic | The dashboard installs from use; no unit screen. | host only |

## Listening light, face, and the words on the screen

| Setting or choice | Where | Default | Verdict | Reason | Cost |
|---|---|---|---|---|---|
| Listening light (off, dim, normal) | `listen_light`; Settings > General `MAC_R_LISTEN_LIGHT` (switch) | normal | automatic | Normal by day and dim at night from the clock and the room light. Drop the Settings row. | NX family, small |
| Listening light color | `listen_light_color` in `unit_prefs.py` | light blue | remove | Cue colors carry meaning (listening, picture, live view). A color picker lets someone make them ambiguous. | host only |
| Listening face (the face changes when it listens) | `listen_face` | on | Advanced | Part of the cue rule above. | host only |
| Face style (big eyes, eyes only, stock, classic, minimal) | `self.face.set_config` `style`; Settings > Faces tab (`MAC_TAB_FACES`, pair tiles); host faces page | big eyes | keep, trim to three | Classic and eyes only are close to big eyes and minimal. Keep big eyes, stock, minimal (owner question). | UI family, small |
| Picture faces (picture only, with eyes, short run of frames) | `self.facepic.*`; `host/maipai_body/picture_faces_page.py`; sixth tile in Faces tab | none installed | keep on the dashboard only | Installed-set item (decision 17); the unit tile appears only when a pack is held. | host only |
| Eye color (nine named plus any hex) | face config color key; host faces page | white | Advanced | A taste choice. Offer six, hex only in Advanced. | host only |
| Screen background color | face config `background` | black | Advanced | A taste choice with a power cost; black is right. | host only |
| Emotion tint | face config `emotion_tint`; `emotion_faces` pref | on | remove | Always on. Two switches for a look that is the same for everyone. | UI family, small |
| Captions on the face (on, off) | face config `captions`; also `captions_mode` (off, subtitles, banner) in `unit_prefs.py` | off | keep one, remove three | Four overlapping settings put words on the screen (captions, captions_mode, speech_bubble, caption_size). One switch "Show words" stays. | UI family |
| Speech bubble | `speech_bubble` | off (follows the stock style) | remove | The fourth way to show words. | UI family, small |
| Caption size (small, medium, large) | face config `caption_size` | medium | Advanced | Accessibility need, but one Advanced row is enough. | host only |
| Top bar (hidden, always) | `top_bar` | hidden | remove | The banner row shows what the bar would. | UI family, small |
| Status icons (heard, listening, thinking) | `status_icons`; Settings > General `MAC_R_STATUS_ICONS` | off | automatic | Show when the unit is in a listening or thinking state; no setting. | UI family, small |
| Thinking dots | `thinking_dots` | on | remove | Always on. This is the thinking cue. | UI family, small |
| Time-of-day looks and their four start hours | face config `tod`, `tod_hours` | off | automatic | Night look from the clock; fixed hours; no switch. | UI family, small |
| Night dim | `fx_night_dim`; Settings > General `MAC_R_NIGHT` | off | automatic | The unit knows the time and the room light. Always on, with the sheet slider winning by day. | NX family, small |
| CRT effect | `fx_crt` | off | Advanced | A look effect, not a need. | host only |
| Glow effect | `fx_glow` | off | Advanced | Same. | host only |
| Color mode (normal, mono, warm, cool, duotone, amber, green) | `fx_color_mode` in `unit_prefs.py` (seven values in `main/hal/maipai_prefs_core.h`) | normal | Advanced, trim to four | Seven modes where "normal, warm, mono, cool" cover real needs. | host only |
| Weather and mood overlays | `overlays_enabled`; `self.overlay.*`; `self.face.decorate` | on | Advanced | Needs data from the host; on only when the host sends something. | host only |
| Reaction table (word reactions) | `self.reaction.*` in `main/hal/maipai_react.cc`; host extras page | starter table | Advanced | A maker tool; the starter table is right for everyone else. | host only |
| Turn toward faces (off, talk, always) | `turn_to_faces`; `effective_turn_to_faces` in `unit_prefs.py` | always | Advanced | Uses the camera, so vision off overrides it. Three values where on and off do the job (owner question). | NX family |
| Who turns toward faces (robot, hub, off) | `face_owner` in `unit_prefs.py`; `self.look.claim` | robot | automatic | Home when paired, the robot otherwise. | host only |
| Look at speaker, look at faces, look on wake | host keys `look_speaker`, `look_faces`, `look_on_wake` (`host/maipai_body/app.py`) | not checked | remove, fold into turn toward faces | Three near-identical switches plus the unit's own. One behavior, one Advanced row. | host only |
| Clock face: when it shows by itself | face config `clock_idle_s` (0 to 3600) | 0 (never) | Advanced, two values | "Never" or "after 1 minute idle". | host only |
| Clock style (digits, ring) | face config `clock_style` | digits | remove | Pick one. The ring is the lesser choice. | UI family, small |
| 24 hour clock | face config `clock24` | not checked | automatic | From language and time zone, with an Advanced override. | host only |
| Language | first run, Settings > General `MAC_R_LANGUAGE`, face config `lang`, host language | asked once | keep | Asked once at first run; later it lives in Settings only. Not asked again anywhere else. | none |
| Time zone | More > Time zone (27 stock zones, `apps/app_setup/workers/system.cpp`, `main/hal/maipai_more.cc`); `self.clock.set_zone` | UTC until set | automatic | The host knows its own zone and sends it; the clock comes from `self.clock.set`. Keep the list only when no host is paired, behind Advanced. | host only, then NX family |
| Brightness | sheet slider, Settings > General `MAC_R_BRIGHT`, Setup app display page, host `brightness` | 100 | keep one | Four places for one value. Keep the sheet and Settings; drop the stock page. | UI family |
| Screen timeout and power save | Setup app power-saving page (`apps/app_setup/workers/ai_agent.cpp`); rest stages and dim rules in `docs/design/screen-stays-dim-2026-11-16.md` | host rest stages | automatic | The unit knows the cable and the battery. No page. | NX family |

## Movement

| Setting or choice | Where | Default | Verdict | Reason | Cost |
|---|---|---|---|---|---|
| Idle motion on or off | tool `self.robot.set_idle_motion` (`main/hal/hal_mcp.cpp`); host `idle_motion` | off | remove | Same job as the next row. | host only |
| Idle movement (off, calm, lively) | host `idle_movement` (`host/maipai_body/app.py`, settings page) | off | Advanced | One row replaces the two. | host only |
| Dance to music | host `dance_to_music` (`robot.dance.auto`) | not checked | Advanced | A feature switch; the dance list needs no setting. | host only |
| Dances (ten built in) | `self.robot.dance`, `self.robot.dance_list` | n/a | keep as features | Not a setting. | none |
| Head home position and servo test | Setup app servo page (`apps/app_setup/workers/servo.cpp`) | factory | Advanced | A maker or repair step. | host only |

## Quick settings sheet, pages, apps

| Setting or choice | Where | Default | Verdict | Reason | Cost |
|---|---|---|---|---|---|
| Which items the sheet shows (11 possible: volume, brightness, mute, quiet, lock, apps, games, wifi, battery, tailnet, address) | `self.pages.set` `sheet_items` in `main/hal/maipai_pages_unit.cc`; `main/hal/maipai_pages_core.h` | a fixed starter set | remove | The sheet is the same on every robot, so a friend can follow a guide. Host layout editor goes behind Advanced. | host only |
| Sheet closes after N seconds (8 to 30) | `sheet_s` | 10 | remove | Nobody needs to tune it. | host only |
| Swipe pages left and right (clock, timers, games, actions, frame, tiles) | `self.pages.set` `left`, `right`; `host/maipai_body/swipe_pages.py`, `settings_ui_pages.py` | starter set | Advanced | A layout choice for people who like to tinker. | host only |
| Pages idle return time (5 to 300 s) | `idle_s` | not checked | remove | Same as above. | host only |
| Action buttons (2 to 4 of beep, dance, game, hello) | `actions` | not checked | Advanced | Same. | host only |
| Apps wall and app visibility | Setup app visibility page (`apps/app_setup/workers/feature_toggle.cpp`); `MAC_APP_NAMES` in `main/hal/maipai_apps_core.h` | all shown | automatic | Show what is installed; no visibility page. | UI family |
| Timers and alarms | `self.timer.*`; Apps wall | n/a | keep as features | A person sets a timer when they need one; no settings to tidy. | none |
| Games (seven built in) | `self.game.*`; sheet and Apps wall | n/a | keep as features | No setting beyond picking a game. | none |

## Network, account, updates, setup

| Setting or choice | Where | Default | Verdict | Reason | Cost |
|---|---|---|---|---|---|
| Wi-Fi network | Settings > Network `MAC_R_WIFI_PAGE`, `self.wifi.list_saved`; setup portal (`MAIPAI_WIFI_PORTAL`) | asked at first run | keep | Required; asked once. | none |
| Network tab info rows (name, signal, hub) | `MAC_R_SSID`, `MAC_R_SIGNAL`, `MAC_R_HUB` | n/a | move to Info tab | They are not choices; the Info tab already lists them. | UI family, small |
| Private network (tailnet) row | `MAC_R_TAILNET`; `self.tailnet.status`; test hook `self.network.prefer_tailnet` | per build | Advanced | Used by roaming setups only. The test hook is a bench tool. | host only |
| Network test | More > Network test (`apps/app_setup/workers/network_test.cpp`) | n/a | remove | It tests stock vendor services, which a private robot never calls (decision on zero phone-home, `docs/design/egress-audit.md`). | UI family |
| Account page, unbind and factory reset | Setup app account page (`apps/app_setup/workers/account.cpp`) | n/a | remove the account page; keep factory reset in Advanced with a confirm | There is no vendor account. Factory reset is needed but must be deliberate (`main/hal/maipai_reset.cc`). | UI family |
| Software update | `self.firmware.update`; decision on signed updates (`docs/design/release-and-updates.md`) | ask when one exists | keep | One question when an update is real. | none |
| Mic test and LED color test (Setup app audio and LED pages) | `apps/app_setup/workers/audio.cpp`, `servo.cpp` | n/a | Advanced | Repair and maker checks. | host only |
| Remote LED ring color | host `led` key (`host/maipai_body/unit_device.py`) | not set | remove | Ring colors are cues. Remote lights are an action (flash, beep), not a setting. | host only |
| Voice speed and pitch | host `speech_speed`, `speech_pitch` (`host/robot.example.toml`) | 1.0, 0 | Advanced | Fine tuning; the default is right. | host only |
| Persona | host `persona` | a short helpful line | keep | Changes what the person cares about most. Keep it first on the dashboard. | none |
| Wake word | wake word maker package (`host/maipai_body/settings_ui_wakemaker.py`); `main/hal/maipai_wake*.h` | the built-in word | keep as a package | Off until switched on. A friend picks one word at most. | none |
| Optional packages (memory notes, home assistant, coding companion, wake word maker) | `[packages.*]` in `host/robot.example.toml` | off | Advanced | Costs nothing while off. A list on the dashboard, not on the unit. | none |

## First run

| Step | Where | Default | Verdict | Reason | Cost |
|---|---|---|---|---|---|
| Language | `MFR_LANGUAGE` in `main/hal/maipai_firstrun_core.h`; `docs/design/first-run-flow.md` | none | keep | Everything else follows from it. | none |
| Name (seven names) | `MFR_NAME`; `host/maipai_body/first_run_name.py` | StackChan (highlighted) | keep, skippable | Decision 20 lists the name. Make "StackChan" a one-tap accept. | UX family, small |
| Wi-Fi | `MFR_WIFI` | none | keep | Required. | none |
| Brain (Home, own servers, set one up) | `MFR_BRAIN`; decision 12 | none | keep | The one choice that decides where data goes. | none |
| Privacy note | `MFR_PRIVACY` (`mfr_ack_privacy`) | none | automatic | An acknowledgment, not a choice. Put the words on the Done screen. | UX family, small |

## The ten biggest simplifications

Ranked by clutter removed per effort.

1. Words on the screen: collapse captions, captions mode, speech bubble and caption size into one "Show words" switch. Removes three settings. UI family, small.
2. Quiet: fold the sound policy (enabled, night_ok, muted) into mute, quiet hours with a default 22:00 to 07:00, and the light sensor. Removes three settings. SF family, small.
3. Idle motion: one row (off, calm, lively) replaces two. Host only.
4. Pages and sheet layout: fix the starter layout; the layout editor (left, right, actions, sheet_s, idle_s, sheet_items) goes to Advanced. Removes about six host rows. Host only.
5. Color effects: crt, glow, color mode and overlays behind one Advanced card; seven color modes to four. Host only.
6. Thinking cue: thinking dots, thinking tone, filler wait and status icons become one automatic cue; filler mode stays in Advanced. Removes four. UI and NX families, small.
7. Stock Setup app: drop the account page, the network test and the app visibility page; brightness, power saving and time zone stop having stock pages. Removes six screens. UI family.
8. Time zone, clock 24 hour and night dim become automatic from the host clock and the room light. Removes three, host mostly.
9. Turn toward faces: three host switches plus the unit's own become one Advanced row (or none). Removes four. Host only.
10. First run: drop the separate privacy step into the Done screen and make the name a one-tap default. One fewer screen. UX family, small.

## Choices that need an owner decision

1. Face styles: "Five face styles differ little (big eyes, eyes only, stock, classic, minimal). Keep three (big eyes, stock, minimal)?" Default: yes, three.
2. Turn toward faces: "The robot uses its camera to turn toward people. Should this be a plain on or off switch (default on) instead of off, talk, or always?" Default: on or off.
3. Vision off as a sheet tile: "Vision off is a privacy control but has no tile on the quick sheet. Swap it in for the Apps or Games tile?" Default: yes, swap for Games.
4. Auto lock: "Auto lock offers six times. Offer only off, 1 and 15 minutes?" Default: yes.
5. Quiet hours: "Should quiet hours start on by default at 22:00 to 07:00, so the robot makes no own sounds at night?" Default: yes.
6. Network test: "The stock network test contacts vendor services. Remove it, or replace it with a test of the paired host only?" Default: replace with a host-only test.
7. Name at first run: "Should a person be able to skip naming the robot and keep StackChan?" Default: yes.
8. Time zone: "May the host set the unit's time zone from its own, and the unit screen list stay only when no host is paired?" Default: yes.
