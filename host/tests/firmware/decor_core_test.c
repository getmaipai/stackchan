/* Host test for the face decorator core (patch U01): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include <string.h>
#include "maipai_decor_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void test_names(void)
{
    CHECK(md_from_name("none") == MD_NONE);
    CHECK(md_from_name("sweat") == -1); /* dropped (patch X02): the sweat drop and the blush are unknown names now */
    CHECK(md_from_name("shy") == -1);
    CHECK(md_dropped(MD_SWEAT) && md_dropped(MD_SHY) && !md_dropped(MD_HEART));
    CHECK(md_from_name("zzz") == MD_ZZZ);
    CHECK(md_from_name("sparkles") == MD_SPARKLES);
    CHECK(md_from_name("Sweat") == -1); /* exact names only */
    CHECK(md_from_name("") == -1);
    CHECK(md_from_name(NULL) == -1);
    for (int i = 0; i < MD_COUNT; i++) {
        CHECK(md_from_name(MD_NAMES[i]) == (md_dropped(i) ? -1 : i));
    }
    CHECK(md_seconds_ok(1) && md_seconds_ok(60) && !md_seconds_ok(0) && !md_seconds_ok(61) && !md_seconds_ok(-3));
}

static void test_trig(void)
{
    CHECK(md_sin256(0) == 0);
    CHECK(md_sin256(90) == 256);
    CHECK(md_sin256(180) == 0);
    CHECK(md_sin256(270) == -256);
    CHECK(md_sin256(-90) == -256);
    CHECK(md_sin256(450) == 256);
    CHECK(md_cos256(0) == 256);
    CHECK(md_cos256(180) == -256);
    for (int d = 0; d < 720; d += 7) {
        CHECK(md_sin256(d) >= -256 && md_sin256(d) <= 256);
    }
    CHECK(md_tri(0, 1000) == 0);
    CHECK(md_tri(500, 1000) == 255);
    CHECK(md_tri(1000, 1000) == 0);
}

static void test_every_kind_stays_on_the_screen_and_in_range(void)
{
    for (int kind = 1; kind < MD_COUNT; kind++) {
        const int n = md_part_count(kind);
        CHECK(n > 0 && n <= MD_MAX_PARTS);
        for (uint32_t t = 0; t < 61000; t += 133) {
            md_part_t parts[MD_MAX_PARTS];
            memset(parts, 0xAB, sizeof(parts));
            const int got = md_parts(kind, t, parts, MD_MAX_PARTS);
            CHECK(got == n);
            for (int i = 0; i < got; i++) {
                /* inside the 320 by 240 screen (centre origin), with the part's own size */
                CHECK(parts[i].x - parts[i].w / 2 >= -160 && parts[i].x + parts[i].w / 2 <= 160);
                CHECK(parts[i].y - parts[i].h / 2 >= -120 && parts[i].y + parts[i].h / 2 <= 120);
                CHECK(parts[i].w > 0 && parts[i].h > 0);
            }
        }
    }
}

static void test_none_and_unknown_draw_nothing(void)
{
    md_part_t parts[MD_MAX_PARTS];
    CHECK(md_parts(MD_NONE, 0, parts, MD_MAX_PARTS) == 0);
    CHECK(md_parts(99, 0, parts, MD_MAX_PARTS) == 0);
    CHECK(md_parts(-1, 0, parts, MD_MAX_PARTS) == 0);
    CHECK(md_parts(MD_ZZZ, 0, parts, 3) == 0); /* too small a buffer writes nothing */
}

static void test_motion(void)
{
    md_part_t a[MD_MAX_PARTS], b[MD_MAX_PARTS];
    /* a falling drop moves down and fades at the end of its fall */
    md_parts(MD_TEARS, 0, a, MD_MAX_PARTS);
    md_parts(MD_TEARS, 500, b, MD_MAX_PARTS);
    CHECK(b[0].y > a[0].y);
    md_parts(MD_TEARS, 1400, b, MD_MAX_PARTS);
    CHECK(b[0].opa < 255);
    /* the loop repeats */
    md_parts(MD_SWEAT, 100, a, MD_MAX_PARTS);
    md_parts(MD_SWEAT, 1700, b, MD_MAX_PARTS);
    CHECK(a[0].y == b[0].y);
    /* the dizzy dots orbit: two moments differ, a full turn (1400 ms) matches */
    md_parts(MD_DIZZY, 0, a, MD_MAX_PARTS);
    md_parts(MD_DIZZY, 350, b, MD_MAX_PARTS);
    CHECK(a[0].x != b[0].x || a[0].y != b[0].y);
    md_parts(MD_DIZZY, 1400, b, MD_MAX_PARTS);
    CHECK(a[0].x == b[0].x && a[0].y == b[0].y);
    /* the two eyes spin opposite ways */
    md_parts(MD_DIZZY, 350, b, MD_MAX_PARTS);
    CHECK((b[0].y + 16) != (b[3].y + 16) || (b[0].x + 70) != -(b[3].x - 70));
    /* sparkles twinkle: the opacity changes with time */
    md_parts(MD_SPARKLES, 0, a, MD_MAX_PARTS);
    md_parts(MD_SPARKLES, 750, b, MD_MAX_PARTS);
    CHECK(a[0].opa != b[0].opa);
    /* the zzz letters rise */
    md_parts(MD_ZZZ, 0, a, MD_MAX_PARTS);
    md_parts(MD_ZZZ, 600, b, MD_MAX_PARTS);
    CHECK(b[0].y < a[0].y);
    /* blush is always visible */
    for (uint32_t t = 0; t < 4000; t += 100) {
        md_parts(MD_SHY, t, a, MD_MAX_PARTS);
        CHECK(a[0].opa >= 110 && a[0].opa <= 180);
    }
    /* stars on the far side are dimmer than on the near side */
    int lo = 255, hi = 0;
    for (uint32_t t = 0; t < 3600; t += 100) {
        md_parts(MD_STARS, t, a, MD_MAX_PARTS);
        if (a[0].opa < lo) lo = a[0].opa;
        if (a[0].opa > hi) hi = a[0].opa;
    }
    CHECK(lo < 150 && hi > 230);
}

/* Patch MD02: the music notes. Nine parts (a head, a stem and a flag for each of three notes); the count hides the others; they float up
 * the sides of the face, never over the eyes or the banner row. */
static void test_notes(void)
{
    CHECK(md_from_name("notes") == MD_NOTES);
    CHECK(md_part_count(MD_NOTES) == 9);
    for (int arg = 1; arg <= 3; arg++) {
        for (uint32_t t = 0; t < 5000; t += 33) {
            md_part_t p[MD_MAX_PARTS];
            CHECK(md_parts_n(MD_NOTES, t, p, MD_MAX_PARTS, arg) == 9);
            int shown = 0;
            for (int k = 0; k < 3; k++) {
                if (p[k * 3].opa > 0) shown++;
                for (int j = 0; j < 3; j++) {
                    const md_part_t* q = &p[k * 3 + j];
                    if (k >= arg) CHECK(q->opa == 0);
                    if (q->opa == 0) continue;
                    CHECK(q->x - q->w / 2 >= -160 && q->x + q->w / 2 <= 160);
                    CHECK(120 + q->y - q->h / 2 >= 28 && 120 + q->y + q->h / 2 <= 184); /* inside the face zone */
                    CHECK(q->x <= -100 || q->x >= 100 || q->y < -60);                  /* off the eyes (they sit at x +-70 +-42) */
                }
            }
            CHECK(shown <= arg);
        }
    }
    md_part_t a[MD_MAX_PARTS], b[MD_MAX_PARTS];
    md_parts_n(MD_NOTES, 0, a, MD_MAX_PARTS, 3);
    md_parts_n(MD_NOTES, 600, b, MD_MAX_PARTS, 3);
    CHECK(a[0].y != b[0].y); /* they float */
    CHECK(md_parts(MD_NOTES, 0, a, MD_MAX_PARTS) == 9);
}

int main(void)
{
    test_notes();
    test_names();
    test_trig();
    test_every_kind_stays_on_the_screen_and_in_range();
    test_none_and_unknown_draw_nothing();
    test_motion();
    if (failures) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
