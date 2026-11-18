# Mouth cues for replies of more than one sentence

Status 2026-11-18: the host sends one list for a one-sentence reply. A longer reply sends none, because the unit (patch SF10) cannot take it.

## Why the host alone cannot do it
- The unit starts a list at the first audio frame of a turn (`mmc_start`) and keeps the mouth closed after its last cue. A list sent while speech is playing only goes pending: it does not play and the mouth falls back to the loudness.
- A reply is one paced stream, and the host does not have the audio of sentence 2 until sentence 1 is already playing. Holding the first audio until the whole reply is synthesized would add seconds before the robot speaks.

## Proposed unit change (firmware track, small)
Add an optional `append` flag to `self.face.mouth_cues`: `{"cues": "[[ms, level], ...]", "append": true}` adds the cues to the list that is playing, with `ms` counted from the same first audio frame of the speech, so the host sends one list per sentence as each is synthesized, with the times continuing from the audio already sent. Rules: each call keeps the existing checks (up to 160 cues, 12 in any second, times in order, level 0 to 4); the total across a speech stays within 60 s of span; an append whose first time is before the last time already held is refused with `bad_time`; the mouth closes after the last cue as today.

## Host half (built 2026-11-18, waits for the unit)
The unit announces `mouth_cues_append: true` in its hello features. The host asks `device_supports("mouth_cues_append", device)` per reply: a unit that says yes gets one list per sentence (the first as a new list, the next with `append` true, times continuing from the audio already queued, a closing cue clamped so times never go back, stopping at the 60 s span); a unit that does not keeps the one-sentence rule. Covered by `host/tests/test_mouth_cues_wiring.py`.

## Still to do
- Proof: the virtual unit's `self.face.mouth_cues` handler takes `append`, and the e2e scenario with a two-sentence reply checks two calls with continuing times.
