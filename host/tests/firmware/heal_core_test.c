/* Host test for the restart guard's allowance (patch R04): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include "maipai_heal_core.h"

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
    /* The first three restarts in a window go at once, whatever the uptime. */
    for (int n = 0; n < 3; n++) {
        CHECK(mhc_allow(n, 0));
        CHECK(mhc_wait_s(n, 0) == 0);
    }

    /* The failing case of 2026-11-16: three used, a fourth freeze. R02 refused for the rest of the hour; now it
     * waits for the unit to have run five minutes since its last restart, and then goes. */
    CHECK(!mhc_allow(3, 0));
    CHECK(!mhc_allow(3, 299));
    CHECK(mhc_allow(3, 300));
    CHECK(mhc_wait_s(3, 100) == 200);

    /* The wait grows, and is capped: a freeze that keeps coming back is never a reboot loop, and never waits
     * longer than half an hour. */
    CHECK(mhc_backoff_s(4) == 600);
    CHECK(mhc_backoff_s(5) == 1200);
    CHECK(mhc_backoff_s(6) == MHC_BACKOFF_MAX_S);
    CHECK(mhc_backoff_s(50) == MHC_BACKOFF_MAX_S);
    CHECK(!mhc_allow(6, 1799));
    CHECK(mhc_allow(6, 1800));

    /* Never a loop: after the free ones, two restarts are always at least five minutes of running apart. */
    for (int n = 3; n < 40; n++) {
        CHECK(mhc_backoff_s(n) >= MHC_BACKOFF_BASE_S);
        CHECK(!mhc_allow(n, MHC_BACKOFF_BASE_S - 1));
    }

    /* A freeze can always be cleared: for any count some uptime of at most the cap allows it. */
    for (int n = 0; n < 100; n++) {
        CHECK(mhc_allow(n, MHC_BACKOFF_MAX_S));
    }

    if (failures == 0) {
        printf("all passed\n");
    }
    return failures == 0 ? 0 : 1;
}
