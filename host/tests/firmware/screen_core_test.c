/* Host test for the screen's wake rule (patch W01): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include "maipai_screen_core.h"

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
    /* The saved level: what the person chose, never below the floor, 75 when nothing was saved. */
    CHECK(msc_saved_level(0, 0) == 75);
    CHECK(msc_saved_level(1, 100) == 100);
    CHECK(msc_saved_level(1, 42) == 42);
    CHECK(msc_saved_level(1, 0) == MSC_FLOOR_LEVEL);
    CHECK(msc_saved_level(1, -5) == MSC_FLOOR_LEVEL);
    CHECK(msc_saved_level(1, 250) == 100);

    /* The failing case of 2026-11-16: the host dimmed the screen to 5 and a touch must bring it back to 100. */
    CHECK(msc_is_dim(5, 100));
    CHECK(msc_is_dim(0, 100)); /* a screen that is off is dim too */
    CHECK(!msc_is_dim(100, 100));
    CHECK(!msc_is_dim(100, 60)); /* brighter than saved is not dim: nothing to restore */
    CHECK(msc_wake_due(5, 100, 1000, -1));
    CHECK(!msc_wake_due(100, 100, 1000, -1));

    /* A finger held on the glass is one wake: nothing again inside the gap, then due again. */
    CHECK(!msc_wake_due(5, 100, 1100, 1000));
    CHECK(msc_wake_due(5, 100, 1000 + MSC_MIN_GAP_MS, 1000));

    /* The host hears about a wake only when it restored something, and not in a flurry. */
    CHECK(!msc_event_due(0, 5000, -1));
    CHECK(msc_event_due(1, 5000, -1));
    CHECK(!msc_event_due(1, 5100, 5000));
    CHECK(msc_event_due(1, 5000 + MSC_EVENT_GAP_MS, 5000));

    /* A press right after a wake only woke the screen (no listen, no toggle); an old wake claims nothing. */
    CHECK(msc_touch_only_woke(2000, 1900));
    CHECK(!msc_touch_only_woke(2000, -1));
    CHECK(!msc_touch_only_woke(2000, 2000 - MSC_TOUCH_CLAIM_MS));
    CHECK(!msc_touch_only_woke(2000, 3000)); /* a wake in the future (clock went back) claims nothing */

    /* No host for a minute: a dimmed screen comes back by itself; a lit one or a live host leaves it alone. */
    CHECK(!msc_hub_gone_due(5, 100, 50000, 0));
    CHECK(msc_hub_gone_due(5, 100, MSC_HUB_GONE_MS, 0));
    CHECK(!msc_hub_gone_due(100, 100, 200000, 0));
    CHECK(!msc_hub_gone_due(5, 100, 200000, -1)); /* the host is up */

    if (failures == 0) {
        printf("all passed\n");
    }
    return failures == 0 ? 0 : 1;
}
