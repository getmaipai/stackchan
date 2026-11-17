/* Host test for the face detector's pure part (patch FD02): the real fd_convert_rgb888, fd_crop_origin, fd_pick, the percentile ring,
 * the rate clamp and the model names.
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> facedet_core_test.c -lm */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maipai_facedet_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void test_yuyv_known_colors(void)
{
    /* two pixels: Y U Y V. Mid gray (Y 126, U V 128) is 128 gray; Y 16 is black; Y 235 is white. */
    uint8_t f[4 * 2] = {16, 128, 16, 128, 235, 128, 235, 128};
    uint8_t out[4 * 3];
    CHECK(fd_convert_rgb888(f, sizeof(f), 4, 1, MW_FMT_YUYV, 0, 0, 4, 1, out, 0) == 0);
    CHECK(out[0] == 0 && out[1] == 0 && out[2] == 0 && out[3] == 0);
    CHECK(out[6] >= 254 && out[7] >= 254 && out[8] >= 254);
    /* pure red in BT.601 limited range: Y 82, U 90, V 240 */
    uint8_t r[4] = {82, 90, 82, 240};
    CHECK(fd_convert_rgb888(r, sizeof(r), 2, 1, MW_FMT_YUYV, 0, 0, 2, 1, out, 0) == 0);
    CHECK(out[0] > 245 && out[1] < 12 && out[2] < 12);
    CHECK(fd_convert_rgb888(r, sizeof(r), 2, 1, MW_FMT_YUYV, 0, 0, 2, 1, out, 1) == 0); /* swapped: blue first */
    CHECK(out[2] > 245 && out[0] < 12);
}

static void test_uyvy_matches_yuyv(void)
{
    uint8_t a[8], b[8];
    for (int i = 0; i < 8; i++) a[i] = (uint8_t)(40 + i * 23);
    /* the same two pixels in UYVY order: U Y0 V Y1 */
    b[0] = a[1]; b[1] = a[0]; b[2] = a[3]; b[3] = a[2];
    b[4] = a[5]; b[5] = a[4]; b[6] = a[7]; b[7] = a[6];
    uint8_t oa[4 * 3], ob[4 * 3];
    CHECK(fd_convert_rgb888(a, 8, 4, 1, MW_FMT_YUYV, 0, 0, 4, 1, oa, 0) == 0);
    CHECK(fd_convert_rgb888(b, 8, 4, 1, MW_FMT_UYVY, 0, 0, 4, 1, ob, 0) == 0);
    CHECK(memcmp(oa, ob, sizeof(oa)) == 0);
}

static void test_rgb565_and_gray(void)
{
    /* little endian: 0xF800 red, 0x07E0 green, 0x001F blue, 0xFFFF white */
    uint8_t f[8] = {0x00, 0xF8, 0xE0, 0x07, 0x1F, 0x00, 0xFF, 0xFF};
    uint8_t o[4 * 3];
    CHECK(fd_convert_rgb888(f, sizeof(f), 4, 1, MW_FMT_RGB565, 0, 0, 4, 1, o, 0) == 0);
    CHECK(o[0] == 255 && o[1] == 0 && o[2] == 0);
    CHECK(o[3] == 0 && o[4] == 255 && o[5] == 0);
    CHECK(o[6] == 0 && o[7] == 0 && o[8] == 255);
    CHECK(o[9] == 255 && o[10] == 255 && o[11] == 255);
    uint8_t g[3] = {10, 128, 250};
    uint8_t og[9];
    CHECK(fd_convert_rgb888(g, sizeof(g), 3, 1, MW_FMT_GREY, 0, 0, 3, 1, og, 0) == 0);
    CHECK(og[3] == 128 && og[4] == 128 && og[5] == 128 && og[6] == 250);
}

static void test_window_and_errors(void)
{
    uint8_t f[8 * 4 * 2];
    for (size_t i = 0; i < sizeof(f); i++) f[i] = (uint8_t)i;
    uint8_t o[2 * 2 * 3];
    CHECK(fd_convert_rgb888(f, sizeof(f), 8, 4, MW_FMT_RGB565, 2, 1, 2, 2, o, 0) == 0);
    /* the window's first pixel is frame pixel (2, 1): bytes at (1 * 8 + 2) * 2 = 20 */
    int v = f[20] | (f[21] << 8);
    CHECK(o[0] == (uint8_t)((((v >> 11) & 31) << 3) | (((v >> 11) & 31) >> 2)));
    CHECK(fd_convert_rgb888(f, sizeof(f), 8, 4, MW_FMT_RGB565, 7, 0, 2, 2, o, 0) == -1);   /* outside */
    CHECK(fd_convert_rgb888(f, sizeof(f), 8, 4, MW_FMT_RGB565, 0, 3, 2, 2, o, 0) == -1);
    CHECK(fd_convert_rgb888(f, sizeof(f), 8, 4, MW_FMT_YUYV, 1, 0, 2, 2, o, 0) == -1);    /* an odd column of YUV */
    CHECK(fd_convert_rgb888(f, 10, 8, 4, MW_FMT_RGB565, 0, 0, 2, 2, o, 0) == -1);         /* the buffer is short */
    CHECK(fd_convert_rgb888(f, sizeof(f), 8, 4, MW_FMT_NONE, 0, 0, 2, 2, o, 0) == -1);
    CHECK(fd_convert_rgb888(NULL, sizeof(f), 8, 4, MW_FMT_RGB565, 0, 0, 2, 2, o, 0) == -1);
}

static void test_crop_origin(void)
{
    int x, y;
    fd_crop_origin(320, 240, 160, 120, 160, 120, &x, &y);
    CHECK(x == 80 && y == 60);
    fd_crop_origin(320, 240, 160, 120, 5, 5, &x, &y);
    CHECK(x == 0 && y == 0);
    fd_crop_origin(320, 240, 160, 120, 315, 235, &x, &y);
    CHECK(x == 160 && y == 120);
    fd_crop_origin(320, 240, 160, 120, 201.0f, 100, &x, &y);
    CHECK(x % 2 == 0 && x + 160 <= 320);
    fd_crop_origin(100, 80, 160, 120, 50, 40, &x, &y); /* a frame smaller than the window: clamp to the corner */
    CHECK(x == 0 && y == 0);
}

static void test_pick(void)
{
    fd_box_t b[3] = {{10, 10, 40, 40, 0.9f}, {120, 60, 200, 140, 0.7f}, {260, 50, 300, 90, 0.95f}};
    fd_face_t f;
    memset(&f, 0, sizeof(f));
    CHECK(fd_pick(b, 3, 0.5f, 320, 240, &f) == 1);
    CHECK(f.valid && f.cx == 160.0f && f.cy == 100.0f && f.w == 80.0f && f.score == 0.7f); /* the big one near the middle */
    CHECK(fd_pick(b, 3, 0.8f, 320, 240, &f) == 1 && f.score == 0.95f);                  /* the others are under the floor */
    CHECK(fd_pick(b, 3, 0.99f, 320, 240, &f) == 0);
    fd_box_t bad[1] = {{50, 50, 50, 90, 0.9f}};
    CHECK(fd_pick(bad, 1, 0.5f, 320, 240, &f) == 0);
    CHECK(fd_pick(b, 0, 0.5f, 320, 240, &f) == 0);
}

static void test_percentile_and_ring(void)
{
    fd_ring_t r;
    fd_ring_clear(&r);
    CHECK(fd_percentile(&r, 50) == 0);
    for (uint32_t i = 1; i <= 100; i++) fd_ring_add(&r, i);
    CHECK(fd_percentile(&r, 50) == 50 && fd_percentile(&r, 99) == 99 && fd_percentile(&r, 100) == 100 && fd_percentile(&r, 1) == 1);
    CHECK(fd_ring_max(&r) == 100);
    fd_ring_clear(&r);
    for (uint32_t i = 0; i < 10; i++) fd_ring_add(&r, i == 9 ? 1000 : 100 + i); /* one slow frame */
    CHECK(fd_percentile(&r, 50) == 104 && fd_percentile(&r, 99) == 1000);
    fd_ring_clear(&r);
    for (uint32_t i = 1; i <= FD_SAMPLES + 44; i++) fd_ring_add(&r, i); /* wraps: the newest 256 are held */
    CHECK(r.n == FD_SAMPLES && r.seen == FD_SAMPLES + 44);
    CHECK(fd_percentile(&r, 100) == FD_SAMPLES + 44 && fd_percentile(&r, 1) == 47);
}

static void test_rate_and_names(void)
{
    CHECK(fd_period_ms(3) == 333 && fd_period_ms(2) == 500 && fd_period_ms(5) == 200);
    CHECK(fd_period_ms(0) == 333 && fd_period_ms(-4) == 333);
    CHECK(fd_period_ms(1) == 500 && fd_period_ms(9) == 200);
    CHECK(fd_model_parse("msrmnp") == FD_MODEL_MSRMNP && fd_model_parse("msr") == FD_MODEL_MSRMNP);
    CHECK(fd_model_parse("pico224") == FD_MODEL_PICO224 && fd_model_parse("pico") == FD_MODEL_PICO224);
    CHECK(fd_model_parse("yunet") == -1 && fd_model_parse("") == -1 && fd_model_parse(NULL) == -1);
    CHECK(strcmp(FD_MODEL_NAMES[FD_MODEL_PICO224], "pico224") == 0);
}

int main(void)
{
    test_yuyv_known_colors();
    test_uyvy_matches_yuyv();
    test_rgb565_and_gray();
    test_window_and_errors();
    test_crop_origin();
    test_pick();
    test_percentile_and_ring();
    test_rate_and_names();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
