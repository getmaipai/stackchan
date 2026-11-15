# Scope: the core robot and MaiPai Home

Owner direction, 2026-11-15: the core MaiPai for StackChan app should be simple and single purpose, not stretched to hold the kitchen sink. Anything bigger runs with MaiPai Home.

## The core purpose

A private voice robot. It listens, answers with your own LLM, shows a face, keeps time, reacts to touch and motion, dances, protects your privacy and travels with you. It needs no brain beyond the LLM.

## In the core

Voice (wake word, follow-ups, interrupt, stop, ten commands), faces and clock, timers and alarms, reactions and idle life, dance on request and to music, mute, camera off and full quiet, the always-on cues, lights and sounds, on the go with Tailscale, pairing and security, signed updates with rollback, reset, English and Spanish, switch and go back.

## With MaiPai Home (not in the core)

| Feature | Why it goes to Home |
|---|---|
| Camera: snapshots, face follow, wave and mirror, take my picture, name list, what is this | Needs vision, identity and storage that Home already owns |
| Watch mode, security alarm, alerts | Alerts, recipients and quiet hours are household features |
| Baby and pet monitor | Listening in and alerts need Home's recipients and rules |
| Find my robot, remote beep, lights, talk, pan and tilt, live view | Needs accounts, a safe remote path and an activity log |
| Games and a pet mood | Persistent state and content, a Home package |
| Coding companion | An integration with an agent, a Home package |
| Home tools: local API, events, MQTT, home-automation bridge, metrics, MCP | Integrations belong in one place, Home |
| Memory, people, calendars, announcements, naming songs, child and teen rules | Household data and policy |

## What this means for the code

- The core host keeps only the voice turn, the face, timers, reactions, dance, privacy switches, pairing and updates.
- The monitoring, remote, camera-analysis, games, coding and integration modules ship with the Home adapter, or as Home packages, and are not part of the core install.
- The unit keeps the body half of each (the cues, the camera and microphone switches, the always-on indicators), so the privacy rules hold whatever runs on top.
- The cue rules stay in the core: any mode that opens the microphone or camera still draws its cue first, from one code path.

## Open

- The firmware already includes some body halves for the moved features (camera capture, streaming, the music detector). Decide which stay compiled in and which become optional builds, to keep the core small and inside the memory gate.
- Whether `home_url` pairing should be offered during first setup, so the extras are one step away.
- The docs mark moved features with the `Needs MaiPai Home` tag. Moving one back to the core is a tag change plus a design decision.
