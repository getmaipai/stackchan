/* Host test for the talk-over decisions (patch SF18). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the headers>. */
#include <stdio.h>
#include "maipai_barge_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void scenario(uint32_t t0)
{
    mbg_t m;
    mbg_init(&m);
    CHECK(mbg_wake_hit(&m, t0) == MBG_WAKE); /* idle: the normal wake */
    mbg_speaking(&m, 1);
    CHECK(mbg_wake_hit(&m, t0 + 100) == MBG_WAIT);   /* the first hit while speaking waits for a second */
    CHECK(mbg_wake_hit(&m, t0 + 900) == MBG_ABORT);  /* the second inside a second fires */
    CHECK(!mbg_frame_ok(&m));                         /* the old turn's late frames are dropped */
    mbg_tts_start(&m);
    CHECK(mbg_frame_ok(&m));                          /* the next reply plays */
    /* a lone hit expires */
    mbg_speaking(&m, 0);
    mbg_speaking(&m, 1);
    CHECK(mbg_wake_hit(&m, t0 + 5000) == MBG_WAIT);
    CHECK(mbg_wake_hit(&m, t0 + 5000 + MBG_TWO_HIT_MS + 50) == MBG_WAIT); /* too late: it counts as a new first hit */
    CHECK(mbg_frame_ok(&m));
    /* a sentence that says the wake phrase: hits are ignored during it and 500 ms after, then the rule is back */
    mbg_speaking(&m, 0);
    mbg_speaking(&m, 1);
    mbg_no_barge_sentence(&m, t0 + 10000, 2000);
    CHECK(mbg_wake_hit(&m, t0 + 10500) == MBG_IGNORE);
    CHECK(mbg_wake_hit(&m, t0 + 10000 + 2000 + 400) == MBG_IGNORE);
    CHECK(mbg_wake_hit(&m, t0 + 10000 + 2000 + 600) == MBG_WAIT);
    CHECK(mbg_wake_hit(&m, t0 + 10000 + 2000 + 700) == MBG_ABORT);
    /* the end of speech clears the pending state */
    mbg_speaking(&m, 0);
    CHECK(m.first_hit_at == 0 && m.no_barge_until == 0);
    CHECK(mbg_wake_hit(&m, t0 + 20000) == MBG_WAKE);
}

int main(void)
{
    scenario(1000u);
    scenario(0x90000000u);
    scenario(0xFFFFF800u); /* across the wrap */
    if (failures) return 1;
    printf("barge core ok\n");
    return 0;
}
