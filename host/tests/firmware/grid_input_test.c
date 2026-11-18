/* Host test for the grid games' touch classifier and the vertical-swipe rule of the gesture layer (patch SF76). cc -std=c99 -Wall -Wextra -Werror -I<dir> grid_input_test.c */
#include <stdio.h>
#include "maipai_grid_input_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void test_classify(void)
{
    CHECK(gi_classify(100, 100, 100, 100, 80) == GI_TAP && gi_classify(100, 100, 104, 96, 300) == GI_TAP);
    CHECK(gi_classify(100, 100, 100, 100, 449) == GI_TAP && gi_classify(100, 100, 100, 100, 450) == GI_LONG && gi_classify(100, 100, 106, 100, 2000) == GI_LONG);
    CHECK(gi_classify(100, 100, 100, 160, 120) == GI_SWIPE_DOWN && gi_classify(100, 160, 100, 100, 120) == GI_SWIPE_UP);
    CHECK(gi_classify(100, 100, 170, 100, 120) == GI_SWIPE_RIGHT && gi_classify(170, 100, 100, 100, 120) == GI_SWIPE_LEFT);
    CHECK(gi_classify(100, 100, 100, 160, 3000) == GI_NONE);                 /* too slow: a drag */
    CHECK(gi_classify(100, 100, 150, 150, 120) == GI_NONE);                 /* a diagonal is no swipe */
    CHECK(gi_classify(100, 100, 130, 100, 3000) == GI_NONE);                /* moved and held: neither a long press nor a swipe */
    for (int d = 0; d < 360; d += 7) {                                       /* never more than one answer, always a defined one */
        const int dx = (int)(60.0 * ((d % 90) < 45 ? 1 : -1)), dy = (d % 2) ? 60 : -60;
        const int r = gi_classify(160, 120, 160 + dx, 120 + dy, 100);
        CHECK(r >= GI_NONE && r <= GI_SWIPE_RIGHT);
    }
}

static mgs_out_t swipe_with(mgs_t* g, int x0, int y0, int x1, int y1, uint32_t held, int flags)
{
    static uint32_t t = 100000;
    t += 5000;
    mgs_down(g, x0, y0, t, flags);
    return mgs_up(g, x1, y1, t + held);
}

static void test_the_gesture_rule(void)
{
    mgs_t g;
    mgs_init(&g);
    mgs_config(&g, 1, 1, 10, 20);
    /* a game without the flag: a swipe down anywhere stops it, as before */
    mgs_out_t o = swipe_with(&g, 160, 60, 160, 170, 150, MGS_F_GAME);
    CHECK(o.act == MGS_ACT_STOP && o.stop);
    /* a game that takes vertical swipes: inside the play area the swipe is the game's: no stop, no page, no sheet */
    mgs_init(&g);
    mgs_config(&g, 1, 1, 10, 20);
    o = swipe_with(&g, 160, 60, 160, 170, 150, MGS_F_GAME | MGS_F_GAME_VERT);
    CHECK(o.act == MGS_ACT_NONE && !o.stop && g.mode == MGS_FACE);
    o = swipe_with(&g, 160, 170, 160, 60, 150, MGS_F_GAME | MGS_F_GAME_VERT);                 /* swipe up: no sheet */
    CHECK(o.act == MGS_ACT_NONE && g.mode == MGS_FACE);
    /* the bottom edge still stops it */
    o = swipe_with(&g, 160, 230, 160, 238, 60, MGS_F_GAME | MGS_F_GAME_VERT);                 /* too short: not a swipe */
    o = swipe_with(&g, 160, 226, 160, 160, 100, MGS_F_GAME | MGS_F_GAME_VERT);                /* up from the bottom edge: no sheet during a game */
    CHECK(o.act == MGS_ACT_NONE);
    mgs_init(&g);
    mgs_config(&g, 1, 1, 10, 20);
    o = swipe_with(&g, 160, 150, 160, 236, 120, MGS_F_GAME | MGS_F_GAME_VERT);                /* down, begun at 150: the game's */
    CHECK(o.act == MGS_ACT_NONE);
    /* the side edges still change the volume during such a game */
    o = swipe_with(&g, 4, 100, 120, 100, 200, MGS_F_GAME | MGS_F_GAME_VERT);
    CHECK(o.act == MGS_ACT_VOLUME);
    /* without a game the vertical swipe is the unit's, flag or no flag */
    mgs_init(&g);
    mgs_config(&g, 1, 1, 10, 20);
    o = swipe_with(&g, 160, 60, 160, 170, 150, MGS_F_GAME_VERT);
    CHECK(o.act == MGS_ACT_STOP);
}

int main(void)
{
    test_classify();
    test_the_gesture_rule();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("grid input: all passed\n");
    return 0;
}
