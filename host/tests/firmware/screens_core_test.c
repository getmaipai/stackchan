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

/* ---- patch NX03: no two overlay screens are ever visible ----
 * Every named screen the unit can show, mapped to the surface the manager knows. The Apps wall, the games wall, Timers and Alarms are four views of
 * the one Apps screen; the six swipe pages are one page surface. */
typedef struct {
    const char* name;
    int surface;
} named_t;
static const named_t NAMES[] = {
    {"sheet", MSCR_SHEET},       {"page clock", MSCR_PAGE},   {"page timers", MSCR_PAGE},   {"page games", MSCR_PAGE},
    {"page actions", MSCR_PAGE}, {"page frame", MSCR_PAGE},   {"page tiles", MSCR_PAGE},    {"apps", MSCR_APPS},
    {"games wall", MSCR_APPS},   {"timers", MSCR_APPS},       {"alarms", MSCR_APPS},        {"settings", MSCR_SETTINGS},
    {"quick settings", MSCR_QUICK}, {"wifi", MSCR_WIFI},      {"more", MSCR_MORE},          {"lock keypad", MSCR_LOCK},
    {"first run", MSCR_FIRSTRUN},
};
#define N_NAMES ((int)(sizeof(NAMES) / sizeof(NAMES[0])))

static mscr_t M;
static unsigned glass; /* what is really drawn: kept apart from the manager's own set, so the check does not trust the thing it checks */
static int overlays_on_glass(void)
{
    int n = 0;
    for (int i = 0; i < MSCR_COUNT; i++) {
        if (i != MSCR_SHEET && ((glass >> i) & 1u)) n++;
    }
    return n;
}
/* What the unit's callers do: a screen opens only while not locked (the lock check of patch LK03), and the manager's close list is obeyed. */
static void show_named(int k)
{
    const int id = NAMES[k].surface;
    if ((glass & MSCR_BIT(MSCR_LOCK)) && id != MSCR_LOCK) return;   /* locked: nothing else opens */
    const unsigned close = mscr_enter(&M, id);
    for (int i = 0; i < MSCR_COUNT; i++) {
        if (close & MSCR_BIT(i)) {
            glass &= ~MSCR_BIT(i);
            mscr_exit(&M, i);   /* the closed screen reports itself */
        }
    }
    M.cur = (int8_t)id;
    glass |= MSCR_BIT(id);
}
static void hide_surface(int id)
{
    glass &= ~MSCR_BIT(id);
    mscr_exit(&M, id);
}
static void check_glass(void)
{
    CHECK(overlays_on_glass() <= 1);                                              /* never two overlay screens */
    CHECK(!(glass & MSCR_BIT(MSCR_SHEET)) || (glass & ~(MSCR_BIT(MSCR_SHEET) | MSCR_BIT(MSCR_PAGE))) == 0);   /* the sheet only over the face or a page */
    CHECK(M.visible_mask == glass && mscr_valid(&M));
}

static void test_first_run_pauses_face(void)
{
    mscr_t state;
    mscr_init(&state);
    CHECK((state.visible_mask & ~MSCR_BIT(MSCR_SHEET)) == 0); /* the face runs with no full-screen surface */
    mscr_enter(&state, MSCR_FIRSTRUN);
    CHECK((state.visible_mask & ~MSCR_BIT(MSCR_SHEET)) != 0); /* first run pauses the face */
    CHECK(state.visible_mask == MSCR_BIT(MSCR_FIRSTRUN));
    mscr_exit(&state, MSCR_FIRSTRUN);
    CHECK((state.visible_mask & ~MSCR_BIT(MSCR_SHEET)) == 0);
}

static void test_surfaces(void)
{
    /* the reported case: the games page is up, the sheet opens over it, the Apps tile is tapped: only the Apps wall may be left */
    mscr_init(&M);
    glass = 0;
    show_named(3);   /* page games */
    show_named(0);   /* the sheet over it: both are allowed */
    CHECK(glass == (MSCR_BIT(MSCR_PAGE) | MSCR_BIT(MSCR_SHEET)));
    check_glass();
    show_named(7);   /* apps */
    CHECK(glass == MSCR_BIT(MSCR_APPS));
    check_glass();
    /* the sheet alone, over the face, and a page opening closes it */
    mscr_init(&M);
    glass = 0;
    show_named(0);
    CHECK(glass == MSCR_BIT(MSCR_SHEET));
    show_named(1);
    CHECK(glass == MSCR_BIT(MSCR_PAGE));
    /* an overlay screen is never covered by the sheet or a page: they close it */
    show_named(11);  /* settings */
    show_named(0);
    CHECK(glass == MSCR_BIT(MSCR_SHEET));
    show_named(11);
    show_named(4);
    CHECK(glass == MSCR_BIT(MSCR_PAGE));
    /* the lock keypad closes everything and nothing opens over it until it is gone */
    show_named(0);
    show_named(15);
    CHECK(glass == MSCR_BIT(MSCR_LOCK));
    for (int k = 0; k < N_NAMES - 1; k++) show_named(k);
    CHECK(glass == MSCR_BIT(MSCR_LOCK));
    hide_surface(MSCR_LOCK);
    CHECK(glass == 0 && M.cur == MSCR_NONE);
    /* every ordered pair and triple of named screens, from every start, with a close after each */
    for (int a = 0; a < N_NAMES; a++) {
        for (int b = 0; b < N_NAMES; b++) {
            for (int c = 0; c < N_NAMES; c++) {
                mscr_init(&M);
                glass = 0;
                show_named(a);
                check_glass();
                show_named(b);
                check_glass();
                show_named(c);
                check_glass();
                if (!(glass & MSCR_BIT(MSCR_LOCK))) CHECK(glass & MSCR_BIT(NAMES[c].surface));   /* the last one asked for is on the glass */
            }
        }
    }
    /* a long random walk of opens and closes, every step checked against the glass */
    uint32_t r = 987654321u;
    mscr_init(&M);
    glass = 0;
    for (int i = 0; i < 50000; i++) {
        r ^= r << 13; r ^= r >> 17; r ^= r << 5;
        if ((r >> 9) % 4 == 0) hide_surface((int)(r % MSCR_COUNT)); else show_named((int)(r % N_NAMES));
        check_glass();
    }
    /* an id outside the table changes nothing */
    const mscr_t before = M;
    CHECK(mscr_enter(&M, -1) == 0 && mscr_enter(&M, MSCR_COUNT) == 0 && memcmp(&before, &M, sizeof(M)) == 0);
}

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
    test_surfaces();
    test_first_run_pauses_face();
    if (failures == 0) {
        printf("screens_core_test: all passed\n");
        return 0;
    }
    printf("%d failure(s)\n", failures);
    return 1;
}
