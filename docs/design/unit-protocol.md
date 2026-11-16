# Unit protocol (as built)

Status: as-built record of what the host and the StackChan unit exchange today. It is the input for
the versioned `schema/` folder (empty so far) and for a later virtual unit (simulator). It is not a
design: where code and a plan disagree, this page follows the code. Every fact ends with a
`[from code: file]` tag naming a source file only. Anything not confirmed in code is under "Open".

The wire format is the xiaozhi-esp32 WebSocket protocol, used by the M5Stack StackChan firmware.
MaiPai adds the MCP tool set, the `system` frames, the pairing token and the avatar camera socket
on top of it.

## 1. Transports and ports

Three listeners on the host, all started by the unit's host service.

| Listener | Default port | Purpose | Source |
|---|---|---|---|
| Voice and tool socket (WebSocket) | 8765 | hello, listen, tts, llm, mcp, system, Opus audio | `server.py`, `provision.py` |
| Avatar socket (WebSocket) | 8766 | camera JPEG frames up, camera start and stop down | `avatar/server.py`, `provision.py` |
| Side HTTP service | 8767 | photo upload, notify audio, firmware image, loopback admin routes | `server.py` |

- Ports are defaults; the unit gets its URLs from NVS (section 8). `ws://` or `wss://` both work; a
  local CA can be generated for `wss://` [from code: provision.py, tls.py].
- Voice socket: any path is accepted, no path check. Max incoming frame 1 MiB (close code 1009 if
  exceeded). Server pings every 20 s with a 20 s timeout [from code: server.py].
- Avatar socket: the path must be exactly `/stackChan/ws?deviceType=StackChan`, otherwise close 1008
  [from code: avatar/server.py].

### 1.1 Request headers (both sockets)

| Header | Value | Rule |
|---|---|---|
| `Device-Id` | unit MAC, `aa:bb:cc:dd:ee:ff` | must match a MAC pattern |
| `Client-Id` | UUID | must match a UUID pattern |
| `Authorization` | `Bearer <token>` | long-lived device token, or an enrollment code on first connect |
| `Protocol-Version` | `1` | voice socket only; any other value closes with 1002 |

[from code: server.py, pairing.py, avatar/server.py]

### 1.2 Binary frames

Voice socket, unit to host: one WebSocket binary message is one raw Opus packet (no header). Host to
unit: the same, one packet per message [from code: server.py, turn.py].

| Direction | Codec | Sample rate | Channels | Frame | Notes |
|---|---|---|---|---|---|
| unit to host (mic) | Opus | 16000 Hz after decode | mono | 60 ms (host does not enforce) | decoded then resampled to 16 kHz float |
| host to unit (speech) | Opus, voip mode | 24000 Hz | mono | 60 ms = 1440 samples | 24 kbps, cutoff 8000 Hz, one frame per packet |

[from code: turn.py]. The hello reply advertises the downlink as `format opus, sample_rate 24000,
channels 1, frame_duration 60` [from code: server.py].

While the host has the unit's camera flagged as streaming on the voice socket, binary messages are
stored as photos instead of audio (a legacy path; the avatar socket carries the camera now)
[from code: server.py].

Avatar socket frame, both directions: `[type: 1 byte][length: 4 bytes big-endian][payload]`; total
length must equal 5 + length; payload max 1 MiB (camera frames 2 MiB) [from code: avatar/codec.py,
avatar/server.py].

| Type | Direction | Payload |
|---|---|---|
| 0x01 | unit to host | Opus audio; ignored by the host on this socket |
| 0x02 | unit to host | one JPEG camera frame (must be valid JPEG, else dropped) |
| 0x03 | host to unit | ControlAvatar JSON (eye weights, rotation, mouth); in practice faces go over the voice socket instead (section 4.5) |
| 0x04 | unit to host | ControlMotion; discarded while the software emergency stop is engaged |
| 0x05 | host to unit | start camera stream (empty payload) |
| 0x06 | host to unit | stop camera stream (empty payload) |

[from code: avatar/server.py, avatar_frames.py]. Host-internal code also uses a different envelope
(`0xAA 0x55`, 2-byte length, command byte); it is translated to the type/length form before sending
and never appears on the wire [from code: avatar_frames.py].

## 2. Connection and hello

1. Unit opens the voice socket with the headers in 1.1 [from code: server.py].
2. Host authorizes (section 7). On success it creates a `session_id` (32 hex characters) and replaces
   any older session of the same `Device-Id` (old one closed with 1012) [from code: server.py].
3. Unit sends `hello` within the idle timeout (default 30 s), else the host closes with 1001
   [from code: server.py].
4. Host replies with its `hello`; one hello per session (a second one gets an `error`, code -32600).

Unit hello (fields the host reads):

```json
{"type": "hello", "features": {"notify": true}}
```

Only `type` and `features` (an object of booleans) are read. `features.notify` gates the `notify`
frame; the host answers `NotSupported` if the unit did not advertise it [from code: server.py].

Host hello reply:

```json
{
  "type": "hello", "version": 1, "transport": "websocket",
  "session_id": "0123456789abcdef0123456789abcdef",
  "audio_params": {"format": "opus", "sample_rate": 24000, "channels": 1, "frame_duration": 60}
}
```

On the first connect with an enrollment code the reply also carries `"maipai_token": "<token>"`, a
one-time delivery of the long-lived device token (section 7) [from code: server.py, pairing.py].

Capability and version facts the host learns, and from where:

- Contract version: none exists. The only version field is `version: 1` in the hello reply and the
  `Protocol-Version: 1` header [from code: server.py]. See Open.
- Firmware version: not in hello. The unit reports it in a `fw` telemetry event (`version` field,
  about once a minute); the host compares it as a dotted number against thresholds (0.2.54 sleeping
  face, 0.2.66 listening and thinking faces, 0.2.93 seven extra faces) [from code: app.py,
  expression_map.py, face_vocabulary.py, routines.py].
- Face pack: there is no face-pack field. The host picks faces by firmware version, falling back to
  an older face the unit already draws (for example `joy` falls back to `happy`) [from code:
  face_vocabulary.py, expression_map.py].
- Sensors: no sensor list in hello. Known by tool: battery, ambient light, head touch, tilt and
  shake, camera, microphone, tailnet state (section 6) [from code: adapter.py, companion.py].
- Tool list: `tools/list` is never requested by the host; tools are called by name and an unknown one
  returns an error text containing "unknown tool" or "not supported" [from code: server.py].

## 3. Message types (JSON text frames)

Every host-to-unit JSON frame has `session_id` and `type`. Unit-to-host frames need only `type`
[from code: server.py].

### 3.1 Unit to host

| type | Fields | Host action |
|---|---|---|
| `hello` | `features` | reply with hello (section 2) |
| `listen` | `state` start, stop or detect; `mode` auto, manual or realtime; `aec` bool | starts or ends a voice turn (section 5) |
| `abort` | none | cancels the turn, replies `tts` stop |
| `mcp` | `payload`: JSON-RPC 2.0 | `ping` and `initialize` answered; results and errors resolve host tool calls |

Invalid JSON gets `error` code -32700; any other type gets `error` code -32600 ("Send hello, listen,
abort, or mcp") [from code: server.py].

```json
{"type": "listen", "state": "detect", "mode": "auto", "aec": true}
{"type": "mcp", "payload": {"jsonrpc": "2.0", "id": 7, "result": {"content": [{"type": "text", "text": "{\"yaw\":0,\"pitch\":5}"}]}}}
```

### 3.2 Host to unit

| type | Fields | Meaning |
|---|---|---|
| `hello` | see section 2 | session start |
| `tts` | `state`: start, sentence_start, stop | speaker gate around reply audio |
| `llm` | `emotion`: a face name | set the face (works in agent mode) |
| `mcp` | `payload` JSON-RPC `tools/call` | tool call on the unit |
| `system` | `command` plus optional fields | `idle`, `reboot`, `updating`, `updated`, `wake_selftest`, `wake_rebuild` |
| `notify` | `audio_url` | play an Ogg clip from the side HTTP service; needs `features.notify` |
| `error` | `code`, `message` | protocol error |

```json
{"session_id": "…", "type": "tts", "state": "start"}
{"session_id": "…", "type": "llm", "emotion": "happy"}
{"session_id": "…", "type": "system", "command": "updating", "version": "0.2.7", "progress": 40}
{"session_id": "…", "type": "notify", "audio_url": "http://192.0.2.10:8767/notify/aa:bb:cc:dd:ee:ff/abc.ogg"}
```

[from code: server.py]

### 3.3 MCP envelope

Host call (ids are numeric and increasing; the firmware parses them as numbers):

```json
{"type": "mcp", "payload": {"jsonrpc": "2.0", "method": "tools/call",
  "params": {"name": "self.robot.set_head_angles", "arguments": {"yaw": 20, "pitch": 10, "speed": 150}}, "id": 12}}
```

Unit reply: `result.content[0].text` holds JSON text (or plain text); `result.isError: true` makes the
host raise with the joined text; a JSON-RPC `error.message` does the same. An empty content list
means `true`. Default call timeout 5 s; late or unknown ids are dropped, and a reply arriving before
the host registers the call is held (up to 32) until its deadline. A disconnect fails every pending
call [from code: server.py].

Unit-initiated MCP requests: `ping` is answered `result {}`; `initialize` is answered with
`protocolVersion 2024-11-05`, `capabilities {tools {listChanged false}, vision {url, token}}` and
`serverInfo {name, version}`. The `vision.url` is where the unit POSTs photos (section 6.4)
[from code: server.py].

## 4. Control commands (host to unit)

All are MCP tools called with the envelope above [from code: server.py, adapter.py, companion.py,
and the module named per row].

| Area | Tool | Arguments | Source |
|---|---|---|---|
| Head | `self.robot.set_head_angles` | `yaw`, `pitch` ints (-9999 means keep), `speed` (100 to 150 normal, soft max 400) | adapter.py, profile.py |
| Head | `self.robot.get_head_angles` | none; returns `{yaw, pitch}` ints | adapter.py |
| Head | `self.robot.set_idle_motion` | `enabled` bool | server.py |
| Head | `self.robot.dance`, `stop_dance` | `name`: happy, robot, panic, look_around | companion.py |
| LED | `self.robot.set_led_color` | `red`, `green`, `blue` 0 to 255 (both halves) | server.py |
| LED | `self.robot.set_led_colors` | `led_N_red/green/blue` for N 0 to 11 (all 12 pixels) | server.py |
| Sound | `self.audio_speaker.set_volume` | `volume` percent (host keeps 20 to 100) | server.py, volume.py |
| Sound | `self.audio.play_sound` | `name`, `urgent`, `test` | sounds.py |
| Sound | `self.audio.set_sound_policy` | `enabled`, `night_ok`, `muted`, `dark`, `quiet_from`, `quiet_to` (minutes of day) | sounds.py |
| Sound | `self.audio.sound_info` | none; counts played, refused, clips_played, clips_missing | sounds.py |
| Sound | `self.audio.listen`, `notify`, `alert` | listen window, spoken notice, alert text | server.py |
| Face | `llm` frame `emotion` (3.2) | names in 4.5 | server.py |
| Face | `self.screen.set_face_background` | `palette` string, `night` bool | server.py |
| Face | `self.screen.set_brightness` | `brightness` percent | server.py |
| Face | `self.face.song_title`, `music_notes`, `sleep_z` | `text` (max 60), notes flag, `stage` 1 or 2 | song_title.py, sleep_z.py |
| Face | `self.facepic.begin`, `frame`, `data`, `commit`, `clear`, `status` | `mode` picture, overlay or sequence, `fps` 1 to 12, `overlay` places JSON; `slot`, `index`, `bytes`, `crc`, `raw`; `at`, `b64` (pieces of 2,048 bytes); the owner's own pictures as the face, kept in the unit's memory (docs/design/picture-faces-2026-11-16.md) | picture_faces.py |
| Camera | `self.camera.take_photo` | `question` string; unit uploads JPEG to the vision URL | server.py |
| Privacy | `self.privacy.get`, `set`, `set_policy` | `mute`, `vision_off`, `quiet` as 0 or 1; `local_unmute` bool | privacy.py |
| Timers | `self.timer.set`, `alarm`, `snooze`, `cancel`, `stop`, `list` | `seconds`, `hour`, `minute`, `label`, `silent` | timers.py |
| Reminders | `self.robot.create_reminder`, `get_reminders`, `stop_reminder` | reminder fields | server.py |
| Wi-Fi | `self.wifi.add`, `forget`, `switch`, `use_now`, `list_saved` | `ssid` (1 to 32 bytes), `password` (max 63), `index` | companion.py, wifi_list.py |
| Network | `self.network.prefer_tailnet` | `minutes` 0 to 120 | wifi_list.py |
| Music | `self.music.set`, `capture_clip`, `read_clip`, `drop_clip` | `enabled`; `seconds` 5 to 15; `offset`, `length` | music_dance_wiring.py, music_identify.py |
| Status | `self.battery.get_status` | none; returns `{percent 0 to 100, charging bool}` | server.py |
| Status | `self.get_device_status`, `self.screen.get_ambient_light` | none; light returns `lux`, `ch0`, `ch1` | server.py |
| Firmware | `self.firmware.update` | `url`, `sha256`, `size`, `version` | firmware_update.py |

Read-only tools (`self.battery.get_status`, `self.screen.get_ambient_light`,
`self.robot.get_reminders`, `self.privacy.get`) are retried once after 0.5 s [from code: server.py].
Head yaw range is plus or minus 128 degrees in the host profile; pitch 5 to 85 [from code: profile.py].

### 4.5 Face names

Accepted by `llm.emotion`: neutral, happy, angry, sad, doubtful (host name `doubt`), sleepy,
sleeping, surprised, winking (host name `wink`), listening, thinking, joy, content, excited, shocked,
curious, love, worried [from code: server.py, avatar/server.py]. The host never sends model text as a
face name; the table is closed [from code: avatar/server.py].

### 4.6 System commands

- `idle`: leave listening and go idle [from code: server.py].
- `reboot`: restart the unit. The unit refuses a fourth self-restart in an hour and reports
  `heal_hold`; the host then stops asking [from code: server.py, self_heal.py].
- `updating` with `version` (matches `[0-9A-Za-z.+-]{1,32}`) and `progress` 0 to 100, and `updated`:
  show update state on the face [from code: server.py].
- `wake_selftest`, `wake_rebuild`: wake-word engine self-test steps; first test 300 s after
  connect, then hourly and 60 s after a turn [from code: self_heal.py].

### 4.7 Firmware update flow

1. Host asks Home for a verified image (`version`, `size`, `sha256`) [from code: firmware_update.py].
2. Host checks the gate: unit older than target, link healthy, no turn or call, no timer within 10
   minutes, not muted or in full quiet, battery at least 40 percent or charging, 6 hour backoff after
   a failure, setting `robot.firmware.auto` not off [from code: firmware_update.py].
3. Host publishes the image at `GET /firmware/{device_id}/{token}` (random token, one read, 10 minute
   life, no auth header) and calls `self.firmware.update` [from code: server.py].
4. Unit streams the image, emits `firmware_update_*` events (section 6), restarts. If the unit does
   not report the new version within 15 minutes the host counts a rollback [from code:
   firmware_update.py].

## 5. Turn lifecycle

Wake word, touch, or an on-unit trigger starts a turn on the unit; the host never starts one except
through `self.audio.listen` [from code: turn.py, server.py].

1. Unit sends `listen` with `state` `detect` (wake word heard) or `start` (button, follow-up), plus
   `mode` and `aec`, then streams 60 ms Opus frames. The host drops the request if the robot is muted
   or full quiet (it sends `system idle`), or within 4 s after a line it spoke on its own.
2. The host decodes Opus to 16 kHz and streams it to speech-to-text. Frames in the first 0.3 s after
   a listen start are dropped (the pop-up tone); frames while speaking are dropped unless `aec` is
   true; frames within 0.18 s after speech ended are dropped.
3. Speech-to-text keeps listening through short silence (wake patience), reconnects its own link up
   to 2 times, and treats under 0.5 s as no speech. A follow-up window of 5 s opens after a reply
   ended less than 2 s ago.
4. The unit sends `listen` `stop` when it hears silence; the host closes its capture and (in
   realtime mode) answers `tts start`. For `start` and `detect` in realtime mode the host sends
   `tts start` at once.
5. Host speaks: `tts` `start`, 30 ms settle, optional `tts` `sentence_start`, then Opus packets: the
   first 3 back to back (15 ms gap), the rest paced at 60 ms; then `llm` `neutral`, then `tts`
   `stop`. A pre-roll of about 14 frames and a catch-up limit of 2 frames behind are used by the
   reply streamer.
6. Abort: unit `abort` (or a socket close) cancels capture, playback and the turn; host replies
   `tts` `stop`. A spoken stop phrase ends a reply the same way [from code: turn.py, stop_phrases.py,
   server.py].

Stray audio: six or more frames with no listen start, within 0.5 s of each other and within 120 s of
the last turn, begin a turn on their own [from code: turn.py].

The unit never receives an `stt` frame; the recognized text stays on the host [from code: server.py].

## 6. Telemetry (unit to host)

The unit does not push telemetry over the socket. The host polls the tool `self.robot.get_events`
every 0.5 s while awake and every 0.5 s asleep (touch poll); each call drains a list of event
objects, each with `kind` (string) and `at_ms` (int), plus small int, string or bool fields
[from code: companion.py, app.py].

Example reply text (inside the MCP result):

```json
[{"kind": "heap_stats", "at_ms": 812345, "int_free": 98304, "int_min": 71000},
 {"kind": "head_touch", "at_ms": 812900}]
```

Gesture events that cause behaviour: `head_touch`, `head_swipe_forward`, `head_swipe_back`, `shake`,
`level_changed` (adds `volume`, `brightness` percent).

Diagnostic kinds (logged, never a reason to react): `heap_stats`, `stack_stats`, `boot`
(carries `heal_n`, `heal_hold`, `heal_why`, `muted`, `quiet`, `mic_rms_max`), `wake_stats`, `wake`,
`fw` (`version`), `power_poll` (charger reading and flap count, once a minute), `touch_down`,
`touch_up`, `face_pressed`, `face_clicked`, `gesture`, `gesture_ignored`, `click_ignored`,
`head_touch_stats`, `stop_word`, `shake_peak`, `imu_stats`, `avatar_channel`, `tap`, `state_guard`,
`touch_path`, `camera`, `barge_stats`, `orientation`, `playback`, `wifi`, `offline_tap`,
`coredump`, `heal`, `wake_selftest`, `sound_played`, `tailnet_state` (`state`, `ip`), `wifi_use_ok`,
`wifi_use_revert` (hub unreachable 3 minutes), `privacy`, `privacy_refused`, `timer_fired`,
`timer_ended`, `timer_missed`, `music_feat`, `music_stats`, `music_clip_ready`,
`music_clip_cancelled`, and the update set `firmware_update_started`, `_progress` (`percent`),
`_done`, `_failed` (`reason`), `_validated` [from code: companion.py, self_heal.py,
firmware_update.py].

Battery and power: pulled, not pushed. `self.battery.get_status` returns `percent` 0 to 100 and
`charging`; any other shape is rejected as lost body. Host caches it for 5 s [from code: server.py,
dance_wiring.py].

### 6.4 HTTP side service

| Route | Caller | Rule |
|---|---|---|
| `POST /vision/{device_id}` | unit | multipart field `image`, `file` or `photo`, JPEG (starts `FF D8`), max 2 MiB; `Authorization: Bearer` or `?token=`; 401 or 403 on a bad token |
| `GET /notify/{device_id}/{audio_id}.ogg` | unit | bearer token; one read; `audio/ogg` |
| `GET /firmware/{device_id}/{token}` | unit | random one-time path, no auth, 10 minutes |
| `POST /robot/updating`, `/robot/updated` | Home backend | loopback, same origin, `application/json` |
| `GET /selftest/checks`, `POST /selftest/run` | local admin | loopback only |

[from code: server.py]

## 7. Pairing and tokens

1. An admin issues an enrollment code (random, 24-byte URL-safe, stored as SHA-256, valid 24 h by
   default, at most 32 live at once) and writes it into the unit's NVS as the token [from code:
   pairing.py, provision.py].
2. Unit connects with `Authorization: Bearer <code>`. The first hello reply returns `maipai_token`;
   the unit must store it in NVS at `websocket/token` and use it from then on. The code binds to the
   first `Device-Id` and `Client-Id` and is spent only when the real token authenticates once.
   Reconnecting with the code is allowed meanwhile for the same pair only [from code: server.py,
   pairing.py].
3. A unit with no valid token is recorded as a pending request (max 8, 10 minute life, at most 8
   requests per source address per 10 minutes, else close 1013) and closed with 1008; an admin
   approves its `Device-Id` and a token is provisioned [from code: server.py, pairing.py].
4. The host stores only the SHA-256 of tokens. Every incoming frame re-checks authorization; a
   revoked pairing closes the socket with 1008 [from code: pairing.py, server.py].

NVS keys written at provisioning: namespace `websocket` (`url`, `token`, `version` i32 = 1, and
`avatar_url`), `wifi/ota_url` (left empty), `board/uuid` (the Client-Id) [from code: provision.py].

## 8. Timings

| Item | Value | Source |
|---|---|---|
| Hello wait (voice) | 30 s idle timeout before hello | server.py |
| Hello wait (avatar) | 10 s; hello max 4096 bytes | avatar/server.py |
| WebSocket ping | every 20 s, 20 s timeout | server.py |
| Tool call timeout | 5 s | server.py |
| Event poll | 0.5 s | app.py |
| Camera start retry | every 5 s until the first frame; stall check every 5 s; re-ask at 60 s, reconnect (1012) next, then reboot request | avatar/server.py, self_heal.py |
| Watchdog | window 120 s; warn at 6 timeouts and more timeouts than answers; reboot request after 120 s of trouble or 60 s with no answer; at most one per 600 s | watchdog.py |
| Sound policy push | on change, else every 300 s; retry 5 s after a failure | sounds.py |
| Firmware update backoff | 6 h after failure; 15 min to see the new version | firmware_update.py |
| Reconnect | unit-side; the host replaces the old session with close 1012 at once | server.py |

## 9. Error cases and close codes

| Case | Result |
|---|---|
| Wrong `Protocol-Version` | close 1002 |
| Missing or malformed `Device-Id` or `Client-Id` | close 1008 |
| Not approved or bad token | pending request, close 1008 |
| Too many pairing requests | close 1013 |
| No hello before idle timeout | close 1001 |
| Superseded by a newer session | close 1012 |
| Pairing revoked mid-session | close 1008 |
| Frame over 1 MiB | close 1009 |
| Bad avatar path, hello, or frame | close 1008 or 1002 |
| Bad JSON, unknown type, repeat hello | `error` frame, session stays open |
| Tool timeout | host raises "did not answer"; watchdog counts it |
| Tool error text with "out of range" or "envelope" | out of envelope |
| Tool error text with "unknown tool" or "not supported" | not supported |

[from code: server.py, avatar/server.py, adapter.py]

## Open

1. No contract version field exists; hello carries only `version: 1`. The schema needs one.
2. Full list of `features` keys in the unit hello (only `notify` is read by the host).
3. Exact field lists of `heap_stats`, `stack_stats`, `power_poll` and most diagnostic events; only
   `fw.version`, `boot` heal fields and the update events are read by name.
4. Unit-side `listen` and `tts` behaviour (state machine, buffering) is in firmware, not host code.
5. Shape of `self.get_device_status`, `self.robot.get_reminders` and `self.privacy.get` replies.
6. Whether the unit sends `stt` or `llm` text frames to the host (the host ignores them if so).
7. Opus packet size limits from the unit (the host sets none).
8. Reconnect backoff schedule on the unit.
9. Sensor capability list for hello (battery, light, touch, tilt) is not advertised today.
10. Whether the 0xAA55 envelope still has any wire use (host-internal only per the code read).
11. Head speed units and exact yaw hardware limit (profile 128 degrees is a host limit).
