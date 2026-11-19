# What this display can do

One page for anyone designing a screen. It collects the bench's measured numbers, the rules that follow from them, and what the firmware track's work on the display speed has found so far. Last updated 2026-11-19 from the b80 and b85 bench results the coordinator forwarded; the numbers marked "open" change when the next ones arrive. The long versions: `docs/plan/games-visual-budget.md` (the budget and its rules), `docs/dev/display-speed.md` (the wire and the experiments).

## The numbers

| Fact | Value | How we know |
|---|---|---|
| Screen | 320 by 240 pixels, 16 bits a pixel | the panel |
| Wire | SPI at 40 MHz, 0.4 us a pixel: 100 by 100 is 4.0 ms, the whole screen 30.7 ms | arithmetic; 40 MHz is the most these pins allow |
| Measured, a flat 100 by 100 box drawn and flushed | **7.33 ms on the b85 image** (8.49 ms on b80) | `self.game.bench_box`, 2026-11-19 |
| Measured, a whole screen | **about 56 ms on b85 (65 ms on b80)**, so 15 to 18 frames a second at best; the game-over entry frame, which also draws a backdrop and two shadowed buttons, took 56 to 96 ms | the box time times 7.68; `self.game.bench_over` |
| Four in a Row, plain look, gap between ticks | median 40 to 44 ms, worst 81 ms on b80 and 109 ms on b85 (spikes to 92 ms on b80) | the same benches |

Draw time is small next to the flush: the flush of the pixels is almost all of the cost, and every separate rectangle is its own transfer, so **a screen that redraws many small rectangles in one frame costs more than their pixels say** (the first game-over motion, 18 confetti rectangles a frame, came out at about 42 ms a frame on the unit where the pixels predicted 4). Keep a frame to at most three rectangles. **Cost in milliseconds is the number of pixels redrawn times 0.73 per 1,000 (0.85 on b80), times the technique's factor below, plus a little for each rectangle.**

| One 100 by 100 box, drawn and flushed | b85 ms | Against flat | b80 ms |
|---|---:|---:|---:|
| Flat rectangle | 7.33 | 1.00 | 8.49 |
| Rounded corners | 7.4 | 1.01 | 9.08 |
| Circle | 9.3 | 1.27 | 9.88 |
| Vertical gradient | 9.0 | 1.23 | 9.32 |
| Alpha 50 percent | 9.7 | 1.32 | 9.80 |
| Outline | 10.5 | 1.43 | 10.13 |
| Soft shadow, blur 6 | 14.3 | 1.95 | 13.18 |
| Soft shadow, blur 14 | 21.8 | 2.97 | 20.88 |

Not measured yet: text, scaled text, rotation, squash (the budget has host-ratio estimates, marked as such).

## The rules

1. **A screen that moves redraws only what moves.** Each frame of a motion: at most 16,000 pixels worst and 6,500 on average (about 12 and 5 ms). Say which rectangles changed and invalidate only those; a test must show no pixel changed outside them.
2. **One slow frame is fine when a screen appears,** up to 100 ms, and never during play or a motion. A backdrop gradient and the shadows are drawn then and not again.
3. **After a tap, one frame may take up to about 60 ms.** A turn, a move, a shot, a pressed button.
4. **Shadows:** blur 6 only on things that never move, at most three on a screen; blur 14 only tiny (60 by 60 pixels at most) and still.
5. **Particles are small rectangles,** one per piece, about 100 pixels each, never a band across the area they cross. Slow parts (rain, a clock hand, a glint) move every 60 ms, not every 30.
6. **At most 15 LVGL objects and one draw callback** per game screen; no per-game pictures.
7. **A game that ticks has nothing to spare.** The plain Four in a Row already has a worst gap of 81 ms against a limit of 60, so a richer look for a board that redraws every tick does not fit this display as it flushes now.

## What fits, with the numbers

- A pong or flyer frame: 1,000 to 6,000 pixels, 1 to 5 ms. Fits.
- A game-over screen: one full frame at entry (56 to 96 ms measured), then at the light-motion look 2.4 ms a frame on average for under two seconds. Fits on the host; its bench is the check.
- A confetti burst of 8 pieces in two narrow columns: two rectangles of 36 by 72 pixels every 60 ms, about 2 ms a frame. Fits on the host; 18 separate piece-rectangles a frame did not fit on the unit.
- A whole board repainted with gradients and shadows every tick: 56 ms and more. Does not fit.

## The speed-up work (open)

The firmware track's reading (`docs/dev/display-speed.md`): the wire cannot go faster than 40 MHz on these pins, so a full frame can never take less than 30.7 ms; the 4.5 ms of a 100 by 100 box above the wire is unexplained (the byte swap on the processor, small draw buffers of 10 lines, the wait between strips, the bench's own handling). Five bench-only experiments are listed there: a hardware byte swap, bigger strips, buffers in PSRAM, the flush wait counters, and the queue depth. Expected after all of them: a full frame of 45 to 50 ms, a 100 by 100 box of about 5.5 ms. **Results: not in yet.** When they are, this page changes three things: the table of box times, the 0.73 ms per 1,000 pixels (`UNIT_BOX_US` in `scripts/virtual-unit/games_cost.py`), and rule 7, which is where the richer Four in a Row look would switch on (the activation rule is in `docs/plan/games-richer-look-bench.md`).

## Before you design a screen

1. Count the pixels that change per frame and multiply by 0.73 ms per 1,000 and by the technique factor, and count the rectangles (at most three). Over 12 ms in the worst frame or 5 ms on average: simplify.
2. Put everything that does not move in the first frame.
3. Add the screen's row to `scripts/virtual-unit/games_cost.py` and run it: the renderer counts the pixels and checks the rectangles.
4. Run the bench train for the screen and read the gaps and the entry frame against the gates in its manifest.
