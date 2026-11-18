# Game sounds: loudness report

Made by `scripts/make-game-sounds.py`. Every sound is normalized to a peak of -10 dBFS (chime level) with a 2 ms fade at each end; none clips. Original work, CC0-1.0.

| Sound | What | ms | WAV bytes | mu-law bytes | Peak dBFS | RMS dBFS |
|---|---|---:|---:|---:|---:|---:|
| `chip_land_1` | a chip lands in row 1: a soft wooden clack, higher each row | 90 | 2,924 | 720 | -10.0 | -25.0 |
| `chip_land_2` | a chip lands in row 2: a soft wooden clack, higher each row | 90 | 2,924 | 720 | -10.0 | -25.2 |
| `chip_land_3` | a chip lands in row 3: a soft wooden clack, higher each row | 90 | 2,924 | 720 | -10.0 | -24.3 |
| `chip_land_4` | a chip lands in row 4: a soft wooden clack, higher each row | 90 | 2,924 | 720 | -10.0 | -24.1 |
| `chip_land_5` | a chip lands in row 5: a soft wooden clack, higher each row | 90 | 2,924 | 720 | -10.0 | -23.5 |
| `chip_land_6` | a chip lands in row 6: a soft wooden clack, higher each row | 90 | 2,924 | 720 | -10.9 | -24.7 |
| `drop_whoosh` | a chip starts to fall: a quick falling whoosh | 140 | 4,524 | 1,120 | -10.0 | -23.8 |
| `move_unit` | the robot's own move: a two note blip with a different (triangle) timbre | 150 | 4,844 | 1,200 | -10.0 | -19.8 |
| `win_fanfare` | a win: a short rising arpeggio | 250 | 8,044 | 2,000 | -10.0 | -19.3 |
| `lose` | a loss: a soft descending three notes | 240 | 7,724 | 1,920 | -10.0 | -18.3 |
| `draw` | a draw: two level notes | 220 | 7,084 | 1,760 | -10.0 | -19.1 |
| `illegal_thud` | an illegal move: a low short thud | 100 | 3,244 | 800 | -10.3 | -21.7 |
| `tap_tick` | a menu or board tap: a tiny tick | 30 | 1,004 | 240 | -10.7 | -23.5 |
| `flip` | a card flips: a quick rising sweep | 70 | 2,284 | 560 | -10.0 | -20.9 |
| `slide` | a tile slides: a short soft scrape | 90 | 2,924 | 720 | -10.0 | -23.2 |
| `pop` | something pops: a rising blip | 50 | 1,644 | 400 | -10.5 | -21.1 |
| `match_found` | a pair matches: two bright notes | 210 | 6,764 | 1,680 | -10.0 | -19.6 |
| `mine_flag` | a flag is planted: a small tick and a low blip | 110 | 3,564 | 880 | -10.0 | -19.4 |
| `hangman_ok` | a right letter: a gentle high note | 120 | 3,884 | 960 | -10.0 | -18.8 |
| `hangman_bad` | a wrong letter: a short low buzz | 140 | 4,524 | 1,120 | -10.0 | -16.9 |
