/* Host test for the Train 2 cores (patches T01 to T05): cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers>. */
#include <stdio.h>
#include <string.h>
#include "maipai_battery_core.h"
#include "maipai_hourly_core.h"
#include "maipai_wake_core.h"
#include "maipai_link_quiet_core.h"
#include "maipai_cue_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static mb_event_t polls(mb_ladder_t* l, int level, int on_power, int n)
{
    mb_event_t last = MB_NONE;
    for (int i = 0; i < n; i++) {
        mb_event_t e = mb_update(l, level, on_power);
        if (e != MB_NONE) last = e;
    }
    return last;
}

static void test_battery(void)
{
    mb_ladder_t l;
    mb_init(&l);
    CHECK(polls(&l, 60, 0, 5) == MB_NONE);
    /* one noisy low reading never fires; three agreeing ones do, once */
    CHECK(mb_update(&l, 19, 0) == MB_NONE);
    CHECK(mb_update(&l, 40, 0) == MB_NONE);
    CHECK(mb_update(&l, 19, 0) == MB_NONE && mb_update(&l, 19, 0) == MB_NONE && mb_update(&l, 19, 0) == MB_CHIRP);
    CHECK(polls(&l, 19, 0, 30) == MB_NONE);
    CHECK(polls(&l, 9, 0, 3) == MB_ASK);
    CHECK(polls(&l, 9, 0, 30) == MB_NONE);
    CHECK(polls(&l, 4, 0, 3) == MB_SLEEP);
    CHECK(polls(&l, 4, 0, 30) == MB_NONE);
    /* a cable in re-arms every step and no step fires on it */
    CHECK(polls(&l, 3, 1, 10) == MB_NONE);
    CHECK(polls(&l, 19, 0, 3) == MB_CHIRP);
    /* a failed read (level 0) or an impossible one changes nothing */
    mb_init(&l);
    CHECK(polls(&l, 0, 0, 10) == MB_NONE && polls(&l, 101, 0, 10) == MB_NONE);
    /* a unit that boots at 8 percent fires the request only */
    mb_init(&l);
    CHECK(polls(&l, 8, 0, 3) == MB_ASK);
    CHECK(polls(&l, 8, 0, 20) == MB_NONE);
    /* the level creeping back up re-arms a step only once it is 5 points clear */
    CHECK(polls(&l, 12, 0, 10) == MB_NONE); /* 12 is still within 5 of 10 */
    CHECK(polls(&l, 16, 0, 10) == MB_NONE);
    CHECK(polls(&l, 8, 0, 3) == MB_ASK);
    /* the power is cut only while still on battery and still at 5 or less */
    CHECK(mb_sleep_still_needed(4, 0) && !mb_sleep_still_needed(4, 1) && !mb_sleep_still_needed(9, 0));
    CHECK(!mb_sleep_still_needed(0, 0));
    /* words: both languages, ASCII only */
    for (int lang = 0; lang < 2; lang++) {
        for (int ev = MB_ASK; ev <= MB_SLEEP; ev++) {
            const char* t = mb_text((mb_lang_t)lang, (mb_event_t)ev);
            CHECK(t != NULL && strlen(t) > 10 && strlen(t) < 40);
            for (const char* c = t; *c; c++) CHECK((unsigned char)*c < 0x80);
        }
    }
    CHECK(strcmp(mb_text(MB_LANG_EN, MB_CHIRP), "") == 0);
}

static void test_hourly(void)
{
    ms_policy_t p;
    ms_policy_default(&p);
    int32_t last = -1;
    /* the default quiet window is 22:00 to 07:00 */
    CHECK(mh_quiet_now(&p, 23 * 60, 0) && mh_quiet_now(&p, 3 * 60, 0) && !mh_quiet_now(&p, 10 * 60, 0));
    p.quiet_from = 13 * 60;
    p.quiet_to = 14 * 60;
    CHECK(mh_quiet_now(&p, 13 * 60 + 5, 0) && !mh_quiet_now(&p, 23 * 60, 0)); /* the person's window wins */
    ms_policy_default(&p);
    p.dark = 1;
    CHECK(mh_quiet_now(&p, 12 * 60, 1) && !mh_quiet_now(&p, 12 * 60, 0)); /* dark counts only while Home is up */

    CHECK(mh_decide(&last, 1, -1, 5, 0, 0, 0) == MH_NO_CLOCK);
    CHECK(mh_decide(&last, 0, 10 * 60, 5, 0, 0, 0) == MH_OFF);
    CHECK(mh_decide(&last, 1, 10 * 60 + 1, 5, 0, 0, 0) == MH_NOT_TOP);
    CHECK(mh_decide(&last, 1, 10 * 60, 5, 0, 0, 0) == MH_CHIME);
    CHECK(mh_decide(&last, 1, 10 * 60, 5, 0, 0, 0) == MH_DONE); /* once per hour, however long the minute lasts */
    CHECK(mh_decide(&last, 1, 11 * 60, 6, 0, 0, 0) == MH_CHIME);
    /* quiet skips the whole hour; busy waits for a free moment inside the minute */
    CHECK(mh_decide(&last, 1, 12 * 60, 7, 1, 0, 0) == MH_QUIET);
    CHECK(mh_decide(&last, 1, 12 * 60, 7, 0, 0, 0) == MH_DONE);
    CHECK(mh_decide(&last, 1, 13 * 60, 8, 0, 1, 0) == MH_BUSY);
    CHECK(mh_decide(&last, 1, 13 * 60, 8, 0, 0, 0) == MH_CHIME);
    /* the test flag ignores the minute and the once-an-hour record but never quiet or busy */
    CHECK(mh_decide(&last, 1, 13 * 60 + 30, 8, 0, 0, 1) == MH_CHIME);
    CHECK(mh_decide(&last, 1, 13 * 60 + 30, 8, 1, 0, 1) == MH_QUIET);
    CHECK(mh_decide(&last, 1, 13 * 60 + 30, 8, 0, 1, 1) == MH_BUSY);
    CHECK(mh_decide(&last, 0, 13 * 60 + 30, 8, 0, 0, 1) == MH_OFF);
}

static void test_wake(void)
{
    CHECK(mw_judge(1, 0, 50, 45) == MW_ALIVE);
    CHECK(mw_judge(0, 0, 0, 0) == MW_SKIPPED_NOT_ARMED);
    CHECK(mw_judge(1, 1, 0, 0) == MW_SKIPPED_BUSY);
    CHECK(mw_judge(1, 0, 3, 3) == MW_NO_AUDIO);
    CHECK(mw_judge(1, 0, 50, 1) == MW_NO_FETCH);
    CHECK(mw_needs_repair(MW_NO_AUDIO) && mw_needs_repair(MW_NO_FETCH));
    CHECK(!mw_needs_repair(MW_ALIVE) && !mw_needs_repair(MW_SKIPPED_NOT_ARMED) && !mw_needs_repair(MW_SKIPPED_BUSY));
    CHECK(strcmp(mw_word(MW_SKIPPED_BUSY), "skipped") == 0 && strcmp(mw_why(MW_SKIPPED_BUSY), "busy") == 0);
}

static void test_link(void)
{
    mq_link_t l;
    mq_init(&l);
    mq_down(&l, 1000);
    CHECK(mq_poll(&l, 1000 + 59000, 0) == 0);  /* a one minute restart: silent */
    CHECK(mq_up(&l) == 0);                     /* and nothing on return */
    mq_down(&l, 5000);
    CHECK(mq_poll(&l, 5000 + 179999u, 0) == 0);
    CHECK(mq_poll(&l, 5000 + 180000u, 1) == 0); /* waiting for approval: never a tone */
    CHECK(mq_poll(&l, 5000 + 180000u, 0) == 1); /* three minutes: one tone */
    CHECK(mq_poll(&l, 5000 + 200000u, 0) == 0); /* only one per outage */
    mq_down(&l, 9999);                          /* a second down call inside the outage changes nothing */
    CHECK(mq_up(&l) == 1);                      /* back chime after a tone that sounded */
    CHECK(mq_up(&l) == 0);
    /* a tick counter that wrapped still measures the outage */
    mq_down(&l, 0xFFFFFF00u);
    CHECK(mq_poll(&l, 0x00000100u, 0) == 0);
    CHECK(mq_poll(&l, 0xFFFFFF00u + MQ_OFFLINE_SOUND_AFTER_MS, 0) == 1);
}

static void test_cue(void)
{
    mc_cue_t c;
    mc_init(&c);
    CHECK(mc_poll(&c, 100) == 0);
    CHECK(mc_begin(&c, 1000, MC_HOLD_PHOTO_MS) == 1); /* drawn now */
    CHECK(mc_begin(&c, 1500, MC_HOLD_STREAM_MS) == 0); /* already shown: extended, not drawn again */
    CHECK(mc_poll(&c, 3999) == 0);
    CHECK(mc_poll(&c, 4000) == 1); /* 1500 + 2500: the later frame's hold won */
    CHECK(mc_poll(&c, 4001) == 0);
    /* a later short hold never cuts an earlier long one */
    CHECK(mc_begin(&c, 10000, MC_HOLD_PHOTO_MS) == 1);
    CHECK(mc_begin(&c, 10100, 100) == 0);
    CHECK(mc_poll(&c, 12999) == 0 && mc_poll(&c, 13000) == 1);
    /* the clock wrapping inside a hold */
    CHECK(mc_begin(&c, 0xFFFFFF00u, MC_HOLD_STREAM_MS) == 1);
    CHECK(mc_poll(&c, 0x00000100u) == 0);
    CHECK(mc_poll(&c, 0xFFFFFF00u + MC_HOLD_STREAM_MS) == 1);
}

int main(void)
{
    test_battery();
    test_hourly();
    test_wake();
    test_link();
    test_cue();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
