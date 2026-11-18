/* Host test for the offline dance cap (patch SF14). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the headers>. */
#include <stdio.h>
#include "maipai_dance_cap_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

/* run one second ticks of motion from t0 for n seconds; returns the second at which the cap stopped it, or -1 */
static int run(mdc_t* c, uint32_t t0, int n)
{
    for (int i = 0; i < n; i++) {
        if (!mdc_allow(c, t0 + (uint32_t)i * 1000u, 1)) return i;
    }
    return -1;
}

static void scenario(uint32_t t0)
{
    mdc_t c;
    mdc_init(&c);
    CHECK(run(&c, t0, 599) == -1);          /* just under ten minutes: fine */
    CHECK(mdc_allow(&c, t0 + 600000u, 1) == 0); /* ten minutes of motion: rest */
    CHECK(mdc_allow(&c, t0 + 600000u + 60000u, 1) == 0);
    CHECK(mdc_allow(&c, t0 + 600000u + MDC_REST_MS - 1000u, 1) == 0);
    CHECK(mdc_allow(&c, t0 + 600000u + MDC_REST_MS + 1000u, 1) == 1); /* rested: may move again */
    /* a short pause does not restart the count; a long one does */
    mdc_init(&c);
    CHECK(run(&c, t0, 300) == -1);
    CHECK(mdc_allow(&c, t0 + 305000u, 0) == 1); /* 5 s pause */
    CHECK(run(&c, t0 + 310000u, 300) == 290);   /* the count went on: stopped at ten minutes in all */
    mdc_init(&c);
    CHECK(run(&c, t0, 500) == -1);
    CHECK(mdc_allow(&c, t0 + 505000u, 0) == 1);
    CHECK(run(&c, t0 + 505000u + MDC_PAUSE_MS + 1000u, 590) == -1); /* a 30 s pause: counts from zero */
}

int main(void)
{
    scenario(1000u);
    scenario(0x90000000u); /* past 24.9 days of uptime */
    scenario(0xFFFFF000u); /* across the 32-bit wrap */
    if (failures) return 1;
    printf("dance cap ok\n");
    return 0;
}
