/* Host test of maipai_balance_core.h (patch UX27, Balance): the lean moves the ball, the plate shrinks, holes open and arm, falling ends the game, the autopilot can play, standing still cannot,
 * and the dirty rectangles cover what moved. Placement: host-side test. Upstream: none. */
#include <stdio.h>
#include <string.h>
#include "maipai_balance_core.h"

#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); return 1; } } while (0)

int main(void)
{
    bl_t g;
    bl_init(&g, 4);
    CHECK(g.phase == BL_PLAY && g.plate_r == BL_R0 && g.holes == 0 && bl_dist(g.x, g.y, 0, 0) >= 38 && bl_dist(g.x, g.y, 0, 0) <= 56);
    { /* flat: the ball stays; a lean rolls it toward the lean, forward is up the screen; a small lean (a dead-zone leftover of 60 permille) still moves it */
        bl_t a, b, c, d, e;
        bl_init(&a, 4); b = a; c = a; d = a; e = a;
        for (int i = 0; i < 20; i++) { bl_step(&a, 0, 0); bl_step(&b, 500, 0); bl_step(&c, -500, 0); bl_step(&d, 0, 500); bl_step(&e, 60, 0); }
        CHECK(a.x == g.x && a.y == g.y);
        CHECK(b.x > g.x + 16 * 256 && b.y == g.y);              /* right moves it right, not up or down */
        CHECK(c.x < g.x - 16 * 256);
        CHECK(d.y < g.y - 16 * 256 && d.x == g.x);              /* forward moves it up the screen */
        CHECK(e.x > g.x + 256);                                  /* a small lean moves it too: nothing is lost to rounding */
    }
    { /* the speed is capped, and friction brings a ball to rest */
        bl_t a;
        bl_init(&a, 4);
        a.holes = 0;
        for (int i = 0; i < 25 && a.phase == BL_PLAY; i++) bl_step(&a, 1000, 0);
        CHECK(a.vx <= BL_VMAX && a.vx >= -BL_VMAX);
        bl_t b;
        bl_init(&b, 4);
        b.vx = 1200;
        for (int i = 0; i < 90; i++) bl_step(&b, 0, 0);
        CHECK(b.phase == BL_PLAY && b.vx < 100 && b.vx > -100);
    }
    { /* rolling off the plate ends the game; the plate shrinks and holes open on their schedule and arm after a moment */
        bl_t a;
        bl_init(&a, 4);
        int n = 0;
        while (a.phase == BL_PLAY && n++ < 400) bl_step(&a, 1000, 0);
        CHECK(a.phase == BL_OVER && a.why == BL_WHY_EDGE && a.event == BL_E_FELL);
        bl_t b;
        bl_init(&b, 4);
        for (int i = 0; i < BL_SHRINK_TICKS * 3; i++) { bl_t before = b; bl_step(&b, 0, 0); (void)before; }
        CHECK(b.plate_r == BL_R0 - 3 || b.phase == BL_OVER);
        bl_t c;
        bl_init(&c, 4);
        for (int i = 0; i < BL_SPAWN_TICKS; i++) bl_step(&c, 0, 0);
        CHECK(c.holes == 1 && c.age[0] < BL_ARM_TICKS);
        const int hx = c.hx[0], hy = c.hy[0];
        for (int i = 0; i < BL_ARM_TICKS; i++) bl_step(&c, 0, 0);
        CHECK(c.holes >= 1 && c.age[0] >= BL_ARM_TICKS && c.hx[0] == hx && c.hy[0] == hy);
        /* a ball on a hole that is only a ring is safe, on an armed one it falls */
        bl_t d;
        bl_init(&d, 4);
        for (int i = 0; i < BL_SPAWN_TICKS; i++) bl_step(&d, 0, 0);
        d.x = d.hx[0] * 256; d.y = d.hy[0] * 256; d.vx = d.vy = 0;
        bl_step(&d, 0, 0);
        CHECK(d.phase == BL_PLAY);
        d.age[0] = BL_ARM_TICKS;
        bl_step(&d, 0, 0);
        CHECK(d.phase == BL_OVER && d.why == BL_WHY_HOLE);
    }
    { /* a hole never opens on the ball or within 32 px of another hole, and the holes stay on the plate */
        for (uint32_t seed = 1; seed <= 30; seed++) {
            bl_t a;
            bl_init(&a, seed);
            int r, p;
            for (int t = 0; t < 30 * 100 && a.phase == BL_PLAY; t++) {
                bl_autopilot(&a, &r, &p);
                bl_step(&a, r, p);
                if (a.event == BL_E_HOLE_OPENS) {
                    const int i = a.holes - 1;
                    CHECK(a.hx[i] * a.hx[i] + a.hy[i] * a.hy[i] <= (a.plate_r - BL_HOLE) * (a.plate_r - BL_HOLE));
                    CHECK(bl_dist(a.x, a.y, a.hx[i], a.hy[i]) >= 30);
                    for (int k = 0; k < i; k++) CHECK((a.hx[k] - a.hx[i]) * (a.hx[k] - a.hx[i]) + (a.hy[k] - a.hy[i]) * (a.hy[k] - a.hy[i]) >= 32 * 32);
                }
            }
        }
    }
    { /* the autopilot plays a long game; standing still does not last */
        int survived = 0, idle_dead = 0, idle_longest = 0;
        for (uint32_t seed = 1; seed <= 20; seed++) {
            bl_t a, b;
            bl_init(&a, seed); bl_init(&b, seed);
            int r, p, t = 0;
            while (a.phase == BL_PLAY && t++ < 30 * 150) { bl_autopilot(&a, &r, &p); bl_step(&a, r, p); }
            if (a.phase == BL_PLAY) survived++;
            t = 0;
            while (b.phase == BL_PLAY && t++ < 30 * 150) bl_step(&b, 0, 0);
            if (b.phase == BL_OVER) { idle_dead++; if (bl_seconds(&b) > idle_longest) idle_longest = bl_seconds(&b); }
        }
        printf("balance: the autopilot lasted 150 s on %d of 20 courses; standing still ended %d of 20, the longest %d s\n", survived, idle_dead, idle_longest);
        CHECK(survived >= 18 && idle_dead == 20 && idle_longest <= 110);
    }
    { /* the same seed gives the same course; the dirty rectangles cover the ball's old and new place and stay small */
        bl_t a, b;
        bl_init(&a, 9); bl_init(&b, 9);
        for (int i = 0; i < 100; i++) { bl_step(&a, 300, -200); bl_step(&b, 300, -200); }
        CHECK(memcmp(&a, &b, sizeof(a)) == 0);
        long total = 0, worst = 0, steps = 0;
        for (uint32_t seed = 1; seed <= 12; seed++) {
            bl_t s;
            bl_init(&s, seed);
            for (int t = 0; t < 30 * 90 && s.phase == BL_PLAY; t++) {
                bl_t n = s;
                int r, p;
                bl_autopilot(&n, &r, &p);
                bl_step(&n, r, p);
                bl_rect_t rr[6];
                const int cnt = bl_dirty(&s, &n, rr);
                CHECK(cnt >= 2 && cnt <= 6);
                const int xs[2] = {bl_ball_px_x(&s), bl_ball_px_x(&n)}, ys[2] = {bl_ball_px_y(&s), bl_ball_px_y(&n)};
                for (int k = 0; k < 2; k++) {
                    int hit = 0;
                    for (int i = 0; i < cnt; i++) hit |= xs[k] - BL_BALL >= rr[i].x && ys[k] - BL_BALL >= rr[i].y && xs[k] + BL_BALL <= rr[i].x + rr[i].w && ys[k] + BL_BALL <= rr[i].y + rr[i].h;
                    CHECK(hit);
                }
                long px = 0;
                for (int i = 0; i < cnt; i++) px += (long)rr[i].w * rr[i].h;
                total += px; steps++;
                if (px > worst) worst = px;
                s = n;
            }
        }
        printf("balance: dirty area per tick: mean %ld px, worst %ld px (the screen is 76,800)\n", total / steps, worst);
        CHECK(total / steps < 2500 && worst < 40000);
    }
    puts("balance_core_test: all passed");
    return 0;
}
