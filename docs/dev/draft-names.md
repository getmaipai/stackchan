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
