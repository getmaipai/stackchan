/* Host test for the camera probe core (patch SF45). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include <string.h>
#include "maipai_campro_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

int main(void)
{
    /* the gate: each privacy rule refuses the run, in a fixed order */
    CHECK(cpr_gate(0, 0, 0, 0) == 0);
    CHECK(cpr_gate(1, 1, 1, 1) == 1 && cpr_gate(0, 1, 1, 1) == 2 && cpr_gate(0, 0, 1, 1) == 3 && cpr_gate(0, 0, 0, 1) == 4);
    for (int i = 1; i < 5; i++) CHECK(strstr(CPR_REASON_TEXT[i], "before probing") != NULL);

    /* a 320 by 240 frame in each format: uniform luma 100 reads 100 everywhere */
    static uint8_t frame[320 * 240 * 2];
    uint8_t grid[CPR_GRID];
    for (size_t i = 0; i < sizeof(frame); i += 2) { frame[i] = 100; frame[i + 1] = 128; }  /* YUYV: Y then chroma */
    CHECK(cpr_sample_grid(frame, sizeof(frame), 320, 240, CPR_FMT_YUYV, grid) == 0 && grid[0] == 100 && grid[CPR_GRID - 1] == 100);
    for (size_t i = 0; i < sizeof(frame); i += 2) { frame[i] = 128; frame[i + 1] = 90; }   /* UYVY: chroma then Y */
    CHECK(cpr_sample_grid(frame, sizeof(frame), 320, 240, CPR_FMT_UYVY, grid) == 0 && grid[100] == 90);
    memset(frame, 77, sizeof(frame));
    CHECK(cpr_sample_grid(frame, 320 * 240, 320, 240, CPR_FMT_GREY, grid) == 0 && grid[5] == 77);
    memset(frame, 0xff, sizeof(frame));                                                      /* RGB565 white */
    CHECK(cpr_sample_grid(frame, sizeof(frame), 320, 240, CPR_FMT_RGB565, grid) == 0 && grid[0] >= 250);
    /* refused: a short buffer, a small frame, an unknown format, no data */
    CHECK(cpr_sample_grid(frame, 100, 320, 240, CPR_FMT_YUYV, grid) == -1);
    CHECK(cpr_sample_grid(frame, sizeof(frame), 16, 16, CPR_FMT_YUYV, grid) == -1);
    CHECK(cpr_sample_grid(frame, sizeof(frame), 320, 240, 0x12345678u, grid) == -1);
    CHECK(cpr_sample_grid(NULL, 0, 320, 240, CPR_FMT_GREY, grid) == -1);

    /* statistics: a dark scene reads near 0, a still scene has noise 0, a changing one reads the change */
    cpr_t st;
    cpr_init(&st);
    uint8_t a[CPR_GRID], b[CPR_GRID];
    memset(a, 3, sizeof(a));
    memset(b, 3, sizeof(b));
    cpr_brightness(&st, a);
    cpr_noise(&st, a, b);
    CHECK(st.bright_n == 1 && st.noise_n == 1 && st.noise_sum == 0);
    memset(b, 13, sizeof(b));
    cpr_noise(&st, a, b);
    CHECK(st.noise_n == 2 && st.noise_sum == 10u * 16u);
    cpr_frame(&st, 40);
    cpr_frame(&st, 60);
    cpr_encoded(&st, 100, 9000);
    cpr_encoded(&st, 140, 11000);
    CHECK(st.frames == 2 && st.cap_max_ms == 60 && st.encoded == 2 && st.bytes_max == 11000 && st.enc_max_ms == 140);
    char out[700];
    cpr_report(&st, 1000, 320, 240, CPR_FMT_YUYV, 20, 1, 50000, 3000000, out, sizeof(out));
    CHECK(strstr(out, "\"frames_per_s\":2.0") != NULL && strstr(out, "\"format\":\"yuyv\"") != NULL && strstr(out, "\"mean\":10000") != NULL);
    CHECK(strstr(out, "\"brightness\":3.0") != NULL && strstr(out, "\"noise\":5.00") != NULL);
    /* an empty run does not divide by zero */
    cpr_init(&st);
    cpr_report(&st, 0, 0, 0, 0, 20, 1, 0, 0, out, sizeof(out));
    CHECK(strstr(out, "\"frames\":0") != NULL);
    if (failures) return 1;
    printf("campro core ok\n");
    return 0;
}
