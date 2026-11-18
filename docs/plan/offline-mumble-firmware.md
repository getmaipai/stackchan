# Offline mumble voice: feasibility on the unit (firmware track, 2026-11-18)

Owner decision 24: with no voice model reachable the robot "talks" in short tones made from the caption text (no audio files), with the mouth moving to them. **Verdict: feasible, small, no new task.** **Measured** = read from the code or measured on the bench; **estimate** = to measure on the unit.

## What exists and is reused

| Piece | Where | What it gives |
|---|---|---|
| Code-made tones | `maipai_games_sfx_core.h`: `mgs_render` renders a list of tone segments (glide from one pitch to another, sine, square or triangle, a volume, up to 8 segments, 900 ms) to 16 kHz mono PCM, normalized to the shared peak (22,000 of 32,767, the loudness of the chimes) | the voice: one syllable is one to three segments. **Measured**: the nine grid sounds render to 45 to 520 ms and 720 to 8,320 samples |
| Playing PCM | `AudioService::PlayPcm(buf, n, 16000)` copies the buffer into the audio queue; the sound policy gate `maipai_sounds_gate("popup")` decides (mute, sounds off, quiet hours) and the system volume applies | playback with the household's mute rules for free |
| Mouth cues | `maipai_mouthcue_core.h`: a list of (time, level) cues per speech, at most 160 per call, 480 held, 12 in any second, appended lists join (`mmc_set`, `mmc_append`) | the mouth. A syllable rate of 4 to 7 a second fits under 12 cues a second with one cue per syllable |
| Captions | the caption path already receives the sentence text (`maipai_subtitles`) | the input text |
| Recorded phrases | 16 Ogg clips in the image (about 60 KB, `MAIPAI_OFFLINE_PHRASES`) and the household phrase pack | stay (below) |

## The design

A pure core `maipai_mumble_core.h` (plain C99, no allocation, host-tested) turns a sentence into a **syllable timeline**: the vowel groups of the text, with the number of syllables of each word estimated from vowels (a stable rule in every language of the six; no dictionary). Each syllable becomes one tone segment list:

- **Pitch:** a note of a fixed pentatonic scale chosen from the letters of the syllable (a hash, so the same word always sounds the same, which is what makes it read as a voice); a small glide up or down inside the syllable; the first letter of a sentence starts mid-range, a question mark lifts the last syllables, a full stop falls.
- **Timing:** 90 to 150 ms a syllable by vowel length, 60 ms between words, 180 ms at a comma, 320 ms at a sentence end.
- **Character:** a triangle wave for a warm, quiet timbre; the loudness follows the chime level and the sound policy, never above it; "excited" text (exclamation mark) a little higher and quicker, "sad" lower: the caption's emotion tag, which the unit already receives for the face, picks the base pitch.
- **Mouth:** one cue per syllable (level from the vowel: open for a, o; small for i, e), emitted with the same timeline, handed to `mmc_set` at the moment the first tone is queued so the mouth and the sound start together.

## Where it runs and what it costs

| | Cost | Basis |
|---|---|---|
| Flash | about 3 KB of code and a 0.3 KB table | estimate (the sound core's render is about 1.5 KB) |
| RAM while a sentence plays | one render buffer in PSRAM for the sentence, freed when it has been queued: 16 kHz x 2 bytes x seconds: a 3 second sentence is 96 KB, **too much for a block**, so it renders **a few syllables at a time** (about 0.5 s, 16 KB) and queues them as it goes | estimate; `PlayPcm` copies, so the buffer is reused |
| CPU | one syllable of 120 ms is 1,920 samples at about 50 cycles each: about 0.4 ms at 240 MHz | estimate |
| Tasks, timers | none: it runs on the application task (`Application::Schedule`) in slices of one chunk per 100 ms timer tick that already exists for captions; no new task, no PSRAM-stack task touches flash | design rule |
| Internal RAM | none persistent; no change to the largest block | design rule (decision 15) |

## Rules

- **Never in full quiet; silent when muted; the tone only at the chime level in quiet hours** (the same gate as every unit sound). A turn is capped at 20 seconds of mumble; a longer reply is shown as captions only after that.
- **Only when no host voice is available.** The host decides (it knows whether a voice model answered): it sends the text with a flag, or no audio; the unit never guesses. A turn with real audio never mumbles.
- **The mumble stops at once** on the wake word, the stop word, a touch that ends it, a new turn (as speech does today).
- **The camera cue, the lock and the limiter are untouched**; it moves nothing but the mouth.

## What stays recorded (real audio, not mumble)

1. The **offline-state phrases** ("no Wi-Fi", "Home not answering", "Home has not approved me", "connecting", "I'm back": 16 clips, in the image and the household phrase pack): they are the unit's words when it has no host, so they stay real.
2. **Alarms, timers and notification chimes** (tones and the shipped notification sounds): a sound a person must notice.
3. **Safety and care phrases**: anything the unit must say clearly with no host (low battery, the crisis handling of `docs/SAFETY.md`, the lock and pairing prompts) stays spoken audio or on-screen text. The mumble is for conversation, never for information a person needs to understand.

## Tests and proof

Host C test: the same text gives the same timeline; syllable counts for sample words in all six languages; the cue list obeys the 12-a-second and 160-cue limits for the longest allowed text; rendered buffers peak at the shared level and end in silence; a 20 second cap. On the unit: the mouth follows the tones within 40 ms; the bench frame recorder (SF75) and a silent render check; the owner listens to WAVs rendered by `scripts/sfx-wav.sh` from the same core before it is switched on. Not built yet; this note is the design and the budget.
