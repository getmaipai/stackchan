/* Host test for the subtitle strip timing (patch N04): the fixed zone, the pages, the fades, the 0.8 s hold after the last
 * sentence, and a sticky text. cc -std=c99 -Wall -Wextra -Werror -I<headers> subs_core_test.c */
#include <stdio.h>
#include <string.h>

#include "maipai_banner_core.h"
#include "maipai_subs_core.h"

static int fails;
#define CHECK(c)                                        \
    do {                                                \
        if (!(c)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #c); \
            fails++;                                    \
        }                                               \
    } while (0)

static void test_zone(void)
{
    /* the strip is the bottom zone of the banner core's table, and room for two 20 px lines with 4 px of padding */
    CHECK(MS_ZONE_Y0 == MB_ZONE_SUB_Y0 && MS_ZONE_Y1 == MB_ZONE_SUB_Y1);
    CHECK(MS_ZONE_Y1 - MS_ZONE_Y0 == 56);
    CHECK(MS_LINES * MS_FONT_PX + 2 * MS_PAD_Y <= MS_ZONE_Y1 - MS_ZONE_Y0);
    /* two lines of 23 px fill the middle; one line sits in the vertical middle of the zone */
    CHECK(ms_text_top(2, 23) == MS_ZONE_Y0 + (56 - 46) / 2);
    CHECK(ms_text_top(1, 23) == MS_ZONE_Y0 + (56 - 23) / 2);
}

static void test_one_sentence(void)
{
    ms_t s;
    ms_init(&s);
    const uint16_t chars[1] = {20};
    CHECK(!ms_visible(&s) && ms_opa(&s, 0) == 0);
    ms_begin(&s, 1000, 1, chars);
    CHECK(ms_visible(&s) && ms_opa(&s, 1000) == 0 && s.phase == MS_IN);
    CHECK(ms_opa(&s, 1075) > 100 && ms_opa(&s, 1075) < 150);  /* the 150 ms fade in */
    ms_tick(&s, 1200);
    CHECK(s.phase == MS_SHOW && ms_opa(&s, 1200) == 255);
    /* the robot is still talking: the page stays past its time, up to the linger limit */
    ms_tick(&s, 2700);
    CHECK(ms_visible(&s));
    /* it stops talking: 0.8 s later the strip fades out over 150 ms and is gone */
    const uint32_t stop = 3000;
    ms_end(&s, stop);
    ms_tick(&s, stop + 700);
    CHECK(s.phase == MS_SHOW);
    ms_tick(&s, stop + 801);
    CHECK(s.phase == MS_OUT);
    CHECK(ms_opa(&s, stop + 801 + 75) > 100 && ms_opa(&s, stop + 801 + 75) < 150);
    ms_tick(&s, stop + 801 + 151);
    CHECK(s.phase == MS_IDLE && !ms_visible(&s));
}

static void test_pages(void)
{
    ms_t s;
    ms_init(&s);
    const uint16_t chars[3] = {60, 40, 10};
    ms_begin(&s, 0, 3, chars);
    const uint32_t r0 = s.rev;
    ms_tick(&s, 3000);
    CHECK(s.page == 0);                            /* 60 characters: 3.3 s */
    CHECK(ms_tick(&s, 3400) == 1 && s.page == 1 && s.rev == r0 + 1);
    ms_tick(&s, 3400 + 2300);                      /* 40 characters: 2.2 s */
    CHECK(s.page == 2);
    CHECK(ms_page_ms(1) == MS_PAGE_MIN_MS && ms_page_ms(1000) == MS_PAGE_MAX_MS);
    /* the last page of a sentence waits for the robot to stop; a page that is long done leaves 0.8 s after the stop */
    ms_end(&s, 20000);
    ms_tick(&s, 20700);
    CHECK(s.phase == MS_SHOW);
    ms_tick(&s, 20801);
    CHECK(s.phase == MS_OUT);
}

static void test_next_sentence_replaces(void)
{
    ms_t s;
    ms_init(&s);
    const uint16_t a[1] = {30}, b[2] = {50, 20};
    ms_begin(&s, 0, 1, a);
    ms_tick(&s, 400);
    ms_begin(&s, 500, 2, b);
    CHECK(s.phase == MS_IN && s.page == 0 && s.pages == 2 && s.ending == 0);
    CHECK(ms_opa(&s, 500) == 0);                   /* fades in from nothing: no flash of the old words */
    ms_end(&s, 600);
    ms_begin(&s, 700, 1, a);                       /* a new sentence cancels an earlier end */
    CHECK(s.ending == 0);
}

static void test_linger_without_end_signal(void)
{
    ms_t s;
    ms_init(&s);
    const uint16_t a[1] = {10};
    ms_begin(&s, 0, 1, a);
    ms_tick(&s, 4000);
    CHECK(ms_visible(&s));
    ms_tick(&s, MS_LINGER_MS + MS_PAGE_MIN_MS + 10);
    CHECK(s.phase == MS_OUT);                      /* never stuck on the screen if the end signal is lost */
}

static void test_stop(void)
{
    ms_t s;
    ms_init(&s);
    const uint16_t a[1] = {10};
    ms_begin(&s, 0, 1, a);
    ms_tick(&s, 300);
    ms_stop(&s, 400);
    CHECK(s.phase == MS_OUT);
    ms_tick(&s, 400 + MS_FADE_MS + 1);
    CHECK(!ms_visible(&s));
    ms_stop(&s, 1000);                             /* stopping nothing is harmless */
    CHECK(!ms_visible(&s));
}

int main(void)
{
    test_zone();
    test_one_sentence();
    test_pages();
    test_next_sentence_replaces();
    test_linger_without_end_signal();
    test_stop();
    if (fails) {
        printf("%d failures\n", fails);
        return 1;
    }
    printf("subs_core_test: all passed\n");
    return 0;
}
