/* Host test of maipai_reversi_core.h (patch UX22, Reversi): the rules, passes, the end, the unit's move and its cost, and the touch mapping. Placement: host-side test. Upstream: none. */
#include <stdio.h>
#include <string.h>
#include "maipai_reversi_core.h"

#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); return 1; } } while (0)

/* a plain pseudo-random choice for the "other player" in the playouts */
static uint32_t s_rng = 12345;
static uint32_t rnd(void) { s_rng = s_rng * 1664525u + 1013904223u; return s_rng >> 8; }

static int random_person_move(rv_t* g)
{
    int cells[64], n = 0;
    for (int i = 0; i < RV_CELLS; i++) if (rv_legal(g, i, RV_PERSON)) cells[n++] = i;
    if (n == 0) return 0;
    return rv_person_move(g, cells[rnd() % (uint32_t)n]);
}

int main(void)
{
    rv_t g;
    rv_init(&g);
    CHECK(rv_discs(&g, RV_PERSON) == 2 && rv_discs(&g, RV_UNIT) == 2 && g.turn == RV_PERSON && g.last == -1);
    CHECK(rv_count_moves(g.b, RV_PERSON) == 4 && rv_count_moves(g.b, RV_UNIT) == 4);
    /* the four first moves of black: (2,3) (3,2) (4,5) (5,4) i.e. cells 19, 26, 37, 44 */
    CHECK(rv_legal(&g, 19, RV_PERSON) && rv_legal(&g, 26, RV_PERSON) && rv_legal(&g, 37, RV_PERSON) && rv_legal(&g, 44, RV_PERSON));
    CHECK(!rv_legal(&g, 0, RV_PERSON) && !rv_legal(&g, 27, RV_PERSON) && !rv_legal(&g, 63, RV_PERSON));    /* a corner, an occupied cell, far away */
    CHECK(rv_person_move(&g, 0) == 0 && g.turn == RV_PERSON);                                              /* an illegal move changes nothing */
    CHECK(rv_person_move(&g, 19) == 1 && rv_discs(&g, RV_PERSON) == 4 && rv_discs(&g, RV_UNIT) == 1 && g.b[27] == RV_PERSON && g.turn == RV_UNIT && g.last == 19);
    CHECK(rv_person_move(&g, 26) == 0);                                                                    /* not the person's turn */
    const int u = rv_unit_move(&g);
    CHECK(u >= 0 && g.turn == RV_PERSON && g.b[u] == RV_UNIT && rv_unit_move(&g) == -1);
    /* a flip in several directions at once: black at the corner of a hand-made position */
    {
        rv_t h;
        memset(&h, 0, sizeof(h));
        h.b[1] = RV_UNIT; h.b[2] = RV_PERSON;                     /* row: _ U P at the top left */
        h.b[8] = RV_UNIT; h.b[16] = RV_PERSON;                    /* column */
        h.b[9] = RV_UNIT; h.b[18] = RV_PERSON;                    /* diagonal */
        CHECK(rv_flips(h.b, 0, RV_PERSON, 0) == 3);
        CHECK(rv_flips(h.b, 0, RV_PERSON, 1) == 3 && h.b[1] == RV_PERSON && h.b[8] == RV_PERSON && h.b[9] == RV_PERSON && h.b[0] == RV_PERSON);
    }
    /* a pass: the unit has no move but the person has */
    {
        rv_t h;
        memset(&h, 0, sizeof(h));
        h.b[0] = RV_PERSON; h.b[1] = RV_UNIT; h.turn = RV_PERSON; h.phase = RV_PLAY;
        CHECK(rv_count_moves(h.b, RV_PERSON) == 1 && rv_count_moves(h.b, RV_UNIT) == 0);
        CHECK(rv_person_move(&h, 2) == 1);                       /* P U P flips the white disc: now only black discs remain */
        CHECK(h.phase == RV_END && rv_result(&h) == RV_WON);     /* neither side can move: the end, black wins */
        memset(&h, 0, sizeof(h));
        h.b[0] = RV_PERSON; h.b[1] = RV_UNIT; h.b[48] = RV_UNIT; h.b[56] = RV_PERSON; h.turn = RV_PERSON; h.phase = RV_PLAY;   /* a row P U _ and a column _ U P: two moves for the person, none for the unit afterwards */
        CHECK(rv_person_move(&h, 2) == 1 && h.turn == RV_PERSON && h.passes == 1 && h.last_pass == 1 && h.phase == RV_PLAY);   /* the unit has no reply, so the person moves again */
    }
    /* whole games: the unit against a random person: every game ends, the counts add up, and the unit mostly wins */
    {
        int unit_wins = 0, person_wins = 0, draws = 0;
        uint32_t max_nodes = 0;
        for (int game = 0; game < 120; game++) {
            s_rng = 1000u + (uint32_t)game;
            rv_init(&g);
            int guard = 0;
            while (g.phase == RV_PLAY && guard++ < 200) {
                if (g.turn == RV_PERSON) CHECK(random_person_move(&g) > 0);
                else { CHECK(rv_unit_move(&g) >= 0); if (g.nodes > max_nodes) max_nodes = g.nodes; }
            }
            CHECK(g.phase == RV_END && guard < 200);
            CHECK(rv_discs(&g, RV_PERSON) + rv_discs(&g, RV_UNIT) <= 64);
            const int r = rv_result(&g);
            CHECK(r == RV_WON || r == RV_LOST || r == RV_DRAW);
            if (r == RV_LOST) unit_wins++; else if (r == RV_WON) person_wins++; else draws++;
        }
        CHECK(unit_wins >= 100);                                 /* a two-ply search beats random play in most games (measured: see the spec) */
        CHECK(max_nodes <= 800);                                 /* one unit move searches at most 800 nodes: a bounded slice */
        printf("reversi: unit won %d, person %d, drawn %d of 120; most nodes in one move %u\n", unit_wins, person_wins, draws, (unsigned)max_nodes);
    }
    /* touch mapping: each cell's center maps back to itself; the board is 8 px clear of the score column and at least 24 px per cell */
    for (int i = 0; i < RV_CELLS; i++) {
        int x, y, w, h;
        rv_cell_box(i, &x, &y, &w, &h);
        CHECK(w >= 24 && h >= 24 && rv_hit(x + w / 2, y + h / 2) == i && rv_hit(x, y) == i && rv_hit(x + w - 1, y + h - 1) == i);
    }
    CHECK(rv_hit(7, 100) == -1 && rv_hit(100, 29) == -1 && rv_hit(100, 231) == -1 && rv_hit(209, 100) == -1);
    { int x, y, w, h; rv_cell_box(63, &x, &y, &w, &h); CHECK(x + w + 8 <= 216 && y + h + 8 <= 240); }
    puts("reversi_core_test: all passed");
    return 0;
}
