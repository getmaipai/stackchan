/* Host test for the face pictures (patch V23): the rounded box, the discs, the lid and cheek cuts and the mouth stroke.
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> sprite_core_test.c -lm */
#include <stdio.h>
#include <stdlib.h>

#include "maipai_sprite_core.h"

static int fails;
#define CHECK(c)                                                    \
    do {                                                            \
        if (!(c)) {                                                 \
            fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c);   \
            fails++;                                                \
        }                                                           \
    } while (0)

static double sum_a(const uint8_t* a, int n)
{
    double s = 0;
    for (int i = 0; i < n; i++) s += a[i];
    return s / 255.0;
}

static ml_shape_t* mk(ml_shape_t* s, int kind, int col, float a, float b, float c, float d, float e)
{
    memset(s, 0, sizeof(*s));
    s->kind = (uint8_t)kind;
    s->col  = (uint8_t)col;
    s->opa  = 255;
    s->v[0] = a; s->v[1] = b; s->v[2] = c; s->v[3] = d; s->v[4] = e;
    return s;
}

static void test_rrect(void)
{
    enum { W = 96, H = 104 };
    static uint8_t a[W * H];
    msp_rrect_alpha(a, W, H, 0);
    CHECK(sum_a(a, W * H) == (double)(W * H)); /* a plain box is solid */
    msp_rrect_alpha(a, W, H, 48);
    const double area = (W - 96) * 0.0 + 3.14159265 * 48 * 48 + 96 * (H - 96); /* a disc and the straight part between the caps */
    CHECK(fabs(sum_a(a, W * H) - area) / area < 0.005);
    CHECK(a[0] == 0 && a[W - 1] == 0 && a[(H - 1) * W] == 0 && a[H * W - 1] == 0); /* the four corners are empty */
    CHECK(a[(H / 2) * W + W / 2] == 255 && a[(H / 2) * W] == 255);                    /* the middle and the straight sides are solid */
    for (int j = 0; j < H; j++) {
        for (int i = 0; i < W / 2; i++) {
            CHECK(a[j * W + i] == a[j * W + W - 1 - i]); /* left-right symmetry, exactly */
        }
    }
    for (int j = 0; j < H / 2; j++) {
        for (int i = 0; i < W; i++) {
            CHECK(a[j * W + i] == a[(H - 1 - j) * W + i]); /* top-bottom symmetry, exactly */
        }
    }
}

static void test_disc(void)
{
    enum { W = 90, H = 90 };
    static uint16_t p[W * H];
    for (int i = 0; i < W * H; i++) p[i] = 0xFFFF;
    msp_disc_paint(p, W, H, 45.0f, 45.0f, 37.0f, 0x0000);
    double dark = 0;
    for (int i = 0; i < W * H; i++) dark += (0xFFFF - p[i]) / 65535.0 > 0.5 ? 1 : 0;
    const double area = 3.14159265 * 37 * 37;
    CHECK(fabs(dark - area) / area < 0.01);
    CHECK(p[45 * W + 45] == 0x0000 && p[0] == 0xFFFF);
    /* a disc that runs off the picture never writes outside it (the sanitizer would stop us) */
    msp_disc_paint(p, W, H, 2.0f, 88.0f, 30.0f, 0x1234);
    msp_disc_paint(p, W, H, 200.0f, 200.0f, 5.0f, 0x1234);
}

static void test_erase(void)
{
    enum { W = 40, H = 40 };
    static uint8_t a[W * H];
    memset(a, 255, sizeof(a));
    const float q[8] = {0, 0, 40, 0, 40, 10, 0, 10}; /* the top ten rows */
    msp_erase_quad(a, W, H, q);
    CHECK(a[0] == 0 && a[9 * W + 39] == 0 && a[10 * W] == 255 && a[39 * W + 39] == 255);
    memset(a, 255, sizeof(a));
    const float s[8] = {0, 0, 40, 0, 40, 20, 0, 10}; /* a sloped lid edge: half a pixel row of cover on the line */
    msp_erase_quad(a, W, H, s);
    CHECK(a[0] == 0 && a[18 * W + 39] == 0);   /* above the edge: gone */
    CHECK(a[25 * W + 39] == 255);              /* below it: kept */
    CHECK(a[19 * W + 39] > 0 && a[19 * W + 39] < 255); /* on the edge: a soft step */
}

static void test_plain_eye_and_render(void)
{
    ml_shape_t sh[8];
    int n = 0;
    mk(&sh[n++], ML_SH_RRECT, ML_COL_FG, 0, 0, 96, 104, 48);
    mk(&sh[n++], ML_SH_CIRCLE, ML_COL_BG, 0, 2, 36, 0, 0);
    mk(&sh[n++], ML_SH_CIRCLE, ML_COL_HL, -12, -10, 9, 0, 0);
    msp_box_t b;
    CHECK(msp_eye_plain(sh, n, &b));
    CHECK(b.w == 96 && b.h == 104 && b.x1 == -48 && b.y1 == -52);
    static uint16_t rgb[96 * 104];
    static uint8_t a[96 * 104];
    msp_eye_render(sh, n, &b, 0xFFFF, 0x0000, rgb, a);
    CHECK(rgb[(52 + 2) * 96 + 48] == 0x0000);           /* the pupil's middle is the screen colour */
    CHECK(rgb[(52 - 10) * 96 + 48 - 12] == 0xFFFF);     /* the highlight inside it is the face colour */
    CHECK(rgb[(52) * 96 + 3] == 0xFFFF);                /* the white of the eye */
    CHECK(a[0] == 0 && a[52 * 96 + 48] == 255);         /* off the rounded corner: nothing; the middle: solid */
    /* a pupil that leaves the box is cut by it: the alpha is the box's, so nothing shows outside */
    sh[1].v[0] = 60;
    msp_eye_render(sh, n, &b, 0xFFFF, 0x0000, rgb, a);
    CHECK(a[52 * 96 + 95] == 255);
    /* a fading eye, a heart and a closed arc are shape draws */
    sh[0].opa = 200;
    CHECK(!msp_eye_plain(sh, n, &b));
    sh[0].opa = 255;
    ml_shape_t h;
    mk(&h, ML_SH_HEART, ML_COL_FG, 0, 0, 20, 0, 0);
    ml_shape_t withheart[2] = {h, sh[0]};
    CHECK(!msp_eye_plain(withheart, 2, &b));
    mk(&sh[n++], ML_SH_LINE, ML_COL_FG, 0, 0, 10, 0, 5);
    CHECK(!msp_eye_plain(sh, n, &b));
}

static void test_stroke(void)
{
    ml_shape_t sh[16];
    int n = 0;
    for (int i = 0; i < 12; i++) mk(&sh[n++], ML_SH_LINE, ML_COL_FG, (float)(i * 3 - 18), 0, (float)(i * 3 - 15), 0, 8);
    msp_box_t b;
    int t;
    uint8_t opa;
    CHECK(msp_stroke_plain(sh, n, &b, &t, &opa));
    CHECK(t == 8 && opa == 255);
    static msp_brush_t brush;
    brush.t = 0;
    static uint8_t m[160 * 160];
    CHECK((size_t)b.w * (size_t)b.h <= sizeof(m));
    msp_stroke_render(sh, n, &b, t, &brush, m);
    /* the stroke runs 36 pixels (to x = 18) and is 8 thick with round ends: a 36 by 8 bar plus the two caps */
    const double want = 36.0 * 8.0 + 3.14159265 * 16.0 - 0.0;
    CHECK(fabs(sum_a(m, b.w * b.h) - want) / want < 0.04);
    /* a mask drawn again from the same list is the same, exactly (the brush is reused) */
    static uint8_t m2[160 * 160];
    msp_stroke_render(sh, n, &b, t, &brush, m2);
    CHECK(memcmp(m, m2, (size_t)b.w * (size_t)b.h) == 0);
    /* a single disc: the open mouth of the round O */
    ml_shape_t dot;
    mk(&dot, ML_SH_CIRCLE, ML_COL_FG, 0, 0, 12, 0, 0);
    CHECK(msp_stroke_plain(&dot, 1, &b, &t, &opa) && t == 24);
    msp_stroke_render(&dot, 1, &b, t, &brush, m);
    const double disc = 3.14159265 * 144.0;
    CHECK(fabs(sum_a(m, b.w * b.h) - disc) / disc < 0.03);
    /* a thicker stroke than the brush, or a mixed list, is left to the shape draws */
    mk(&dot, ML_SH_CIRCLE, ML_COL_FG, 0, 0, 30, 0, 0);
    CHECK(!msp_stroke_plain(&dot, 1, &b, &t, &opa));
    sh[1].v[4] = 6;
    CHECK(!msp_stroke_plain(sh, n, &b, &t, &opa));
}

int main(void)
{
    test_rrect();
    test_disc();
    test_erase();
    test_plain_eye_and_render();
    test_stroke();
    if (fails) {
        fprintf(stderr, "sprite core: %d failed\n", fails);
        return 1;
    }
    printf("sprite core: all passed\n");
    return 0;
}
