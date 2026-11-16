# Voice path: connections, model options, measurements and the low-latency design (2026-11-16)

Placement: design and measurement note for an outside technical review. Facts are marked [measured], [from code] or [estimate]. Nothing here is a claim about a finished product.

## 1. The system in one picture

```
 StackChan unit (ESP32-S3, 16 MB flash, 8 MB PSRAM, mic, speaker, 320x240 screen, servos, LED ring)
   wake word + stop word on the unit (offline), Opus encode/decode, face and light cues, touch, IMU
        |  one persistent WebSocket (TCP, keepalive, NODELAY), JSON control + binary Opus
        v
 Host (Python, runs on a Mac or Linux box on the home network)
   :8765 voice socket   :8766 avatar/camera socket   :8767 HTTP (photos, notify audio)
   turn engine: speech-to-text (STT) -> brain (language model) -> text-to-speech (TTS) -> Opus -> unit
        |                         |                           |
   STT service              Brain adapter                 TTS service
```

The unit is complete without the host for wake, stop, mute, timers, faces and cues. The host does the heavy language work.

## 2. Unit link and audio format [from code]

| Direction | Codec | Rate | Frame | Notes |
|---|---|---|---|---|
| unit to host (microphone) | Opus | 16 kHz mono | 60 ms | host decodes and resamples to 16 kHz float |
| host to unit (speech) | Opus, voip mode | 24 kHz mono | 60 ms (1440 samples) | 24 kbps, cutoff 8 kHz, one frame per packet |

- Control messages are JSON over the same socket: hello (advertises audio params and features), listen start/stop (mode, aec), stt text, llm emotion, tts start/sentence/stop, tool calls (MCP-style tools for head, LEDs, volume, screen, faces, timers, games, privacy).
- The host sends the first 3 speech frames back to back (15 ms gap), then paces at 60 ms.
- Persistent connection: no handshake per turn. Heartbeat every 20 s. The unit keeps Wi-Fi power save off during a turn.

## 3. Brain options (what answers) [from code: host/robot.example.toml]

`brain = "llm"` (standalone) or `brain = "home"` (the household hub).

1. **Own model, `brain = "llm"`:** any OpenAI-compatible chat-completions endpoint (`[llm] url`, `model`, optional key from an env var name, persona prompt, timeout, history length). The host appends `/v1/chat/completions` and requests `stream=true` (SSE). A per-unit table can give each robot its own model and persona.
2. **Household hub, `brain = "home"`:** the hub's own turn API with persona, memory and tools; it streams `delta` events per token. The host also reaches the hub's chat endpoint with a scoped, revocable key (`turn` scope) for plain chat.
3. **Speech services:** `stt_url` and `tts_url` (HTTP) can point to local engines. The host also has a built-in local-speech client. Today's local engines: Moonshine (tiny) for STT and Piper (lessac) for TTS, both on the CPU. The older path used the hub's own speech engines, which require the hub's credentials.
4. **Local-only commands** (stop, quieter, louder, timer, time, mute) run with no model and no network round trip; the unit's command spotter handles stop and mute offline.

Mood and effect tags: the reply may start with a tag from a fixed list ([happy], [sad], [surprised], ...); the host strips tags before speech and sets the face. Weather and similar overlays use the same tag grammar.

## 4. The turn, stage by stage

1. Wake word fires on the unit (wakenet, offline). Cue (sound, light, face) from preloaded samples, before any network step. Pre-roll of about 500 ms of audio is kept so the first words are not clipped.
2. Unit streams Opus frames to the host while the person speaks.
3. Host: voice activity detection and end-of-speech timer (today 0.75 s of silence), partial transcripts, noise gate (drops steady noise, very short sounds, known noise phrases), echo guard (ignores the microphone for 0.9 s after the unit speaks).
4. STT final transcript.
5. Local command router (exact phrase and confidence of at least 0.8) or the brain.
6. Brain streams tokens. The host cuts the stream into sentences and sends each finished sentence to TTS immediately (new, 2026-11-16).
7. TTS audio is Opus-encoded in 60 ms frames and streamed to the unit; the unit plays while the next sentence is synthesised.
8. Barge-in: the wake word or a touch stops playback and cancels the in-flight turn.

## 5. Measurements

Old hub path, from the earlier base [measured, hub side]:

| Stage | Median | p95 |
|---|---|---|
| end of speech to final transcript | 750 ms | 823 ms (this is the silence timer) |
| final transcript to first model token | 1.53 s | 3.9 s (warm 0.7 to 1.3 s, cold 3 to 4 s) |
| sentence text to first speech audio | 0.7 to 1.4 s | |
| unit round trip, radio asleep | 280 to 400 ms | 1.3 s peaks |

New host, fake unit, same Mac [measured 2026-11-16, while the Mac was also rendering video]:

| Step | Time |
|---|---|
| STT (Moonshine tiny, CPU) | 0.03 s |
| household model, one block reply | 13.7 s (direct call 11.4 s) |
| TTS (Piper, CPU) | 0.1 s |
| first audio after end of speech, whole-reply path | 14.7 s |
| short utterances ("I'm tired"): chat 1.5 to 1.8 s, first audio after end of speech | 2.4 s |
| host reply frames | 60 ms steady, max 61 ms, none over 150 ms |

Conclusion so far: on the host the speech services are fast; nearly all delay is the language model (time to first token and total length), and it rises sharply when the GPU is shared with video work. The speech frames themselves are smooth on the host.

Unit-side: an A/B against the owner's original firmware image (same host) is in progress; results are not in yet.

## 6. Design for least latency

On the unit (no host in the path):
- Wake cue from a preloaded sample before any network step; target under 150 ms after the phrase ends.
- Persistent connection, TCP_NODELAY, keepalive; Wi-Fi power save off during a turn; no logging, flash or NVS writes in the turn's hot path.
- Barge-in stops playback in under 200 ms and flushes the queue.
- Audio, microphone and servo tasks outrank animation; animation sheds load (particles, glow, scanlines) when frames run late.
- Filler cue (tone, or a cached non-word sound or short phrase) only if no audio within a set delay (default 400 ms); options none, tone, phrase.

On the host (in parallel with the person speaking):
1. Stream the reply and speak sentence by sentence (done). Expected gain 0.5 to 3 s on long replies [estimate].
2. Adaptive end-of-speech: cut the silence timer from 750 to about 400 ms with a completeness check so mid-clause pauses are not cut. About 300 to 400 ms saved [estimate].
3. Speculative start: send the partial transcript to the model before end of speech is certain; cancel on mismatch.
4. Keep model connections alive; cache the persona prompt prefix; keep the persona short; ask for a short first sentence.
5. Route routine turns to a small fast model, hard ones to the large model.
6. TTS: small first chunk (first sentence), warm engine, pre-synthesised acknowledgements for common replies.
7. Opus frame size: test 20 and 40 ms against the current 60 ms (saves 20 to 40 ms each way; risk: choppiness).
8. Resource priority: voice turns first, then images, then video; never run a heavy GPU job during a voice turn.
9. Local commands (timer, volume, mute, stop) skip the model entirely.

Rough sum with the fixes: about 1.35 s from end of speech to first audio [estimate]; a 1.0 s median needs a cached opener.

## 7. Known problems and what is being checked

- Owner reports stutter and about 3 s response on the unit. Candidates under test: the echo canceller set to learn room sound (the original firmware turned it off), the stop-word model's task stack placed in PSRAM (the original moved it to internal RAM after 30 to 45 s stalls), a wake word detected but dropped on the persistent socket, faster face redraw competing with audio, trimmed TLS certificate list, buffers moved to PSRAM.
- False triggers on fan noise: host noise gate plus wake and VAD thresholds on the unit (under test).
- A wrong reply once told the time for "I'm tired": the host's local command matcher cannot produce it (full-phrase match); suspected speech-to-text mishearing in the older path. Now logged per utterance with engine, confidence and route.

## 8. Questions for an outside reviewer

1. Is a 400 ms silence hangover with a completeness check the right end-of-speech design for a home robot, or should a semantic turn-detector replace the timer?
2. Speculative model calls on partial transcripts: worth the extra load on a shared home GPU?
3. For a 16 kHz uplink and 24 kHz downlink, are 20 ms Opus frames over Wi-Fi worth the jitter risk compared with 60 ms?
4. Best split between a small fast model for routine turns and a large model for hard ones, and how to route without a classifier round trip.
5. Filler sounds: how long a delay before a filler feels natural rather than intrusive?
6. Anything in the unit-side design that adds avoidable delay.
