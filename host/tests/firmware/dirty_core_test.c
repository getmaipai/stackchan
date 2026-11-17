/* Host test for the dirty rectangles and the gaze spring (patch V20).
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> dirty_core_test.c -lm */
#include <stdio.h>
#include <stdlib.h>

#include "maipai_dirty_core.h"

static int fails;
#define CHECK(c)                                                    \
    do {                                                            \
        if (!(c)) {                                                 \
            fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c);   \
            fails++;                                                \
        }                                                           \
    } while (0)

/* A scan of one shape list into a coverage map by the same rule the page uses: inside a rounded box or a circle. */
static void test_unchanged(void)
{
    ml_shape_t a[2];
    memset(a, 0, sizeof(a));
    a[0].kind = ML_SH_RRECT; a[0].v[2] = 96; a[0].v[3] = 104; a[0].v[4] = 48; a[0].opa = 255;
    a[1].kind = ML_SH_CIRCLE; a[1].col = ML_COL_BG; a[1].v[0] = -1; a[1].v[1] = 2; a[1].v[2] = 36; a[1].opa = 255;
    md_set_t s;
    md_diff(&s, a, 2, 0, 0, a, 2, 0, 0, 2);
    CHECK(s.n == 0); /* nothing changed: nothing is sent */
}

static void test_small_move_is_small(void)
{
    ml_shape_t a[2], b[2];
    memset(a, 0, sizeof(a));
    a[0].kind = ML_SH_RRECT; a[0].v[2] = 96; a[0].v[3] = 104; a[0].v[4] = 48; a[0].opa = 255;
    a[1].kind = ML_SH_CIRCLE; a[1].col = ML_COL_BG; a[1].v[0] = -1; a[1].v[1] = 2; a[1].v[2] = 36; a[1].opa = 255;
    memcpy(b, a, sizeof(a));
    md_set_t s;
    md_diff(&s, a, 2, 0, 0, b, 2, 1, 0, 2); /* the eye drifts one pixel to the right */
    CHECK(s.n > 0);
    CHECK(s.n <= 2); /* every area costs LVGL a pass: few */
    {   /* never more than the old way: one box round every old and new shape */
        md_rect_t u = {1 << 20, 1 << 20, -(1 << 20), -(1 << 20)}, q;
        for (int i = 0; i < 2; i++) {
            md_shape_bounds(&a[i], 0, 0, &q); u.x1 = md_min(u.x1, q.x1); u.y1 = md_min(u.y1, q.y1); u.x2 = md_max(u.x2, q.x2); u.y2 = md_max(u.y2, q.y2);
            md_shape_bounds(&b[i], 1, 0, &q); u.x1 = md_min(u.x1, q.x1); u.y1 = md_min(u.y1, q.y1); u.x2 = md_max(u.x2, q.x2); u.y2 = md_max(u.y2, q.y2);
        }
        for (int k = 0; k < s.n; k++) CHECK(s.r[k].x1 >= u.x1 && s.r[k].y1 >= u.y1 && s.r[k].x2 <= u.x2 && s.r[k].y2 <= u.y2);
    }
    /* the highlight alone moving: only its own corner */
    ml_shape_t c[3], d[3];
    memset(c, 0, sizeof(c));
    c[0].kind = ML_SH_RRECT; c[0].v[2] = 96; c[0].v[3] = 104; c[0].v[4] = 48; c[0].opa = 255;
    c[1].kind = ML_SH_CIRCLE; c[1].col = ML_COL_HL; c[1].v[0] = 12; c[1].v[1] = 14; c[1].v[2] = 4; c[1].opa = 255;
    memcpy(d, c, sizeof(c));
    d[1].v[0] = 13;
    md_diff(&s, c, 2, 0, 0, d, 2, 0, 0, 2);
    CHECK(s.n <= 2 && md_area(&s) < 400);
}

static void test_covers_the_old_and_new_edges(void)
{
    ml_shape_t a[1], b[1];
    memset(a, 0, sizeof(a));
    a[0].kind = ML_SH_CIRCLE; a[0].v[2] = 20; a[0].opa = 255;
    memcpy(b, a, sizeof(a));
    b[0].v[2] = 24; /* grows */
    md_set_t s;
    md_diff(&s, a, 1, 0, 0, b, 1, 0, 0, 2);
    /* every point on the new circle's rim (and the old one's) lies inside a rectangle */
    for (int deg = 0; deg < 360; deg += 5) {
        const float rad = (float)deg * 3.14159265f / 180.0f;
        for (int r = 20; r <= 24; r += 4) {
            const int x = (int)lroundf(cosf(rad) * (float)r), y = (int)lroundf(sinf(rad) * (float)r);
            int hit = 0;
            for (int k = 0; k < s.n; k++) hit |= (x >= s.r[k].x1 && x <= s.r[k].x2 && y >= s.r[k].y1 && y <= s.r[k].y2);
            CHECK(hit);
        }
    }
}

static void test_appear_and_vanish(void)
{
    ml_shape_t a[1], b[2];
    memset(a, 0, sizeof(a));
    memset(b, 0, sizeof(b));
    a[0].kind = ML_SH_RRECT; a[0].v[2] = 40; a[0].v[3] = 40; a[0].v[4] = 20; a[0].opa = 255;
    b[0] = a[0];
    b[1].kind = ML_SH_QUAD; b[1].col = ML_COL_BG; b[1].opa = 255;
    b[1].v[0] = -20; b[1].v[1] = -30; b[1].v[2] = 20; b[1].v[3] = -30; b[1].v[4] = 20; b[1].v[5] = -10; b[1].v[6] = -20; b[1].v[7] = -10;
    md_set_t s;
    md_diff(&s, a, 1, 0, 0, b, 2, 0, 0, 2);
    CHECK(s.n == 1);
    CHECK(s.r[0].x1 <= -20 && s.r[0].x2 >= 20 && s.r[0].y1 <= -30 && s.r[0].y2 >= -10);
    md_diff(&s, b, 2, 0, 0, a, 1, 0, 0, 2);
    CHECK(s.n == 1);
}

static void test_many_pieces_never_drop(void)
{
    ml_shape_t a[ML_MAX_SHAPES], b[ML_MAX_SHAPES];
    memset(a, 0, sizeof(a));
    for (int i = 0; i < ML_MAX_SHAPES; i++) {
        a[i].kind = ML_SH_LINE; a[i].opa = 255; a[i].v[0] = (float)(i * 4); a[i].v[2] = (float)(i * 4); a[i].v[3] = 10; a[i].v[4] = 3;
    }
    memcpy(b, a, sizeof(a));
    for (int i = 0; i < ML_MAX_SHAPES; i++) b[i].v[3] = 12;
    md_set_t s;
    md_diff(&s, a, ML_MAX_SHAPES, 0, 0, b, ML_MAX_SHAPES, 0, 0, 2);
    CHECK(s.n <= 2);
    for (int i = 0; i < ML_MAX_SHAPES; i++) {
        int hit = 0;
        for (int k = 0; k < s.n; k++) hit |= ((i * 4) >= s.r[k].x1 && (i * 4) <= s.r[k].x2 && 11 >= s.r[k].y1 && 11 <= s.r[k].y2);
        CHECK(hit);
    }
}

static void test_gaze_spring(void)
{
    mx_spring1_t g = {0.0f, 0.0f};
    float peak = 0.0f;
    int t90 = -1, settled = -1;
    for (int ms = 1; ms <= 400; ms++) {
        mx_spring1_step(&g, 10.0f, 1.0f, MX_GAZE_K, MX_GAZE_ZETA);
        if (g.x > peak) peak = g.x;
        if (t90 < 0 && g.x >= 9.0f) t90 = ms;
        if (settled < 0 && g.x != 10.0f ? 0 : settled < 0) settled = ms;
    }
    CHECK(t90 > 0 && t90 <= 60);      /* a jump is 90 percent done within 60 ms */
    CHECK(peak > 10.0f && peak < 11.2f); /* a little overshoot, no more than 12 percent */
    CHECK(g.x == 10.0f);              /* and it ends on the target */
    /* a slow frame stays stable */
    mx_spring1_t h = {0.0f, 0.0f};
    for (int i = 0; i < 40; i++) mx_spring1_step(&h, 10.0f, 50.0f, MX_GAZE_K, MX_GAZE_ZETA);
    CHECK(h.x > 9.0f && h.x < 11.5f);
    (void)settled;
}

int main(void)
{
    test_unchanged();
    test_small_move_is_small();
    test_covers_the_old_and_new_edges();
    test_appear_and_vanish();
    test_many_pieces_never_drop();
    test_gaze_spring();
    if (fails) {
        fprintf(stderr, "dirty core: %d failed\n", fails);
        return 1;
    }
    printf("dirty core: all passed\n");
    return 0;
}
