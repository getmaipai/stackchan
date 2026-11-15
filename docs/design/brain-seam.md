# Brain seam call map

`Brain` is the host boundary for answering and household knowledge. The current body still owns audio capture/playback, face, timers, and command delivery.

| File and function | Home request | Needed back |
|---|---|---|
| `speech/stt_stream.py`, `SttStreamClient.run` | Stream captured PCM to `/api/stt/stream` | final text, speech state, locally retained audio span |
| `speech/turn_client.py`, `TurnClient.stream` | POST utterance and speaker/presence context to `/api/turn/stream` | ordered cues and final reply/turn identifiers |
| `speech/turn_client.py`, `TurnClient.cancel` | POST `/api/turn/{id}/cancel` | whether in-flight work was cancelled |
| `speech/tts_playback.py`, `TtsPlaybackClient.speak` | POST text and optional turn generation to `/api/tts` | streamed audio and completion/cancel result |
| `bodies/stackchan/vision_post.py`, `VisionPoster.post` | Upload JPEG plus purpose/scene hints to `/api/devices/me/vision` | acceptance, status and description availability |
| `link/roster.py`, `RosterPoller.refresh` | GET `/api/devices/me/people` | current people and follow-up policy snapshot |
| `link/channel.py`, `CommandChannel._settings_command` | Receive Home `settings_changed` command | settings values applied by body listeners |
| `app.py`, `_wire_timers_and_announcements` | issue reminder tool calls through robot adapter | created/listed/stopped household reminder records |

Settings arrive over the existing command channel and stay push based. Timer countdowns, ring, snooze, audio hardware, and local vision detection stay in the body. Link pairing, state reporting, firmware assets/update, check-in, and notification delivery remain lifecycle integrations rather than answering calls; they are not part of this seam. STT, TTS, roster and reminder transport implementations remain in their existing modules and can be moved behind richer brain adapters in a later pass without changing their wire contracts.
