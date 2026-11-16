/* Host test for the version screen core (patch U05): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include <string.h>
#include "maipai_version_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void test_ten_taps_open(void)
{
    mv_state_t s;
    mv_init(&s);
    uint32_t t = 1000;
    for (int i = 0; i < 9; i++, t += 300) {
        CHECK(mv_tap(&s, t) == 0);
    }
    CHECK(mv_is_open(&s, t) == 0);
    CHECK(mv_tap(&s, t) == 1); /* the tenth */
    CHECK(mv_is_open(&s, t + 10) == 1);
}

static void test_a_slow_tap_starts_over(void)
{
    mv_state_t s;
    mv_init(&s);
    uint32_t t = 1000;
    for (int i = 0; i < 6; i++, t += 500) {
        mv_tap(&s, t);
    }
    t += MV_TAP_GAP_MS + 1; /* too slow */
    for (int i = 0; i < 9; i++, t += 500) {
        CHECK(mv_tap(&s, t) == 0); /* only nine since the restart */
    }
    CHECK(mv_is_open(&s, t) == 0);
    CHECK(mv_tap(&s, t) == 1);
}

static void test_exactly_two_seconds_still_counts(void)
{
    mv_state_t s;
    mv_init(&s);
    uint32_t t = 5000;
    for (int i = 0; i < 9; i++, t += MV_TAP_GAP_MS) {
        mv_tap(&s, t);
    }
    CHECK(mv_tap(&s, t) == 1);
}

static void test_details_close_by_themselves(void)
{
    mv_state_t s;
    mv_init(&s);
    uint32_t t = 100;
    for (int i = 0; i < 10; i++, t += 100) {
        mv_tap(&s, t);
    }
    CHECK(mv_is_open(&s, t + MV_OPEN_MS - 200) == 1);
    CHECK(mv_is_open(&s, t + MV_OPEN_MS + 5000) == 0);
    CHECK(mv_tap(&s, t + MV_OPEN_MS + 6000) == 0); /* counting starts again */
    CHECK(s.taps == 1);
}

static void test_a_tap_while_open_does_nothing(void)
{
    mv_state_t s;
    mv_init(&s);
    uint32_t t = 100;
    for (int i = 0; i < 10; i++, t += 100) {
        mv_tap(&s, t);
    }
    CHECK(mv_tap(&s, t) == 0 && mv_is_open(&s, t) == 1);
}

static void test_tag_words(void)
{
    char out[40];
    mv_tag("0.2.273", out, sizeof(out));
    CHECK(strcmp(out, "v0.2.273") == 0);
    mv_tag("v1.4.0", out, sizeof(out));
    CHECK(strcmp(out, "v1.4.0") == 0);
    mv_tag("1.6.2-maipai.1", out, sizeof(out));
    CHECK(strcmp(out, "v1.6.2-maipai.1") == 0);
    mv_tag("0.2.273-dirty", out, sizeof(out));
    CHECK(strcmp(out, "not a release build") == 0);
    mv_tag("", out, sizeof(out));
    CHECK(strcmp(out, "not a release build") == 0);
    mv_tag("12", out, sizeof(out));
    CHECK(strcmp(out, "not a release build") == 0);
}

static void test_signature_words_never_claim_too_much(void)
{
    mv_info_t i;
    memset(&i, 0, sizeof(i));
    CHECK(strstr(mv_signature_word(&i), "not known") != NULL);
    i.image_state = MV_IMG_USB;
    CHECK(strstr(mv_signature_word(&i), "wireless updates are off") != NULL);
    i.update_key = 1;
    CHECK(strstr(mv_signature_word(&i), "must be signed") != NULL);
    i.image_state = MV_IMG_VALID;
    CHECK(strstr(mv_signature_word(&i), "signed update and confirmed") != NULL);
    i.update_key = 0;
    CHECK(strstr(mv_signature_word(&i), "no update key") != NULL);
    i.image_state = MV_IMG_PENDING;
    CHECK(strstr(mv_signature_word(&i), "waiting") != NULL);
    /* with no key built in, a confirmed image is never called signed */
    i.image_state = MV_IMG_VALID;
    CHECK(strstr(mv_signature_word(&i), "installed by a signed update") == NULL);
}

static void test_bytes_and_lines(void)
{
    char out[16];
    mv_bytes_word(0, out, sizeof(out));
    CHECK(strcmp(out, "0 KB") == 0);
    mv_bytes_word(53707, out, sizeof(out));
    CHECK(strcmp(out, "52 KB") == 0);
    mv_bytes_word(8129208, out, sizeof(out));
    CHECK(strcmp(out, "7.8 MB") == 0);
    mv_bytes_word(1048576, out, sizeof(out));
    CHECK(strcmp(out, "1.0 MB") == 0);
    mv_info_t i;
    memset(&i, 0, sizeof(i));
    snprintf(i.version, sizeof(i.version), "%s", "0.2.273");
    snprintf(i.slot, sizeof(i.slot), "%s", "ota_1");
    i.slot_known = 1;
    i.image_state = MV_IMG_USB;
    i.internal_free = 53707;
    i.internal_min = 39828;
    i.psram_free = 8129208;
    i.psram_min = 8117260;
    char lines[MV_LINES][MV_LINE];
    CHECK(mv_detail_lines(&i, lines) == MV_LINES);
    CHECK(strcmp(lines[0], "Version: 0.2.273") == 0);
    CHECK(strcmp(lines[1], "Tag: v0.2.273") == 0);
    CHECK(strstr(lines[2], "flashed by cable") != NULL);
    CHECK(strcmp(lines[3], "Slot: ota_1") == 0);
    CHECK(strstr(lines[4], "52 KB") != NULL && strstr(lines[4], "39 KB") != NULL);
    CHECK(strstr(lines[5], "7.8 MB") != NULL);
    i.slot_known = 0;
    i.version[0] = '\0';
    mv_detail_lines(&i, lines);
    CHECK(strcmp(lines[0], "Version: unknown") == 0 && strcmp(lines[3], "Slot: unknown") == 0);
}

int main(void)
{
    test_ten_taps_open();
    test_a_slow_tap_starts_over();
    test_exactly_two_seconds_still_counts();
    test_details_close_by_themselves();
    test_a_tap_while_open_does_nothing();
    test_tag_words();
    test_signature_words_never_claim_too_much();
    test_bytes_and_lines();
    if (failures) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
