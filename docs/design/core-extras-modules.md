# Host modules: core or extras

Status: first pass 2026-11-15 from a read of the module names under `host/maipai_body`. A lane confirms each by reading the code before moving it. Rule: `AGENTS.md`, "Scope". Feature logic leaves this public repo (see below); the capability driver stays.

## Stay in the core
Voice turn and speech (`speech/` except voices and voiceprint), `turn.py`, `repeat.py` (what did you say), `timers.py`, `initiative/alarm.py`, `reactions.py`, `idle_faces.py`, `sleep_z.py`, `dance*.py` and `music_dance*.py` (dance on request and to music), `light*`, `ring*`, `sounds.py`, `volume.py`, `brightness.py`, `privacy.py`, `stop_phrases.py`, `face_*`, `expression/`, `renderer.py`, `gaze.py`, `head_*` (head gate and touch filter), `presence/{night,power,safety,thermal,touch,knock,carry_reaction,motor_health,motion_state,sleep_auto}.py` (the robot's own body), `firmware_update.py`, `wifi_list.py`, `uplink_stats.py`, `self_heal.py`, `estop_recovery.py`, pairing, config, cli, `brain/`, `hal/`.

## Leave the core repo (Home does it, or it is a Home feature)
- Vision and identity: `vision/` (gallery, recognize, embed, detect, watch, live_view, look_fast, capture except the cue path), `vision_bridge.py`, `vision_post.py`, `ambient_vision.py`, `sight.py`, `person_tracker.py`, `speaker_gaze.py`, `meeting_faces.py`.
- Household and identity: `speaker_evidence.py`, `speaker_fusion.py`, `speech/voiceprint.py`, `owner_levels.py`, `presence_watch.py`, `presence/{attention,arbitration,funnel,entries,observations,doa,auto_dance}.py` (who is home, who is speaking), `announce.py`, `initiative/offer.py`, `companion.py`, `routines.py`.
- Music identification and library: `music_identify.py`, `song_title.py`, `speech/music.py`.
- Voices catalog: `speech/voices.py` and cloned-voice handling (Home owns voice records; the core keeps the plain built-in voice).
- Old dashboard: `dashboard/` (Home is the dashboard). The core gets its OWN small local settings page, new code, built in the flasher and settings phase: robot status, the `robot.toml` settings, the pairing code, mute, update and the persona text. It is served by the core host, needs no Home, and never shows household data.
- `moves/` stays in core because dance needs it.

## Where moved code ends up (owner rule, 2026-11-15, with the reason)

Reason: feature logic for watch, monitor, identity, alerts and similar is robot-agnostic. If it lived in this public repo, people would build hacks around it, and it would be copied for Reachy Mini and other bots. It belongs in Home, written once against a robot capability interface that every bot implements.
So this repo holds only what is native to this bot: the unit protocol, a thin capability API (camera frame, microphone stream, lights, moves, display and cues, heartbeat, sensors), and the cue enforcement. Cue enforcement lives on the unit, so a modified host cannot open the camera or microphone without the cue.
Sorting the older modules, decided per module by a lane that reads the code:
1. Capability driver code (talks to the unit): stays here, small, behind the capability API.
2. Feature logic (detectors, alerts, monitor modes, identity, recognition, recipients, games, coding companion): not kept here. Home already has much of it in TypeScript; the rest is rewritten in Home against the capability API. The old Python is deleted from this repo once Home covers it, or kept in a private holding folder outside the public tree until then.
3. Robot-side compute Home needs (for example face detection on frames): a Home package or Home sidecar, never this repo.
Nothing in this repo imports Home code. Home's pin to this repo moves on firmware releases because its flash flow uses this repo's flasher and assets, and when the capability API changes.

## Stay in the unit, always
The cue code path, camera and microphone switches, always-on indicators, the heartbeat, hard mute. Firmware body halves of moved features sit behind Kconfig switches (`home` preset only).

## Open
- `speech/offline_clips*` and the sherpa engines serve the own-LLM local speech engine: core.
- `hub_host.py` and `link/` are the Home link: they move into the Home adapter, and the core keeps only the paired-host link its own LLM brain needs.
