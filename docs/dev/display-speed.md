# Display speed: what the wire allows and where the rest goes (firmware track, 2026-11-19)

Question from the bench numbers: a flat 100 by 100 box costs 8,490 us (redraw plus flush), so a full 320 by 240 redraw is about 65 ms. **Measured** is from `self.game.bench_box` on the unit; **read** is from our tree or the ESP-IDF docs in `~/esp/esp-idf-6.1.1`; **not measured** needs an experiment below.

## The wire (read)

| Fact | Value | Source |
|---|---|---|
| Panel interface | SPI3, MOSI 37, SCLK 36, CS 3, DC 35, mode 2 | `main/hal/board/stackchan.cc` `InitializeSpi`, `InitializeIli9342Display` |
| Clock | 40 MHz, 16 bits a pixel | `io_config.pclk_hz = 40 MHz`, `bits_per_pixel = 16` |
| Wire time, pixels only | 0.4 us a pixel: **100x100 = 4.0 ms, 320x240 = 30.7 ms** | arithmetic |
| Can the clock go to 80 MHz? | **No, on these pins.** SPI3 pins go through the GPIO matrix, which allows only up to 40 MHz; 80 MHz needs IO_MUX pins | IDF `spi_master.rst`: "Allows signals with clock frequencies only up to 40 MHz, as opposed to 80 MHz if IO_MUX pins are used" |
| Draw buffers | two buffers of 10 lines (3,200 pixels, 6.4 KB each), in internal DMA RAM, `swap_bytes = 1`, partial refresh, `trans_size 0` | `main/hal/board/stackchan_display.cc` (patch V26) |
| Fx hook | skipped while a game or a full-screen page shows | `maipai_fx.cc` `post_to_flush` |

So the ceiling of this board is **30.7 ms for a full frame** (32 fps at best, with no drawing cost at all). The panel's own datasheet limit is not read here; 40 MHz is already what the maker ships.

## Where 8.5 ms goes for a 100x100 box (not measured; the wire is 4.0 ms)

A 100 wide area with a 3,200 pixel buffer is drawn in 4 strips of 32 rows, each a CASET, RASET and RAMWR then the pixels. The 4.5 ms above the wire is some mix of: the byte swap of every pixel on the CPU before the DMA (`swap_bytes = 1`), the fill itself, the per strip command overhead, the wait between a finished strip and the next free buffer, and the bench's own refresh and lock handling. Nothing in this list can be split from the numbers we have.

## Experiments, each one bench-only and measured with `bench_box` (flat 100x100, and a full 320x240 fill)

1. **Hardware byte swap**: set the panel's endianness (a command the ILI9341 family has, RGB565 byte order) and `swap_bytes = 0`: removes the CPU swap. Expected gain: small (about 0.1 to 0.3 ms per 10,000 pixels).
2. **Bigger strips**: draw buffers of 20 or 40 lines (12.8 or 25.6 KB each; internal RAM is the price, so the memory gate says how far): fewer commands, longer DMA runs. Expected gain: up to 1 ms on a full frame.
3. **Buffers in PSRAM** (`buff_spiram = 1`): frees internal RAM and allows full-frame buffers, but a PSRAM to SPI DMA is slower and shares the PSRAM bus with the camera and the audio; measure before using it.
4. **Draw once, flush less**: the biggest lever is not the speed but the **area**: SF78 already redraws only the moving area in the grid games (the 15 fps fall became 40 ms ticks). A game that redraws a whole board every tick cannot beat 30.7 ms however the driver is tuned.
5. **Transaction queue depth** (10 now) and the LVGL task priority (3): check the strips are not waiting for the CPU; read `FLUSH_WAIT_START` and `FLUSH_WAIT_FINISH` counts the face bench already collects.

Order to run them: 1 and 2 first (one small bench patch with a tool `self.bench.display_tune {buf_lines, hw_swap}` that rebuilds the display's buffers at run time), then 3, then read the flush wait counters for 5. Expected ceiling after all of that: about **45 to 50 ms for a full frame**, never below 30.7 ms; a 100x100 box can reach about 5.5 ms.

## What this means for the games

- Every full-board redraw costs 45 to 65 ms today; a dirty-rectangle redraw of a 100x100 area costs 8.5 ms (the box time).
- The richer Four in a Row look (UX26) stays out until its board redraw is dirty-rectangle only (docs/dev/games-footprint.md has the object costs; the bench's box times show gradient 9.3 ms, circle 9.9 ms, outline 10.1 ms, shadow 13 to 21 ms for 100x100).
- A faster driver helps everything by at most about a quarter; fewer pixels per tick helps by a factor of five or more.
