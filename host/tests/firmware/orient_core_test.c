/* Host test for the orientation tracker (patch I01): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header> ... -lm. */
#include <stdio.h>
#include <string.h>
#include "maipai_orient_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

/* Feed n samples 100 ms apart; return the last non-NONE result and the number of events. */
static int feed(mo_orient_t* o, float x, float y, float z, int n, uint32_t* t, int* events)
{
    int last = MO_NONE;
    for (int i = 0; i < n; i++) {
        *t += 100;
        const int r = mo_update(o, x, y, z, *t);
        if (r != MO_NONE) {
            last = r;
            (*events)++;
        }
    }
    return last;
}

int main(void)
{
    mo_orient_t o;
    uint32_t t = 0;
    int ev     = 0;
    mo_init(&o);

    /* Resting upright (gravity on +z in the sensor frame): one pose event within one second. */
    CHECK(feed(&o, 0.2f, 0.1f, 9.8f, 10, &t, &ev) == MO_CHANGED && ev == 1 && o.current == 4);
    CHECK(strcmp(mo_name(o.current), "+z") == 0);
    /* Staying put makes no new event inside the minute, then one repeat. */
    ev = 0;
    feed(&o, 0.2f, 0.1f, 9.8f, 500, &t, &ev);
    CHECK(ev == 0);
    CHECK(feed(&o, 0.2f, 0.1f, 9.8f, 120, &t, &ev) == MO_STILL && ev == 1);

    /* Onto one ear (+x), reported within 0.6 s; then the other ear (-x): not locked (patch 071 bug). */
    ev = 0;
    CHECK(feed(&o, 9.8f, 0.0f, 0.3f, 6, &t, &ev) == MO_CHANGED && ev == 1 && o.current == 0);
    ev = 0;
    CHECK(feed(&o, -9.8f, 0.0f, 0.3f, 10, &t, &ev) == MO_CHANGED && ev == 1 && o.current == 1);
    /* And back upright. */
    ev = 0;
    CHECK(feed(&o, 0.0f, 0.0f, 9.8f, 10, &t, &ev) == MO_CHANGED && o.current == 4);

    /* Upside down: the -y axis (or any other) works the same way. */
    ev = 0;
    CHECK(feed(&o, 0.0f, -9.8f, 0.0f, 10, &t, &ev) == MO_CHANGED && o.current == 3);

    /* Carrying or shaking: a total pull outside 0.8 to 1.2 g never makes an event. */
    mo_init(&o);
    t = 0;
    ev = 0;
    feed(&o, 0.0f, 0.0f, 9.8f, 10, &t, &ev);
    ev = 0;
    for (int i = 0; i < 40; i++) {
        feed(&o, (i & 1) ? 20.0f : -20.0f, 0.0f, 9.8f, 1, &t, &ev);
    }
    CHECK(ev == 0 && o.current == 4);

    /* A flick shorter than the hold (3 samples) does not change the pose. */
    ev = 0;
    feed(&o, 9.8f, 0.0f, 0.3f, 3, &t, &ev);
    feed(&o, 0.0f, 0.0f, 9.8f, 10, &t, &ev);
    CHECK(ev == 0 && o.current == 4);

    /* A weak pull (under 6.5 along the dominant axis, e.g. tilted 45 degrees) is no pose. */
    mo_init(&o);
    t = 0;
    ev = 0;
    feed(&o, 6.2f, 0.0f, 6.2f, 20, &t, &ev);
    CHECK(ev == 0 && o.current == -1);

    /* The clock wrapping around does not break the minute repeat. */
    mo_init(&o);
    t = 0xFFFFFFFFu - 3000u;
    ev = 0;
    feed(&o, 0.0f, 0.0f, 9.8f, 10, &t, &ev);
    CHECK(ev == 1);
    ev = 0;
    feed(&o, 0.0f, 0.0f, 9.8f, 700, &t, &ev);
    CHECK(ev == 1);

    CHECK(strcmp(mo_name(-1), "?") == 0 && strcmp(mo_name(6), "?") == 0);
    if (failures == 0) {
        printf("orient core: ok\n");
    }
    return failures != 0;
}
