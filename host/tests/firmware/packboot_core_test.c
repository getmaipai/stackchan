/* Host test for when the pack boot task starts (patch FM04): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include "maipai_packboot_core.h"

static int failures;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); failures++; } } while (0)

int main(void)
{
    /* Not at 15 s, not at any fixed time, while the application has not reached standby (the wake model may still be loading). */
    CHECK(!mpb_should_start(0, 0, 0));
    CHECK(!mpb_should_start(0, 0, 15));
    CHECK(!mpb_should_start(0, 0, MPB_FALLBACK_S - 1));
    /* At the first standby, whenever that is: early, or late on a slow connect. */
    CHECK(mpb_should_start(0, 1, 5));
    CHECK(mpb_should_start(0, 1, 90));
    /* A unit that never reaches standby still applies its saved look, after the fallback. */
    CHECK(mpb_should_start(0, 0, MPB_FALLBACK_S));
    /* Once started, never again, whatever happens after (the main loop calls this every 20 ms). */
    for (unsigned s = 0; s < 400; s += 7) {
        CHECK(!mpb_should_start(1, 0, s));
        CHECK(!mpb_should_start(1, 1, s));
    }
    if (failures == 0) printf("packboot_core_test: all passed\n");
    return failures == 0 ? 0 : 1;
}
