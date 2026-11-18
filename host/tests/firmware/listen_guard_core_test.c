/* Host test for the listening guard rule of patch SF03. cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include "maipai_listen_guard_core.h"

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
    CHECK(!mlg_should_end(3, 3, 8, 60));   /* early, silent */
    CHECK(mlg_should_end(8, 8, 8, 60));    /* 8 s of silence ends it */
    CHECK(!mlg_should_end(20, 2, 8, 60));  /* a sentence that runs on: voice 2 s ago keeps it open */
    CHECK(mlg_should_end(30, 8, 8, 60));   /* then 8 s of silence ends it */
    CHECK(mlg_should_end(60, 0, 8, 60));   /* nothing holds a turn open past the cap */
    if (failures) return 1;
    printf("listen guard ok\n");
    return 0;
}
