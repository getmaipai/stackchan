/* Host test for the overlay engine (patches TA04, O01): bounded particle state, deterministic seeds, the dirty rectangles that
 * make a partial flush correct, behind-the-face drawing, the text zones left alone, element sizes, zzz placement, the
 * named combinations, the governor share, end of life.
 * cc -std=c99 -Wall -Wextra -Werror -fsanitize=address,undefined -I<headers> overlay_core_test.c -lm */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "maipai_overlay_core.h"

static int fails;
#define CHECK(c)                                                \
    do {                                                        \
        if (!(c)) {                                             \
            printf("FAIL line %d: %s\n", __LINE__, #c);         \
            fails++;                                            \
        }                                                       \
    } while (0)

static const uint16_t BG = MO_RGB(8, 8, 24);

/* A stand-in for what LVGL draws: a dark screen with two bright round eyes. */
static void face(uint16_t* s, int x1, int y1, int x2, int y2)
{
    const int w = x2 - x1 + 1;
    for (int y = y1; y <= y2; y++)
        for (int x = x1; x <= x2; x++) {
            const int a = (x - 88) * (x - 88) + (y - 92) * (y - 92) < 24 * 24;
            const int b = (x - 232) * (x - 232) + (y - 92) * (y - 92) < 24 * 24;
            s[(size_t)(y - y1) * (size_t)w + (size_t)(x - x1)] = (a || b) ? 0xFFFF : BG;
        }
}

static void render(const mo_layer_t* layers, uint16_t* out, int x1, int y1, int x2, int y2)
{
    face(out, x1, y1, x2, y2);
    mc_t c = mc_make(out, x1, y1, x2, y2, 0, 0);
    mo_draw_all(layers, &c);
}

static uint32_t hash_state(const mo_layer_t* L)
{
    uint32_t h = 2166136261u;
    for (int i = 0; i < L->n; i++) {
        const uint8_t* b = (const uint8_t*)&L->p[i];
        for (size_t k = 0; k < sizeof L->p[i]; k++) h = (h ^ b[k]) * 16777619u;
    }
    return h ^ L->tick ^ ((uint32_t)L->s0 << 8) ^ L->rng; /* the generator too: two seeds that ended on the same tick still differ */
}

static int caps_ok(const mo_layer_t* L)
{
    return L->n <= MO_MAX_P && L->n <= mo_cap(L->id, L->intensity) + 2 && L->ndirty <= MO_MAX_DIRTY;
}

static void test_names(void)
{
    CHECK(MO_COUNT == 19 && MOP_COUNT == 10);
    const char* host[] = {"rain", "snow", "sun", "clouds", "wind", "thunder", "fog", "stars", "disco", "confetti", "fireworks",
                          "hearts", "steam", "balloons", "leaves", "zzz"};
    for (int i = 0; i < 16; i++) CHECK(mo_id(host[i]) != 0 && !mo_is_preset(mo_id(host[i]))); /* the host's one list (reply_tags.OVERLAYS) */
    const char* combos[] = {"stormy", "rainy", "snowy", "sunny", "windy", "night", "party", "celebrate", "love", "sleeping"};
    for (int i = 0; i < 10; i++) CHECK(mo_is_preset(mo_id(combos[i])) && strcmp(MOP_NAMES[i], combos[i]) == 0);
    CHECK(mo_id("hail") == 0 && mo_id("") == 0);
    for (int i = 1; i < MO_COUNT; i++) CHECK(mo_id(MO_NAMES[i]) == i);
    CHECK(mo_layer_of(MO_RAIN) == 0 && mo_layer_of(MO_STARS) == 0 && mo_layer_of(MO_ZZZ) == 1 && mo_layer_of(MO_CONFETTI) == 1);
    CHECK(sizeof(mo_layer_t) * MO_LAYERS < 3000); /* the three layers: under 3 KB of state, in PSRAM on the unit */
}

static void test_bounded_and_deterministic(void)
{
    for (int id = 1; id < MO_COUNT; id++) {
        for (int inten = 1; inten <= 3; inten++) {
            mo_layer_t a, b;
            memset(&a, 0, sizeof a); memset(&b, 0, sizeof b);
            mo_start(&a, id, inten, 20, 1234);
            mo_start(&b, id, inten, 20, 1234);
            int worst = 0;
            for (int t = 0; t < 900; t++) { /* 30 s */
                mo_step(&a, 33); mo_step(&b, 33);
                a.ndirty = b.ndirty = 0;
                if (!caps_ok(&a)) { printf("cap broken: %s %d tick %d n=%d\n", MO_NAMES[id], inten, t, a.n); fails++; break; }
                if ((int)a.n > worst) worst = a.n;
                for (int i = 0; i < a.n; i++) { /* positions stay near the screen */
                    const int x = mo_px(a.p[i].x), y = mo_px(a.p[i].y);
                    if (x < -200 || x > MO_W + 200 || y < -200 || y > MO_H + 200) { printf("wandered: %s tick %d (%d,%d)\n", MO_NAMES[id], t, x, y); fails++; break; }
                }
            }
            CHECK(hash_state(&a) == hash_state(&b)); /* same seed, same picture */
            mo_layer_t c;
            memset(&c, 0, sizeof c);
            mo_start(&c, id, inten, 20, 999);
            for (int t = 0; t < 900; t++) { mo_step(&c, 33); c.ndirty = 0; }
            if (id != MO_SUN && id != MO_FOG && id != MO_MOON) {
                if (!(hash_state(&a) != hash_state(&c) || id == MO_CLOUDS)) printf("same picture for two seeds: %s intensity %d\n", MO_NAMES[id], inten);
                CHECK(hash_state(&a) != hash_state(&c) || id == MO_CLOUDS); /* another seed, another picture */
            }
            CHECK(a.id == (uint8_t)id);
        }
    }
}

static void test_end_of_life(void)
{
    for (int id = 1; id < MO_COUNT; id++) {
        mo_layer_t L;
        memset(&L, 0, sizeof L);
        mo_start(&L, id, 3, 3, 77);
        int done_at = -1;
        for (int t = 0; t < 1200; t++) {
            mo_step(&L, 33);
            L.ndirty = 0;
            if (mo_done(&L)) { done_at = t; break; }
        }
        if (done_at < 0) { printf("never ended: %s\n", MO_NAMES[id]); fails++; }
        /* 3 s run, then the leftovers fall or fade: within 12 s in all cases */
        if (!(done_at >= 90 && done_at < 700)) printf("end time odd: %s done_at %d\n", MO_NAMES[id], done_at);
        CHECK(done_at >= 90 && done_at < 700);
    }
    /* until cleared: runs on, stop ends it, clear is at once */
    mo_layer_t L;
    memset(&L, 0, sizeof L);
    mo_start(&L, MO_SNOW, 2, 0, 5);
    for (int t = 0; t < 900; t++) { mo_step(&L, 33); L.ndirty = 0; }
    CHECK(!mo_done(&L) && L.spawning);
    mo_stop(&L);
    for (int t = 0; t < 600; t++) { mo_step(&L, 33); L.ndirty = 0; }
    CHECK(mo_done(&L));
    mo_start(&L, MO_RAIN, 3, 0, 5);
    for (int t = 0; t < 60; t++) { mo_step(&L, 33); L.ndirty = 0; }
    mo_clear(&L);
    CHECK(L.id == MO_NONE && L.n == 0 && L.ndirty > 0 && mo_done(&L)); /* its old pixels are marked for repaint */
    /* a stall: a two-second frame runs at most MO_MAX_STEPS ticks */
    mo_start(&L, MO_RAIN, 2, 0, 5);
    CHECK(mo_step(&L, 2000) == MO_MAX_STEPS);
    CHECK(mo_step(&L, 10) == 0);
    mo_clear(&L);
}

/* The property that makes a partial flush correct: after each tick, flushing only the dirty rectangles leaves the panel
 * showing what a full redraw would show. */
static void test_dirty_rectangles(void)
{
    static uint16_t panel[MO_W * MO_H], truth[MO_W * MO_H], tile[MO_W * MO_H];
    for (int id = 1; id < MO_COUNT; id++) {
        for (int inten = 1; inten <= 3; inten += 2) {
            mo_layer_t L[MO_LAYERS];
            memset(L, 0, sizeof L);
            const int ly = mo_layer_of(id);
            mo_start(&L[ly], id, inten, 8, 4242);
            face(panel, 0, 0, MO_W - 1, MO_H - 1); /* the panel starts as a clean face */
            long stale_worst = 0;
            int first_bad = -1;
            for (int t = 0; t < 420; t++) {
                if (t > 0) mo_step(&L[ly], 33);
                mo_rect_t r[MO_MAX_DIRTY];
                const int nr = mo_take_dirty(&L[ly], r);
                for (int k = 0; k < nr; k++) { /* flush each dirty rectangle in 20-row strips as the unit does */
                    for (int y0 = r[k].y1; y0 <= r[k].y2; y0 += 20) {
                        const int y1 = y0, y2 = (y0 + 19 < r[k].y2) ? y0 + 19 : r[k].y2;
                        render(L, tile, r[k].x1, y1, r[k].x2, y2);
                        for (int y = y1; y <= y2; y++)
                            memcpy(panel + (size_t)y * MO_W + r[k].x1, tile + (size_t)(y - y1) * (size_t)(r[k].x2 - r[k].x1 + 1),
                                   sizeof(uint16_t) * (size_t)(r[k].x2 - r[k].x1 + 1));
                    }
                }
                /* while an overlay fades in or out its brightness changes every tick and is repainted every few: judged
                 * only when steady; the end of the run is judged below */
                const int fading = L[ly].t_ms < MO_FADE_MS + 100 || !L[ly].spawning;
                if (fading && mo_is_static(id)) continue;
                render(L, truth, 0, 0, MO_W - 1, MO_H - 1);
                long stale = 0;
                for (int i = 0; i < MO_W * MO_H; i++) {
                    const int d = abs(mfx_luma5(panel[i]) - mfx_luma5(truth[i]));
                    if (d > 4) { stale++; if (first_bad < 0) first_bad = i; }
                }
                if (stale > stale_worst) stale_worst = stale;
            }
            if (stale_worst > 0) printf("stale pixels: %s intensity %d worst %ld first at (%d,%d)\n", MO_NAMES[id], inten, stale_worst, first_bad % MO_W, first_bad / MO_W);
            CHECK(stale_worst == 0);
            /* the end: when it is done the panel shows the clean face again (nothing left behind) */
            for (int t = 0; t < 1200 && !mo_done(&L[ly]); t++) {
                mo_step(&L[ly], 33);
                mo_rect_t r[MO_MAX_DIRTY];
                const int nr = mo_take_dirty(&L[ly], r);
                for (int k = 0; k < nr; k++) {
                    render(L, tile, r[k].x1, r[k].y1, r[k].x2, r[k].y2);
                    for (int y = r[k].y1; y <= r[k].y2; y++)
                        memcpy(panel + (size_t)y * MO_W + r[k].x1, tile + (size_t)(y - r[k].y1) * (size_t)(r[k].x2 - r[k].x1 + 1),
                               sizeof(uint16_t) * (size_t)(r[k].x2 - r[k].x1 + 1));
                }
            }
            CHECK(mo_done(&L[ly]));
            mo_clear(&L[ly]); /* what the caller does when it sees the end: repaint the last of it */
            {
                mo_rect_t r[MO_MAX_DIRTY];
                const int nr = mo_take_dirty(&L[ly], r);
                for (int k = 0; k < nr; k++) {
                    render(L, tile, r[k].x1, r[k].y1, r[k].x2, r[k].y2);
                    for (int y = r[k].y1; y <= r[k].y2; y++)
                        memcpy(panel + (size_t)y * MO_W + r[k].x1, tile + (size_t)(y - r[k].y1) * (size_t)(r[k].x2 - r[k].x1 + 1),
                               sizeof(uint16_t) * (size_t)(r[k].x2 - r[k].x1 + 1));
                }
            }
            face(truth, 0, 0, MO_W - 1, MO_H - 1);
            long left = 0;
            for (int i = 0; i < MO_W * MO_H; i++) left += abs(mfx_luma5(panel[i]) - mfx_luma5(truth[i])) > 2;
            if (left) printf("left behind after the end: %s intensity %d: %ld pixels\n", MO_NAMES[id], inten, left);
            CHECK(left == 0);
        }
    }
}

static long changed_pixels(const uint16_t* a, const uint16_t* b)
{
    long n = 0;
    for (int i = 0; i < MO_W * MO_H; i++) n += a[i] != b[i];
    return n;
}

static void test_draws_something_and_stays_behind(void)
{
    static uint16_t clean[MO_W * MO_H], img[MO_W * MO_H];
    face(clean, 0, 0, MO_W - 1, MO_H - 1);
    for (int id = 1; id < MO_COUNT; id++) {
        mo_layer_t L[MO_LAYERS];
        memset(L, 0, sizeof L);
        const int ly = mo_layer_of(id);
        mo_start(&L[ly], id, 3, 0, 31337);
        long best = 0;
        for (int t = 0; t < 400; t++) {
            mo_step(&L[ly], 33);
            L[ly].ndirty = 0;
            if (t % 20 == 19) {
                render(L, img, 0, 0, MO_W - 1, MO_H - 1);
                const long n = changed_pixels(img, clean);
                if (n > best) best = n;
            }
        }
        if (best == 0) printf("draws nothing: %s\n", MO_NAMES[id]);
        CHECK(best > 20);
        if (mo_behind(id)) { /* the eyes are never touched */
            long touched = 0;
            for (int y = 0; y < MO_H; y++)
                for (int x = 0; x < MO_W; x++) {
                    const int a = (x - 88) * (x - 88) + (y - 92) * (y - 92) < 24 * 24, b = (x - 232) * (x - 232) + (y - 92) * (y - 92) < 24 * 24;
                    if ((a || b) && img[y * MO_W + x] != 0xFFFF) touched++;
                }
            if (touched) printf("covers an eye: %s %ld\n", MO_NAMES[id], touched);
            CHECK(touched == 0);
        }
    }
}

static void test_zzz(void)
{
    mo_layer_t L;
    memset(&L, 0, sizeof L);
    mo_start(&L, MO_ZZZ, 2, 0, 99);
    int spawns = 0, max_alive = 0, left = 0, right = 0, sizes[3] = {0, 0, 0};
    int minx = 999, maxx = -999, miny = 999, maxy = -999;
    for (int t = 0; t < 30 * 30; t++) { /* 30 seconds */
        mo_step(&L, 33);
        L.ndirty = 0;
        for (int i = 0; i < L.n; i++) {
            const int x = mo_px(L.p[i].x), y = mo_px(L.p[i].y), s = mo_zzz_s(&L.p[i]);
            spawns += L.p[i].age == 1;
            if (L.p[i].age == 1) { if (x < 160) left++; else right++; }
            sizes[s == 24 ? 0 : (s == 36 ? 1 : 2)]++;
            CHECK(s == 24 || s == 36 || s == 48);
            if (x - s / 2 < minx) minx = x - s / 2;
            if (x + s / 2 > maxx) maxx = x + s / 2;
            if (y - s / 2 < miny) miny = y - s / 2;
            if (y + s / 2 > maxy) maxy = y + s / 2;
        }
        if (L.n > max_alive) max_alive = L.n;
    }
    CHECK(spawns >= 14 && spawns <= 26);      /* a z every 1.2 to 1.7 seconds */
    CHECK(left >= 5 && right >= 5);           /* both sides of the head */
    CHECK(max_alive >= 3 && max_alive <= 4);  /* three or four alive */
    CHECK(sizes[0] > 100 && sizes[1] > 100 && sizes[2] > 100); /* all three sizes */
    CHECK(minx >= 0 && maxx <= 320);          /* inside the screen at every size */
    CHECK(miny >= 29 && maxy <= 183);         /* inside the face zone (y 28 to 184), clear of the banner and the subtitles */
    /* the eyes: the right big eye ends at x 270 and the left one starts at x 50; a glyph never reaches them */
    int in_left = 0, in_right = 0;
    for (int t = 0; t < 600; t++) { mo_step(&L, 33); L.ndirty = 0; for (int i = 0; i < L.n; i++) { const int x = mo_px(L.p[i].x); if (x < 160) in_left += x + mo_zzz_s(&L.p[i]) / 2 > 50; else in_right += x - mo_zzz_s(&L.p[i]) / 2 < 270; } }
    CHECK(in_left == 0 && in_right == 0);
    /* a glyph: filled, with a darker outline, solid pixels at each size; the smallest dimension of the strokes is 6 px or more */
    static uint16_t buf[MO_W * MO_H];
    long fillpx[3], edgepx[3];
    const int sz[3] = {24, 36, 48};
    for (int k = 0; k < 3; k++) {
        face(buf, 0, 0, MO_W - 1, MO_H - 1);
        mc_t c = mc_make(buf, 0, 0, MO_W - 1, MO_H - 1, 0, 0);
        c.behind = 1;
        mo_draw_z(&c, 160, 120, sz[k], MO_RGB(206, 200, 255), MO_RGB(96, 84, 184), 255);
        fillpx[k] = edgepx[k] = 0;
        for (int i = 0; i < MO_W * MO_H; i++) { fillpx[k] += buf[i] == MO_RGB(206, 200, 255); edgepx[k] += buf[i] == MO_RGB(96, 84, 184); }
        const int o = sz[k] >= 40 ? 3 : 2, si = sz[k] - 2 * o, t = si / 4;
        /* the top bar is t rows thick and the full width of the filled Z, the bottom bar likewise */
        int full_rows = 0;
        for (int y = 0; y < MO_H; y++) { int run = 0; for (int x = 0; x < MO_W; x++) run += buf[y * MO_W + x] == MO_RGB(206, 200, 255); if (run == si) full_rows++; }
        CHECK(full_rows >= 2 * t - 1);
        CHECK(t >= 5);
    }
    CHECK(fillpx[0] > 120 && fillpx[1] > fillpx[0] * 2 && fillpx[2] > fillpx[1] * 3 / 2);
    CHECK(edgepx[0] > 60 && edgepx[2] > edgepx[0]);
}

static void test_governor_share_and_layers(void)
{
    mo_layer_t L;
    memset(&L, 0, sizeof L);
    mo_start(&L, MO_RAIN, 3, 0, 5);
    for (int t = 0; t < 200; t++) { mo_step(&L, 33); L.ndirty = 0; }
    const int full = L.n;
    L.pct = 50;
    for (int t = 0; t < 200; t++) { mo_step(&L, 33); L.ndirty = 0; }
    CHECK(full >= 26 && L.n <= full / 2 + 2); /* the share halves what is alive within a few seconds */
    L.pct = 100;
    for (int t = 0; t < 200; t++) { mo_step(&L, 33); L.ndirty = 0; }
    CHECK((int)L.n >= full - 3); /* and restores */
    /* two layers at once keep their own state */
    mo_layer_t two[MO_LAYERS];
    memset(two, 0, sizeof two);
    mo_start(&two[0], MO_RAIN, 2, 0, 1);
    mo_start(&two[1], MO_CONFETTI, 2, 0, 2);
    for (int t = 0; t < 100; t++) { mo_step(&two[0], 33); mo_step(&two[1], 33); }
    CHECK(two[0].n > 0 && two[1].n > 0 && two[0].id == MO_RAIN && two[1].id == MO_CONFETTI);
    /* a new overlay in the same layer replaces the old one */
    mo_start(&two[0], MO_SNOW, 1, 0, 3);
    CHECK(two[0].id == MO_SNOW && two[0].n == 0 && two[1].id == MO_CONFETTI);
}

static void test_thunder_and_fireworks(void)
{
    mo_layer_t L;
    memset(&L, 0, sizeof L);
    mo_start(&L, MO_THUNDER, 3, 0, 8);
    int flashes = 0, prev = 0;
    for (int t = 0; t < 900; t++) {
        mo_step(&L, 33);
        L.ndirty = 0;
        if (L.s1 > 0 && prev == 0) flashes++;
        prev = L.s1 > 0;
    }
    CHECK(flashes >= 5 && flashes <= 14); /* 30 s of heavy storm: a flash every 1.5 to 3.5 s */
    mo_start(&L, MO_FIREWORKS, 3, 0, 8);
    int bursts = 0, maxn = 0;
    for (int t = 0; t < 900; t++) {
        const int before = L.n;
        mo_step(&L, 33);
        L.ndirty = 0;
        if ((int)L.n - before >= 8) bursts++;
        if (L.n > maxn) maxn = L.n;
    }
    CHECK(bursts >= 8 && maxn <= 40);
}


/* ---- element sizes (patch O01): what the owner can see at arm's length ---- */

static uint16_t blank_buf[MO_W * MO_H];

static void blank(void)
{
    for (int i = 0; i < MO_W * MO_H; i++) blank_buf[i] = BG;
}

typedef struct { int x1, y1, x2, y2, n; } box_t;

static box_t painted(void)
{
    box_t b = {9999, 9999, -1, -1, 0};
    for (int y = 0; y < MO_H; y++)
        for (int x = 0; x < MO_W; x++)
            if (blank_buf[y * MO_W + x] != BG) {
                b.n++;
                if (x < b.x1) b.x1 = x;
                if (x > b.x2) b.x2 = x;
                if (y < b.y1) b.y1 = y;
                if (y > b.y2) b.y2 = y;
            }
    return b;
}

static int max_run(void)
{
    int best = 0;
    for (int y = 0; y < MO_H; y++) {
        int run = 0;
        for (int x = 0; x < MO_W; x++) {
            run = blank_buf[y * MO_W + x] != BG ? run + 1 : 0;
            if (run > best) best = run;
        }
    }
    return best;
}

static void test_sizes(void)
{
    /* rain: 3 px wide, 14 to 24 px long (a lone streak on a clean screen) */
    for (int len = 14; len <= 24; len += 10) {
        blank();
        mo_p_t p;
        memset(&p, 0, sizeof p);
        p.x = (int16_t)(160 * MO_FP); p.y = (int16_t)(120 * MO_FP); p.vx = -10; p.vy = 74; p.a = (uint8_t)len;
        mo_layer_t L;
        memset(&L, 0, sizeof L);
        L.id = MO_RAIN; L.intensity = 2; L.spawning = 1; L.n = 1; L.p[0] = p; L.pct = 100;
        mc_t c = mc_make(blank_buf, 0, 0, MO_W - 1, MO_H - 1, 0, 0);
        mo_draw(&L, &c);
        const box_t b = painted();
        CHECK(b.y2 - b.y1 + 1 >= len - 2 && b.y2 - b.y1 + 1 <= len + 4);
        CHECK(max_run() >= 3 && max_run() <= 5); /* 3 px wide (a slant widens a row by a pixel or two) */
    }
    /* snow: flakes 5 to 10 px, four sizes */
    int snow_min = 99, snow_max = 0;
    for (int a = 0; a < 4; a++) {
        blank();
        mo_layer_t L;
        memset(&L, 0, sizeof L);
        L.id = MO_SNOW; L.intensity = 2; L.spawning = 1; L.n = 1; L.p[0].x = (int16_t)(160 * MO_FP); L.p[0].y = (int16_t)(120 * MO_FP); L.p[0].a = (uint8_t)a; L.pct = 100;
        mc_t c = mc_make(blank_buf, 0, 0, MO_W - 1, MO_H - 1, 0, 0);
        mo_draw(&L, &c);
        const box_t b = painted();
        const int w = b.x2 - b.x1 + 1;
        if (w < snow_min) snow_min = w;
        if (w > snow_max) snow_max = w;
    }
    CHECK(snow_min >= 5 && snow_max >= 10 && snow_max <= 15);
    /* hearts 24, 32 and 40 px */
    for (int a = 0; a < 3; a++) {
        blank();
        mo_layer_t L;
        memset(&L, 0, sizeof L);
        L.id = MO_HEARTS; L.intensity = 2; L.spawning = 1; L.n = 1; L.p[0].x = (int16_t)(160 * MO_FP); L.p[0].y = (int16_t)(120 * MO_FP); L.p[0].a = (uint8_t)a; L.p[0].age = 30; L.p[0].life = 150; L.pct = 100;
        mc_t c = mc_make(blank_buf, 0, 0, MO_W - 1, MO_H - 1, 0, 0);
        mo_draw(&L, &c);
        const box_t b = painted();
        const int w = b.x2 - b.x1 + 1, h = b.y2 - b.y1 + 1, want = 24 + 8 * a;
        CHECK(w >= want - 2 && w <= want + 6 && h >= want - 4 && h <= want + 6);
    }
    /* confetti 8 to 14 px in every phase */
    for (int ph = 0; ph < 4; ph++) {
        blank();
        mo_layer_t L;
        memset(&L, 0, sizeof L);
        L.id = MO_CONFETTI; L.intensity = 2; L.spawning = 1; L.n = 1; L.p[0].x = (int16_t)(160 * MO_FP); L.p[0].y = (int16_t)(120 * MO_FP); L.p[0].age = (uint16_t)(ph * 4); L.pct = 100;
        mc_t c = mc_make(blank_buf, 0, 0, MO_W - 1, MO_H - 1, 0, 0);
        mo_draw(&L, &c);
        const box_t b = painted();
        const int w = b.x2 - b.x1 + 1, h = b.y2 - b.y1 + 1;
        CHECK(w >= 8 && w <= 14 && h >= 8 && h <= 14);
    }
    /* leaves 14 px long in every turn */
    for (int ph = 0; ph < 16; ph += 3) {
        blank();
        mo_layer_t L;
        memset(&L, 0, sizeof L);
        L.id = MO_LEAVES; L.intensity = 2; L.spawning = 1; L.n = 1; L.p[0].x = (int16_t)(160 * MO_FP); L.p[0].y = (int16_t)(120 * MO_FP); L.p[0].age = (uint16_t)(ph * 4); L.pct = 100;
        mc_t c = mc_make(blank_buf, 0, 0, MO_W - 1, MO_H - 1, 0, 0);
        mo_draw(&L, &c);
        const box_t b = painted();
        const int ext = mo_max(b.x2 - b.x1 + 1, b.y2 - b.y1 + 1);
        CHECK(ext >= 12 && ext <= 18 && b.n >= 50);
    }
    /* clouds: a back and a front layer, big, 80 px wide at least, covering a good part of the top */
    {
        blank();
        mo_layer_t L;
        memset(&L, 0, sizeof L);
        mo_start(&L, MO_CLOUDS, 2, 0, 12);
        for (int t = 0; t < 40; t++) { mo_step(&L, 33); L.ndirty = 0; }
        mc_t c = mc_make(blank_buf, 0, 0, MO_W - 1, MO_H - 1, 0, 0);
        mo_draw(&L, &c);
        const box_t b = painted();
        CHECK(b.n > 76800 / 6 && b.y2 < 100); /* more than a sixth of the screen, in the top 100 rows */
        CHECK(L.n == 5);
        int widest = 0;
        for (int i = 0; i < L.n; i++) widest = mo_max(widest, mo_cloud_w(&L.p[i]));
        CHECK(widest >= 104);
        mo_start(&L, MO_CLOUDS, 3, 0, 12);
        L.t_ms = 2000;
        blank();
        mo_draw(&L, &c);
        CHECK(painted().n > 76800 / 5); /* heavy: about a quarter of the screen */
    }
    /* the sun: 52 px across with rays out to 100 px across */
    {
        blank();
        mo_layer_t L;
        memset(&L, 0, sizeof L);
        mo_start(&L, MO_SUN, 2, 0, 12);
        L.t_ms = 2000;
        mc_t c = mc_make(blank_buf, 0, 0, MO_W - 1, MO_H - 1, 0, 0);
        mo_draw(&L, &c);
        const box_t b = painted();
        CHECK(b.x2 - b.x1 + 1 >= 90 && b.n > 4000);
    }
    /* fireworks: a burst reaches 60 to 100 px from where it opened, and every spark has a trail */
    {
        mo_layer_t L;
        memset(&L, 0, sizeof L);
        mo_start(&L, MO_FIREWORKS, 1, 0, 5); /* light: one burst at a time, so every spark belongs to the first */
        int best = 0, bx = 0, by = 0, have = 0, t0 = 0;
        for (int t = 0; t < 600; t++) {
            mo_step(&L, 33);
            L.ndirty = 0;
            for (int i = 0; i < L.n; i++) {
                if (L.p[i].a == 1 && L.p[i].age == 1 && !have) { bx = mo_px(L.p[i].x); by = mo_px(L.p[i].y); have = 1; t0 = t; }
            }
            if (have) {
                for (int i = 0; i < L.n; i++) {
                    if (L.p[i].a != 1 || L.p[i].age < t - t0) continue; /* the first burst's sparks only */
                    const int dx = mo_px(L.p[i].x) - bx, dy = mo_px(L.p[i].y) - by;
                    const int d = (int)sqrtf((float)(dx * dx + dy * dy));
                    if (d > best) best = d;
                }
            }
            if (have && t > 200) break;
        }
        CHECK(best >= 60 && best <= 100);
    }
}

/* ---- the text zones: the banner row and the subtitle strip are left alone while they show ---- */

static void test_zones(void)
{
    static uint16_t clean[MO_W * MO_H], img[MO_W * MO_H];
    face(clean, 0, 0, MO_W - 1, MO_H - 1);
    for (int id = 1; id < MO_COUNT + MOP_COUNT; id++) {
        const int eid = id < MO_COUNT ? id : MO_PRESET_BASE + (id - MO_COUNT);
        mo_layer_t L[MO_LAYERS];
        memset(L, 0, sizeof L);
        CHECK(mo_set(L, eid, 3, 0, 4711) != 0);
        long in_top = 0, in_bottom = 0, in_face_zone = 0;
        for (int t = 0; t < 360; t++) {
            for (int l = 0; l < MO_LAYERS; l++) { mo_step(&L[l], 33); L[l].ndirty = 0; }
            if (t % 12 != 11) continue;
            face(img, 0, 0, MO_W - 1, MO_H - 1);
            mc_t c = mc_make(img, 0, 0, MO_W - 1, MO_H - 1, 1, 1);
            mo_draw_all(L, &c);
            for (int y = 0; y < MO_H; y++)
                for (int x = 0; x < MO_W; x++) {
                    if (img[y * MO_W + x] == clean[y * MO_W + x]) continue;
                    if (y < MO_ZONE_TOP) in_top++;
                    else if (y >= MO_ZONE_BOTTOM) in_bottom++;
                    else in_face_zone++;
                }
        }
        if (in_top || in_bottom) printf("text zone touched: %d top %ld bottom %ld\n", eid, in_top, in_bottom);
        CHECK(in_top == 0 && in_bottom == 0);
        CHECK(in_face_zone > 50);
        /* with no text showing the same overlay may use the whole screen: zones are open */
        face(img, 0, 0, MO_W - 1, MO_H - 1);
        mc_t open = mc_make(img, 0, 0, MO_W - 1, MO_H - 1, 0, 0);
        mo_draw_all(L, &open);
    }
}

/* ---- the named combinations ---- */

static void test_presets(void)
{
    const int want[MOP_COUNT][3] = {
        {MO_CLOUDS, MO_THUNDER, 0}, {MO_CLOUDS, MO_RAIN, 0}, {MO_CLOUDS, MO_SNOW, 0}, {MO_SUN, MO_CLOUDS, 0}, {MO_CLOUDS, MO_LEAVES, MO_WIND},
        {MO_STARS, MO_MOON, 0}, {MO_DISCO, MO_CONFETTI, 0}, {MO_FIREWORKS, MO_CONFETTI, 0}, {MO_HEARTS, MO_SPARKLES, 0}, {MO_STARS, MO_ZZZ, 0},
    };
    static uint16_t clean[MO_W * MO_H], img[MO_W * MO_H];
    face(clean, 0, 0, MO_W - 1, MO_H - 1);
    for (int pi = 0; pi < MOP_COUNT; pi++) {
        mo_layer_t L[MO_LAYERS];
        memset(L, 0, sizeof L);
        const int mask = mo_set(L, MO_PRESET_BASE + pi, 2, 6, 100 + (uint32_t)pi);
        int expect = 0;
        for (int l = 0; l < MO_LAYERS; l++) {
            CHECK(L[l].id == want[pi][l]);
            if (want[pi][l]) { expect |= 1 << l; CHECK(L[l].combo == 1); }
        }
        CHECK(mask == expect);
        long best = 0;
        int worst_n = 0;
        for (int t = 0; t < 360; t++) {
            for (int l = 0; l < MO_LAYERS; l++) { mo_step(&L[l], 33); L[l].ndirty = 0; worst_n = mo_max(worst_n, L[l].n); }
            if (t % 20 == 19) {
                render(L, img, 0, 0, MO_W - 1, MO_H - 1);
                long n = 0;
                for (int i = 0; i < MO_W * MO_H; i++) n += img[i] != clean[i];
                if (n > best) best = n;
            }
        }
        if (best < 800) printf("a preset that draws too little: %s %ld\n", MOP_NAMES[pi], best);
        CHECK(best > 800);
        CHECK(worst_n <= MO_MAX_P);
        /* ends by itself after its time and the fades */
        int done_at = -1;
        for (int t = 0; t < 1200; t++) {
            int all = 1;
            for (int l = 0; l < MO_LAYERS; l++) { mo_step(&L[l], 33); L[l].ndirty = 0; all &= mo_done(&L[l]); }
            if (all) { done_at = t; break; }
        }
        CHECK(done_at >= 0);
        /* a single overlay while a preset runs ends the preset (no half pictures) */
        mo_set(L, MO_PRESET_BASE + pi, 2, 0, 7);
        mo_set(L, MO_SNOW, 2, 0, 8);
        int others = 0;
        for (int l = 0; l < MO_LAYERS; l++) others += l != mo_layer_of(MO_SNOW) && L[l].id != MO_NONE;
        CHECK(L[mo_layer_of(MO_SNOW)].id == MO_SNOW && others == 0 && L[mo_layer_of(MO_SNOW)].combo == 0);
        /* a preset replaces a single overlay too */
        mo_set(L, MO_PRESET_BASE + pi, 2, 0, 9);
        CHECK(L[0].id == want[pi][0] && L[1].id == want[pi][1] && L[2].id == want[pi][2]);
    }
    /* rain and snow in a preset start under the clouds' belly */
    mo_layer_t L[MO_LAYERS];
    memset(L, 0, sizeof L);
    mo_set(L, MO_PRESET_BASE + MOP_RAINY, 2, 0, 3);
    int high = 0;
    for (int t = 0; t < 200; t++) { mo_step(&L[1], 33); L[1].ndirty = 0; for (int i = 0; i < L[1].n; i++) high += L[1].p[i].age == 1 && mo_px(L[1].p[i].y) < 10; }
    CHECK(high == 0);
    /* the intensity moves every part (light stormy is not heavy) */
    mo_set(L, MO_PRESET_BASE + MOP_STORMY, 1, 0, 3);
    CHECK(L[0].intensity == 2 && L[1].intensity == 2);
    mo_set(L, MO_PRESET_BASE + MOP_STORMY, 3, 0, 3);
    CHECK(L[0].intensity == 3 && L[1].intensity == 3);
}

/* ---- the performance contract: caps, and the governor's share sheds ---- */

static void test_caps_and_shedding(void)
{
    for (int id = 1; id < MO_COUNT; id++) {
        for (int inten = 1; inten <= 3; inten++) CHECK(mo_cap(id, inten) <= MO_MAX_P);
    }
    /* at half share every particle overlay keeps at most half of its cap alive */
    for (int id = 1; id < MO_COUNT; id++) {
        if (mo_cap(id, 3) == 0 || id == MO_CLOUDS || id == MO_DISCO || id == MO_STARS) continue;
        mo_layer_t L;
        memset(&L, 0, sizeof L);
        mo_start(&L, id, 3, 0, 61);
        L.pct = 50;
        int worst = 0;
        for (int t = 0; t < 900; t++) { mo_step(&L, 33); L.ndirty = 0; if (t > 300 && (int)L.n > worst) worst = L.n; }
        if (worst > (mo_cap(id, 3) + 1) / 2 + 2) printf("does not shed: %s worst %d cap %d\n", MO_NAMES[id], worst, mo_cap(id, 3));
        CHECK(worst <= (mo_cap(id, 3) + 1) / 2 + 2);
    }
}

/* ---- the face's dark insides (a pupil, an open mouth) are not background ---- */

static void test_protected_ellipses(void)
{
    static uint16_t clean[MO_W * MO_H], img[MO_W * MO_H];
    for (int y = 0; y < MO_H; y++)
        for (int x = 0; x < MO_W; x++) {
            const int a = (x - 88) * (x - 88) + (y - 92) * (y - 92), b = (x - 232) * (x - 232) + (y - 92) * (y - 92);
            /* a white ring around a black pupil: the pupil is as dark as the background */
            clean[y * MO_W + x] = ((a < 40 * 40 && a >= 28 * 28) || (b < 40 * 40 && b >= 28 * 28)) ? 0xFFFF : BG;
        }
    long strays = 0, changed = 0;
    for (int id = 1; id < MO_COUNT + MOP_COUNT; id++) {
        const int eid = id < MO_COUNT ? id : MO_PRESET_BASE + (id - MO_COUNT);
        mo_layer_t L[MO_LAYERS];
        memset(L, 0, sizeof L);
        mo_set(L, eid, 3, 0, 2024);
        for (int t = 0; t < 300; t++) {
            for (int l = 0; l < MO_LAYERS; l++) { mo_step(&L[l], 33); L[l].ndirty = 0; }
            if (t % 15 != 14) continue;
            memcpy(img, clean, sizeof img);
            mc_t c = mc_make(img, 0, 0, MO_W - 1, MO_H - 1, 0, 0);
            mc_protect(&c, 88, 92, 42, 42);
            mc_protect(&c, 232, 92, 42, 42);
            mo_draw_all(L, &c);
            for (int y = 0; y < MO_H; y++)
                for (int x = 0; x < MO_W; x++) {
                    if (img[y * MO_W + x] == clean[y * MO_W + x]) continue;
                    changed++;
                    const int a = (x - 88) * (x - 88) + (y - 92) * (y - 92), b = (x - 232) * (x - 232) + (y - 92) * (y - 92);
                    strays += a < 42 * 42 || b < 42 * 42;
                }
        }
    }
    if (strays) printf("painted inside a protected eye: %ld\n", strays);
    CHECK(strays == 0 && changed > 1000);
    /* the same overlays do reach the pupil when nothing is protected (the check is not vacuous) */
    long inside = 0;
    mo_layer_t L[MO_LAYERS];
    memset(L, 0, sizeof L);
    mo_set(L, MO_PRESET_BASE + MOP_LOVE, 3, 0, 5);
    for (int t = 0; t < 600; t++) { for (int l = 0; l < MO_LAYERS; l++) { mo_step(&L[l], 33); L[l].ndirty = 0; } }
    for (int t = 0; t < 40; t++) {
        for (int l = 0; l < MO_LAYERS; l++) { mo_step(&L[l], 33); L[l].ndirty = 0; }
        memcpy(img, clean, sizeof img);
        mc_t c = mc_make(img, 0, 0, MO_W - 1, MO_H - 1, 0, 0);
        mo_draw_all(L, &c);
        for (int y = 60; y < 124; y++) for (int x = 56; x < 120; x++) inside += img[y * MO_W + x] != clean[y * MO_W + x] && (x - 88) * (x - 88) + (y - 92) * (y - 92) < 28 * 28;
    }
    CHECK(inside > 0);
}

int main(void)
{
    test_names();
    test_bounded_and_deterministic();
    test_end_of_life();
    test_dirty_rectangles();
    test_draws_something_and_stays_behind();
    test_zzz();
    test_governor_share_and_layers();
    test_thunder_and_fireworks();
    test_sizes();
    test_zones();
    test_presets();
    test_caps_and_shedding();
    test_protected_ellipses();
    if (fails) {
        printf("%d failed\n", fails);
        return 1;
    }
    printf("overlay_core_test: all passed\n");
    return 0;
}
