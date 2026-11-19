# Face styles: what fits and what does not

Measured 2026-11-19 on the host renderer in dirty-area mode (`scripts/virtual-unit/face_style_cost.py`): each style stepped one 33 ms frame at a time for 4 seconds in four states, the pixels flushed in each frame kept. A frame costs 0.733 ms per 1,000 pixels (the bench's flat box, `UNIT_BOX_US` in `games_cost.py`). Nothing here is read on a unit; the cost row is an estimate from the bench constant.

**Rule used for a face:** mean at most 6,500 pixels a frame, worst frame at most 30 ms (40,900 pixels), one 33 ms step. The 16,000 pixel worst-frame rule is for game loops; the shipped default, Big eyes, already reaches 22,000 on a blink.

| Style | Neutral mean / worst px | Speaking mean / worst px | Surprised worst px | Worst frame ms | Verdict |
|---|---|---|---|---|---|
| Big eyes (base) | 3343 / 22386 | 3338 / 22386 | 30130 | 22.1 | fits, the reference |
| Stock (base) | 189 / 1620 | 189 / 1620 | 1620 | 3.4 | fits |
| Minimal (base) | 479 / 3150 | 479 / 3150 | 4408 | 3.2 | fits |
| Classic | 1890 / 9702 | 1890 / 9702 | 14804 | 10.9 | fits |
| Eyes only | 1942 / 14450 | 2103 / 15390 | 19902 | 14.6 | fits |
| Round | 2643 / 17250 | 2643 / 17250 | 22525 | 16.5 | fits |
| Cat | 1275 / 9522 | 1275 / 9522 | 13398 | 9.8 | fits |
| Robot | 858 / 9954 | 858 / 9954 | 13430 | 9.8 | fits |
| Sleepy | 1713 / 14442 | 1713 / 14442 | 19838 | 14.5 | fits |
| Pixel | 541 / 9798 | 541 / 9798 | 13746 | 10.1 | fits |
| Heart eyes | 0 / 0 | 0 / 0 | 0 | 0.0 | fits, with two parts left out (below) |
| Rubber hose | 3709 / 23750 | 3709 / 23750 | 28886 | 21.2 | fits, close to Big eyes |
| Neon anime | 2964 / 20806 | 2964 / 20806 | 28122 | 20.6 | fits, close to Big eyes |

Memory: no style costs anything until installed; see `docs/design/face-styles.md`. A style change is one full redraw (56 to 65 ms) for every style alike.

## What did not fit, and what was done

- **A beating heart eye.** The base Love face beats the hearts at 1.2 Hz. As a style that always beats, Heart eyes cost 22,000 pixels a frame on average and 50,000 on its worst frame (a full screen, 36 ms). The style keeps hearts that do not beat or blink; the Love mood in other styles is unchanged.
- **Heart drift.** With the gaze drift left on, Heart eyes still redrew both hearts every few frames (8,300 pixels mean). Drift is 0 in its recipe.
- **A glow made with a blurred shadow** (Neon anime). A blur of 14 costs 21.8 ms for a small box alone (`UNIT_BOX_US`). The glow is a wider translucent rounded box behind the ring instead.
- **Moving sparkles** (Neon anime). A twinkle redraws a rectangle every step. The four sparkles are still.
- **A film-grain or paper texture** (Rubber hose). A full-screen pattern is a 56 to 65 ms full redraw whenever anything moves. Not drawn.
- **Hands, gloves and noodle limbs** (Rubber hose). They need the body, which the face zone does not have. The look is carried by the eyes, grin, cheeks and tuft.

## Not proven

Run on a unit: the frame cost (K is the bench's constant), the internal RAM of the writable row and of a decorated style, installing a style through `self.assets.install`, and the first draw after a style change. The firmware track wires the install and applies the recipe; the patch only adds the reader, the row and the drawing.
