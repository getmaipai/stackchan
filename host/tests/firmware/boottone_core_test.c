/* Host test for the start-up sound rules (patch SF46). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include "maipai_boottone_core.h"

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
    /* a saved 0 stays 0; no saved value (negative) takes the default; a high value is capped */
    CHECK(mbt_boot_volume(0, 10) == 0);
    CHECK(mbt_boot_volume(35, 10) == 35);
    CHECK(mbt_boot_volume(-1, 10) == 10);
    CHECK(mbt_boot_volume(-7, 10) == 10);
    CHECK(mbt_boot_volume(250, 10) == 100);
    CHECK(mbt_boot_volume(-1, -3) == 0 && mbt_boot_volume(-1, 400) == 100);
    /* a start-up tone: only when not muted, not in full quiet and the policy allows it */
    CHECK(mbt_tone_allowed(0, 0, 1));
    CHECK(!mbt_tone_allowed(1, 0, 1));
    CHECK(!mbt_tone_allowed(0, 1, 1));
    CHECK(!mbt_tone_allowed(0, 0, 0));
    CHECK(!mbt_tone_allowed(1, 1, 0));
    for (int m = 0; m < 2; m++)
        for (int q = 0; q < 2; q++)
            for (int p = 0; p < 2; p++) CHECK(mbt_tone_allowed(m, q, p) == (!m && !q && p));
    if (failures) return 1;
    printf("boottone core ok\n");
    return 0;
}
