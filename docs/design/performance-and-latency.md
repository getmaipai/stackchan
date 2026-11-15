# Performance and latency

Principle: the unit reacts at once from its own hardware. The host works in parallel with the person speaking.
Hub-side numbers below were measured. Robot end-to-end timing does not exist yet, so unit figures are estimates (E).

## Instant on the unit (no host in the path)

1. Wake tone and listening cue fire from the wake callback, from a preloaded sample, before any network step. The ring and face change in the same instant.
   Today the tone is sequenced behind state changes. Target: under 150 ms after the phrase ends.
2. The first tone of a turn is never held back by the tone rate limit.
3. The local command set (stop, mute, quiet, don't move, volume, brightness, timers) acts with no host and no model.
4. Barge-in: speech stops the instant the wake word or a touch arrives. Flush the playback queue.
5. Pre-roll: keep about 500 ms of audio before the wake word so the first words are not clipped.
6. Persistent connection with TCP_NODELAY and keepalive. No handshake per turn. Heartbeats every 20 s against idle drops.
7. Radio power lease: awake from wake detection to end of turn, asleep when idle. Saves 100 to 300 ms (E).
8. Hot path stays clean: no logging, NVS or flash writes during a turn.
9. Thinking cue within about 300 ms of end of speech: dots, ring chase, quiet tone.

## Parallel on the host

10. Stream audio from the first frame so a transcript forms while the person talks.
11. Smart end-of-speech: shorter, adaptive silence timer plus a completeness check. Saves 300 to 400 ms (E). Today the timer is 0.75 s.
12. Stream the reply and speak by sentence. Today the host drains the whole turn before the first speech call.
    Start speech on the first complete sentence. Saves 0.5 to 3 s on longer replies (E). Safety and age gates, where a brain has them, run per sentence.
13. Keep the model warm and reuse the cached system prompt. Ask for a short first sentence.
14. A small fast model for chat, a bigger one on request. Show time to first token in the web app.
15. Pre-synthesised acknowledgements and confirmations play instantly.
16. Robot controls (timer, volume, mute, camera) skip the model through a command grammar. It never filters normal conversation.
17. Opus frames: 60 ms today. Test 20 or 40 ms for 20 to 40 ms saved each way. Choppiness risk.
18. Prebuffer and settle: tighten the 3 frame, 15 ms prebuffer and 30 ms settle after measuring. About 50 ms (E).
19. Guard against buffering a whole pitch-shifted sentence before sending.

## Measured chain on the hub (old base)

| Stage | Number |
|---|---|
| End of speech to final transcript | 750 ms median, 823 ms p95 (this is the silence timer) |
| Final transcript to first model token | 1.53 s median, 3.9 s p95 (warm 0.7 to 1.3 s, cold 3 to 4 s) |
| Sentence text to first speech audio | 0.7 to 1.4 s |
| Unit round trip with radio asleep | 280 to 400 ms average, 1.3 s peaks |

Wake detection after the phrase ends is an estimate of 200 to 400 ms.

## Measure it

Timestamps per turn, one `turn_id` on everything, one clock offset measured at hello:
wake detected, tone started, listen start at the host, first uplink frame, end of speech, final transcript, first token,
first sentence, first speech byte, first frame sent, first frame played, abort sent, silence on the unit.
Show p50 and p95 per stage in the web diagnostics and the host log. Tag each record with its surface.
A fixed spoken script runs as a regression check. No stage's p95 may get worse (the latency gate).
Ship a timing tool and publish measured numbers with the hardware and model versions used.

## Targets

- Wake tone and listening cue: under 150 ms.
- Interrupt stop: under 200 ms.
- Local command: under 300 ms from the last word.
- End of speech to first audio: under 1.0 s median, under 2.0 s p95, on a typical local setup with a small fast model and streaming speech.
- Rough sum with the fixes: about 1.35 s (E). A 1.0 s median needs a cached opener.
- Honest limit: this depends on the owner's hardware and models. The design only guarantees no avoidable delay is added.
  A 4B class model reaches a first token under 400 ms warm. A 27B class model on the current machine does not.

## Open

- Whether power-save off brings back the mesh access point SYN-ACK failure.
- Whether 20 ms Opus frames decode in time on the new base.
- Robot end-to-end baseline (needs the unit awake).
- Wake tone leaking into the mic when played from the callback.
