/* Host test for the quiet schedule with days and "Quiet now" (patch SF52). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include "maipai_sounds_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

#define MIN(h, m) ((h) * 60 + (m))
enum { SUN = 0, MON, TUE, WED, THU, FRI, SAT };
#define DAY(d) (1u << (d))

int main(void)
{
    ms_policy_t p;
    ms_policy_default(&p);
    /* default: off until set, every day selected, quiet-now off */
    CHECK(p.quiet_from == -1 && p.quiet_days == 0x7f && p.quiet_now == 0);
    CHECK(!ms_is_night_ex(&p, MIN(23, 0), WED, 0));
    /* a schedule 22:00 to 07:00 every day */
    p.quiet_from = MIN(22, 0);
    p.quiet_to = MIN(7, 0);
    CHECK(ms_is_night_ex(&p, MIN(23, 30), WED, 0) && ms_is_night_ex(&p, MIN(3, 0), THU, 0) && !ms_is_night_ex(&p, MIN(12, 0), WED, 0));
    CHECK(!ms_is_night_ex(&p, MIN(7, 0), THU, 0) && ms_is_night_ex(&p, MIN(6, 59), THU, 0) && ms_is_night_ex(&p, MIN(22, 0), THU, 0));
    /* weekdays only (Monday to Friday): a window belongs to the day it starts on */
    p.quiet_days = (uint8_t)(DAY(MON) | DAY(TUE) | DAY(WED) | DAY(THU) | DAY(FRI));
    CHECK(ms_is_night_ex(&p, MIN(23, 0), FRI, 0));      /* Friday evening: quiet */
    CHECK(ms_is_night_ex(&p, MIN(3, 0), SAT, 0));       /* Saturday 03:00 belongs to Friday's window: quiet */
    CHECK(!ms_is_night_ex(&p, MIN(23, 0), SAT, 0));     /* Saturday evening: not a selected day */
    CHECK(!ms_is_night_ex(&p, MIN(3, 0), SUN, 0));      /* Sunday 03:00 belongs to Saturday's window: not quiet */
    CHECK(ms_is_night_ex(&p, MIN(3, 0), MON, 0) == 0);  /* Monday 03:00 belongs to Sunday's window: not quiet */
    CHECK(ms_is_night_ex(&p, MIN(23, 0), SUN, 0) == 0 && ms_is_night_ex(&p, MIN(23, 0), MON, 0));
    /* a same-day window (13:00 to 15:00) on Tuesday only */
    p.quiet_from = MIN(13, 0);
    p.quiet_to = MIN(15, 0);
    p.quiet_days = DAY(TUE);
    CHECK(ms_is_night_ex(&p, MIN(14, 0), TUE, 0) && !ms_is_night_ex(&p, MIN(14, 0), WED, 0));
    /* no days selected: the schedule never applies */
    p.quiet_days = 0;
    CHECK(!ms_is_night_ex(&p, MIN(14, 0), TUE, 0));
    /* no calendar yet (weekday -1): any selected day counts, none selected never */
    p.quiet_days = 0x7f;
    CHECK(ms_is_night_ex(&p, MIN(14, 0), -1, 0));
    p.quiet_days = 0;
    CHECK(!ms_is_night_ex(&p, MIN(14, 0), -1, 0));
    /* the clock is not set (minute -1): the schedule says nothing */
    p.quiet_days = 0x7f;
    CHECK(!ms_is_night_ex(&p, -1, TUE, 0));
    /* "Quiet now" wins over everything, and the host's dark verdict counts only while the host is up */
    ms_policy_default(&p);
    p.quiet_now = 1;
    CHECK(ms_is_night_ex(&p, MIN(12, 0), WED, 0) && ms_is_night_ex(&p, -1, -1, 0));
    p.quiet_now = 0;
    p.dark = 1;
    CHECK(ms_is_night_ex(&p, MIN(12, 0), WED, 1) && !ms_is_night_ex(&p, MIN(12, 0), WED, 0));
    /* the exceptions: with quiet now on, the safety cues and the tones that answer a person still play; the ordinary cues do not */
    ms_policy_default(&p);
    p.quiet_now = 1;
    const int night = ms_is_night_ex(&p, MIN(12, 0), WED, 0);
    CHECK(night == 1);
    CHECK(ms_decide(&p, MS_SND_LOW_BATTERY, 0, night, 0) == MS_OK);
    CHECK(ms_decide(&p, MS_SND_SHUTTER, 0, night, 0) == MS_OK);
    CHECK(ms_decide(&p, MS_SND_POPUP, 0, night, 0) == MS_OK);
    CHECK(ms_decide(&p, MS_SND_SUCCESS, 0, night, 0) == MS_NIGHT);
    CHECK(ms_decide(&p, MS_SND_OFFLINE, 0, night, 0) == MS_NIGHT);
    /* find-my-robot still sounds through quiet */
    CHECK(ms_decide(&p, MS_SND_SUCCESS, 0, night, MS_BYPASS_FIND) == MS_OK);
    if (failures) return 1;
    printf("quiet schedule core ok\n");
    return 0;
}
