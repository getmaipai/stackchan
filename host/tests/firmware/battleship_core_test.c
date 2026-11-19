/* Host test of maipai_battleship_core.h (patch UX23, Battleship-lite): the hidden fleet, shots, sinking, the end, and the touch mapping. Placement: host-side test. Upstream: none. */
#include <stdio.h>
#include <string.h>
#include "maipai_battleship_core.h"

#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); return 1; } } while (0)

int main(void)
{
    /* every seed hides the same fleet shape (3, 2, 2), inside the sea, straight, with no two ships touching even at a corner */
    for (uint32_t seed = 1; seed < 2000; seed++) {
        bs_t g;
        bs_init(&g, seed);
        int count[4] = {0, 0, 0, 0};
        for (int i = 0; i < BS_CELLS; i++) { CHECK(g.ship[i] <= 3); count[g.ship[i]]++; }
        CHECK(count[1] == 3 && count[2] == 2 && count[3] == 2);
        for (int id = 1; id <= 3; id++) {
            int rows[2] = {99, -1}, cols[2] = {99, -1};
            for (int i = 0; i < BS_CELLS; i++) if (g.ship[i] == id) {
                const int r = i / 6, c = i % 6;
                if (r < rows[0]) rows[0] = r;
                if (r > rows[1]) rows[1] = r;
                if (c < cols[0]) cols[0] = c;
                if (c > cols[1]) cols[1] = c;
            }
            CHECK((rows[0] == rows[1]) != (cols[0] == cols[1]) || g.len[id] == 1);   /* straight: one row or one column */
            CHECK((rows[1] - rows[0] + 1) * (cols[1] - cols[0] + 1) == g.len[id]);  /* and whole, no gap */
        }
        for (int i = 0; i < BS_CELLS; i++) {
            if (!g.ship[i]) continue;
            for (int dr = -1; dr <= 1; dr++) for (int dc = -1; dc <= 1; dc++) {
                const int r = i / 6 + dr, c = i % 6 + dc;
                if (r < 0 || r >= 6 || c < 0 || c >= 6) continue;
                const int o = g.ship[r * 6 + c];
                CHECK(o == 0 || o == g.ship[i]);   /* a neighbor cell is water or the same ship */
            }
        }
        CHECK(g.shots_left == BS_SHOTS && g.ships_left == 3 && g.phase == BS_PLAY && g.last == -1);
    }
    { bs_t a, b, c; bs_init(&a, 9); bs_init(&b, 9); bs_init(&c, 10); CHECK(memcmp(a.ship, b.ship, BS_CELLS) == 0 && memcmp(a.ship, c.ship, BS_CELLS) != 0); }
    { /* a shot: miss, hit, sunk, repeat ignored */
        bs_t g;
        bs_init(&g, 3);   /* 000022 / 000000 / 000003 / 000003 / 000000 / 001110 */
        CHECK(bs_fire(&g, 0) == BS_R_MISS && g.seen[0] == BS_MISS && g.shots_left == BS_SHOTS - 1 && g.last == 0);
        CHECK(bs_fire(&g, 0) == BS_R_IGNORED && g.shots_left == BS_SHOTS - 1);            /* the same cell twice costs nothing */
        CHECK(bs_fire(&g, -1) == BS_R_IGNORED && bs_fire(&g, 36) == BS_R_IGNORED);
        CHECK(bs_fire(&g, 4) == BS_R_HIT && g.seen[4] == BS_HIT && g.ships_left == 3);
        CHECK(bs_fire(&g, 5) == BS_R_SUNK && g.seen[4] == BS_SUNK && g.seen[5] == BS_SUNK && g.ships_left == 2);   /* the whole ship shows as sunk */
        CHECK(bs_fire(&g, 17) == BS_R_HIT && bs_fire(&g, 23) == BS_R_SUNK && g.ships_left == 1);
        CHECK(bs_fire(&g, 32) == BS_R_HIT && bs_fire(&g, 33) == BS_R_HIT);
        CHECK(bs_fire(&g, 34) == BS_R_WON && g.phase == BS_WON && g.ships_left == 0);                                  /* the last cell of the last ship wins */
        CHECK(bs_fire(&g, 1) == BS_R_IGNORED);                                                                        /* nothing after the end */
    }
    { /* as many misses as there are shots lose */
        bs_t g;
        bs_init(&g, 3);
        int fired = 0, last = 0;
        for (int i = 0; i < BS_CELLS && g.phase == BS_PLAY; i++) if (!g.ship[i]) { last = bs_fire(&g, i); fired++; }
        CHECK(g.phase == BS_LOST && last == BS_R_LOST && fired == BS_SHOTS && g.shots_left == 0 && g.ships_left == 3);
    }
    { /* a careful search (a hit's neighbors first) usually wins within the shots: the game can be won */
        int wins = 0;
        for (uint32_t seed = 1; seed < 200; seed++) {
            bs_t g;
            bs_init(&g, seed);
            int tried[BS_CELLS] = {0};
            for (int guard = 0; guard < 80 && g.phase == BS_PLAY; guard++) {
                int pick = -1;
                for (int i = 0; i < BS_CELLS && pick < 0; i++) {   /* next to a hit that is not sunk yet */
                    if (g.seen[i] != BS_HIT) continue;
                    const int nb[4] = {i - 6, i + 6, (i % 6) ? i - 1 : -1, (i % 6 < 5) ? i + 1 : -1};
                    for (int k = 0; k < 4; k++) if (nb[k] >= 0 && nb[k] < BS_CELLS && g.seen[nb[k]] == BS_UNSEEN) { pick = nb[k]; break; }
                }
                if (pick < 0) for (int i = 0; i < BS_CELLS; i++) if (g.seen[i] == BS_UNSEEN && ((i / 6 + i % 6) % 2 == 0)) { pick = i; break; }   /* a checkerboard: every ship of length 2 or more has a cell on it */
                if (pick < 0) for (int i = 0; i < BS_CELLS; i++) if (g.seen[i] == BS_UNSEEN) { pick = i; break; }
                (void)tried;
                bs_fire(&g, pick);
            }
            if (g.phase == BS_WON) wins++;
        }
        CHECK(wins >= 80 && wins < 180);   /* winnable (about half the games with a sensible search), and not a sure thing */
    }
    /* touch mapping: every cell's own box maps back to it; the gaps belong to a neighbor; outside is -1; the sea is 8 px clear of the side panel */
    for (int i = 0; i < BS_CELLS; i++) {
        int x, y, w, h;
        bs_cell_box(i, &x, &y, &w, &h);
        CHECK(w >= 24 && h >= 24 && bs_hit(x, y) == i && bs_hit(x + w - 1, y + h - 1) == i && bs_hit(x + w / 2, y + h / 2) == i);
    }
    CHECK(bs_hit(7, 100) == -1 && bs_hit(100, 33) == -1 && bs_hit(100, 226) == -1 && bs_hit(200, 100) == -1);
    { int x, y, w, h; bs_cell_box(35, &x, &y, &w, &h); CHECK(x + w + 8 <= 216 && y + h + 8 <= 240); }
    puts("battleship_core_test: all passed");
    return 0;
}
