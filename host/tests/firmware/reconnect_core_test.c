/* Host test for the host-reconnect rules (patch SF49). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include "maipai_reconnect_core.h"

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
    /* the delays double from 1 s to the cap and stay there */
    uint32_t d = MRC_INITIAL_MS;
    const uint32_t want[] = {2000, 4000, 8000, 16000, 30000, 30000, 30000};
    for (int i = 0; i < 7; i++) {
        d = mrc_grow(d, MRC_CAP_NEAR_MS);
        CHECK(d == want[i]);
    }
    CHECK(mrc_grow(0, MRC_CAP_NEAR_MS) == 2000);                 /* a zero delay starts at 1 s */
    CHECK(mrc_grow(100000, MRC_CAP_FAR_MS) == MRC_CAP_FAR_MS);
    /* the wait: the delay plus up to a quarter, never above the cap, for every random value tried */
    for (uint32_t delay = 1000; delay <= 120000; delay = mrc_grow(delay, 120000)) {
        for (uint32_t rnd = 0; rnd < 4000000000u; rnd += 99999991u) {
            const uint32_t w = mrc_wait(delay, 120000, rnd);
            CHECK(w >= delay && w <= delay + delay / 4u && w <= 120000);
            const uint32_t w30 = mrc_wait(delay, 30000, rnd);
            CHECK(w30 <= 30000 && w30 >= (delay < 30000 ? delay : 30000));
        }
        if (delay == 120000) break;
    }
    /* the cap: 30 s for ten minutes, then 120 s */
    CHECK(mrc_cap(0) == 30000 && mrc_cap(599999) == 30000 && mrc_cap(600000) == 120000 && mrc_cap(86400000u) == 120000);
    /* the bound: a host that comes back is found within the cap plus one connect */
    for (uint32_t away = 0; away < 4000000; away += 7919) CHECK(mrc_wait(mrc_cap(away), mrc_cap(away), 0xffffffffu) <= mrc_cap(away));
    /* the notice: not before 10 minutes, once, then every 30 minutes */
    CHECK(!mrc_notice_due(0, 0) && !mrc_notice_due(599999, 0));
    CHECK(mrc_notice_due(600000, 0));
    CHECK(!mrc_notice_due(601000, 600000) && !mrc_notice_due(600000 + 1799999u, 600000));
    CHECK(mrc_notice_due(600000 + 1800000u, 600000));
    if (failures) return 1;
    printf("reconnect core ok\n");
    return 0;
}
