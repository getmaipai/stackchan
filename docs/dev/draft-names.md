# Draft names to confirm

The user docs were written ahead of the build. Names below appear in `docs/user/` but not in `docs/design/` or the code.
When the build settles each one, rename it in the docs or keep it, then delete its line here. Delete this file when it is empty.

## Settings keys

`persona`, `persona_lock`, `hourly_chime`, `idle_motion`, `pet_mood`, `cues`, `camera`, `camera_retention`, `vision_url`,
`api`, `events`, `mqtt_url`, `ha_bridge`, `metrics`, `mcp`, `home_url`, `quick_sliders` values (volume, brightness).

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
