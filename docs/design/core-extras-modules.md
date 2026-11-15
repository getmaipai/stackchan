# Host modules: core or extras

Status: first pass 2026-11-15 from a read of the module names under `host/maipai_body`. A lane confirms each by reading the code before moving it. Rule: `AGENTS.md`, "Scope". Extras move to `host/maipai_body/extras/` (installed only with the Home adapter); an architecture test fails the build if core imports extras.

## Stay in the core
Voice turn and speech (`speech/` except voices and voiceprint), `turn.py`, `repeat.py` (what did you say), `timers.py`, `initiative/alarm.py`, `reactions.py`, `idle_faces.py`, `sleep_z.py`, `dance*.py` and `music_dance*.py` (dance on request and to music), `light*`, `ring*`, `sounds.py`, `volume.py`, `brightness.py`, `privacy.py`, `stop_phrases.py`, `face_*`, `expression/`, `renderer.py`, `gaze.py`, `head_*` (head gate and touch filter), `presence/{night,power,safety,thermal,touch,knock,carry_reaction,motor_health,motion_state,sleep_auto}.py` (the robot's own body), `firmware_update.py`, `wifi_list.py`, `uplink_stats.py`, `self_heal.py`, `estop_recovery.py`, pairing, config, cli, `brain/`, `hal/`.

## Move to extras (Home does it, or it is a Home feature)
- Vision and identity: `vision/` (gallery, recognize, embed, detect, watch, live_view, look_fast, capture except the cue path), `vision_bridge.py`, `vision_post.py`, `ambient_vision.py`, `sight.py`, `person_tracker.py`, `speaker_gaze.py`, `meeting_faces.py`.
- Household and identity: `speaker_evidence.py`, `speaker_fusion.py`, `speech/voiceprint.py`, `owner_levels.py`, `presence_watch.py`, `presence/{attention,arbitration,funnel,entries,observations,doa,auto_dance}.py` (who is home, who is speaking), `announce.py`, `initiative/offer.py`, `companion.py`, `routines.py`.
- Music identification and library: `music_identify.py`, `song_title.py`, `speech/music.py`.
- Voices catalogue: `speech/voices.py` and cloned-voice handling (Home owns voice records; the core keeps the plain built-in voice).
- Dashboard: `dashboard/` (Home is the dashboard).
- Moves package: keep in core only if recorded moves are needed for dance; else extras (decide when the dance lane reads it).

## Stay in the unit, always
The cue code path, camera and microphone switches, always-on indicators, the heartbeat, hard mute. Firmware body halves of moved features sit behind Kconfig switches (`home` preset only).

## Open
- `speech/offline_clips*` and the sherpa engines serve the own-LLM local speech engine: core.
- `hub_host.py` and `link/` are the Home link: they move into the Home adapter, and the core keeps only the paired-host link its own LLM brain needs.
