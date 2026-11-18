/* Host test for the second set of grid rule sets (patch SF67): Hangman, the 2048 slider, Snake, Mine Finder. cc -std=c99 -Wall -Wextra -Werror -I<dir> grid_games2_test.c */
#include <stdio.h>
#include "maipai_grid_hangman_core.h"
#include "maipai_grid_slide_core.h"
#include "maipai_grid_snake_core.h"
#include "maipai_grid_mines_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void test_hangman(void)
{
    gh_t h;
    CHECK(gh_init(&h, "robot", 7) && h.len == 5);
    CHECK(!gh_init(&h, "ab", 7) && !gh_init(&h, "toolongwordhere", 7) && !gh_init(&h, "bad1word", 7) && !gh_init(&h, NULL, 7) && !gh_init(&h, "robot", 0) && !gh_init(&h, "robot", 8));
    gh_init(&h, "Robot", 3);                                              /* case is folded */
    char s[16];
    gh_shown(&h, s, sizeof(s));
    CHECK(strcmp(s, "_____") == 0);
    CHECK(gh_guess(&h, 'o') == GH_HIT && gh_guess(&h, 'O') == GH_REPEAT && gh_guess(&h, '1') == GH_BAD && gh_guess(&h, 'z') == GH_MISS);
    gh_shown(&h, s, sizeof(s));
    CHECK(strcmp(s, "_O_O_") == 0 && h.misses == 1);
    CHECK(gh_guess(&h, 'r') == GH_HIT && gh_guess(&h, 'b') == GH_HIT && gh_guess(&h, 't') == GH_HIT);
    CHECK(h.result == GR_PERSON_WON && gh_score(&h) == 5 * 10 + (3 - 1) * 5);
    CHECK(gh_guess(&h, 'q') == GH_BAD);                                   /* the game is over */
    gh_shown(&h, s, sizeof(s));
    CHECK(strcmp(s, "ROBOT") == 0);
    gh_init(&h, "robot", 3);                                              /* a lost game */
    gh_guess(&h, 'x'); gh_guess(&h, 'y');
    CHECK(h.result == GR_PLAYING);
    CHECK(gh_guess(&h, 'z') == GH_MISS && h.result == GR_UNIT_WON && gh_score(&h) == 0);
    gh_shown(&h, s, sizeof(s));
    CHECK(strcmp(s, "ROBOT") == 0);
    CHECK(gh_key_letter(0, 0) == 'A' && gh_key_letter(8, 0) == 'I' && gh_key_letter(7, 2) == 'Z' && gh_key_letter(8, 2) == 0 && gh_key_letter(9, 0) == 0);
}

static void test_slide(void)
{
    gsl_t g;
    gsl_init(&g, 5u);
    int tiles = 0;
    for (int i = 0; i < 16; i++) tiles += g.t[i] != 0;
    CHECK(tiles == 2);
    uint8_t line[4] = {1, 1, 2, 2};
    int moved = 0;
    CHECK(gsl_line(line, &moved) == 4 + 8 && line[0] == 2 && line[1] == 3 && line[2] == 0 && moved);        /* 2+2=4, 4+4=8: two merges */
    uint8_t line2[4] = {1, 1, 1, 0};
    moved = 0;
    CHECK(gsl_line(line2, &moved) == 4 && line2[0] == 2 && line2[1] == 1 && line2[2] == 0);                 /* a tile merges once per slide */
    uint8_t line3[4] = {1, 2, 3, 4};
    moved = 0;
    CHECK(gsl_line(line3, &moved) == 0 && !moved);                                                          /* nothing moves */
    /* directions on a known board */
    memset(&g, 0, sizeof(g)); g.rng = 9u;
    g.t[0] = 1; g.t[3] = 1;                                                                                 /* row 0: a . . a */
    CHECK(gsl_slide(&g, GS_LEFT) == 1 && g.t[0] == 2 && g.score == 4);
    memset(&g, 0, sizeof(g)); g.rng = 9u;
    g.t[0] = 1; g.t[12] = 1;                                                                                /* column 0: a . . a */
    CHECK(gsl_slide(&g, GS_DOWN) == 1 && g.t[12] == 2);
    memset(&g, 0, sizeof(g)); g.rng = 9u;
    g.t[0] = 3;
    CHECK(gsl_slide(&g, GS_UP) == 0 && gsl_slide(&g, GS_LEFT) == 0);                                        /* no move, no new tile */
    CHECK(gsl_empty_count(&g) == 15 && gsl_slide(&g, 9) == 0);
    CHECK(gsl_slide(&g, GS_RIGHT) == 1 && g.t[3] == 3 && gsl_empty_count(&g) == 14);                        /* moved: one tile added */
    /* a full board with no merges is over; with a merge it is not */
    memset(&g, 0, sizeof(g));
    for (int i = 0; i < 16; i++) g.t[i] = (uint8_t)(1 + ((i / 4 + i % 4) % 2));
    CHECK(!gsl_can_move(&g) && gsl_result(&g) == GR_UNIT_WON);
    g.t[1] = g.t[0];
    CHECK(gsl_can_move(&g) && gsl_result(&g) == GR_PLAYING);
    g.won = 1; g.t[1] = 3;                                                                                  /* back to no merges; reached 2048 earlier */
    CHECK(gsl_result(&g) == GR_PERSON_WON);
    /* a long seeded random play never breaks the invariants and is reproducible */
    uint32_t score_a = 0, score_b = 0;
    for (int run = 0; run < 2; run++) {
        gsl_init(&g, 42u);
        uint32_t rs = 7u;
        for (int i = 0; i < 400 && gsl_can_move(&g); i++) {
            gsl_slide(&g, (int)(gr_rand(&rs) % 4u));
            for (int k = 0; k < 16; k++) CHECK(g.t[k] <= 17);
        }
        (run == 0 ? &score_a : &score_b)[0] = g.score;
    }
    CHECK(score_a == score_b && score_a > 0);
}

static void test_snake(void)
{
    gsn_t s;
    gsn_init(&s, 3u);
    CHECK(s.len == 3 && gsn_head(&s) == 4 * 10 + 3 && s.food != 255 && !s.occ[s.food]);
    gsn_turn(&s, GSN_LEFT);                                                  /* a reverse is ignored */
    CHECK(s.next_dir == GSN_RIGHT);
    s.food = 0;
    CHECK(gsn_step(&s) == GSN_MOVED && gsn_head(&s) == 4 * 10 + 4 && s.len == 3 && !s.occ[4 * 10 + 1]);
    s.food = 4 * 10 + 5;
    CHECK(gsn_step(&s) == GSN_ATE && s.len == 4 && s.score == 1 && s.food != 255 && !s.occ[s.food]);
    gsn_turn(&s, GSN_UP);
    CHECK(gsn_step(&s) == GSN_MOVED && gsn_head(&s) == 3 * 10 + 5);
    /* a wall */
    gsn_init(&s, 3u);
    int died = 0;
    for (int i = 0; i < 20 && !died; i++) died = gsn_step(&s) == GSN_DIED;
    CHECK(died && !s.alive && gsn_step(&s) == GSN_DIED);
    /* itself: a loop of a long snake */
    gsn_init(&s, 3u);
    s.food = 4 * 10 + 4; gsn_step(&s);                                       /* eat: length 4 */
    s.food = 4 * 10 + 5; gsn_step(&s);                                       /* eat: length 5 */
    gsn_turn(&s, GSN_UP);   s.food = 255; CHECK(gsn_step(&s) == GSN_MOVED);
    gsn_turn(&s, GSN_LEFT); CHECK(gsn_step(&s) == GSN_MOVED);
    gsn_turn(&s, GSN_DOWN); CHECK(gsn_step(&s) == GSN_DIED);                 /* head runs into its own body */
    /* the tail cell is free for a snake that does not grow: chasing its own tail in a 2 by 2 loop of length 4 is legal */
    gsn_init(&s, 3u);
    s.food = 4 * 10 + 4; CHECK(gsn_step(&s) == GSN_ATE);                      /* length 4, head (row 4, col 4) */
    s.food = 255;
    gsn_turn(&s, GSN_UP);   CHECK(gsn_step(&s) == GSN_MOVED);                 /* (3,4) */
    gsn_turn(&s, GSN_LEFT); CHECK(gsn_step(&s) == GSN_MOVED);                 /* (3,3) */
    gsn_turn(&s, GSN_DOWN); CHECK(gsn_step(&s) == GSN_MOVED && gsn_head(&s) == 4 * 10 + 3); /* into the cell the tail just left */
    /* the step interval: 300 ms, shortening with each food to a floor of 80 ms */
    gsn_init(&s, 3u);
    CHECK(gsn_interval_ms(&s) == 420);
    s.score = 5;  CHECK(gsn_interval_ms(&s) == 360);
    s.score = 27; CHECK(gsn_interval_ms(&s) == 100);
    s.score = 200; CHECK(gsn_interval_ms(&s) == 100);
    /* a seeded random walk: every step is legal or ends the game, the body stays consistent with the occupancy */
    uint32_t rs = 77u;
    for (int game = 0; game < 40; game++) {
        gsn_init(&s, (uint32_t)(game + 1));
        for (int i = 0; i < 400 && s.alive; i++) {
            if (gr_rand(&rs) % 3u == 0) gsn_turn(&s, (int)(gr_rand(&rs) % 4u));
            gsn_step(&s);
            int occ = 0;
            for (int k = 0; k < GSN_CELLS; k++) occ += s.occ[k];
            CHECK(!s.alive || (occ == s.len && (s.food == 255 || !s.occ[s.food])));
        }
    }
}

static void test_mines(void)
{
    gmn_t m;
    gmn_init(&m, 11u);
    CHECK(gmn_reveal(&m, -1) == GMN_IGNORED && gmn_reveal(&m, 64) == GMN_IGNORED && gmn_flag(&m, 3) == GMN_FLAGGED && gmn_reveal(&m, 3) == GMN_IGNORED && gmn_flag(&m, 3) == GMN_UNFLAGGED);
    /* the first reveal is never a mine and never next to one: over many seeds */
    for (uint32_t seed = 1; seed < 200; seed++) {
        gmn_init(&m, seed);
        const int first = (int)(seed % 64);
        const int r = gmn_reveal(&m, first);
        CHECK(r == GMN_OPENED || r == GMN_CLEARED);
        CHECK(!(m.c[first] & GMN_MINE) && (m.c[first] & GMN_COUNT) == 0);
        int mines = 0;
        for (int i = 0; i < 64; i++) mines += (m.c[i] & GMN_MINE) != 0;
        CHECK(mines == GMN_MINES);
        CHECK(m.open_count >= 1);
    }
    /* a known board: count, flood and win. Column 3 is a wall of 8 mines, plus the corners 0 and 56, so a flood from the right edge cannot reach the left */
    memset(&m, 0, sizeof(m));
    m.rng = 1u;
    m.placed = 1;
    for (int r = 0; r < 8; r++) m.c[r * 8 + 3] |= GMN_MINE;
    m.c[0] |= GMN_MINE; m.c[56] |= GMN_MINE;
    for (int i = 0; i < 64; i++) {
        int n = 0;
        for (int dr = -1; dr <= 1; dr++) for (int dc = -1; dc <= 1; dc++) {
            const int r = i / 8 + dr, c = i % 8 + dc;
            if ((dr || dc) && r >= 0 && r < 8 && c >= 0 && c < 8 && (m.c[r * 8 + c] & GMN_MINE)) n++;
        }
        m.c[i] = (uint8_t)((m.c[i] & ~GMN_COUNT) | n);
    }
    CHECK(gmn_flag(&m, 63) == GMN_FLAGGED && m.flags == 1);
    CHECK(gmn_reveal(&m, 63) == GMN_IGNORED);                                 /* a flagged cell is not opened */
    CHECK(gmn_flag(&m, 63) == GMN_UNFLAGGED);
    CHECK(gmn_reveal(&m, 63) == GMN_OPENED && m.result == GR_PLAYING);       /* a zero floods the lower rows */
    CHECK((m.c[47] & GMN_OPEN) && !(m.c[9] & GMN_OPEN));                      /* the right side opened, the left did not */
    int guard = 0;
    for (int i = 0; i < 64 && !guard; i++) {                                 /* open every remaining safe cell */
        if (!(m.c[i] & (GMN_MINE | GMN_OPEN))) {
            const int r = gmn_reveal(&m, i);
            guard = r == GMN_CLEARED;
        }
    }
    CHECK(m.result == GR_PERSON_WON && m.open_count == 54);
    CHECK(gmn_reveal(&m, 0) == GMN_IGNORED);                                  /* the game is over */
    /* a mine ends the game and shows every mine */
    memset(&m, 0, sizeof(m)); m.rng = 1u; m.placed = 1;
    m.c[5] = GMN_MINE; m.c[20] = GMN_MINE;
    CHECK(gmn_reveal(&m, 5) == GMN_BOOM && m.result == GR_UNIT_WON && (m.c[20] & GMN_OPEN));
}

int main(void)
{
    test_hangman();
    test_slide();
    test_snake();
    test_mines();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("grid games 2: all passed\n");
    return 0;
}
