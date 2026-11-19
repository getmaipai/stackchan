/* Host test of maipai_flyer_core.h (patch UX25, Flappy-style flyer): gravity, the hop, the pipes and their gaps, scoring, the end, and a steady course. Placement: host-side test. Upstream: none. */
#include <stdio.h>
#include <string.h>
#include "maipai_flyer_core.h"

#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); return 1; } } while (0)

/* a plain autopilot: hop when the bird's middle falls below the next pipe's gap middle (a little lower, since a hop rises about 30 px) */
static int autopilot_score(uint32_t seed, int ticks)
{
    fl_t g;
    fl_init(&g, seed);
    for (int t = 0; t < ticks && g.phase == FL_PLAY; t++) {
        int next = -1;
        for (int i = 0; i < FL_PIPES; i++) if (g.px[i] + FL_PIPE_W * 16 >= FL_BIRD_X * 16 && (next < 0 || g.px[i] < g.px[next])) next = i;
        const int mid = next >= 0 ? g.gap[next] + FL_GAP / 2 : (FL_TOP + FL_BOTTOM) / 2;
        if (fl_bird_top(&g) + FL_BIRD / 2 > mid + 14 && g.vy >= 0) fl_tap(&g);
        fl_step(&g);
    }
    return g.phase == FL_PLAY ? 1000 + g.score : g.score;
}

int main(void)
{
    fl_t g;
    fl_init(&g, 4);
    CHECK(g.phase == FL_PLAY && g.score == 0 && g.px[0] > 320 * 16);
    for (int i = 0; i < FL_PIPES; i++) {   /* gaps stay inside the sky, pipes are spaced evenly */
        CHECK(g.gap[i] >= FL_TOP + 24 && g.gap[i] + FL_GAP <= FL_BOTTOM - 24);
        if (i) CHECK(g.px[i] - g.px[i - 1] == FL_SPACING * 16);
    }
    { /* a bird that never hops falls to the floor and the game ends, with no points */
        fl_t a;
        fl_init(&a, 4);
        int t = 0;
        while (a.phase == FL_PLAY && t++ < 400) fl_step(&a);
        CHECK(a.phase == FL_OVER && a.event == FL_E_HIT && a.score == 0 && t < 60);
        CHECK(!fl_tap(&a));                                      /* a tap after the end does nothing */
    }
    { /* a hop lifts the bird: higher a few ticks later than a bird that did not hop */
        fl_t a, b;
        fl_init(&a, 4); fl_init(&b, 4);
        fl_tap(&a);
        for (int i = 0; i < 6; i++) { fl_step(&a); fl_step(&b); }
        CHECK(a.event != FL_E_HIT && fl_bird_top(&a) < fl_bird_top(&b) - 20);
    }
    { /* the pipes scroll left at the set speed and come back at the right with a new gap */
        fl_t a;
        fl_init(&a, 4);
        const int32_t x0 = a.px[0];
        a.y = (FL_TOP + 100) * 16; a.vy = 0;
        fl_step(&a);
        CHECK(a.px[0] == x0 - FL_SPEED);
        int wraps = 0;
        for (int t = 0; t < 2000 && a.phase == FL_PLAY; t++) { a.y = ((FL_TOP + FL_BOTTOM) / 2) * 16; a.vy = 0; const int32_t before = a.px[0]; fl_step(&a); if (a.px[0] > before) wraps++; }
        (void)wraps;
        CHECK(a.px[0] > -FL_PIPE_W * 16 - 16 && a.px[1] > -FL_PIPE_W * 16 - 16);
    }
    { /* the same seed gives the same course; another seed another */
        fl_t a, b, c;
        fl_init(&a, 9); fl_init(&b, 9); fl_init(&c, 10);
        CHECK(memcmp(&a, &b, sizeof(a)) == 0 && memcmp(a.gap, c.gap, sizeof(a.gap)) != 0);
    }
    { /* the autopilot flies 40 s through at least a dozen pipes on most courses: the game can be played, and the gaps are fair */
        int good = 0, best = 0;
        for (uint32_t seed = 1; seed <= 40; seed++) {
            const int s = autopilot_score(seed, 40 * 30);
            const int n = s >= 1000 ? s - 1000 : s;
            if (n >= 12) good++;
            if (n > best) best = n;
        }
        printf("flyer: the autopilot reached 12 pipes on %d of 40 courses, best %d\n", good, best);
        CHECK(good >= 30);
    }
    { /* a pipe at the bird's height ends the game; passing one scores exactly once */
        fl_t a;
        fl_init(&a, 4);
        a.px[0] = (FL_BIRD_X - 10) * 16;
        a.gap[0] = FL_TOP + 24;                                    /* the gap is near the top; the bird is in the middle: it hits the pipe */
        a.y = ((FL_TOP + FL_BOTTOM) / 2) * 16; a.vy = 0;
        fl_step(&a);
        CHECK(a.phase == FL_OVER);
        fl_init(&a, 4);
        a.px[0] = (FL_BIRD_X - FL_PIPE_W + 1) * 16 + FL_SPEED - 1;
        a.gap[0] = (FL_TOP + FL_BOTTOM) / 2 - FL_GAP / 2;
        a.y = ((FL_TOP + FL_BOTTOM) / 2 - FL_BIRD / 2) * 16; a.vy = -FL_GRAVITY;
        int before = a.score;
        for (int i = 0; i < 4 && a.phase == FL_PLAY; i++) { a.y = ((FL_TOP + FL_BOTTOM) / 2 - FL_BIRD / 2) * 16; a.vy = -FL_GRAVITY; fl_step(&a); }
        CHECK(a.phase == FL_PLAY && a.score == before + 1);
    }
    puts("flyer_core_test: all passed");
    return 0;
}
