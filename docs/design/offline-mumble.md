# The offline mumble

Owner decision 24 (2026-11-18). When the robot has words to show but no voice to say them, it mumbles them: one short note for every character of the caption, timed to the caption, with the mouth moving to match. It is made from a rule and a small table, with no audio file, so it costs almost nothing and works in every language. Patch: `firmware/patches/UX16-offline-mumble-core.patch` (the pure C core and its tests). Listen to it: `python3 scripts/sounds-demo.py` then open <http://127.0.0.1:8796/> (six languages, each with its mouth drawn beside the player).

## When it plays

- The unit has a caption to show (the captions setting is on) and there is no voice for it: offline, or the speech service did not answer in time. With a voice, nothing changes.
- It is a sound like any other: mute, full quiet and quiet hours silence it, and the volume is the system volume. With the sound off the caption and the mouth still show.
- It starts when the caption appears and ends when the caption ends. A new caption replaces it.
- Off by default until the owner has listened to the samples and chosen (decision 24 asks for the words first; the setting is the firmware track's).

## The rule

The text is read as UTF-8, one slot per character. The slots share the caption's time equally (`slot i` runs from `start + span * i / n` to `start + span * (i + 1) / n`, in integers), so the mumble follows the caption timing whatever the speed.

| Character | Note | Mouth |
|---|---|---|
| Vowel a e i o u (accents fold: à é î õ ü, and æ œ) | A fixed low note each (0, 4, 9, 2, 7 semitones above 196 Hz), 90 percent of the slot, gliding up 2 semitones, full loudness | a 100, o 85, u 70, e 60, i 45 |
| Consonant (ç ñ ß fold to c n s), digit, any other script's letter | A short higher note from a five-note scale (picked by the letter), 60 percent of the slot, gliding down 1 semitone, loudness 55 | 30; 10 for b m p (the lips meet) |
| Space, comma, dash, quote, bracket | Rest | 0 |
| . ! ? and the Spanish inverted marks | Rest | 0 |
| Emoji and symbols | Rest | 0 |

The end of a sentence bends the last letters: a question rises 3, 5 and 7 semitones over its last three letters, a call lifts the last letter 2, a statement drops it 2. That is all the "intonation" there is; it is enough to tell a question from a statement without a word being understood.

All six languages (English, Spanish, French, German, Portuguese, Italian) are Latin script, so every letter has a note. Any other script maps by its character number and still mumbles. The same text always gives the same notes: the unit and the reference implementation agree note for note (`host/tests/test_mumble.py` compiles the core and compares them on all six sample sentences and an edge-case line).

## Mouth

Each note carries a mouth level (the table above). The caller sets the face's speak level to it at the note's start and to 0 at its end, the way it already does for a spoken voice; the face code is unchanged. The virtual unit does the same: `sim.mumble {text, ms}` (a rig control, not a firmware tool) moves the mouth on the fake clock. The filmstrip `host/tests/golden/screens/mumble-mouth-sync.png` shows nine slots of "Hello! I am".

## Cost

- No audio file, no table in flash beyond 45 frequencies (90 bytes) and a few small arrays.
- The state is one `mm_t` (about 40 bytes). `mm_next()` returns one note; the caller renders it into the 20 ms audio frame it already fills (16 kHz, 320 samples). Nothing is buffered beyond that frame.
- Time: a few microseconds a character (integer math, a scan to the end of the sentence for the inflection). No task of its own: it runs in the audio frame callback or the caption timer.

## What is in the patch and what is the firmware track's

In the patch: `maipai_mumble_core.h` (`mm_init`, `mm_next`), its test, the reference, the samples, the demo page, the virtual unit control.

The firmware track's: render each note (sine with a quarter triangle, a 5 ms attack and a 15 ms fall, from `f0` to `f1`, loudness scaled to the chime level) into the audio path; start it from the caption event with the caption's start and end times; set the mouth; the offline and no-voice conditions; the setting; the sound policy gate; the memory row. The reference renderer in `scripts/virtual-unit/mumble.py` is the sound to match.

## Samples and what is not proven

Six samples of about three seconds are in `docs/dev/mumble/` (8 kHz, 16 bit, 330 KB in all, CC0-1.0), made by `scripts/make-mumble-samples.py`. Nobody has listened to them except through their numbers (peak about -8 dBFS, about half the samples above a quiet threshold); the owner's ears decide the pitch, the length of the notes and whether the glides sound like a voice. If he wants it different, the tables at the top of `mumble.py` and the core change together and the test keeps them equal. Not proven on a unit: the sound through the speaker and the mouth timing against it.
