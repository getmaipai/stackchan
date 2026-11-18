# Game sounds: what the robot plays and the sketches

Two sets, to be heard side by side (the sounds page of the playground lists both):

- **On the robot** (`on-the-robot/*.wav`): rendered by the unit's own tone core (`maipai_games_sfx_core.h`, `mgs_render`) from its tone-segment table, with `scripts/render-unit-sounds.py`. These are the sounds the robot plays: the good, fanfare, bad, thud, rattle and ting clips, and the grid game clips of SF72 (`grid_tick_lo|mid|hi`, `grid_clack_lo|mid|hi`, `grid_drop`, `grid_lose`, `grid_draw`; rendered with `--patch` from the branch `fw/unproven` until SF72 is in the series). Each clip is a few tone segments (a start and an end pitch, a length, a wave, a level), normalized to a peak of 22,000 of 32,767.
- **Sketches** (`*.wav` here): twenty original sounds made by `scripts/make-game-sounds.py` with envelopes and a little noise (a wooden clack for the chips, a whoosh, a fanfare, and more). They are proposals: they cover sounds the tone table does not (flip, slide, pop, match, mine flag, hangman) and a richer chip clack.

**Cost.** The tone table is tiny: SF72 adds nine clips of sixteen segments, about 160 bytes of table and a few hundred bytes of names, rendered when played (no stored audio, no RAM held). The sketches as stored audio are 23.7 KB as 8 kHz mu-law for the twenty (about 1.2 KB each) or 95.6 KB as 16 kHz WAV, in flash or in the installed set (a sound pack slot), and they need a decoder path the table does not. If the owner prefers a sketch to a tone clip, the cost of that one sound is its 1 to 2 KB.

All sounds are original work released as CC0-1.0. Nobody has listened to the sketches except through their waveform numbers (`loudness.md`) and spectrograms (`spectrograms.png`).
