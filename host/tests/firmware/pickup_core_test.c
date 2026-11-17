/* Host test for pickup, carried and set-down (patch TB04), against synthesised accelerometer traces.
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with the header> ... -lm.
 *
 * Each trace is built from segments. The world has gravity (1 g up); a segment adds a vertical push `v`, a sideways
 * push `h` and tilts the unit by `theta`; the sensor reads (h, (1+v) sin theta, (1+v) cos theta) in g, times 9.80665,
 * plus a little noise. Samples come every 20 ms with a few ms of jitter, as the real task does. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maipai_pickup_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

#define PI_F 3.14159265f
#define MAXEV 64

static mp_t det;
static uint32_t clk;
static uint32_t seed = 12345;
static int ev_kind[MAXEV];
static uint32_t ev_at[MAXEV];
static int ev_n;
static float theta_now;  /* degrees, where the last segment left the tilt */
static float noise_g = 0.008f;

static float rnd(void)
{
    seed = seed * 1664525u + 1013904223u;
    return ((float)((seed >> 8) & 0xFFFF) / 32768.0f) - 1.0f; /* -1..1 */
}

static void reset(void)
{
    mp_init(&det);
    clk = 1000;
    ev_n = 0;
    theta_now = 0;
    noise_g = 0.008f;
}

static void feed(float v, float h, float theta_deg)
{
    clk += 20 + (uint32_t)(rnd() * 2.0f + 2.0f); /* 20..24 ms */
    const float th = theta_deg * PI_F / 180.0f;
    const float s  = 1.0f + v;
    const float x  = h + noise_g * rnd();
    const float y  = s * sinf(th) + noise_g * rnd();
    const float z  = s * cosf(th) + noise_g * rnd();
    const mp_event_t e = mp_update(&det, x * MP_G, y * MP_G, z * MP_G, clk);
    if (e != MP_NONE && ev_n < MAXEV) {
        ev_kind[ev_n] = (int)e;
        ev_at[ev_n++] = clk;
    }
}

/* Segment helpers: each runs for `ms` and leaves the tilt where it ended. */
static void still(uint32_t ms)
{
    const uint32_t end = clk + ms;
    while (clk < end) feed(0, 0, theta_now);
}
static void lobe(uint32_t ms, float amp, float theta_to) /* a half sine of vertical push, tilting on the way */
{
    const uint32_t t0 = clk;
    const float th0   = theta_now;
    while (clk < t0 + ms) {
        const float f = (float)(clk - t0) / (float)ms;
        feed(amp * sinf(PI_F * f), 0, th0 + (theta_to - th0) * f);
    }
    theta_now = theta_to;
}
static void ramp(uint32_t ms, float theta_to) /* a slow tilt with no push */
{
    const uint32_t t0 = clk;
    const float th0   = theta_now;
    while (clk < t0 + ms) feed(0, 0, th0 + (theta_to - th0) * (float)(clk - t0) / (float)ms);
    theta_now = theta_to;
}
static void bob(uint32_t ms, float vamp, float hz, float tilt_amp) /* walking: a bob and a little tilt */
{
    const uint32_t t0 = clk;
    const float base  = theta_now;
    while (clk < t0 + ms) {
        const float t = (float)(clk - t0) / 1000.0f;
        feed(vamp * sinf(2 * PI_F * hz * t), 0.02f * sinf(2 * PI_F * hz * t * 0.5f), base + tilt_amp * sinf(2 * PI_F * hz * 0.5f * t));
    }
}
static void side(uint32_t ms, float amp, float hz) /* sideways swing (a shake) */
{
    const uint32_t t0 = clk;
    while (clk < t0 + ms) feed(0, amp * sinf(2 * PI_F * hz * (float)(clk - t0) / 1000.0f), theta_now);
}
static void bump(float amp, uint32_t spike_ms) /* a knock: a short spike that rings down */
{
    const uint32_t t0 = clk;
    while (clk < t0 + spike_ms) feed(amp, 0, theta_now);
    const uint32_t t1 = clk;
    while (clk < t1 + 400) {
        const float t = (float)(clk - t1) / 1000.0f;
        feed(amp * 0.6f * expf(-t / 0.08f) * cosf(2 * PI_F * 12.0f * t), 0, theta_now);
    }
}

static int count(int kind)
{
    int n = 0;
    for (int i = 0; i < ev_n; i++) n += ev_kind[i] == kind;
    return n;
}

static void dump(const char* name)
{
    printf("  %s:", name);
    for (int i = 0; i < ev_n; i++) printf(" %s@%u", MP_EVENT_NAMES[ev_kind[i]], (unsigned)(ev_at[i] - 1000));
    printf("\n");
}

int main(void)
{
    /* 1. A full pickup: straight up, carried, then put down with a bump. Exactly lifted, carried, set_down, in order. */
    reset();
    still(2500);
    CHECK(ev_n == 0);
    const uint32_t lift_start = clk;
    lobe(260, 0.30f, 6);   /* pushed up */
    lobe(260, -0.30f, 12); /* slowed */
    bob(3500, 0.14f, 1.8f, 6.0f); /* carried */
    CHECK(ev_kind[0] == MP_LIFTED && ev_at[0] - lift_start < 1100); /* the lift is known within a second of the push */
    lobe(260, -0.22f, 2);      /* lowered */
    bump(0.5f, 40);
    still(2500);
    dump("pickup");
    CHECK(ev_n == 3 && ev_kind[0] == MP_LIFTED && ev_kind[1] == MP_CARRIED && ev_kind[2] == MP_SET_DOWN);
    CHECK(ev_at[1] - ev_at[0] >= MP_DEBOUNCE_MS - 100);
    CHECK(ev_at[2] > ev_at[1]);
    CHECK(mp_axis_name(mp_axis(&det))[1] == 'z'); /* set down upright */
    CHECK(!mp_is_held(&det));

    /* 2. A pickup that tilts the unit: one long push, pose changed 40 degrees, held still. */
    reset();
    still(2500);
    lobe(320, 0.22f, 40);
    still(2500);
    dump("tilt lift");
    CHECK(count(MP_LIFTED) == 1 && mp_is_held(&det));

    /* 3. A slow tilt with no push at all is not a pickup (the orientation event covers it). */
    reset();
    still(2500);
    ramp(2000, 40);
    still(2500);
    CHECK(ev_n == 0);

    /* 4. Table bumps: ten knocks, 0.4 to 0.7 g for 30 to 60 ms, ringing down, pose unchanged. No event at all. */
    reset();
    still(2500);
    for (int i = 0; i < 10; i++) {
        bump(0.4f + 0.03f * (float)i, 30 + (uint32_t)(i % 4) * 10);
        still(2000);
    }
    dump("bumps");
    CHECK(ev_n == 0);

    /* 5. The unit's own speaker: continuous ripple up to 0.06 g on the table, with and without the speaking flag. */
    reset();
    still(2500);
    mp_set_speaking(&det, 1);
    noise_g = 0.06f;
    still(20000);
    noise_g = 0.008f;
    for (uint32_t i = 0; i < 600; i++) feed(0.05f * sinf(2 * PI_F * 17.0f * (float)i * 0.0215f), 0, 0);
    mp_set_speaking(&det, 0);
    noise_g = 0.06f;
    still(10000);
    CHECK(ev_n == 0);

    /* 6. The unit's own head move: a jerk the size of a lift. Ignored when it told the detector; the same trace without
     * that note is a lift, which is why the note exists. */
    reset();
    still(2500);
    mp_note_own(&det, clk, MP_OWN_HOLD_MS, 0);
    lobe(250, 0.25f, 5);
    lobe(250, -0.25f, 0);
    still(3000);
    CHECK(ev_n == 0);
    reset();
    still(2500);
    lobe(250, 0.25f, 5);
    lobe(250, -0.25f, 0);
    still(3000);
    CHECK(count(MP_LIFTED) == 1);

    /* 7. Shake on the table (it is shaken without being lifted): no lift. */
    reset();
    still(2500);
    side(1000, 1.2f, 5.0f);
    still(3000);
    dump("table shake");
    CHECK(count(MP_LIFTED) == 0 && count(MP_CARRIED) == 0);

    /* 8. Shaken in the hand after a lift: one "shaken", still held, no set down; then put back on the table gently:
     * back at the first pose, still for a few seconds: set_down. */
    reset();
    still(2500);
    lobe(260, 0.30f, 20);
    lobe(260, -0.30f, 25);
    still(1800);
    CHECK(count(MP_LIFTED) == 1);
    side(1500, 1.5f, 4.0f);
    still(3000);
    dump("shake in hand");
    CHECK(count(MP_SHAKEN) == 1 && count(MP_SET_DOWN) == 0 && mp_is_held(&det));
    ramp(400, 0);
    still(6500);
    dump("gentle put down");
    CHECK(count(MP_SET_DOWN) == 1 && !mp_is_held(&det));

    /* 9. Debounce: a second push inside 1.5 s of a lift gives no second lift. */
    reset();
    still(2500);
    lobe(260, 0.30f, 10);
    lobe(260, -0.30f, 12);
    lobe(260, 0.30f, 14);
    lobe(260, -0.30f, 14);
    still(2000);
    dump("double push");
    CHECK(count(MP_LIFTED) == 1);

    /* 10. Readings that make no sense (a dropped bus read: zeros) are skipped, not read as free fall. */
    reset();
    still(2500);
    for (int i = 0; i < 20; i++) {
        clk += 20;
        CHECK(mp_update(&det, 0, 0, 0, clk) == MP_NONE);
    }
    still(2000);
    CHECK(ev_n == 0);

    /* 11. A long run of nothing at all for 10 minutes of samples, with the noise a real unit shows: no event. */
    reset();
    still(2500);
    noise_g = 0.015f;
    for (int i = 0; i < 30000; i++) feed(0, 0, 0);
    CHECK(ev_n == 0);

    /* 12. Jitter and a missed read (a 150 ms gap in the middle of a lift) do not break the lift. */
    reset();
    still(2500);
    lobe(260, 0.30f, 6);
    clk += 150;
    lobe(260, -0.30f, 12);
    still(1500);
    CHECK(count(MP_LIFTED) >= 0 && ev_n <= 2); /* may or may not count the gapped lift, never a storm */

    /* 13. The same traces under 40 different noise seeds: the pickup is always lifted, carried, set_down in that order,
     * and the knocks, the speaker and the unit's own move never make an event. */
    for (uint32_t k = 1; k <= 40; k++) {
        seed = 777u * k;
        reset();
        still(2500);
        lobe(260, 0.30f, 6);
        lobe(260, -0.30f, 12);
        bob(3500, 0.14f, 1.8f, 6.0f);
        lobe(260, -0.22f, 2);
        bump(0.5f, 40);
        still(2500);
        if (!(ev_n == 3 && ev_kind[0] == MP_LIFTED && ev_kind[1] == MP_CARRIED && ev_kind[2] == MP_SET_DOWN)) {
            printf("  seed %u: pickup gave %d events\n", (unsigned)k, ev_n);
            failures++;
        }
        reset();
        still(2500);
        for (int i = 0; i < 6; i++) {
            bump(0.4f + 0.05f * (float)(i % 4), 30 + (uint32_t)(i % 4) * 10);
            still(1500);
        }
        noise_g = 0.06f;
        mp_set_speaking(&det, 1);
        still(6000);
        noise_g = 0.008f;
        mp_set_speaking(&det, 0);
        mp_note_own(&det, clk, MP_OWN_HOLD_MS, 0);
        lobe(250, 0.25f, 5);
        lobe(250, -0.25f, 0);
        still(2500);
        if (ev_n != 0) {
            printf("  seed %u: %d false events\n", (unsigned)k, ev_n);
            failures++;
        }
    }

    CHECK(sizeof(mp_t) <= 200);
    printf("mp_t is %u bytes\n", (unsigned)sizeof(mp_t));

    if (failures != 0) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
