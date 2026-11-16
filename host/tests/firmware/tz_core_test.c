/* Host test for the time zone core (patch U03): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>. */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "maipai_tz_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

/* The UTC offset in minutes the C library gives a zone rule at an instant. */
static int offset_min(const char* posix, long long epoch)
{
    setenv("TZ", posix, 1);
    tzset();
    const time_t t = (time_t)epoch;
    struct tm lt;
    localtime_r(&t, &lt);
    struct tm gt;
    gmtime_r(&t, &gt);
    const int a = lt.tm_hour * 60 + lt.tm_min + lt.tm_mday * 1440;
    const int b = gt.tm_hour * 60 + gt.tm_min + gt.tm_mday * 1440;
    int d = a - b;
    if (d > 20 * 1440) d -= 28 * 1440; /* a month wrap: not reached for the dates used */
    if (d < -20 * 1440) d += 28 * 1440;
    return d;
}

static void test_list_shape(void)
{
    CHECK(MZ_COUNT >= 25);
    for (int i = 0; i < MZ_COUNT; i++) {
        CHECK(MZ_ZONES[i].id[0] != '\0' && MZ_ZONES[i].label[0] != '\0' && MZ_ZONES[i].posix[0] != '\0');
        for (const unsigned char* p = (const unsigned char*)MZ_ZONES[i].label; *p; p++) CHECK(*p < 128); /* the screen font has no accents */
        for (int j = i + 1; j < MZ_COUNT; j++) {
            CHECK(strcmp(MZ_ZONES[i].id, MZ_ZONES[j].id) != 0);
            CHECK(strcmp(MZ_ZONES[i].label, MZ_ZONES[j].label) != 0);
        }
        CHECK(mz_find(MZ_ZONES[i].id) == i);
    }
    CHECK(mz_find("nowhere") == -1 && mz_find(NULL) == -1 && mz_find("") == -1);
    CHECK(mz_default_index() == mz_find("utc") && mz_default_index() >= 0);
    CHECK(mz_find_posix("EST5EDT,M3.2.0,M11.1.0") == mz_find("america_new_york"));
    CHECK(mz_find_posix("GMT0") == mz_find("utc")); /* the stock default reads as UTC */
    CHECK(mz_find_posix("CET-1CEST,M3.5.0,M10.5.0/3") >= 0 && mz_find_posix("XYZ") == -1 && mz_find_posix(NULL) == -1);
}

static void test_step_wraps(void)
{
    CHECK(mz_step(0, -1) == MZ_COUNT - 1);
    CHECK(mz_step(MZ_COUNT - 1, 1) == 0);
    CHECK(mz_step(5, 1) == 6 && mz_step(5, -1) == 4);
    CHECK(mz_step(3, MZ_COUNT) == 3);
    CHECK(mz_step(0, -MZ_COUNT - 1) == MZ_COUNT - 1);
}

/* Every rule is a real POSIX rule: summer and winter offsets match what people expect. */
static void test_offsets_are_right(void)
{
    const long long jan = 1768478400LL;  /* 15 January 2026, 12:00 UTC */
    const long long jul = 1784116800LL;  /* 15 July 2026, 12:00 UTC */
    struct { const char* id; int winter; int summer; } want[] = {
        {"america_new_york", -300, -240}, {"america_los_angeles", -480, -420}, {"america_chicago", -360, -300},
        {"america_denver", -420, -360},   {"america_phoenix", -420, -420},     {"europe_london", 0, 60},
        {"europe_paris", 60, 120},        {"europe_berlin", 60, 120},          {"europe_madrid", 60, 120},
        {"europe_rome", 60, 120},         {"europe_athens", 120, 180},         {"europe_moscow", 180, 180},
        {"asia_kolkata", 330, 330},       {"asia_tokyo", 540, 540},            {"asia_shanghai", 480, 480},
        {"australia_sydney", 660, 600},   {"pacific_auckland", 780, 720},     {"utc", 0, 0},
        {"pacific_honolulu", -600, -600}, {"america_sao_paulo", -180, -180},   {"america_bogota", -300, -300},
        {"asia_dubai", 240, 240},         {"asia_karachi", 300, 300},          {"asia_dhaka", 360, 360},
        {"asia_bangkok", 420, 420},       {"america_anchorage", -540, -480},   {"america_halifax", -240, -180},
        {"europe_lisbon", 0, 60},         {"africa_cairo", 120, 120},          {"america_mexico_city", -360, -360},
        {"atlantic_azores", -60, 0},
    };
    const int n = (int)(sizeof(want) / sizeof(want[0]));
    CHECK(n == MZ_COUNT); /* every zone in the list is checked */
    for (int k = 0; k < n; k++) {
        const int i = mz_find(want[k].id);
        CHECK(i >= 0);
        if (i < 0) continue;
        const int w = offset_min(MZ_ZONES[i].posix, jan);
        const int s = offset_min(MZ_ZONES[i].posix, jul);
        if (w != want[k].winter || s != want[k].summer) {
            printf("FAIL %s: winter %d (want %d) summer %d (want %d)\n", want[k].id, w, want[k].winter, s, want[k].summer);
            failures++;
        }
    }
}

static void test_clock_range_and_line(void)
{
    CHECK(mz_epoch_ok(1768478400LL));
    CHECK(!mz_epoch_ok(0) && !mz_epoch_ok(-5) && !mz_epoch_ok(1704067199LL) && !mz_epoch_ok(4102444800LL));
    CHECK(mz_epoch_ok(1704067200LL));
    char out[40];
    mz_line(out, sizeof(out), mz_find("america_new_york"));
    CHECK(strcmp(out, "New York") == 0);
    mz_line(out, sizeof(out), -1);
    CHECK(strcmp(out, "Time zone not set") == 0);
    mz_line(out, sizeof(out), MZ_COUNT);
    CHECK(strcmp(out, "Time zone not set") == 0);
    CHECK(strlen(mz_err_word(MZ_ERR_ZONE)) > 20 && strlen(mz_err_word(MZ_ERR_TIME)) > 20);
}

int main(void)
{
    test_list_shape();
    test_step_wraps();
    test_offsets_are_right();
    test_clock_range_and_line();
    if (failures) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
