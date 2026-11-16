/* Host test for the fluid face core (patch H02): easing, time constants, speech level, mouth curve, gaze drift. */
#include <assert.h>
#include <math.h>
#include <stdio.h>

#include "maipai_facefx_core.h"

static int fails;
#define CHECK(c)                                                    \
    do {                                                            \
        if (!(c)) {                                                 \
            printf("FAIL line %d: %s\n", __LINE__, #c);             \
            fails++;                                                \
        }                                                           \
    } while (0)

static void test_follow(void)
{
    /* never overshoots, whatever the frame time */
    for (float dt = 1.0f; dt < 5000.0f; dt *= 1.7f) {
        const float v = mx_follow(0.0f, 100.0f, dt, 70.0f);
        CHECK(v >= 0.0f && v <= 100.0f);
    }
    /* a stalled frame (12 time constants or more) lands on the target; zero time changes nothing */
    CHECK(mx_follow(10.0f, 90.0f, 2000.0f, 70.0f) == 90.0f);
    CHECK(mx_follow(10.0f, 90.0f, 0.0f, 70.0f) == 10.0f);
    CHECK(mx_follow(10.0f, 90.0f, 20.0f, 0.0f) == 90.0f);
    /* monotone toward the target, and the same path at 20 ms and 33 ms steps within a few percent after 300 ms */
    float a = 0.0f, b = 0.0f;
    for (int i = 0; i < 15; i++) a = mx_follow(a, 100.0f, 20.0f, 70.0f);
    for (int i = 0; i < 10; i++) b = mx_follow(b, 100.0f, 30.0f, 70.0f);
    CHECK(fabsf(a - b) < 4.0f);
    CHECK(a > 95.0f);
}

static void test_blink_timing(void)
{
    /* a lid closing from 100 to 25 is more than 90 percent of the way in 60 ms; opening takes longer */
    float lid = 100.0f;
    for (int t = 0; t < 60; t += 15) lid = mx_follow(lid, 25.0f, 15.0f, mx_lid_tau(lid, 25.0f));
    CHECK(lid < 25.0f + 0.20f * 75.0f); /* more than 80 percent closed in 60 ms */
    float open = 25.0f;
    for (int t = 0; t < 60; t += 15) open = mx_follow(open, 100.0f, 15.0f, mx_lid_tau(open, 100.0f));
    CHECK(open < 100.0f - 0.30f * 75.0f); /* opens slower than it closed */
    CHECK(mx_lid_tau(100.0f, 25.0f) < mx_lid_tau(25.0f, 100.0f));
    CHECK(mx_mouth_tau(0.0f, 80.0f) < mx_mouth_tau(80.0f, 0.0f));
}

static void test_level(void)
{
    CHECK(mx_level_from_rms(0.0f) == 0);
    CHECK(mx_level_from_rms(0.5f) == 0);
    CHECK(mx_level_from_rms(100.0f) == 0);   /* about -50 dBFS */
    CHECK(mx_level_from_rms(32768.0f) == 100);
    CHECK(mx_level_from_rms(8000.0f) == 100);  /* -12 dBFS and louder */
    int last = -1;
    for (float rms = 50.0f; rms < 32768.0f; rms *= 1.3f) {
        const int l = mx_level_from_rms(rms);
        CHECK(l >= last);
        CHECK(l >= 0 && l <= 100);
        last = l;
    }
    const int mid = mx_level_from_rms(1500.0f); /* ordinary speech, about -27 dBFS */
    CHECK(mid > 30 && mid < 80);
}

static void test_mouth(void)
{
    CHECK(mx_mouth_for_level(0) == 0.0f);
    CHECK(mx_mouth_for_level(7) == 0.0f);   /* the noise gate */
    CHECK(mx_mouth_for_level(8) >= 8.0f);
    CHECK(mx_mouth_for_level(100) <= 90.0f + 0.01f);
    CHECK(mx_mouth_for_level(500) == mx_mouth_for_level(100));
    float last = -1.0f;
    for (int l = 0; l <= 100; l++) {
        const float m = mx_mouth_for_level(l);
        CHECK(m >= last);
        last = m;
    }
    /* ordinary speech opens the mouth well past half */
    CHECK(mx_mouth_for_level(50) > 50.0f);
}

static void test_drift(void)
{
    mx_drift_t d;
    mx_drift_init(&d, 12345u);
    float minx = 99, maxx = -99, miny = 99, maxy = -99;
    uint32_t t = 1000;
    int moves = 0;
    float lastx = 0;
    for (int i = 0; i < 20000; i++) { /* 20 ms frames, 400 s */
        mx_drift_step(&d, t, 20.0f, MX_DRIFT_AMP_PX);
        t += 20;
        if (d.x < minx) minx = d.x;
        if (d.x > maxx) maxx = d.x;
        if (d.y < miny) miny = d.y;
        if (d.y > maxy) maxy = d.y;
        if (d.tx != lastx) { moves++; lastx = d.tx; }
    }
    CHECK(minx >= -MX_DRIFT_AMP_PX - 0.01f && maxx <= MX_DRIFT_AMP_PX + 0.01f);
    CHECK(miny >= -MX_DRIFT_AMP_PX - 0.01f && maxy <= MX_DRIFT_AMP_PX + 0.01f);
    CHECK(maxx - minx > 3.0f); /* it does wander */
    /* a new place every 0.7 to 2.2 s: between 400/2.2 and 400/0.7 picks (some picks repeat the same x) */
    CHECK(moves > 60 && moves < 600);
    /* amplitude 0 glides back to the middle and stays */
    for (int i = 0; i < 400; i++) {
        mx_drift_step(&d, t, 20.0f, 0);
        t += 20;
    }
    CHECK(fabsf(d.x) < 0.05f && fabsf(d.y) < 0.05f);
}

static void test_settled(void)
{
    CHECK(mx_settled(1.0f, 1.3f, 0.4f));
    CHECK(!mx_settled(1.0f, 1.5f, 0.4f));
}

int main(void)
{
    test_follow();
    test_blink_timing();
    test_level();
    test_mouth();
    test_drift();
    test_settled();
    if (fails) {
        printf("%d failed\n", fails);
        return 1;
    }
    printf("facefx core: all passed\n");
    return 0;
}
