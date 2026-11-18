/* Host test for the MIC3 bench measurement (patch SF15). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header> ... -lm. */
#include <stdio.h>
#include <stdlib.h>
#include "maipai_mic3_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void feed(m3_t* m, float tone_amp1, float tone_amp3, float noise, int frames, unsigned* seed)
{
    static int16_t buf[1024 * 2];
    for (int done = 0; done < frames; done += 1024) {
        const int n = frames - done < 1024 ? frames - done : 1024;
        for (int i = 0; i < n; i++) {
            const float ph = 2.0f * 3.14159265f * 1000.0f * (float)(done + i) / 16000.0f;
            *seed = *seed * 1664525u + 1013904223u;
            const float r1 = ((float)((*seed >> 8) & 0xFFFF) / 32768.0f - 1.0f) * noise;
            *seed = *seed * 1664525u + 1013904223u;
            const float r3 = ((float)((*seed >> 8) & 0xFFFF) / 32768.0f - 1.0f) * noise;
            buf[i * 2] = (int16_t)(tone_amp1 * sinf(ph) + r1);
            buf[i * 2 + 1] = (int16_t)(tone_amp3 * sinf(ph) + r3);
        }
        m3_feed(m, buf, (size_t)n, 2);
    }
}

int main(void)
{
    unsigned seed = 7;
    m3_t m;
    m3_begin(&m, 16000.0f, 1000.0f);
    /* a quiet room, then a tone that reaches MIC3 loudly and MIC1 faintly */
    m3_set_phase(&m, 0);
    feed(&m, 0, 0, 30.0f, 8000, &seed);
    m3_set_phase(&m, 1);
    feed(&m, 200.0f, 8000.0f, 30.0f, 32000, &seed);
    CHECK(m3_tone_amp(&m, 1, 1) > 7900.0f && m3_tone_amp(&m, 1, 1) < 8100.0f);
    CHECK(m3_tone_amp(&m, 1, 0) > 150.0f && m3_tone_amp(&m, 1, 0) < 250.0f);
    CHECK(m3_snr_db(&m, 1) > 40.0f);
    CHECK(m3_snr_db(&m, 0) > 10.0f && m3_snr_db(&m, 0) < 30.0f);
    CHECK(m3_peak(&m, 1, 1) > 7900 && m3_peak(&m, 1, 1) < 8200);
    CHECK(m3_rms(&m, 0, 1) > 10.0f && m3_rms(&m, 0, 1) < 25.0f);
    /* a silent MIC3 (not routed): no tone and a poor ratio */
    m3_begin(&m, 16000.0f, 1000.0f);
    m3_set_phase(&m, 0);
    feed(&m, 0, 0, 30.0f, 8000, &seed);
    m3_set_phase(&m, 1);
    feed(&m, 200.0f, 0, 30.0f, 32000, &seed);
    CHECK(m3_tone_amp(&m, 1, 1) < 20.0f);
    CHECK(m3_snr_db(&m, 1) < 6.0f);
    /* a clipped MIC3 reports its peak at full scale */
    m3_begin(&m, 16000.0f, 1000.0f);
    m3_set_phase(&m, 1);
    feed(&m, 0, 32000.0f, 0, 16000, &seed);
    CHECK(m3_peak(&m, 1, 1) > 31000);
    /* the median over 200 ms windows ignores a burst of room noise in a few windows */
    m3_begin(&m, 16000.0f, 1000.0f);
    m3_set_phase(&m, 1);
    feed(&m, 0, 4000.0f, 30.0f, 3200 * 3, &seed);   /* three clean windows */
    feed(&m, 0, 4000.0f, 9000.0f, 3200 * 2, &seed); /* two windows of loud room noise */
    CHECK(m.wn[1] == 5);
    CHECK(m3_win_amp_median(&m, 1, 1) > 3800.0f && m3_win_amp_median(&m, 1, 1) < 4300.0f);
    CHECK(m3_win_rms_median(&m, 1, 1) > 2500.0f && m3_win_rms_median(&m, 1, 1) < 3200.0f);
    if (failures) return 1;
    printf("mic3 core ok\n");
    return 0;
}
