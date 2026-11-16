/* Host test for the mood core (patch M01): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include <string.h>
#include "maipai_mood_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void test_days(void)
{
    CHECK(mm_day_from_civil(2020, 1, 1) == 0); /* day 0 means no clock, so the epoch itself reads as 0 */
    CHECK(mm_day_from_civil(2020, 1, 2) == 1);
    CHECK(mm_day_from_civil(2020, 3, 1) - mm_day_from_civil(2020, 2, 28) == 2); /* 2020 is a leap year */
    CHECK(mm_day_from_civil(2021, 1, 1) - mm_day_from_civil(2020, 12, 31) == 1);
    CHECK(mm_day_from_civil(2026, 11, 16) - mm_day_from_civil(2026, 11, 15) == 1);
    CHECK(mm_day_from_civil(2019, 6, 1) == 0);
}

static void test_pets(void)
{
    mm_t m;
    mm_init(&m);
    CHECK(m.care == 50 && m.level == MM_OK && !m.dirty);
    CHECK(mm_pet(&m, 1000) == 1 && m.care == 54 && m.dirty);
    CHECK(mm_pet(&m, 5000) == 0 && m.care == 54); /* too soon: not counted */
    CHECK(mm_pet(&m, 21000) == 1 && m.care == 58);
    CHECK(mm_pet(&m, 25000) == 0); /* the gap runs from the last pet, counted or not */
    CHECK(mm_pet(&m, 46000) == 1 && m.care == 62);
    CHECK(mm_pet(&m, 70000) == 1 && m.care == 66);
    CHECK(m.level == MM_OK);
    CHECK(mm_pet(&m, 100000) == 1 && m.care == 70 && m.level == MM_HIGH);
    /* a day of petting is capped */
    mm_init(&m);
    uint32_t t = 0;
    for (int i = 0; i < 40; i++) {
        t += 30000;
        mm_pet(&m, t);
    }
    CHECK(m.pets_today == MM_PETS_PER_DAY && m.care == 50 + MM_PETS_PER_DAY * MM_PET_POINTS);
    /* care never passes 100 */
    mm_init(&m);
    m.care = 98;
    CHECK(mm_pet(&m, 1) == 1 && m.care == 100);
}

static void test_days_pass(void)
{
    mm_t m;
    mm_init(&m);
    CHECK(mm_new_day(&m, 0) == 0 && m.day == 0); /* no clock: nothing */
    CHECK(mm_new_day(&m, 100) == 1 && m.day == 100 && m.care == 50);
    CHECK(mm_new_day(&m, 100) == 0);
    /* a day with a pet costs nothing; the next day without one costs 12 */
    mm_pet(&m, 1000);
    CHECK(m.care == 54);
    CHECK(mm_new_day(&m, 101) == 1 && m.care == 54 && m.pets_today == 0);
    CHECK(mm_new_day(&m, 102) == 1 && m.care == 42);
    /* three days away: the day that ended plus two whole days */
    CHECK(mm_new_day(&m, 105) == 1 && m.care == 6);
    /* it never goes below 0, and a long absence is capped at 14 days */
    CHECK(mm_new_day(&m, 400) == 1 && m.care == 0 && m.level == MM_LOW);
    mm_init(&m);
    m.care = 100;
    mm_new_day(&m, 10);
    mm_new_day(&m, 1000);
    CHECK(m.care == 0); /* 100 - 14 * 12 is below 0 */
    /* a clock that moves back changes the day and nothing else */
    mm_init(&m);
    m.care = 80;
    mm_new_day(&m, 50);
    CHECK(mm_new_day(&m, 40) == 1 && m.day == 40 && m.care == 80);
}

static void test_levels(void)
{
    CHECK(mm_level_for(MM_OK, 69) == MM_OK && mm_level_for(MM_OK, 70) == MM_HIGH);
    CHECK(mm_level_for(MM_HIGH, 67) == MM_HIGH && mm_level_for(MM_HIGH, 66) == MM_OK);
    CHECK(mm_level_for(MM_OK, 30) == MM_OK && mm_level_for(MM_OK, 29) == MM_LOW);
    CHECK(mm_level_for(MM_LOW, 32) == MM_LOW && mm_level_for(MM_LOW, 33) == MM_OK);
    CHECK(mm_face(MM_HIGH) == 1 && mm_face(MM_OK) == 0 && mm_face(MM_LOW) == 2);
    CHECK(strcmp(mm_word(MM_HIGH), "high") == 0 && strcmp(mm_word(MM_LOW), "low") == 0);
}

static void test_record(void)
{
    mm_t m, n;
    uint8_t rec[MM_REC_BYTES];
    mm_init(&m);
    m.care = 77;
    m.pets_today = 5;
    m.day = 2500;
    mm_store(&m, rec);
    CHECK(mm_load(&n, rec) == 1 && n.care == 77 && n.pets_today == 5 && n.day == 2500 && n.level == MM_HIGH);
    CHECK(!n.dirty && !n.has_pet);
    /* every kind of bad record gives the start state */
    for (int i = 0; i < MM_REC_BYTES; i++) {
        uint8_t bad[MM_REC_BYTES];
        memcpy(bad, rec, sizeof(bad));
        bad[i] ^= 0x10;
        CHECK(mm_load(&n, bad) == 0 && n.care == MM_CARE_START && n.day == 0);
    }
    uint8_t big[MM_REC_BYTES];
    mm_init(&m);
    m.care = 101;
    mm_store(&m, big);
    CHECK(mm_load(&n, big) == 0);
    CHECK(mm_load(&n, 0) == 0 && n.care == MM_CARE_START);
}

int main(void)
{
    test_days();
    test_pets();
    test_days_pass();
    test_levels();
    test_record();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("mood core: all passed\n");
    return 0;
}
