/* Host test for the single overlay screen state (patch UI09): cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> screens_core_test.c */
#include <stdio.h>
#include <string.h>
#include "maipai_screens_core.h"

static int failures;
#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            printf("FAIL line %d: %s\n", __LINE__, #cond);               \
            failures++;                                                  \
        }                                                                \
    } while (0)

/* A model of the glass: a screen "shows" from its open to its close. The manager closes the previous one before the next opens. */
static mscr_t S;
static unsigned shown;
static void open_screen(int id)
{
    const int prev = mscr_open(&S, id);
    if (prev != MSCR_NONE) {
        shown &= ~(1u << prev);   /* the manager closes the one that was up ... */
        mscr_closed(&S, prev);      /* ... and it reports itself closed (a no-op: the new one is already current) */
    }
    shown |= 1u << id;
}
static void close_screen(int id)
{
    shown &= ~(1u << id);
    mscr_closed(&S, id);
}
static int count(unsigned m) { int n = 0; for (int i = 0; i < MSCR_COUNT; i++) n += (m >> i) & 1u; return n; }

int main(void)
{
    mscr_init(&S);
    shown = 0;
    CHECK(S.cur == MSCR_NONE);
    /* the report: Settings, then Games (from More), then More, at the same time */
    open_screen(MSCR_SETTINGS);
    CHECK(count(shown) == 1 && S.cur == MSCR_SETTINGS);
    open_screen(MSCR_MORE);
    CHECK(count(shown) == 1 && S.cur == MSCR_MORE && !(shown & (1u << MSCR_SETTINGS)));
    open_screen(MSCR_QUICK);
    CHECK(count(shown) == 1 && S.cur == MSCR_QUICK);
    open_screen(MSCR_WIFI);
    CHECK(count(shown) == 1 && S.cur == MSCR_WIFI);
    open_screen(MSCR_WIFI);                       /* the same screen again: nothing to close, still one */
    CHECK(count(shown) == 1 && mscr_open(&S, MSCR_WIFI) == MSCR_NONE);
    close_screen(MSCR_WIFI);
    CHECK(count(shown) == 0 && S.cur == MSCR_NONE);   /* a close leaves nothing stale */
    close_screen(MSCR_MORE);                      /* closing a screen that is not up changes nothing */
    CHECK(count(shown) == 0 && S.cur == MSCR_NONE);
    /* every ordered pair and every long random sequence keeps at most one screen up and the state equal to it */
    for (int a = 0; a < MSCR_COUNT; a++) {
        for (int b = 0; b < MSCR_COUNT; b++) {
            mscr_init(&S);
            shown = 0;
            open_screen(a);
            open_screen(b);
            CHECK(count(shown) == 1 && S.cur == b && (shown & (1u << b)));
            close_screen(b);
            CHECK(shown == 0 && S.cur == MSCR_NONE);
        }
    }
    uint32_t r = 12345u;
    mscr_init(&S);
    shown = 0;
    for (int i = 0; i < 20000; i++) {
        r ^= r << 13; r ^= r >> 17; r ^= r << 5;
        const int id = (int)(r % MSCR_COUNT);
        if ((r >> 8) % 3 == 0) close_screen(id); else open_screen(id);
        CHECK(count(shown) <= 1);
        CHECK(S.cur == MSCR_NONE ? shown == 0 : shown == (1u << S.cur));
    }
    if (failures == 0) {
        printf("screens_core_test: all passed\n");
        return 0;
    }
    printf("%d failure(s)\n", failures);
    return 1;
}
