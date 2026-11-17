/* Host test for the private network's relay region and test hook (patches RM04 and RM05):
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with maipai_tailnet_core.h as ORDER leaves it>. */
#include <stdio.h>
#include "maipai_tailnet_core.h"

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
    mt_region_t r = {0, 0};

    /* The failing case of 2026-11-15: the unit's default relay is Frankfurt (4), the hub is on New York (1). */
    CHECK(mt_region_wanted(&r, 1000, 4, 1, 1) == 1);
    /* Nothing to do when they match, when the hub's region is not known yet, or when the client is not connected. */
    CHECK(mt_region_wanted(&r, 1000, 1, 1, 1) == 0);
    CHECK(mt_region_wanted(&r, 1000, 4, 0, 1) == 0);
    CHECK(mt_region_wanted(&r, 1000, 0, 1, 1) == 0);
    CHECK(mt_region_wanted(&r, 1000, 4, 1, 0) == 0);
    CHECK(mt_region_wanted(&r, 1000, 4, -3, 1) == 0);
    CHECK(r.moves == 0); /* asking changes nothing: only mt_region_moved counts a move */

    /* After a move the next one waits a minute, and a boot allows three moves in all. */
    mt_region_moved(&r, 5000);
    CHECK(r.moves == 1);
    CHECK(mt_region_wanted(&r, 5000 + MT_REGION_GAP_MS - 1, 1, 7, 1) == 0);
    CHECK(mt_region_wanted(&r, 5000 + MT_REGION_GAP_MS, 1, 7, 1) == 7);
    mt_region_moved(&r, 5000 + MT_REGION_GAP_MS);
    CHECK(mt_region_wanted(&r, 5000 + 2 * MT_REGION_GAP_MS, 7, 1, 1) == 1);
    mt_region_moved(&r, 5000 + 2 * MT_REGION_GAP_MS);
    CHECK(r.moves == MT_REGION_MAX_MOVES);
    CHECK(mt_region_wanted(&r, 1000000, 1, 9, 1) == 0); /* a hub that keeps changing region cannot make a reconnect storm */

    /* The hook: a request of 1 to 60 minutes sets a deadline; anything else is refused with 0 (off). */
    CHECK(mt_prefer_deadline(1000, 5) == 1000 + 5 * 60000);
    CHECK(mt_prefer_deadline(1000, 60) == 1000 + 60 * 60000);
    CHECK(mt_prefer_deadline(1000, 0) == 0);
    CHECK(mt_prefer_deadline(1000, 61) == 0);
    CHECK(mt_prefer_deadline(1000, -1) == 0);
    CHECK(!mt_prefer_active(0, 1000));                    /* off */
    CHECK(mt_prefer_active(1000 + 300000, 1000));         /* on */
    CHECK(mt_prefer_active(1000 + 300000, 300999));       /* last millisecond */
    CHECK(!mt_prefer_active(1000 + 300000, 301000));      /* five minutes later: the home address again */

    /* The route: the hook forces the private route only when the private network is ready and a hub address is saved. */
    CHECK(mt_prefer_route(0, 1, 1, 1) == 1);
    CHECK(mt_prefer_route(0, 1, 0, 1) == 0);  /* not ready: stay on the normal route */
    CHECK(mt_prefer_route(0, 1, 1, 0) == 0);  /* no hub address */
    CHECK(mt_prefer_route(0, 0, 1, 1) == 0);  /* hook off at home: home */
    CHECK(mt_prefer_route(1, 0, 1, 1) == 1);  /* the normal rule's own choice is kept */

    /* The route choice itself, with the hook off, is the one the earlier test covers; here only that the hook does not
     * disturb the failure streak: the normal rule still runs underneath. */
    mt_route_t route = {0, 0};
    mt_route_result(&route, 0, 1, 1);
    mt_route_result(&route, 0, 1, 1);
    CHECK(route.route == 1);
    CHECK(mt_prefer_route(mt_route_choose(&route, 1, 1), 0, 1, 1) == 1);

    if (failures == 0) {
        printf("all passed\n");
        return 0;
    }
    return 1;
}
