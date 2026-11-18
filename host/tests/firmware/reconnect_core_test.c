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
    /* the delays double from 0.5 s to the cap of the moment and stay there (patch SF64) */
    uint32_t d = MRC_INITIAL_MS;
    const uint32_t want[] = {1000, 2000, 4000, 5000, 5000, 5000};
    for (int i = 0; i < 6; i++) {
        d = mrc_grow(d, MRC_CAP_FAST_MS);
        CHECK(d == want[i]);
    }
    d = MRC_CAP_FAST_MS;
    CHECK((d = mrc_grow(d, MRC_CAP_MID_MS)) == 10000 && (d = mrc_grow(d, MRC_CAP_MID_MS)) == 15000 && mrc_grow(d, MRC_CAP_MID_MS) == 15000);
    CHECK(mrc_grow(0, MRC_CAP_FAST_MS) == 1000);                 /* a zero delay starts at the first step, 0.5 s, and grows to 1 s */
    CHECK(mrc_grow(100000, MRC_CAP_FAR_MS) == MRC_CAP_FAR_MS);
    /* the wait: the delay plus up to a quarter, never above the cap, for every random value tried */
    for (uint32_t delay = MRC_INITIAL_MS; delay <= 120000; delay = mrc_grow(delay, 120000)) {
        for (uint32_t rnd = 0; rnd < 4000000000u; rnd += 99999991u) {
            const uint32_t w = mrc_wait(delay, 120000, rnd);
            CHECK(w >= delay && w <= delay + delay / 4u && w <= 120000);
            const uint32_t w30 = mrc_wait(delay, 30000, rnd);
            CHECK(w30 <= 30000 && w30 >= (delay < 30000 ? delay : 30000));
        }
        if (delay == 120000) break;
    }
    /* the cap by time away: 5 s for 2 minutes, 15 s to 5 minutes, 30 s to 10 minutes, then 120 s */
    CHECK(mrc_cap(0) == 5000 && mrc_cap(119999) == 5000 && mrc_cap(120000) == 15000 && mrc_cap(299999) == 15000);
    CHECK(mrc_cap(300000) == 30000 && mrc_cap(599999) == 30000 && mrc_cap(600000) == 120000 && mrc_cap(86400000u) == 120000);
    /* the common case: the host is down for 20 to 60 seconds; the unit must be back within 5 s of it (plus one connect), simulated with the jitter at its worst */
    for (uint32_t down = 20000; down <= 60000; down += 5000) {
        uint32_t t = 0, delay = MRC_INITIAL_MS;
        while (t < down) {
            const uint32_t cap = mrc_cap(t);
            t += mrc_wait(delay, cap, 0xffffffffu);
            delay = mrc_grow(delay, cap);
        }
        CHECK(t - down <= 5000);
    }
    /* the cost: the number of tries in the first 2 minutes stays small (a polite unit) */
    {
        uint32_t t = 0, delay = MRC_INITIAL_MS;
        int tries = 0;
        while (t < MRC_FAST_UNTIL_MS) {
            t += mrc_wait(delay, mrc_cap(t), 0u);
            delay = mrc_grow(delay, mrc_cap(t));
            tries++;
        }
        CHECK(tries <= 30);
    }
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
