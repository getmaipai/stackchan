# Draft names to confirm

The user docs were written ahead of the build. Names below appear in `docs/user/` but not in `docs/design/` or the code.
When the build settles each one, rename it in the docs or keep it, then delete its line here. Delete this file when it is empty.

## Settings keys

`persona`, `persona_lock`, `hourly_chime`, `idle_motion`, `pet_mood`, `cues`, `camera`, `camera_retention`,
`tailscale` key field on the Network page, `saved_wifi` list, `api`, `events`, `mqtt_url`, `ha_bridge`, `metrics`, `mcp`, `home_url`, `quick_sliders` values (volume, brightness).

## Commands

- `stackchan token` (creates a token for the API and the MCP endpoint).
- `stackchan camera delete` (clears kept snapshots).
- `stackchan notify --status pass|fail` (the command exists in the design; the flag is a guess).
- `stackchan firmware verify` (the design says `verify`).

## Defaults and behaviour

- `update_check` default is weekly. `update_channel` default is stable.
- Voice phrases such as "hard mute", "mirror me", "let's play", "dance", "snooze", "normal".
- The reaction list (surprised, dizzy, tilted, happy) and the "purr".
- Offline phrases recorded in the owner's voice from the web page.

Real names already in the design and used as written: `face_style`, `face_color`, `captions`, `night_mode`, `brain`, `llm_url`,
`stt_url`, `tts_url`, `voice`, `thinking_cue`, `strip_mode`, `quiet_from`, `quiet_to`, `update_*`.

## Confirmed against the code (2026-11-15, from the build session)

- Names in today's code, `host/maipai_body/settings_keys.py`: `robot.face.color`, `robot.night.mode`, `household.quiet_hours.from` and `.to`,
  `robot.power.warn_at`, `robot.timers.enabled`, `robot.announce.enabled`, `robot.muted`, `robot.quiet`, `robot.repeat.enabled`,
  `robot.vision_off`, `robot.mute.local_unmute`, `robot.sounds.enabled`, `robot.sounds.night`. The user docs use the planned `robot.toml`
  names (`face_color`, `night_mode`, `quiet_from`, `quiet_to`). Map them when the standalone config lands (build phase 4).
- `vision_url` exists in the code.
- Entry points today: `stackchan-provision` and `maipai-bot-host`. The `stackchan` command in the docs is planned.
- Not in the code at all (planned): `camera_retention`, `hourly_chime`, `persona_lock`, `pet_mood`, `ha_bridge`, `mcp`,
  `stackchan token`, `stackchan camera delete`, `stackchan notify --status`.
- `prefer_tailnet` comes from the unit protocol (`self.network.prefer_tailnet`, 0 to 120 minutes). The Network page and the tailnet status text are drafts. The robot joining the tailnet by itself is design ANYWHERE-01, not built.

- Reset the robot (Settings > Reset, press then hold three seconds to confirm) is a new feature requested by the owner on 2026-11-15. It is not in the design or the code. The docs describe it as built.
- `docs/user/security.md`: the reset-from-settings step, the Security page with a Forget button, and the private security contact are drafts. The contact must exist before release.

## Claims to measure before release

- Privacy: no network egress proof has been run (`scripts/stackchan-egress-proof.sh` exists; `docs/dev/stackchan-unit-measurements.md` lists it as to do). The docs say "built so" and rate privacy two stars until a capture of an idle and a busy unit shows only the host and the Wi-Fi router. The security audit (docs/design/safety-and-privacy.md, 2026-11-15) lists open fixes: plain ws:// with a static token, linked vendor OTA/MQTT/SNTP code, an open Wi-Fi portal, readable flash.

- The README says MaiPai for StackChan is faster and smoother than the factory firmware. No head-to-head measurement exists yet. Measure wake cue, stop and first audio on the same unit and publish the numbers, or soften the claim.
- The latency figures (150 ms, 300 ms) are design targets, not measured on a unit.
- The plan to measure it is `docs/dev/benchmark-factory-vs-ours.md`. Owner heard consistent stuttering in the factory voice replies; keep that out of the docs until measured.

## Added 2026-11-15 from the build notes

- Real key `robot.dance.auto` (automatic dance, off by default). The docs call it Dance to music in the web settings. Map when the standalone config lands.
- Built per the dev notes but never run on a unit: the little dance, music detection and automatic dance, tap-on-the-face mute, spoken stop, orientation reactions, sounds, wireless update, timers and hub announcements.
- Song naming comes from MaiPai Home. The robot sends a short clip, Home names it. The clip flow is a draft.
- "What do you see" is design only (find-the-person-then-the-face note). Tagged Planned.

## Lights and sounds (2026-11-15)

- Source: `docs/dev/stackchan-lights-audit-and-plan-2026-11-13.md` section 5 (the ring standard), `stackchan-sounds-2026-11-13.md` and `stackchan-timers-and-announcements-2026-11-13.md`. Some rows there are marked proposed. The timer ring and tone are built per the timers note; the other rows follow the proposed standard.
- Conflict to settle: the user docs say the robot shows thinking dots with a quiet tone, while the lights plan (D1) keeps thinking and speaking dark with no tone. The user docs follow the older design for the sound (dots plus a quiet tone, `thinking_cue`) and the lights plan for the ring (dark). The owner should confirm the tone.
- The 'error' tone and 'listening' pop use the shipped tones (`exclamation`, `popup`). The 'back online' chime is the shipped `success`.
- The light show colours for the dance are not specified in the notes, so the page does not name them.
- The lights are two bars of six, one on each side of the base (official hardware page: two rows totaling 12 RGB LEDs), plus a power indicator light at the back. Older design notes call them a ring. The standard drives all 12 the same colour. The drawings put the left bar top to bottom and the right bar bottom to top. The real pixel order and which bar is which is unverified.

## From the official docs (checked 2026-11-15)

- Factory AI agent is powered by XiaoZhi and set up through the StackChan World app. Factory has: dance choreography in the phone app, avatar and monitoring-camera modes, ESP-NOW remote control, an app center, on-device microphone, RGB LED and servo tests, servo calibration, online firmware update, and a documented restore with M5Burner (Only Official). The restore steps in docs/user/switch-from-the-factory-firmware.md follow the official page but have not been run.
- Idea from the official docs: on-robot hardware tests (microphone, light bars, servo). We have `stackchan check` on the host. Ask the build session whether the robot should get the same tests.

## Sponsors (2026-11-15)

- README has a Support the project section linking https://github.com/sponsors/JesseWebDotCom. The link is dead until the owner finishes and publishes the personal GitHub Sponsors listing (checked: no listing on the personal account or the org). Do not release until it resolves, or remove the section.
- `.github/FUNDING.yml` (github: JesseWebDotCom) is staged locally. It goes into the public repo only with the release commit, because the public repo takes no pushes before the firmware release is approved.

## Install page (2026-11-15)

- `stackchan install-service --remove`, `pipx upgrade stackchan` and the host printing its port are drafts. The design names `stackchan install-service` only.
- Do not publish the firewall table until the real port and discovery behaviour are known.

## Renamed term (2026-11-15)

- Owner: "standalone" sounds like "stock" and is a new term. User docs now say "your own LLM", and the setting value is `brain = "llm"` in the docs. The design and code still say `standalone`. The build session should rename the value (or accept both) and the design notes.

## Live view (2026-11-15)

- Owner asked why there is no live video and wants listening, looking and picture-taking always very visible on the robot. The design already has JPEG camera frames streaming up (avatar socket, frame type 0x02, start and stop 0x05 and 0x06), so a low-resolution live view in the web app looks feasible. Not built or measured. The docs mark it Planned.
- New cue invented in the docs: a LIVE dot on the screen for live view, with steady pink light bars. The build session must design it.
- Per the vision channel note (2026-10-21), camera streaming had never worked on a unit in AI-agent mode. Check whether that is fixed before promising live view.
