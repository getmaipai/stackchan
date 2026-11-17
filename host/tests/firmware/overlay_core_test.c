/* Host test for the overlay engine (patch TA04): bounded particle state, deterministic seeds, the dirty rectangles that make
 * a partial flush correct, behind-the-face drawing, zzz placement, the governor share, end of life.
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
    mc_t c = {out, x1, y1, x2, y2, x2 - x1 + 1, 0};
    for (int l = 0; l < 2; l++) mo_draw(&layers[l], &c);
}

static uint32_t hash_state(const mo_layer_t* L)
{
    uint32_t h = 2166136261u;
    for (int i = 0; i < L->n; i++) {
        const uint8_t* b = (const uint8_t*)&L->p[i];
        for (size_t k = 0; k < sizeof L->p[i]; k++) h = (h ^ b[k]) * 16777619u;
    }
    return h ^ L->tick ^ ((uint32_t)L->s0 << 8);
}

static int caps_ok(const mo_layer_t* L)
{
    return L->n <= MO_MAX_P && L->n <= mo_cap(L->id, L->intensity) + 2 && L->ndirty <= MO_MAX_DIRTY;
}

static void test_names(void)
{
    CHECK(MO_COUNT == 17);
    const char* host[] = {"rain", "snow", "sun", "clouds", "wind", "thunder", "fog", "stars", "disco", "confetti", "fireworks",
                          "hearts", "steam", "balloons", "leaves", "zzz"};
    for (int i = 0; i < 16; i++) CHECK(mo_id(host[i]) != 0); /* the host's one list (reply_tags.OVERLAYS) */
    CHECK(mo_id("hail") == 0 && mo_id("") == 0);
    for (int i = 1; i < MO_COUNT; i++) CHECK(mo_id(MO_NAMES[i]) == i);
    CHECK(mo_layer_of(MO_RAIN) == 0 && mo_layer_of(MO_STARS) == 0 && mo_layer_of(MO_ZZZ) == 1 && mo_layer_of(MO_CONFETTI) == 1);
    CHECK(sizeof(mo_layer_t) * 2 < 1500); /* both layers: under 1.5 KB of static state */
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
            if (id != MO_SUN && id != MO_FOG) CHECK(hash_state(&a) != hash_state(&c) || id == MO_CLOUDS); /* another seed, another picture */
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
            mo_layer_t L[2];
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
                if (fading && (id == MO_SUN || id == MO_FOG || id == MO_DISCO || id == MO_CLOUDS || id == MO_STARS)) continue;
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
        mo_layer_t L[2];
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
    int spawns = 0, last_n = 0, max_alive = 0, minx = 999, maxx = -999, miny = 999, maxy = -999;
    for (int t = 0; t < 30 * 30; t++) { /* 30 seconds */
        mo_step(&L, 33);
        L.ndirty = 0;
        int born = 0;
        for (int i = 0; i < L.n; i++) born += L.p[i].age == 0;
        spawns += born;
        (void)last_n;
        if (L.n > max_alive) max_alive = L.n;
        for (int i = 0; i < L.n; i++) {
            const int x = mo_px(L.p[i].x), y = mo_px(L.p[i].y);
            if (x < minx) minx = x;
            if (x > maxx) maxx = x;
            if (y < miny) miny = y;
            if (y > maxy) maxy = y;
        }
    }
    CHECK(spawns >= 14 && spawns <= 26);      /* a z every 1.2 to 2 seconds */
    CHECK(max_alive >= 3 && max_alive <= 5);  /* three to five alive */
    CHECK(minx >= 258 && maxx + 12 <= 319);   /* right of the eyes (the big eyes end at x 256), inside the screen */
    CHECK(miny >= 14 && maxy <= 72);          /* above the eyes (they start at y 68) and not off the top */
    /* the glyph grows: three sizes over a life */
    mo_p_t p;
    memset(&p, 0, sizeof p);
    /* drawn pixels per size, on a clean canvas */
    static uint16_t buf[MO_W * MO_H];
    long px[3];
    for (int sz = 0; sz < 3; sz++) {
        face(buf, 0, 0, MO_W - 1, MO_H - 1);
        mc_t c = {buf, 0, 0, MO_W - 1, MO_H - 1, MO_W, 0};
        mo_draw_z(&c, 270, 30, sz, 0xFFFF, 255);
        px[sz] = 0;
        for (int i = 0; i < MO_W * MO_H; i++) px[sz] += buf[i] != BG && !((i % MO_W - 88) * (i % MO_W - 88) + (i / MO_W - 92) * (i / MO_W - 92) < 576) && !((i % MO_W - 232) * (i % MO_W - 232) + (i / MO_W - 92) * (i / MO_W - 92) < 576);
    }
    CHECK(px[0] > 10 && px[1] > px[0] && px[2] > px[1]);
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
    mo_layer_t two[2];
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
    CHECK(bursts >= 8 && maxn <= 28);
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
    if (fails) {
        printf("%d failed\n", fails);
        return 1;
    }
    printf("overlay_core_test: all passed\n");
    return 0;
}
