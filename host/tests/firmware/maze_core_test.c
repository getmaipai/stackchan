/* Host test of maipai_maze_core.h (patch UX28, Maze): every seed makes a perfect maze, the marble rolls with the lean and stops at walls without passing through, the autopilot solves every maze,
 * and the dirty rectangles cover what moved. Placement: host-side test. Upstream: none. */
#include <stdio.h>
#include <string.h>
#include "maipai_maze_core.h"

#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); return 1; } } while (0)

static int opposite(int d) { return d == MZ_N_ ? MZ_S : (d == MZ_S ? MZ_N_ : (d == MZ_E ? MZ_W : MZ_E)); }

int main(void)
{
    /* every seed: a perfect maze: 126 openings (63 passages, each seen from both cells), every opening matched on the other side, none through the border, all 64 cells reachable */
    for (uint32_t seed = 1; seed <= 300; seed++) {
        mz_t g;
        mz_init(&g, seed);
        int openings = 0;
        for (int c = 0; c < MZ_CELLS; c++) {
            const int x = c % MZ_N, y = c / MZ_N;
            for (int d = 1; d <= 8; d <<= 1) {
                if (!(g.open[c] & d)) continue;
                openings++;
                const int nb = c + (d == MZ_N_ ? -MZ_N : (d == MZ_S ? MZ_N : (d == MZ_E ? 1 : -1)));
                CHECK(!(d == MZ_N_ && y == 0) && !(d == MZ_S && y == MZ_N - 1) && !(d == MZ_E && x == MZ_N - 1) && !(d == MZ_W && x == 0));
                CHECK(g.open[nb] & opposite(d));
            }
        }
        CHECK(openings == 126);
        int seen[MZ_CELLS] = {0}, queue[MZ_CELLS], qh = 0, qt = 0;
        queue[qt++] = 0; seen[0] = 1;
        while (qh < qt) {
            const int c = queue[qh++];
            const int nb[4] = {(g.open[c] & MZ_N_) ? c - MZ_N : -1, (g.open[c] & MZ_E) ? c + 1 : -1, (g.open[c] & MZ_S) ? c + MZ_N : -1, (g.open[c] & MZ_W) ? c - 1 : -1};
            for (int k = 0; k < 4; k++) if (nb[k] >= 0 && !seen[nb[k]]) { seen[nb[k]] = 1; queue[qt++] = nb[k]; }
        }
        CHECK(qt == MZ_CELLS);
        CHECK(mz_next_toward_goal(&g, 0) >= 0 && mz_next_toward_goal(&g, MZ_CELLS - 1) == -1);
    }
    { mz_t a, b, c; mz_init(&a, 9); mz_init(&b, 9); mz_init(&c, 10); CHECK(memcmp(a.open, b.open, MZ_CELLS) == 0 && memcmp(a.open, c.open, MZ_CELLS) != 0); }
    { /* the marble starts in the middle of the top left cell, flat does not move it, a lean rolls it, forward is up (it rolls to the top border and stays there) */
        mz_t g;
        mz_init(&g, 4);
        const int x0 = g.x, y0 = g.y;
        for (int i = 0; i < 30; i++) mz_step(&g, 0, 0);
        CHECK(g.x == x0 && g.y == y0);
        mz_t u; mz_init(&u, 4);
        for (int i = 0; i < 30; i++) mz_step(&u, 0, 800);                  /* forward at the top border: no move, and it touches */
        CHECK((u.y >> 8) == MZ_R + MZ_WALL / 2 && u.touched);   /* it rolls up to the border and rests against it */
        mz_t w; mz_init(&w, 4);
        for (int i = 0; i < 30; i++) mz_step(&w, -800, 0);                 /* left at the left border */
        CHECK((w.x >> 8) == MZ_R + MZ_WALL / 2);
        mz_t s; mz_init(&s, 4);
        for (int i = 0; i < 12; i++) mz_step(&s, 60, 0);                   /* a small lean moves it too */
        CHECK(s.x > x0 || !(s.open[0] & MZ_E));
    }
    { /* a marble never ends up inside a wall, and never leaves the maze, whatever the lean (a pseudo-random lean for 60 seconds on 40 mazes) */
        for (uint32_t seed = 1; seed <= 40; seed++) {
            mz_t g;
            mz_init(&g, seed);
            uint32_t r = seed * 7919u;
            int roll = 0, pitch = 0;
            for (int t = 0; t < 30 * 60 && g.phase == MZ_PLAY; t++) {
                if (t % 20 == 0) { r = r * 1664525u + 1013904223u; roll = (int)((r >> 8) % 2001u) - 1000; r = r * 1664525u + 1013904223u; pitch = (int)((r >> 8) % 2001u) - 1000; }
                mz_step(&g, roll, pitch);
                CHECK(!mz_hits(&g, g.x, g.y));
                CHECK((g.x >> 8) > 0 && (g.x >> 8) < MZ_N * MZ_CELL && (g.y >> 8) > 0 && (g.y >> 8) < MZ_N * MZ_CELL);
            }
        }
    }
    { /* the autopilot solves every maze, in a sensible time; the time is counted; a won game stays won */
        int won = 0, worst = 0;
        long sum = 0;
        for (uint32_t seed = 1; seed <= 100; seed++) {
            mz_t g;
            mz_init(&g, seed);
            int r, p, t = 0;
            while (g.phase == MZ_PLAY && t++ < 30 * 120) { mz_autopilot(&g, &r, &p); mz_step(&g, r, p); }
            if (g.phase == MZ_WON) { won++; sum += mz_seconds(&g); if (mz_seconds(&g) > worst) worst = mz_seconds(&g); }
            const int s0 = mz_seconds(&g);
            mz_step(&g, 500, 500);
            CHECK(mz_seconds(&g) == s0);
        }
        printf("maze: the autopilot solved %d of 100 mazes, mean %ld s, slowest %d s\n", won, sum / (won ? won : 1), worst);
        CHECK(won == 100 && worst <= 90);
    }
    { /* dirty rectangles: the marble old and new, the goal pulse, the time chip; small */
        long total = 0, worst = 0, steps = 0;
        for (uint32_t seed = 1; seed <= 12; seed++) {
            mz_t s;
            mz_init(&s, seed);
            for (int t = 0; t < 30 * 90 && s.phase == MZ_PLAY; t++) {
                mz_t n = s;
                int r, p;
                mz_autopilot(&n, &r, &p);
                mz_step(&n, r, p);
                mz_rect_t rr[4];
                const int cnt = mz_dirty(&s, &n, rr);
                CHECK(cnt >= 2 && cnt <= 4);
                const int xs[2] = {mz_marble_px_x(&s), mz_marble_px_x(&n)}, ys[2] = {mz_marble_px_y(&s), mz_marble_px_y(&n)};
                for (int k = 0; k < 2; k++) {
                    int hit = 0;
                    for (int i = 0; i < cnt; i++) hit |= xs[k] - MZ_R >= rr[i].x && ys[k] - MZ_R >= rr[i].y && xs[k] + MZ_R <= rr[i].x + rr[i].w && ys[k] + MZ_R <= rr[i].y + rr[i].h;
                    CHECK(hit);
                }
                long px = 0;
                for (int i = 0; i < cnt; i++) px += (long)rr[i].w * rr[i].h;
                total += px; steps++;
                if (px > worst) worst = px;
                s = n;
            }
        }
        printf("maze: dirty area per tick: mean %ld px, worst %ld px\n", total / steps, worst);
        CHECK(total / steps < 1200 && worst < 8000);
    }
    /* touch geometry: the maze is inside the glass, 8 px clear of the side column */
    CHECK(MZ_BX >= 8 && MZ_BX + MZ_N * MZ_CELL + 8 <= 216 && MZ_BY + MZ_N * MZ_CELL + 8 <= 240 && MZ_CELL >= 24);
    puts("maze_core_test: all passed");
    return 0;
}
