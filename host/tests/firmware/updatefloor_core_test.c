/* Host test for the build floor of signed updates (patch SF37). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header> ... */
#include <stdio.h>
#include <string.h>
#include "maipai_updatehdr_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void header(uint8_t h[MUH_HDR_LEN], uint32_t build)
{
    memset(h, 0, MUH_HDR_LEN);
    memcpy(h, "MPUH1", 5);
    memcpy(h + 48, "m5cores3", 8);
    h[8] = (uint8_t)build; h[9] = (uint8_t)(build >> 8); h[10] = (uint8_t)(build >> 16); h[11] = (uint8_t)(build >> 24);
    h[12] = 1;
}

int main(void)
{
    uint8_t h[MUH_HDR_LEN];
    muh_hdr_t out;
    /* the floor is the higher of the stored and the compiled number; negative or zero counts as none */
    CHECK(muh_floor(0, 0) == 0 && muh_floor(5, 0) == 5 && muh_floor(0, 7) == 7 && muh_floor(9, 7) == 9 && muh_floor(-3, 4) == 4);
    /* a unit flashed over USB with a compiled number refuses an older release even with an empty flash */
    header(h, 6);
    CHECK(muh_parse(h, sizeof(h), muh_floor(0, 7), "m5cores3", &out) == MUH_NOT_NEWER);
    header(h, 8);
    CHECK(muh_parse(h, sizeof(h), muh_floor(0, 7), "m5cores3", &out) == MUH_OK && out.build == 8);
    /* a build number of 2^31 or more is refused (it would be stored as a negative number) */
    header(h, 0x80000000u);
    CHECK(muh_parse(h, sizeof(h), 0, "m5cores3", &out) == MUH_BUILD_ZERO);
    header(h, 0x7fffffffu);
    CHECK(muh_parse(h, sizeof(h), 0, "m5cores3", &out) == MUH_OK);
    /* the board id: all zero is refused, another board is refused, an empty or too long id in the build refuses everything */
    header(h, 9);
    CHECK(muh_parse(h, sizeof(h), 0, "m5cores3", &out) == MUH_OK);
    CHECK(muh_parse(h, sizeof(h), 0, "m5cores4", &out) == MUH_BOARD_OTHER);
    CHECK(muh_parse(h, sizeof(h), 0, "m5core", &out) == MUH_BOARD_OTHER);
    CHECK(muh_parse(h, sizeof(h), 0, "", &out) == MUH_BOARD_OTHER);
    CHECK(muh_parse(h, sizeof(h), 0, "m5cores3x", &out) == MUH_BOARD_OTHER);
    memset(h + 48, 0, 8);
    CHECK(muh_parse(h, sizeof(h), 0, "m5cores3", &out) == MUH_BOARD_ZERO);
    if (failures) return 1;
    printf("update floor ok\n");
    return 0;
}
