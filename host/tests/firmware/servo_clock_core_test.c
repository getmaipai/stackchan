/* Host test for the servo animation clock (patch SF28). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header> ... -lm.
 * A critically damped spring (the shape of the head's animation) is stepped the way Servo::update does at different update call rates;
 * the position at the same real time must agree, and the speed ceiling must hold. */
#include <math.h>
#include <stdio.h>
#include "maipai_servo_clock_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

/* returns the position (tenth-degrees) at real time t_end_ms of a move from 0 to 400, update calls every call_ms, with or without the ceiling */
static float run(int call_ms, int t_end_ms, int vmax, int fixed_dt, float* peak_speed)
{
    const float k = 170.0f, c = 2.0f * sqrtf(170.0f);
    float x = 0.0f, v = 0.0f;
    uint32_t last = 0;
    int cmd = 0;
    *peak_speed = 0.0f;
    for (int t = call_ms; t <= t_end_ms; t += call_ms) {
        uint32_t elapsed;
        if (!msc_due((uint32_t)t, last, &elapsed)) continue;
        last = (uint32_t)t;
        const float dt = fixed_dt ? 0.02f : msc_dt_s(elapsed);
        const float a = -k * (x - 400.0f) - c * v; /* semi-implicit Euler */
        v += a * dt;
        x += v * dt;
        const int next = vmax > 0 ? msc_limit_step(cmd, (int)x, vmax, dt) : (int)x;
        const float speed = fabsf((float)(next - cmd)) / dt;
        if (speed > *peak_speed) *peak_speed = speed;
        cmd = next;
    }
    return (float)cmd;
}

int main(void)
{
    float peak;
    /* the old clock: a step per second call at 12 ms calls (24 ms apart) advanced 20 ms: the move lagged; the new clock does not */
    const float old12 = run(12, 150, 0, 1, &peak);
    const float new12 = run(12, 150, 0, 0, &peak);
    const float new10 = run(10, 150, 0, 0, &peak);
    const float new20 = run(20, 150, 0, 0, &peak);
    const float new40 = run(40, 150, 0, 0, &peak);
    const float ref = run(1, 150, 0, 0, &peak); /* every call a step: 20 ms steps */
    CHECK(old12 < new12 - 8.0f);                       /* the old clock was behind */
    CHECK(fabsf(new12 - ref) < 0.12f * 400.0f);         /* the same real-time motion within 12 percent at any rate... */
    CHECK(fabsf(new10 - ref) < 0.12f * 400.0f);
    CHECK(fabsf(new20 - ref) < 0.12f * 400.0f);
    CHECK(fabsf(new40 - ref) < 0.20f * 400.0f);          /* ...a 40 ms call rate has fewer, longer steps */
    /* rates 25, 50 and 90 Hz */
    const float r25 = run(40, 300, 0, 0, &peak), r50 = run(20, 300, 0, 0, &peak), r90 = run(11, 300, 0, 0, &peak);
    CHECK(fabsf(r25 - r50) < 80.0f && fabsf(r90 - r50) < 80.0f);
    /* the ceiling: no step is faster than vmax (tenth-degrees per second) */
    const int vmax = msc_vmax_tenth_dps(50); /* 200 degrees per second */
    CHECK(vmax == 2000);
    (void)run(12, 1000, vmax, 0, &peak);
    CHECK(peak <= (float)vmax * 1.05f + 1.0f);
    (void)run(90, 1000, vmax, 0, &peak);
    CHECK(peak <= (float)vmax * 1.05f + 1.0f);
    CHECK(msc_vmax_tenth_dps(0) == 0 && msc_vmax_tenth_dps(150) == 4000);
    CHECK(msc_limit_step(100, 100, 0, 0.02f) == 100 || msc_limit_step(100, 100, 0, 0.02f) == 100);
    /* a stall is not a jump: dt never exceeds 50 ms */
    CHECK(msc_dt_s(5000) == 0.05f && msc_dt_s(1) == 0.02f);
    if (failures) return 1;
    printf("servo clock ok\n");
    return 0;
}
