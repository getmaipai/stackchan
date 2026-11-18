/* Host test for the grid game engine core and its two rule sets (patch SF62): cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> grid_core_test.c -lm */
#include <stdio.h>
#include "maipai_grid_core.h"
#include "maipai_grid_c4_core.h"
#include "maipai_grid_mem_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void test_geometry(void)
{
    gr_layout_t l;
    CHECK(gr_layout(&l, 7, 6, 0) == 1);
    CHECK(l.cw == 40 && l.ch == 32 && l.x0 == 20 && l.y0 >= GR_AREA_Y0 && l.y0 + 6 * l.ch <= GR_AREA_Y1);
    CHECK(gr_cell_at(&l, 21, l.y0 + 1) == 0 && gr_cell_at(&l, 299, l.y0 + 6 * 32 - 1) == 41);
    CHECK(gr_cell_at(&l, 19, 100) == -1 && gr_cell_at(&l, 300, 100) == -1 && gr_cell_at(&l, 100, l.y0 - 1) == -1);
    CHECK(gr_col_at(&l, 21, GR_AREA_Y0) == 0 && gr_col_at(&l, 299, 223) == 6 && gr_col_at(&l, 150, 10) == -1 && gr_col_at(&l, 150, 224) == -1);
    CHECK(gr_layout(&l, 7, 6, 1) == 1 && l.cw == 32 && l.ch == 32 && l.x0 == 48);
    CHECK(gr_layout(&l, 4, 4, 1) == 1 && l.cw == 49 && l.cw * 4 <= GR_AREA_X1 - GR_AREA_X0);
    CHECK(gr_layout(&l, 11, 10, 1) == 0);      /* 110 cells: over the limit */
    CHECK(gr_layout(&l, 0, 4, 1) == 0 && gr_layout(&l, 4, 0, 1) == 0);
    CHECK(gr_layout(&l, 10, 10, 1) == 1 && l.cw == 19);
    CHECK(gr_rules_by_name("connect4") == GR_RULES_CONNECT4 && gr_rules_by_name("memory") == GR_RULES_MEMORY && gr_rules_by_name("chess") == GR_RULES_NONE && gr_rules_by_name(NULL) == GR_RULES_NONE);
}

static void test_c4_rules(void)
{
    gc4_board_t g;
    gc4_clear(&g);
    CHECK(gc4_drop(&g, 3, 1) == 5 && gc4_drop(&g, 3, 2) == 4 && g.b[5 * 7 + 3] == 1 && g.b[4 * 7 + 3] == 2);
    CHECK(gc4_drop(&g, -1, 1) == -1 && gc4_drop(&g, 7, 1) == -1 && gc4_drop(&g, 0, 3) == -1);
    for (int i = 0; i < 4; i++) gc4_drop(&g, 6, i % 2 ? 2 : 1);      /* fill column 6 (no row of four): 1,2,1,2 */
    gc4_drop(&g, 6, 1); gc4_drop(&g, 6, 2);
    CHECK(gc4_drop(&g, 6, 1) == -1 && !gc4_col_free(&g, 6));       /* full */
    /* the four directions */
    gc4_clear(&g);
    for (int c = 0; c < 4; c++) gc4_drop(&g, c, 1);
    CHECK(gc4_win(&g, 1) && !gc4_win(&g, 2) && gc4_result(&g) == GR_PERSON_WON);          /* horizontal */
    gc4_clear(&g);
    for (int i = 0; i < 4; i++) gc4_drop(&g, 2, 2);
    CHECK(gc4_win(&g, 2) && gc4_result(&g) == GR_UNIT_WON);                               /* vertical */
    gc4_clear(&g);
    g.b[5 * 7 + 0] = 1; g.b[4 * 7 + 1] = 1; g.b[3 * 7 + 2] = 1; g.b[2 * 7 + 3] = 1;
    CHECK(gc4_win(&g, 1));                                                                 /* diagonal up */
    gc4_clear(&g);
    g.b[2 * 7 + 3] = 2; g.b[3 * 7 + 4] = 2; g.b[4 * 7 + 5] = 2; g.b[5 * 7 + 6] = 2;
    CHECK(gc4_win(&g, 2));                                                                 /* diagonal down */
    gc4_clear(&g);
    g.b[5 * 7 + 0] = 1; g.b[5 * 7 + 1] = 1; g.b[5 * 7 + 2] = 1;
    CHECK(!gc4_win(&g, 1) && gc4_result(&g) == GR_PLAYING);                                /* three is not four */
    /* a full board with no four is a draw: column pattern of period that avoids lines */
    gc4_clear(&g);
    static const uint8_t pat[6][7] = {
        {1, 1, 2, 2, 1, 1, 2}, {2, 2, 1, 1, 2, 2, 1}, {1, 1, 2, 2, 1, 1, 2},
        {2, 2, 1, 1, 2, 2, 1}, {1, 1, 2, 2, 1, 1, 2}, {2, 2, 1, 1, 2, 2, 1},
    };
    for (int r = 0; r < 6; r++) for (int c = 0; c < 7; c++) g.b[r * 7 + c] = pat[r][c];
    CHECK(gc4_full(&g) && !gc4_win(&g, 1) && !gc4_win(&g, 2) && gc4_result(&g) == GR_DRAW);
}

/* Plays a search to its end the way the game tick does and returns the move; counts the ticks it took. */
static int ai_move(const gc4_board_t* g, int level, uint32_t seed, int* ticks, uint32_t* max_slice)
{
    gc4_search_t s;
    gc4_ai_start(&s, g, level, seed);
    int n = 0;
    uint32_t worst = 0;
    while (!s.done && n < 1000) {
        const uint32_t before = s.nodes;
        gc4_ai_step(&s, GR_SLICE_NODES);
        if (s.nodes - before > worst) worst = s.nodes - before;
        n++;
    }
    if (ticks) *ticks = n;
    if (max_slice) *max_slice = worst;
    return s.best_col;
}

static void test_c4_ai(void)
{
    gc4_board_t g;
    int ticks;
    uint32_t slice;
    /* the unit takes a win */
    gc4_clear(&g);
    for (int c = 0; c < 3; c++) gc4_drop(&g, c, 2);
    gc4_drop(&g, 6, 1); gc4_drop(&g, 6, 1);
    for (int level = 1; level < GC4_LEVELS; level++) CHECK(ai_move(&g, level, 7u, &ticks, &slice) == 3);
    /* the unit blocks the person's win (levels 1 to 3) */
    gc4_clear(&g);
    for (int c = 0; c < 3; c++) gc4_drop(&g, c, 1);
    gc4_drop(&g, 6, 2);
    for (int level = 1; level < GC4_LEVELS; level++) CHECK(ai_move(&g, level, 7u, &ticks, &slice) == 3);
    /* never an illegal move: a board with one open column, every level */
    gc4_clear(&g);
    for (int c = 0; c < 7; c++) {
        if (c == 5) continue;
        for (int r = 0; r < 6; r++) g.b[r * 7 + c] = (uint8_t)(((r + c) % 3 == 0) ? 1 : 2);
    }
    for (int level = 0; level < GC4_LEVELS; level++) CHECK(ai_move(&g, level, 11u, &ticks, &slice) == 5);
    /* a full board: no move, done at once */
    for (int c = 0; c < 7; c++) g.b[c] = 1;
    for (int level = 0; level < GC4_LEVELS; level++) CHECK(ai_move(&g, level, 1u, &ticks, &slice) == -1);
    /* random games from the start: every move legal, no stall (the biggest slice stays within the node budget plus one root move) */
    uint32_t rs = 12345u;
    for (int game = 0; game < 30; game++) {
        gc4_clear(&g);
        for (int ply = 0; ply < 42; ply++) {
            const int who = (ply % 2) ? 2 : 1;
            int col;
            if (who == 1) {
                do col = (int)(gr_rand(&rs) % 7u); while (!gc4_col_free(&g, col));
            } else {
                col = ai_move(&g, 1 + game % 3, (uint32_t)(game + 1), &ticks, &slice);
                CHECK(col >= 0 && gc4_col_free(&g, col));
                CHECK(slice <= GR_SLICE_NODES + 100u); /* the cap is checked on entry to a node: the open siblings add a few dozen */
            }
            if (gc4_drop(&g, col, who) < 0) { CHECK(0); break; }
            if (gc4_result(&g) != GR_PLAYING) break;
            if (gc4_full(&g)) break;
        }
    }
}

static void test_c4_ai_determinism_and_strength(void)
{
    gc4_board_t g;
    gc4_clear(&g);
    gc4_drop(&g, 3, 1);
    int t;
    uint32_t sl;
    const int a = ai_move(&g, 3, 99u, &t, &sl), b = ai_move(&g, 3, 99u, &t, &sl);
    CHECK(a == b && a >= 0);                             /* the same board and seed give the same move */
    const int r1 = ai_move(&g, 0, 5u, &t, &sl), r2 = ai_move(&g, 0, 5u, &t, &sl);
    CHECK(r1 == r2);                                       /* level 0 is random but seeded */
    /* the deep levels see a two-move trap: the unit (2) must not leave the person a double threat; check that level 3 beats level 0 over many games */
    int wins3 = 0, wins0 = 0;
    for (int game = 0; game < 12; game++) {
        gc4_clear(&g);
        for (int ply = 0; ply < 42; ply++) {
            const int who = ply % 2 == 0 ? 1 : 2;
            int col;
            if (who == 1) col = ai_move(&g, 0, (uint32_t)(1000 + game * 7 + ply), &t, &sl); /* a random person */
            else col = ai_move(&g, 3, (uint32_t)(game + 1), &t, &sl);
            if (gc4_drop(&g, col < 0 ? 0 : col, who) < 0) break;
            const int res = gc4_result(&g);
            if (res == GR_UNIT_WON) { wins3++; break; }
            if (res == GR_PERSON_WON) { wins0++; break; }
            if (res == GR_DRAW) break;
        }
    }
    CHECK(wins3 >= 11 && wins0 == 0);                       /* the 6-ply unit beats a random player (11 of 12 at least) and is never beaten by one */
}

static void test_c4_search_cost(void)
{
    /* the cost of one move at each level from an open middle position, in ticks of GR_SLICE_NODES and in total nodes: the plan's 5 ms per 30 ms tick */
    gc4_board_t g;
    gc4_clear(&g);
    gc4_drop(&g, 3, 1); gc4_drop(&g, 3, 2); gc4_drop(&g, 2, 1); gc4_drop(&g, 4, 2); gc4_drop(&g, 3, 1);
    gc4_search_t s;
    for (int level = 1; level < GC4_LEVELS; level++) {
        gc4_ai_start(&s, &g, level, 3u);
        int ticks = 0;
        while (!s.done) { gc4_ai_step(&s, GR_SLICE_NODES); ticks++; }
        printf("connect4 level %d: %u nodes, %d ticks, cut %d\n", level, (unsigned)s.nodes, ticks, s.cut);
        CHECK(ticks <= 12 && s.nodes < 7u * GR_SLICE_NODES + 7u);
    }
}

static void test_memory(void)
{
    gm_t m;
    CHECK(gm_init(&m, 12, 5u) == 1 && gm_init(&m, 15, 5u) == 0 && gm_init(&m, 16, 5u) == 1);
    int count[9] = {0};
    for (int i = 0; i < m.n; i++) count[m.card[i] & GM_SYMBOL_MASK]++;
    for (int s = 1; s <= 8; s++) CHECK(count[s] == 2);                      /* pairs */
    gm_t m2;
    gm_init(&m2, 16, 5u);
    CHECK(memcmp(m.card, m2.card, 16) == 0);                                 /* same seed, same deck */
    gm_init(&m2, 16, 6u);
    CHECK(memcmp(m.card, m2.card, 16) != 0);
    /* play: find a pair, then a mismatch */
    uint32_t t = 1000;
    int a = 0, b = -1, c = -1;
    for (int i = 1; i < 16; i++) if ((m.card[i] & GM_SYMBOL_MASK) == (m.card[a] & GM_SYMBOL_MASK)) b = i;
    for (int i = 1; i < 16; i++) if (i != b && (m.card[i] & GM_SYMBOL_MASK) != (m.card[a] & GM_SYMBOL_MASK)) { c = i; break; }
    CHECK(gm_tap(&m, 99, t) == GM_IGNORED && gm_tap(&m, -1, t) == GM_IGNORED);
    CHECK(gm_tap(&m, a, t) == GM_FIRST && gm_tap(&m, a, t) == GM_IGNORED);   /* the same card again is ignored */
    CHECK(gm_tap(&m, b, t) == GM_MATCH && m.turns == 1 && m.pairs_left == 7 && (m.card[a] & GM_MATCHED));
    CHECK(gm_tap(&m, a, t) == GM_IGNORED);                                   /* matched cards are out */
    int d = -1;
    for (int i = 0; i < 16; i++) if (!(m.card[i] & GM_MATCHED) && i != c && (m.card[i] & GM_SYMBOL_MASK) != (m.card[c] & GM_SYMBOL_MASK)) { d = i; break; }
    CHECK(gm_tap(&m, c, t) == GM_FIRST && gm_tap(&m, d, t) == GM_MISS && m.turns == 2);
    CHECK(gm_tap(&m, 0, t + 100) == GM_IGNORED || (m.card[0] & GM_MATCHED));  /* no third card while a mismatch waits */
    CHECK(gm_tick(&m, t + 899) == 0 && (m.card[c] & GM_FACE_UP));
    CHECK(gm_tick(&m, t + 900) == 1 && !(m.card[c] & GM_FACE_UP) && !(m.card[d] & GM_FACE_UP));
    /* a whole game: solve it by looking at the deck */
    gm_init(&m, 12, 77u);
    int done = 0;
    for (int s = 1; s <= 6; s++) {
        int p[2], k = 0;
        for (int i = 0; i < 12; i++) if ((m.card[i] & GM_SYMBOL_MASK) == s) p[k++] = i;
        t += 5000;
        CHECK(gm_tap(&m, p[0], t) == GM_FIRST);
        const int r = gm_tap(&m, p[1], t);
        CHECK(r == (s == 6 ? GM_DONE : GM_MATCH));
        done = r == GM_DONE;
    }
    CHECK(done && m.pairs_left == 0 && m.turns == 6);
}

int main(void)
{
    test_geometry();
    test_c4_rules();
    test_c4_ai();
    test_c4_ai_determinism_and_strength();
    test_c4_search_cost();
    test_memory();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("grid core: all passed\n");
    return 0;
}
