/* Host test of the mumble note renderer (patch SF87). */
#include <stdio.h>
#include <stdlib.h>
#include "maipai_mumble_render_core.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

static int peak(const int16_t* p, uint32_t n) { int m = 0; for (uint32_t i = 0; i < n; i++) { int a = abs(p[i]); if (a > m) m = a; } return m; }

int main(void)
{
    static int16_t buf[3200], whole[3200], part[3200];
    mm_blip_t v = {0, 60, 196, 233, 100, 100};   /* a full-loudness vowel note: 60 ms from 196 to 233 Hz */
    CHECK(mmr_samples(&v) == 960);
    mmr_render(&v, 0, whole, 960);
    CHECK(peak(whole, 960) <= MMR_PEAK);
    CHECK(peak(whole, 960) > MMR_PEAK * 8 / 10);          /* near the chime level */
    CHECK(abs(whole[0]) < 600);                            /* the attack starts from silence */
    CHECK(abs(whole[959]) < 700);                          /* the fall ends in silence */
    mmr_render(&v, 300, part, 400);                        /* a slice at any offset equals the same samples of the whole note */
    for (int i = 0; i < 400; i++) CHECK(part[i] == whole[300 + i]);
    mmr_render(&v, 900, buf, 200);                         /* past the end is silence */
    for (int i = 60; i < 200; i++) CHECK(buf[i] == 0);
    mm_blip_t c = {0, 40, 392, 370, 55, 30};               /* a consonant (loudness 55) is quieter than a vowel */
    mmr_render(&c, 0, buf, 640);
    CHECK(peak(buf, 640) < peak(whole, 960));
    CHECK(peak(buf, 640) > MMR_PEAK * 4 / 10);
    mm_blip_t r = {0, 0, 0, 0, 0, 0};                      /* a rest is all zeros */
    mmr_render(&r, 0, buf, 100);
    for (int i = 0; i < 100; i++) CHECK(buf[i] == 0);
    mm_blip_t l = {0, 900, 300, 300, 100, 100};            /* a long note is cut at 200 ms */
    CHECK(mmr_samples(&l) == 3200);
    for (int pass = 0; pass < 2; pass++) {                 /* a whole caption never passes the chime level */
        mm_t m; mm_blip_t b; int hi = 0;
        mm_init(&m, "Hello, how are you today? I am fine!", 0, 2400);
        while (mm_next(&m, &b)) {
            mmr_render(&b, 0, buf, mmr_samples(&b));
            int p = peak(buf, mmr_samples(&b)); if (p > hi) hi = p;
        }
        CHECK(hi <= MMR_PEAK && hi > 0);
    }
    CHECK(mmr_mouth_level(0) == 0 && mmr_mouth_level(10) == 0 && mmr_mouth_level(30) == 1 && mmr_mouth_level(60) == 2);
    CHECK(mmr_mouth_level(85) == 3 && mmr_mouth_level(100) == 4);
    printf(fails ? "mumble_render_core_test FAILED\n" : "mumble_render_core_test ok\n");
    return fails ? 1 : 0;
}
