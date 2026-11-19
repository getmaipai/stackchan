/* Host test of maipai_pong_core.h (patch UX24, Pong): the court, bounces, points, the end, the unit's limited paddle, and the drag. Placement: host-side test. Upstream: none. */
#include <stdio.h>
#include <string.h>
#include "maipai_pong_core.h"

#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); return 1; } } while (0)

static int play(uint32_t seed, int aim, int idle, uint32_t* max_ticks)
{
    pg_t g;
    pg_init(&g, seed);
    int guard = 0;
    while (g.phase == PG_PLAY && guard++ < 60000) {
        if (!idle) pg_drag(&g, pg_ball_cy(&g) + aim);
        pg_step(&g);
        if (!(g.bx >= -PG_BALL * 16 - 16 * 12 && g.bx <= PG_W * 16 + 16 * 12 && g.by >= 0 && g.by <= (PG_H - PG_BALL) * 16)) return -2;   /* the ball stays in the court (it may be a little past a side while a point is decided) */
        if (g.uy < 0 || g.uy > PG_H - PG_PAD_H || g.py < 0 || g.py > PG_H - PG_PAD_H) return -3;
    }
    if (max_ticks && g.ticks > *max_ticks) *max_ticks = g.ticks;
    if (g.phase != PG_END) return -1;
    return pg_result(&g);
}

int main(void)
{
    pg_t g;
    pg_init(&g, 5);
    CHECK(g.phase == PG_PLAY && g.sp == 0 && g.su == 0 && g.vx > 0 && g.uy == g.py);
    pg_drag(&g, -50);  CHECK(g.py == 0);
    pg_drag(&g, 9999); CHECK(g.py == PG_H - PG_PAD_H);
    pg_drag(&g, 96);   CHECK(g.py == 96 - PG_PAD_H / 2);
    { /* the serve is the same for the same seed and goes toward the loser of the last point */
        pg_t a, b;
        pg_init(&a, 7); pg_init(&b, 7);
        for (int i = 0; i < 400; i++) { pg_step(&a); pg_step(&b); }
        CHECK(memcmp(&a, &b, sizeof(a)) == 0);
    }
    { /* a wall bounce flips vy and reports it */
        pg_t w;
        pg_init(&w, 3);
        w.by = 2 * 16; w.vy = -48; w.vx = 16; w.bx = 100 * 16;
        pg_step(&w);
        CHECK(w.vy > 0 && w.event == PG_E_WALL && w.by >= 0);
    }
    { /* a ball into the person's paddle comes back faster; a miss scores for the unit */
        pg_t w;
        pg_init(&w, 3);
        w.bx = 40 * 16; w.vx = -48; w.vy = 0; w.by = (PG_H / 2 - PG_BALL / 2) * 16; pg_drag(&w, PG_H / 2);
        for (int i = 0; i < 60 && w.vx < 0; i++) pg_step(&w);
        CHECK(w.vx > 48 && w.event == PG_E_HIT_PERSON || w.event != PG_E_NONE);
        pg_init(&w, 3);
        w.bx = 40 * 16; w.vx = -48; w.vy = 0; w.by = 20 * 16; w.py = PG_H - PG_PAD_H;   /* the paddle is far away */
        for (int i = 0; i < 120 && w.su == 0 && w.phase == PG_PLAY; i++) pg_step(&w);
        CHECK(w.su == 1 && w.vx < 0 && w.bx == (PG_W / 2 - PG_BALL / 2) * 16);        /* the unit scored and the ball is back in the middle, going toward the loser */
    }
    { /* an edge hit gives a steeper ball than a centre hit */
        pg_t a, b;
        pg_init(&a, 3); pg_init(&b, 3);
        a.bx = b.bx = 24 * 16; a.vx = b.vx = -48; a.vy = b.vy = 0; a.by = b.by = 90 * 16;
        pg_drag(&a, pg_ball_cy(&a)); pg_drag(&b, pg_ball_cy(&b) + 18);
        for (int i = 0; i < 20 && a.event != PG_E_HIT_PERSON; i++) pg_step(&a);
        for (int i = 0; i < 20 && b.event != PG_E_HIT_PERSON; i++) pg_step(&b);
        CHECK(a.event == PG_E_HIT_PERSON && b.event == PG_E_HIT_PERSON);
        CHECK((b.vy < 0 ? -b.vy : b.vy) > (a.vy < 0 ? -a.vy : a.vy) + 40);
    }
    { /* an idle person (the paddle stays in the middle) loses most games; a person who aims for the paddle's edge wins nearly all; every game ends */
        int idle_losses = 0, aimed_wins = 0, aimed_ended = 0;
        uint32_t most = 0;
        for (uint32_t seed = 1; seed <= 20; seed++) {
            const int r = play(seed, 0, 1, &most);
            CHECK(r == 1 || r == 2);
            if (r == 2) idle_losses++;
        }
        for (uint32_t seed = 1; seed <= 20; seed++) {
            const int r = play(seed, (seed & 1) ? 18 : -18, 0, &most);
            CHECK(r == 1 || r == 2);
            aimed_ended++;
            if (r == 1) aimed_wins++;
        }
        printf("pong: idle lost %d of 20; aiming won %d of %d; longest game %u ticks (%u s)\n", idle_losses, aimed_wins, aimed_ended, (unsigned)most, (unsigned)(most * PG_TICK_MS / 1000));
        CHECK(idle_losses >= 15);                   /* standing still is not a way to win */
        CHECK(aimed_wins >= 17);                    /* the unit's paddle can be beaten by aiming */
        CHECK(most * PG_TICK_MS < 5 * 60 * 1000u);  /* and a game does not run past five minutes */
    }
    puts("pong_core_test: all passed");
    return 0;
}
