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

    if (failures) return 1;
    printf("mouthcue core ok\n");
    return 0;
}
