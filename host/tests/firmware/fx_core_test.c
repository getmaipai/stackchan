/* Host test for the screen effects and the governor (patches TA02, TA05): scanline row math, split invariance, colour modes,
 * night dim, glow only on background, the governor ladder. cc -std=c99 -Wall -Wextra -Werror -I<headers> fx_core_test.c -lm */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "maipai_fx_core.h"

static int fails;
#define CHECK(c)                                                \
    do {                                                        \
        if (!(c)) {                                             \
            printf("FAIL line %d: %s\n", __LINE__, #c);         \
            fails++;                                            \
        }                                                       \
    } while (0)

static uint16_t* make_screen(uint16_t bg, uint16_t fg)
{
    uint16_t* s = malloc(sizeof(uint16_t) * MFX_W * MFX_H);
    for (int y = 0; y < MFX_H; y++)
        for (int x = 0; x < MFX_W; x++) {
            const int in_eye = (x - 100) * (x - 100) + (y - 92) * (y - 92) < 24 * 24;
            s[y * MFX_W + x] = in_eye ? fg : bg;
        }
    return s;
}

static void post_in_strips(const mfx_t* f, uint16_t* screen, int strip)
{
    uint16_t* buf = malloc(sizeof(uint16_t) * MFX_W * strip);
    for (int y = 0; y < MFX_H; y += strip) {
        const int h = (y + strip <= MFX_H) ? strip : MFX_H - y;
        memcpy(buf, screen + (size_t)y * MFX_W, sizeof(uint16_t) * MFX_W * (size_t)h);
        mfx_post(f, buf, 0, y, MFX_W - 1, y + h - 1);
        memcpy(screen + (size_t)y * MFX_W, buf, sizeof(uint16_t) * MFX_W * (size_t)h);
    }
    free(buf);
}

static void test_scanline_rows(void)
{
    CHECK(!mfx_row_dark(0) && mfx_row_dark(1) && !mfx_row_dark(2) && mfx_row_dark(239));
    mfx_t f;
    memset(&f, 0, sizeof f);
    f.crt = 1;
    uint16_t* s = make_screen(mfx_rgb(40, 40, 40), 0xFFFF);
    mfx_post(&f, s, 0, 0, MFX_W - 1, MFX_H - 1);
    CHECK(s[0 * MFX_W + 5] == mfx_rgb(40, 40, 40));          /* an even row is untouched */
    CHECK(s[1 * MFX_W + 5] == mfx_five_eighths(mfx_rgb(40, 40, 40))); /* an odd row is at five eighths */
    CHECK(s[92 * MFX_W + 100] == 0xFFFF && s[93 * MFX_W + 100] == mfx_five_eighths(0xFFFF));
    /* five eighths of white: every channel between 55 and 70 percent */
    const uint16_t w = mfx_five_eighths(0xFFFF);
    CHECK((w >> 11) >= 17 && (w >> 11) <= 20 && ((w >> 5) & 63) >= 34 && ((w >> 5) & 63) <= 41 && (w & 31) >= 17 && (w & 31) <= 20);
    free(s);
}

static void test_split_invariance(void)
{
    /* LVGL flushes 20-row strips, a blink flushes a small box: the result must not depend on the split */
    mfx_t f;
    memset(&f, 0, sizeof f);
    f.crt = 1;
    f.night = 1;
    mfx_set_mode(&f, 4);
    static uint8_t mask[MFX_GLOW_MAX_SIDE * MFX_GLOW_MAX_SIDE];
    f.gside = mfx_glow_bake(mask, 48);
    f.gmask = mask;
    f.glow  = 1;
    f.gx[0] = 100 - f.gside / 2;
    f.gx[1] = 220 - f.gside / 2;
    f.gy    = 92 - f.gside / 2;
    f.gcol  = 0xFFFF;
    uint16_t* whole = make_screen(mfx_rgb(20, 20, 40), 0xFFFF);
    uint16_t* split = make_screen(mfx_rgb(20, 20, 40), 0xFFFF);
    mfx_post(&f, whole, 0, 0, MFX_W - 1, MFX_H - 1);
    post_in_strips(&f, split, 20);
    CHECK(memcmp(whole, split, sizeof(uint16_t) * MFX_W * MFX_H) == 0);
    uint16_t* seven = make_screen(mfx_rgb(20, 20, 40), 0xFFFF);
    post_in_strips(&f, seven, 7);
    CHECK(memcmp(whole, seven, sizeof(uint16_t) * MFX_W * MFX_H) == 0);
    free(whole); free(split); free(seven);
    /* an odd-sized box in the middle matches the same pixels of the whole */
    uint16_t* a = make_screen(mfx_rgb(20, 20, 40), 0xFFFF);
    uint16_t* b = make_screen(mfx_rgb(20, 20, 40), 0xFFFF);
    mfx_post(&f, a, 0, 0, MFX_W - 1, MFX_H - 1);
    uint16_t box[31 * 17];
    for (int y = 0; y < 17; y++) memcpy(box + y * 31, b + (size_t)(61 + y) * MFX_W + 77, 31 * sizeof(uint16_t));
    mfx_post(&f, box, 77, 61, 107, 77);
    int same = 1;
    for (int y = 0; y < 17; y++)
        for (int x = 0; x < 31; x++) same &= box[y * 31 + x] == a[(size_t)(61 + y) * MFX_W + 77 + x];
    CHECK(same);
    free(a); free(b);
}

static void test_colour_modes(void)
{
    uint16_t ramp[32];
    for (int m = 1; m < MFX_CM_COUNT; m++) {
        mfx_ramp_build(m, ramp);
        for (int i = 1; i < 32; i++) CHECK(mfx_luma5(ramp[i]) >= mfx_luma5(ramp[i - 1])); /* brighter in, brighter out */
    }
    mfx_t f;
    memset(&f, 0, sizeof f);
    mfx_set_mode(&f, 1); /* mono */
    uint16_t px[3] = {mfx_rgb(255, 0, 0), 0xFFFF, 0x0000};
    mfx_post(&f, px, 0, 0, 2, 0);
    CHECK(((px[1] >> 11) << 1) >= 60 && px[2] == 0);
    for (int i = 0; i < 2; i++) { /* a grey: the three channels agree to within the 565 steps */
        const int r = (px[i] >> 11) << 3, g = ((px[i] >> 5) & 63) << 2, b = (px[i] & 31) << 3;
        CHECK(abs(r - g) <= 8 && abs(g - b) <= 8);
    }
    mfx_set_mode(&f, 5); /* amber: white becomes amber, no blue */
    uint16_t w = 0xFFFF;
    mfx_post(&f, &w, 0, 0, 0, 0);
    CHECK((w >> 11) >= 30 && ((w >> 5) & 63) > 40 && (w & 31) <= 2);
    mfx_set_mode(&f, 6); /* green: green dominates */
    w = 0xFFFF;
    mfx_post(&f, &w, 0, 0, 0, 0);
    CHECK(((w >> 5) & 63) > (w >> 11) * 2 && ((w >> 5) & 63) > (w & 31) * 2);
    mfx_set_mode(&f, 4); /* duotone: black is not black (deep blue), white is peach: two colours, not one */
    uint16_t pair[2] = {0, 0xFFFF};
    mfx_post(&f, pair, 0, 0, 1, 0);
    CHECK(pair[0] != 0 && (pair[0] & 31) > (pair[0] >> 11) && (pair[1] >> 11) > (pair[1] & 31));
    mfx_set_mode(&f, 0); /* normal: nothing changes */
    uint16_t same[2] = {0x1234, 0xABCD};
    CHECK(!mfx_any(&f));
    mfx_post(&f, same, 0, 0, 1, 0);
    CHECK(same[0] == 0x1234 && same[1] == 0xABCD);
    mfx_set_mode(&f, 99); /* out of range: normal */
    CHECK(f.mode == 0);
}

static void test_night(void)
{
    mfx_t f;
    memset(&f, 0, sizeof f);
    f.night = 1;
    uint16_t px[2] = {0xFFFF, mfx_rgb(200, 100, 40)};
    mfx_post(&f, px, 0, 0, 1, 0);
    CHECK(px[0] == 0x7BEF); /* white halves to 15/31 and 31/63 */
    CHECK(((px[1] >> 11) << 3) >= 90 && ((px[1] >> 11) << 3) <= 104);
}

static void test_glow(void)
{
    static uint8_t mask[MFX_GLOW_MAX_SIDE * MFX_GLOW_MAX_SIDE];
    const int side = mfx_glow_bake(mask, 48);
    CHECK(side == 2 * (24 + MFX_GLOW_HALO) + 1 && side <= MFX_GLOW_MAX_SIDE);
    CHECK(mask[(side / 2) * side + side / 2] == 0);            /* deep inside the eye: nothing */
    CHECK(mask[(side / 2) * side + side / 2 + 24 - MFX_GLOW_INSET] >= MFX_GLOW_PEAK - 4); /* where the halo starts, under the eye's edge: the peak */
    CHECK(mask[(side / 2) * side + side / 2 + 24] > 40 && mask[(side / 2) * side + side / 2 + 24] < MFX_GLOW_PEAK); /* at the edge: lower */
    CHECK(mask[(side / 2) * side + side / 2 + 24 + MFX_GLOW_HALO] == 0); /* beyond the rim: nothing */
    CHECK(mask[(side / 2) * side + side / 2 + 24 + 7] > 0 && mask[(side / 2) * side + side / 2 + 24 + 7] < mask[(side / 2) * side + side / 2 + 25]);
    CHECK(mask[(side / 2) * side + side / 2 + 24 + 6] > mask[(side / 2) * side + side / 2 + 24 + 7]); /* falls off steadily */
    for (int i = 0; i < side; i++) { /* symmetric */
        CHECK(mask[(side / 2) * side + i] == mask[(side / 2) * side + side - 1 - i]);
        CHECK(mask[i * side + side / 2] == mask[(side - 1 - i) * side + side / 2]);
    }
    /* total bytes: the mask is the only memory the glow needs */
    CHECK((size_t)side * (size_t)side <= 6241);
    mfx_t f;
    memset(&f, 0, sizeof f);
    f.glow  = 1;
    f.gmask = mask;
    f.gside = side;
    f.gx[0] = 100 - side / 2;
    f.gx[1] = 1000; /* the right eye is off screen here */
    f.gy    = 92 - side / 2;
    f.gcol  = 0xFFFF;
    const uint16_t bg = mfx_rgb(8, 8, 24);
    uint16_t* s       = make_screen(bg, 0xFFFF);
    mfx_post(&f, s, 0, 0, MFX_W - 1, MFX_H - 1);
    CHECK(s[92 * MFX_W + 100] == 0xFFFF);                 /* the eye itself is untouched */
    CHECK(s[92 * MFX_W + 100 + 28] != bg);                /* just outside the eye: lit */
    CHECK(mfx_luma5(s[92 * MFX_W + 100 + 26]) > mfx_luma5(s[92 * MFX_W + 100 + 34])); /* falls off */
    CHECK(s[92 * MFX_W + 100 + 24 + MFX_GLOW_HALO + 2] == bg); /* beyond the rim: untouched */
    CHECK(s[5 * MFX_W + 5] == bg);                        /* far away: untouched */
    /* a pixel that is not background (a bright pixel in the halo ring, such as a mouth or a bubble) is left alone */
    uint16_t* t = make_screen(bg, 0xFFFF);
    t[92 * MFX_W + 100 + 28] = mfx_rgb(255, 200, 0);
    mfx_post(&f, t, 0, 0, MFX_W - 1, MFX_H - 1);
    CHECK(t[92 * MFX_W + 100 + 28] == mfx_rgb(255, 200, 0));
    free(s); free(t);
    /* an area that only clips the halo does not write outside its buffer: a one-pixel-wide strip on the edge */
    uint16_t strip[10];
    for (int i = 0; i < 10; i++) strip[i] = bg;
    mfx_post(&f, strip, 124, 85, 124, 94);
    CHECK(strip[0] == bg || strip[0] != bg); /* ran to the end without a crash (checked under -fsanitize in the build) */
}

/* Feeds n frames of frame_us each at 33 ms apart; returns the number of level changes. */
static int feed(mg_t* g, uint32_t* t, int n, uint32_t frame_us)
{
    int ch = 0;
    for (int i = 0; i < n; i++) { *t += 33; ch += mg_feed(g, *t, frame_us); }
    return ch;
}

/* The governor (patches TA05, O03): scripted frame-time traces. A slow frame is over 45 ms. */
static void test_governor(void)
{
    mg_t g;
    uint32_t t = 1000;
    /* calm: nothing happens, ever */
    mg_init(&g);
    feed(&g, &t, 300, 6000);
    CHECK(g.level == MG_LEVEL_FULL && g.sheds == 0 && g.last_fps >= 28 && g.last_fps <= 31 && g.last_load_pct >= 15 && g.last_load_pct <= 21);

    /* sustained slowness with no overlay: the ladder in the owner's order (glow, scanlines, half the particles, the floor, flat) */
    mg_init(&g);
    t = 5000;
    int order[6] = {1, 0, 0, 0, 0, 0};
    for (int i = 0; i < 120; i++) { feed(&g, &t, 1, 60000); order[g.level] = 1; }
    CHECK(g.level == MG_LEVEL_FLAT && g.sheds == 5 && mg_flat(&g) && mg_particles_pct(&g) == 0);
    for (int l = 0; l < 6; l++) CHECK(order[l]);
    mg_init(&g);
    g.level = MG_LEVEL_NO_GLOW;
    CHECK(!mg_glow_ok(&g) && mg_scan_ok(&g) && mg_particles_pct(&g) == 100);
    g.level = MG_LEVEL_NO_SCANLINES;
    CHECK(!mg_scan_ok(&g) && mg_particles_pct(&g) == 100);
    g.level = MG_LEVEL_HALF_PARTICLES;
    CHECK(mg_particles_pct(&g) == 50);
    g.level = MG_LEVEL_LOW_PARTICLES;
    CHECK(mg_particles_pct(&g) == 30 && !mg_flat(&g));

    /* a burst: one or two slow frames (the redraw when an overlay comes back) never shed, with or without the grace period */
    mg_init(&g);
    t = 9000;
    feed(&g, &t, 30, 8000);
    feed(&g, &t, 1, 120000);
    feed(&g, &t, 1, 90000);
    feed(&g, &t, 40, 8000);
    CHECK(g.level == MG_LEVEL_FULL && g.sheds == 0);
    /* three slow frames among ten do shed (outside the grace period) */
    feed(&g, &t, 3, 60000);
    CHECK(g.level == MG_LEVEL_NO_GLOW && g.sheds == 1);
    /* during the grace period only six of ten do */
    mg_init(&g);
    t = 12000;
    feed(&g, &t, 20, 8000);
    mg_note_start(&g, t);
    feed(&g, &t, 1, 120000);
    feed(&g, &t, 3, 70000);
    CHECK(g.level == MG_LEVEL_FULL);
    feed(&g, &t, 1, 70000);
    CHECK(g.level == MG_LEVEL_FULL); /* five slow frames in the window: still under six */
    feed(&g, &t, 1, 70000);
    CHECK(g.level == MG_LEVEL_NO_GLOW);

    /* restore: one level after two seconds with no slow frame, one more after two more, never faster */
    mg_init(&g);
    g.level = MG_LEVEL_HALF_PARTICLES;
    t = 20000;
    feed(&g, &t, 40, 6000); /* 1.3 s */
    CHECK(g.level == MG_LEVEL_HALF_PARTICLES);
    feed(&g, &t, 40, 6000); /* 2.6 s */
    CHECK(g.level == MG_LEVEL_NO_SCANLINES && g.restores == 1);
    feed(&g, &t, 40, 6000);
    CHECK(g.level == MG_LEVEL_NO_SCANLINES);
    feed(&g, &t, 40, 6000);
    CHECK(g.level == MG_LEVEL_NO_GLOW && g.restores == 2);
    /* the restore's own redraw is one slow frame: grace, so it does not shed straight back (the unit's 68 percent flat look) */
    feed(&g, &t, 1, 110000);
    feed(&g, &t, 30, 6000);
    CHECK(g.level == MG_LEVEL_NO_GLOW && g.sheds == 0);

    /* an overlay is running: the floor. Slow frames for ever take it to the floor level and no further: no flat, no flutter. */
    mg_init(&g);
    mg_set_floor(&g, 1);
    t = 30000;
    mg_note_start(&g, t);
    int changes = 0, flat_seen = 0;
    for (int i = 0; i < 300; i++) { changes += feed(&g, &t, 1, 70000); flat_seen |= mg_flat(&g); } /* 10 s of 70 ms frames, a p99 under 100 ms */
    CHECK(g.level == MG_LEVEL_LOW_PARTICLES && !flat_seen && changes == 4 && g.sheds == 4 && g.restores == 0);
    CHECK(mg_particles_pct(&g) == 30 && !mg_glow_ok(&g) && !mg_scan_ok(&g)); /* the effects went first, the overlay stays at 30 percent */
    /* and it comes back up one level every two seconds once the frames are fast, without a single shed on the way */
    int ups = 0;
    for (int i = 0; i < 300; i++) { ups += feed(&g, &t, 1, 9000); }
    CHECK(g.level == MG_LEVEL_FULL && ups == 4 && g.restores == 4 && g.sheds == 4);
    /* the emergency: the 99th percentile over 100 ms for five seconds lets the flat look in; not before */
    mg_init(&g);
    mg_set_floor(&g, 1);
    t = 60000;
    int flat_at = -1;
    for (int i = 0; i < 400; i++) { feed(&g, &t, 1, 130000); if (flat_at < 0 && mg_flat(&g)) flat_at = i; }
    CHECK(flat_at >= 0 && (uint32_t)flat_at * 33 >= 4800 && g.floor == 1);
    mg_init(&g);
    mg_set_floor(&g, 1);
    t = 70000;
    for (int i = 0; i < 100; i++) feed(&g, &t, 1, 130000); /* 3.3 s */
    CHECK(!mg_flat(&g) && g.level == MG_LEVEL_LOW_PARTICLES);
    /* the floor drops an overlay-less ladder back to normal: with no overlay the ladder may reach flat again */
    mg_set_floor(&g, 0);
    CHECK(mg_max_level(&g) == MG_LEVEL_FLAT);
    /* the floor set while the ladder is lower than it clamps nothing; while above it, it clamps */
    mg_init(&g);
    g.level = MG_LEVEL_FLAT;
    CHECK(mg_set_floor(&g, 1) == 1 && g.level == MG_LEVEL_LOW_PARTICLES);

    /* the unit's 12-minute trace: steady 20 ms frames with the redraw spike (100 ms) at every restore, an overlay running from the start
     * at the floor. It must end up at full and never shed after the first second: the old governor sat flat 68 percent of the time. */
    mg_init(&g);
    mg_set_floor(&g, 1);
    g.level = MG_LEVEL_LOW_PARTICLES;
    t = 100000;
    mg_note_start(&g, t);
    uint32_t sheds_before = g.sheds, lvl_time[6] = {0};
    int spiked = 0;
    for (int i = 0; i < 22000; i++) { /* 12 minutes at 30 fps */
        const uint32_t before = g.restores;
        const uint32_t us = spiked ? 100000u : 20000u;
        spiked = 0;
        feed(&g, &t, 1, us);
        if (g.restores != before) spiked = 1; /* the next frame after a restore is the redraw */
        lvl_time[g.level]++;
    }
    CHECK(g.sheds == sheds_before && g.level == MG_LEVEL_FULL && lvl_time[MG_LEVEL_FLAT] == 0 && lvl_time[MG_LEVEL_FULL] > 21000);

    /* nothing drawing at all counts as calm: two idle seconds restore a step */
    mg_init(&g);
    g.level = 2;
    t = 200000;
    g.last_slow_ms = t;
    mg_idle(&g, t);
    int steps = 0;
    for (int s = 0; s < 8; s++) { t += 1000; steps += mg_idle(&g, t); }
    CHECK(g.level == 0 && steps == 2);
}

int main(void)
{
    test_scanline_rows();
    test_split_invariance();
    test_colour_modes();
    test_night();
    test_glow();
    test_governor();
    if (fails) {
        printf("%d failed\n", fails);
        return 1;
    }
    printf("fx_core_test: all passed\n");
    return 0;
}
