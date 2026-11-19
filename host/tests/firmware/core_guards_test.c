/* Host test for the guards added after the static analysis run (patch SF83): the cases the analysis flagged must be safe with damaged or empty input.
 * cc -std=c99 -Wall -Wextra -Werror -I<dir> core_guards_test.c -lm */
#include <stdio.h>
#include <string.h>
#include "maipai_face_track_core.h"
#include "maipai_filler_core.h"
#include "maipai_games_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void test_face_track_empty_history(void)
{
    ft_t t;
    ft_cfg_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    ft_init(&t, &cfg);
    float pan = 1.0f, tilt = 2.0f;
    ft_hist_at(&t, 500, 11.0f, 22.0f, &pan, &tilt);                  /* no readings: the current angles */
    CHECK(pan == 11.0f && tilt == 22.0f);
    ft_hist_add(&t, 100, 5.0f, 6.0f);
    ft_hist_at(&t, 50, 0.0f, 0.0f, &pan, &tilt);                      /* older than the only reading: that reading */
    CHECK(pan == 5.0f && tilt == 6.0f);
    ft_hist_at(&t, 900, 0.0f, 0.0f, &pan, &tilt);                     /* newer than every reading: the newest */
    CHECK(pan == 5.0f && tilt == 6.0f);
    t.hist_n = 0;                                                      /* a count of zero after readings: the current angles, never a read through nothing */
    ft_hist_at(&t, 900, 7.0f, 8.0f, &pan, &tilt);
    CHECK(pan == 7.0f && tilt == 8.0f);
}

static void test_filler_pick_is_always_a_valid_clip(void)
{
    tf_index_t x;
    memset(&x, 0, sizeof(x));
    CHECK(tf_pick(&x, -1, 12345u) == -1);                              /* no clips */
    x.n = 1;
    snprintf(x.clip[0].name, sizeof(x.clip[0].name), "hmm");
    for (uint32_t rnd = 0; rnd < 5000u; rnd += 37u) CHECK(tf_pick(&x, 0, rnd * 2654435761u) == 0);   /* one sound only: the same clip, never a failure */
    x.n = 3;
    snprintf(x.clip[1].name, sizeof(x.clip[1].name), "hmm");
    snprintf(x.clip[2].name, sizeof(x.clip[2].name), "oh");
    for (uint32_t rnd = 0; rnd < 5000u; rnd += 37u) {
        const int c = tf_pick(&x, (int)(rnd % 5u) - 1, rnd * 2654435761u);
        CHECK(c >= 0 && c < 3);
    }
}

static void test_board_bot_with_one_free_cell(void)
{
    /* a bot with one free cell, and with none, at every level: a legal cell or -1, never a modulo by zero */
    mg_run_t r;
    for (int level = 0; level <= 2; level++) {
        memset(&r, 0, sizeof(r));
        r.rng = 7u;
        for (int i = 0; i < MG_BOARD_CELLS; i++) r.board[i] = (uint8_t)(i % 2 ? 1 : 2);
        r.board[4] = 0;
        const int c = mg_board_bot(&r, level);
        CHECK(c == 4);
        r.board[4] = 1;
        CHECK(mg_board_bot(&r, level) < 0);
    }
}

int main(void)
{
    test_face_track_empty_history();
    test_filler_pick_is_always_a_valid_clip();
    test_board_bot_with_one_free_cell();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("core guards: all passed\n");
    return 0;
}
