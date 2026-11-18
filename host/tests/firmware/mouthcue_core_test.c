/* Host test for the mouth cue player (patch SF10). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include "maipai_mouthcue_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

int main(void)
{
    static mmc_t m;
    mmc_init(&m);
    const uint32_t ms[] = {0, 100, 250, 400};
    const uint8_t lv[] = {2, 4, 1, 0};
    int level = -1;
    CHECK(mmc_set(&m, ms, lv, 4, 1000) == MMC_OK);
    CHECK(mmc_level(&m, 1010, &level) == 0); /* pending: the audio drives the mouth */
    mmc_start(&m, 2000);
    CHECK(mmc_level(&m, 2000, &level) == 1 && level == 50);
    CHECK(mmc_level(&m, 2120, &level) == 1 && level == 100);
    CHECK(mmc_level(&m, 2260, &level) == 1 && level == 25);
    CHECK(mmc_level(&m, 2399, &level) == 1 && level == 25);
    CHECK(mmc_level(&m, 2401, &level) == 1 && level == 0); /* the last cue is 0 */
    CHECK(mmc_level(&m, 5000, &level) == 1 && level == 0); /* closed until the speech ends */
    mmc_stop(&m);
    CHECK(mmc_level(&m, 5001, &level) == 0);

    /* ends closed even when the last cue is open */
    const uint32_t ms2[] = {0, 200};
    const uint8_t lv2[] = {3, 4};
    CHECK(mmc_set(&m, ms2, lv2, 2, 0) == MMC_OK);
    mmc_start(&m, 10);
    CHECK(mmc_level(&m, 10 + 250, &level) == 1 && level == 100);
    CHECK(mmc_level(&m, 10 + 600, &level) == 1 && level == 0);

    /* a stale list (arrived for an earlier turn) is dropped at the start */
    mmc_stop(&m);
    CHECK(mmc_set(&m, ms2, lv2, 2, 0) == MMC_OK);
    mmc_start(&m, MMC_STALE_MS + 1);
    CHECK(m.state == MMC_NONE && mmc_level(&m, MMC_STALE_MS + 2, &level) == 0);
    /* a stale list also at a clock past 2^31 ms */
    CHECK(mmc_set(&m, ms2, lv2, 2, 0x90000000u) == MMC_OK);
    mmc_start(&m, 0x90000000u + 500u);
    CHECK(m.state == MMC_PLAYING);

    /* a bad list is refused and does not replace the one waiting */
    mmc_stop(&m);
    CHECK(mmc_set(&m, ms2, lv2, 2, 0) == MMC_OK);
    const uint32_t bad_t[] = {100, 50};
    CHECK(mmc_set(&m, bad_t, lv2, 2, 0) == MMC_BAD_TIME);
    const uint8_t bad_l[] = {1, 5};
    CHECK(mmc_set(&m, ms2, bad_l, 2, 0) == MMC_BAD_LEVEL);
    CHECK(mmc_set(&m, ms2, lv2, 0, 0) == MMC_BAD_COUNT && mmc_set(&m, ms2, lv2, MMC_MAX_CUES + 1, 0) == MMC_BAD_COUNT);
    const uint32_t late[] = {0, MMC_MAX_MS + 1};
    CHECK(mmc_set(&m, late, lv2, 2, 0) == MMC_BAD_TIME);
    CHECK(m.state == MMC_PENDING && m.n == 2);

    /* rate: 13 cues in one second is too fast, 12 is fine */
    static uint32_t fast[13];
    static uint8_t fl[13];
    for (int i = 0; i < 13; i++) {
        fast[i] = (uint32_t)(i * 70);
        fl[i] = 1;
    }
    CHECK(mmc_set(&m, fast, fl, 13, 0) == MMC_TOO_FAST);
    CHECK(mmc_set(&m, fast, fl, 12, 0) == MMC_OK);
    /* 8 cues per second for 20 s stays inside the cap */
    static uint32_t long_t[160];
    static uint8_t long_l[160];
    for (int i = 0; i < 160; i++) {
        long_t[i] = (uint32_t)(i * 125);
        long_l[i] = (uint8_t)(i % 5);
    }
    CHECK(mmc_set(&m, long_t, long_l, 160, 0) == MMC_OK);

    /* append: the next sentence's list continues the playing one */
    {
        static mmc_t a;
        mmc_init(&a);
        const uint32_t s1[] = {0, 100, 200};
        const uint8_t l1[] = {2, 3, 0};
        const uint32_t s2[] = {1500, 1600};
        const uint8_t l2[] = {4, 1};
        CHECK(mmc_append(&a, s1, l1, 3, 0) == MMC_OK && a.state == MMC_PENDING && a.n == 3); /* nothing held: a plain set */
        mmc_start(&a, 1000);
        CHECK(mmc_append(&a, s2, l2, 2, 1100) == MMC_OK && a.n == 5 && a.state == MMC_PLAYING);
        CHECK(mmc_level(&a, 1000 + 1550, &level) == 1 && level == 100); /* the second sentence plays at its offset */
        CHECK(mmc_level(&a, 1000 + 1700, &level) == 1 && level == 25);
        CHECK(mmc_level(&a, 1000 + 2500, &level) == 1 && level == 0);   /* closed after the last cue */
        /* the first time may not be before the last held time */
        const uint32_t early[] = {1000};
        const uint8_t el[] = {1};
        CHECK(mmc_append(&a, early, el, 1, 2000) == MMC_BAD_TIME && a.n == 5);
        /* an append may start at the last held time */
        const uint32_t same[] = {1600, 1700};
        CHECK(mmc_append(&a, same, l2, 2, 2000) == MMC_OK && a.n == 7);
        /* the rate rule holds across the join: 12 held cues inside a second, one more is too fast */
        static mmc_t b;
        mmc_init(&b);
        uint32_t dense[12];
        uint8_t dl[12];
        for (int i = 0; i < 12; i++) {
            dense[i] = (uint32_t)(i * 80);
            dl[i] = 1;
        }
        CHECK(mmc_set(&b, dense, dl, 12, 0) == MMC_OK);
        const uint32_t join[] = {960};
        CHECK(mmc_append(&b, join, el, 1, 0) == MMC_TOO_FAST);
        const uint32_t later[] = {1100};
        CHECK(mmc_append(&b, later, el, 1, 0) == MMC_OK);
        /* the whole held list is bounded */
        static mmc_t c;
        mmc_init(&c);
        static uint32_t chunk[160];
        static uint8_t cl[160];
        for (int i = 0; i < 160; i++) {
            chunk[i] = (uint32_t)(i * 100);
            cl[i] = 1;
        }
        CHECK(mmc_set(&c, chunk, cl, 160, 0) == MMC_OK);
        for (int i = 0; i < 160; i++) chunk[i] = 16000u + (uint32_t)(i * 100);
        CHECK(mmc_append(&c, chunk, cl, 160, 0) == MMC_OK);
        for (int i = 0; i < 160; i++) chunk[i] = 32000u + (uint32_t)(i * 100);
        CHECK(mmc_append(&c, chunk, cl, 160, 0) == MMC_OK && c.n == 480);
        for (int i = 0; i < 160; i++) chunk[i] = 48000u + (uint32_t)(i * 70);
        CHECK(mmc_append(&c, chunk, cl, 1, 0) == MMC_BAD_COUNT); /* 481 cues */
        /* a speech end drops the whole list: a later append is a fresh pending set */
        mmc_stop(&c);
        CHECK(mmc_append(&c, s1, l1, 3, 0) == MMC_OK && c.n == 3 && c.state == MMC_PENDING);
        /* the 60 second span */
        const uint32_t far[] = {70000};
        CHECK(mmc_append(&a, far, el, 1, 0) == MMC_BAD_TIME);
    }
    if (failures) return 1;
    printf("mouthcue core ok\n");
    return 0;
}
