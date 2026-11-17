/* Host cost model for the overlays and effects (patches TA02, TA03). Runs every overlay for 30 simulated seconds, flushes only
 * the dirty rectangles as the unit does, counts what the draw would do, and turns that into a modelled time per second on the
 * unit. These are MODELLED numbers from counted work and stated constants; the measured ones need the unit.
 * cc -std=c99 -O1 -DMO_STATS -I<headers> fx_cost.c -lm */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "maipai_overlay_core.h"

/* Constants of the model. Stated, not measured: ESP32-S3 at 240 MHz, panel on SPI at 40 MHz, 16 bits a pixel. */
#define SPI_PX_PER_S 2500000.0      /* 40 MHz / 16 bits */
#define SPI_AREA_US 90.0            /* command and set-window overhead per flushed area */
#define LVGL_RENDER_US_PER_PX 0.02  /* LVGL software fill of the face under a dirty area, about 5 cycles a pixel */
#define LVGL_AREA_US 30.0           /* per area: invalidation, clipping, the draw task setup */
#define PUT_US 0.15                 /* one blended overlay pixel, about 36 cycles */
#define MODE_US_PER_PX 0.058        /* colour mode: luma and a ramp lookup, about 14 cycles */
#define NIGHT_US_PER_PX 0.021       /* night dim: about 5 cycles */
#define CRT_US_PER_PX 0.0125        /* scanlines: 6 cycles on half the rows */

static uint16_t tile[MO_W * MO_H];

typedef struct { double flush_px, areas, puts, render_px; double max_px; } acc_t;

/* One scenario (a single overlay or a preset) for 30 simulated seconds at a given particle share; the dirty rectangles of all
 * the layers are flushed together as the unit does (strips of 20 rows), and the draw runs once per strip. */
static void run(int id, int inten, int pct, acc_t* a)
{
    static mo_layer_t L[MO_LAYERS];
    memset(L, 0, sizeof L);
    mo_set(L, id, inten, 0, 777);
    for (int l = 0; l < MO_LAYERS; l++) L[l].pct = (uint8_t)pct;
    memset(a, 0, sizeof *a);
    const int ticks = 900; /* 30 s */
    for (int t = 0; t < ticks; t++) {
        double px_tick = 0;
        for (int l = 0; l < MO_LAYERS; l++) {
            mo_step(&L[l], 33);
            mo_rect_t r[MO_MAX_DIRTY];
            const int n = mo_take_dirty(&L[l], r);
            for (int k = 0; k < n; k++) {
                const int w = r[k].x2 - r[k].x1 + 1;
                for (int y0 = r[k].y1; y0 <= r[k].y2; y0 += 20) {
                    const int y2 = (y0 + 19 < r[k].y2) ? y0 + 19 : r[k].y2;
                    const double px = (double)w * (double)(y2 - y0 + 1);
                    memset(tile, 0, sizeof(uint16_t) * (size_t)w * (size_t)(y2 - y0 + 1)); /* a fresh face under the strip */
                    mc_t c = mc_make(tile, r[k].x1, y0, r[k].x2, y2, 0, 0);
                    const unsigned long before = mo_stat_puts;
                    mo_draw_all(L, &c);
                    a->puts += (double)(mo_stat_puts - before);
                    a->flush_px += px;
                    a->areas += 1;
                    px_tick += px;
                }
            }
        }
        if (px_tick > a->max_px) a->max_px = px_tick;
    }
}

static void report(const char* name, int id, int inten)
{
    acc_t full, shed;
    run(id, inten, 100, &full);
    run(id, inten, 50, &shed);
    const int ticks = 900;
    const double secs = ticks / 30.0;
    const double f_full = (full.flush_px / SPI_PX_PER_S + full.areas * SPI_AREA_US / 1e6) / secs;
    const double f_shed = (shed.flush_px / SPI_PX_PER_S + shed.areas * SPI_AREA_US / 1e6) / secs;
    const double cpu_ms = (full.flush_px * LVGL_RENDER_US_PER_PX + full.areas * LVGL_AREA_US + full.puts * PUT_US) / 1000.0 / secs;
    const char* verdict = f_full < 0.25 ? "ok" : (f_full < 0.50 ? "heavy: watch" : "over: governor sheds");
    printf("%-10s %5d | %9.0f %9.0f | %7.1f %8.0f | %7.1f%% %7.1f%% %8.1f | %s\n", name, inten, full.flush_px / ticks, full.max_px, full.areas / ticks,
           full.puts / ticks, f_full * 100.0, f_shed * 100.0, cpu_ms, verdict);
}

int main(void)
{
    printf("%-10s %5s | %9s %9s | %7s %8s | %8s %8s %8s | %s\n", "overlay", "level", "px/tick", "max px", "areas", "puts/tick", "SPI %", "SPI % @50", "CPU ms/s", "verdict");
    for (int id = 1; id < MO_COUNT; id++) {
        for (int inten = 2; inten <= 3; inten++) report(MO_NAMES[id], id, inten);
    }
    for (int pi = 0; pi < MOP_COUNT; pi++) {
        for (int inten = 2; inten <= 3; inten++) report(MOP_NAMES[pi], MO_PRESET_BASE + pi, inten);
    }

    printf("\nEffects, per flushed pixel (modelled): colour mode %.3f us, night dim %.3f us, scanlines %.4f us on average.\n", MODE_US_PER_PX,
           NIGHT_US_PER_PX, CRT_US_PER_PX);
    printf("A full 320x240 frame with every effect: %.1f ms of CPU (a full frame is %.1f ms of SPI, and never flushed at once).\n",
           76800.0 * (MODE_US_PER_PX + NIGHT_US_PER_PX + CRT_US_PER_PX) / 1000.0, 76800.0 / SPI_PX_PER_S * 1000.0);
    const double mouth = 120.0 * 50.0, eyes = 2.0 * 56.0 * 56.0; /* a speaking frame redraws about the mouth box and sometimes the eyes */
    printf("A speaking frame (mouth box %.0f px, eyes %.0f px): effects add %.2f ms (mouth) to %.2f ms (mouth and eyes) of CPU.\n", mouth, eyes,
           mouth * (MODE_US_PER_PX + NIGHT_US_PER_PX + CRT_US_PER_PX) / 1000.0, (mouth + eyes) * (MODE_US_PER_PX + NIGHT_US_PER_PX + CRT_US_PER_PX) / 1000.0);
    return 0;
}
