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
