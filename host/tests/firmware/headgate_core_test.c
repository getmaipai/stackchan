/* Host test for the host head-move gate (patch Y01): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include "maipai_headgate_core.h"

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
    CHECK(mh_head_ignored(1, 0) == 1);  /* an unmarked look while idle with idle movement off: ignored (patch L04) */
    CHECK(mh_head_ignored(0, 0) == 0);  /* not idle, or idle movement on: goes through */
    CHECK(mh_head_ignored(1, 1) == 0);  /* the person asked (source=user): never ignored */
    CHECK(mh_head_ignored(0, 1) == 0);
    if (failures == 0) {
        printf("headgate core: ok\n");
    }
    return failures != 0;
}
