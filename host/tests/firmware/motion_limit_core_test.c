/* Host test for the movement limiter (patch ML01): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header> motion_limit_core_test.c */
#include <stdio.h>
#include <stdlib.h>
#include "maipai_motion_limit_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

/* hold the readings for ms, stepping every 20 ms */
static uint32_t T;
static float AX = 0.0f, AY = 9.8f, AZ = 0.0f, PITCH = 0.0f; /* the gravity vector the IMU reports; upright by default */
static int STALE = 0;                                         /* 1: no readings come in */
static void run(mml_t* m, int carried, int usb, int level, uint32_t ms)
{
    for (uint32_t t = 0; t < ms; t += 20) {
        T += 20;
        if (!STALE) mml_orient_feed(m, T, AX, AY, AZ, PITCH);
        mml_step(m, T, carried, usb, level);
    }
}
static void vec(float deg_roll, float deg_fore)
{ /* gravity tilted by deg_roll to a side and deg_fore in the pitch plane from upright (+y) */
    const float r = 3.14159265f / 180.0f;
    const float g = 9.8f;
    AX = g * sinf(deg_roll * r);
    const float h = g * cosf(deg_roll * r);
    AY = h * cosf(deg_fore * r);
    AZ = h * sinf(deg_fore * r);
}

int main(void)
{
    mml_t m;
    mml_init(&m);
    run(&m, 0, 0, 90, 500);
    CHECK(mml_state(&m) == MML_FREE && mml_scale(&m) == 100 && mml_speed_cap(&m) == 1000 && mml_dance_max(&m) == 4);
    CHECK(mml_angle(&m, 300, 0) == 300);

    /* carried: believed after 150 ms, none moves, the head holds; a set-down only after 1 s */
    run(&m, 1, 0, 90, 100);
    CHECK(mml_state(&m) == MML_FREE);
    run(&m, 1, 0, 90, 100);
    CHECK(mml_state(&m) == MML_CARRIED && mml_scale(&m) == 0 && mml_angle(&m, 300, 42) == 42 && !mml_dances_ok(&m));
    run(&m, 0, 0, 90, 600);
    CHECK(mml_state(&m) == MML_CARRIED);
    run(&m, 0, 0, 90, 600);
    CHECK(mml_state(&m) == MML_FREE);

    /* USB: a cable going in is believed at once (more restrictive); half the excursion, speed cap 60 percent, no full dance */
    run(&m, 0, 1, 90, 40);
    CHECK(mml_state(&m) == MML_USB && mml_scale(&m) == 50 && mml_angle(&m, 300, 0) == 150 && mml_angle(&m, -300, 0) == -150);
    CHECK(mml_speed_cap(&m) == 600 && mml_dance_max(&m) == 3);
    CHECK(mml_stiffness(&m, 650.0f) < 245.0f && mml_stiffness(&m, 100.0f) == 100.0f);
    /* a brief unplug does not flap */
    run(&m, 0, 0, 90, 1000);
    CHECK(mml_state(&m) == MML_USB);
    run(&m, 0, 0, 90, 1500);
    CHECK(mml_state(&m) == MML_FREE);
    /* the off switch lifts the USB limit only; carried still wins */
    run(&m, 0, 1, 90, 2200);
    CHECK(mml_state(&m) == MML_USB);
    m.usb_limit = 0;
    CHECK(mml_state(&m) == MML_FREE && mml_scale(&m) == 100);
    run(&m, 1, 1, 90, 400);
    CHECK(mml_state(&m) == MML_CARRIED && mml_scale(&m) == 0);
    run(&m, 0, 1, 90, 1200);
    CHECK(mml_state(&m) == MML_FREE);
    m.usb_limit = 1;
    run(&m, 0, 0, 90, 2200);
    CHECK(mml_state(&m) == MML_FREE);

    /* battery ladder with hysteresis: 50 / 30 / 15 / 8 going down, +3 coming back */
    CHECK(mml_band_for(51, 0) == 0 && mml_band_for(50, 0) == 0 && mml_band_for(49, 0) == 1);
    CHECK(mml_band_for(29, 1) == 2 && mml_band_for(14, 2) == 3 && mml_band_for(7, 3) == 4);
    CHECK(mml_band_for(52, 1) == 1 && mml_band_for(53, 1) == 0); /* up needs 50 + 3 */
    CHECK(mml_band_for(32, 2) == 2 && mml_band_for(33, 2) == 1);
    CHECK(mml_band_for(17, 3) == 3 && mml_band_for(18, 3) == 2);
    CHECK(mml_band_for(10, 4) == 4 && mml_band_for(11, 4) == 3);
    CHECK(mml_band_for(100, 4) == 0 && mml_band_for(0, 0) == 4);
    /* a level wobbling around 30 does not flap */
    {
        int band = mml_band_for(31, 0), flips = 0;
        for (int i = 0; i < 40; i++) { const int b = mml_band_for(i % 2 ? 31 : 29, band); if (b != band) flips++; band = b; }
        CHECK(flips <= 1);
    }
    run(&m, 0, 0, 60, 100);
    CHECK(mml_state(&m) == MML_FREE);
    run(&m, 0, 0, 45, 100);
    CHECK(mml_state(&m) == MML_BATTERY && m.band == 1 && mml_scale(&m) == 80 && mml_speed_cap(&m) == 800 && mml_dance_max(&m) == 4);
    run(&m, 0, 0, 25, 100);
    CHECK(m.band == 2 && mml_scale(&m) == 50 && mml_speed_cap(&m) == 600 && mml_dance_max(&m) == 3 && mml_angle(&m, 200, 0) == 100);
    run(&m, 0, 0, 12, 100);
    CHECK(m.band == 3 && mml_scale(&m) == 25 && mml_dance_max(&m) == 0 && !mml_dances_ok(&m) && mml_angle(&m, 200, 0) == 50);
    run(&m, 0, 0, 5, 100);
    CHECK(m.band == 4 && mml_scale(&m) == 0 && mml_angle(&m, 200, 7) == 7);
    /* charging on USB is the USB rule, not the ladder: at 5 percent on a cable it is limited, not held */
    run(&m, 0, 1, 5, 2200);
    CHECK(mml_state(&m) == MML_USB && mml_scale(&m) == 50);
    m.usb_limit = 0;
    CHECK(mml_state(&m) == MML_FREE);
    m.usb_limit = 1;
    /* unplugged at 5 percent: back to the hold */
    run(&m, 0, 0, 5, 2200);
    CHECK(mml_state(&m) == MML_BATTERY && mml_scale(&m) == 0);
    /* carried beats the ladder, and the ladder beats nothing */
    run(&m, 1, 0, 90, 400);
    CHECK(mml_state(&m) == MML_CARRIED);
    run(&m, 0, 0, 90, 1200);
    CHECK(mml_state(&m) == MML_FREE && m.band == 0);

    /* the bench force */
    m.force_carried = 1;
    run(&m, 0, 0, 90, 400);
    CHECK(mml_state(&m) == MML_CARRIED);
    m.force_carried = -1;
    m.force_usb = 1;
    run(&m, 0, 0, 90, 3000);
    CHECK(mml_state(&m) == MML_USB);
    m.force_usb = -1;
    m.force_level = 20;
    run(&m, 0, 0, 90, 3000);
    CHECK(mml_state(&m) == MML_BATTERY && m.band == 2);

    /* every result stays inside the range and never exceeds the input excursion */
    for (int c = 0; c < 2; c++) for (int u = 0; u < 2; u++) for (int l = 0; l <= 100; l += 5) {
        mml_t k; mml_init(&k);
        run(&k, c, u, l, 3000);
        for (int a = -600; a <= 600; a += 100) {
            const int r = mml_angle(&k, a, 0);
            CHECK((a >= 0 ? r <= a && r >= 0 : r >= a && r <= 0));
        }
        CHECK(mml_speed_cap(&k) >= 0 && mml_speed_cap(&k) <= 1000);
    }
    /* orientation: the tilt from upright, head pitch compensated */
    {
        int inv;
        CHECK(mml_tilt_deg(0, 9.8f, 0, 0, &inv) == 0 && !inv);
        vec(20, 0); CHECK(abs(mml_tilt_deg(AX, AY, AZ, 0, &inv) - 20) <= 1);
        vec(0, 40); CHECK(abs(mml_tilt_deg(AX, AY, AZ, 0, &inv) - 40) <= 1);
        vec(0, 40); CHECK(mml_tilt_deg(AX, AY, AZ, 40, &inv) <= 1); /* the head pitched 40 degrees reads upright either way it is signed */
        vec(0, 40); CHECK(mml_tilt_deg(AX, AY, AZ, -40, &inv) <= 1);
        vec(60, 0); CHECK(abs(mml_tilt_deg(AX, AY, AZ, 0, &inv) - 60) <= 1 && !inv);
        vec(0, 90); CHECK(abs(mml_tilt_deg(AX, AY, AZ, 0, &inv) - 90) <= 1 && !inv);
        vec(0, 180); CHECK(abs(mml_tilt_deg(AX, AY, AZ, 0, &inv) - 180) <= 1 && inv);
        CHECK(mml_tilt_deg(30.0f, -30.0f, 0.0f, 0, &inv) == -1); /* a shake says nothing */
        CHECK(mml_tilt_deg(0.0f, 0.0f, 0.0f, 0, &inv) == -1);
    }
    /* the bands and their effect, with the whole mix */
    {
        mml_t k;
        mml_init(&k);
        CHECK(mml_orient(&k, 0) == MML_O_UNKNOWN && mml_scale(&k) == 50 && mml_dance_max(&k) == 3); /* no data yet: limited */
        STALE = 0; vec(0, 0);
        run(&k, 0, 0, 90, 100);
        CHECK(k.orient == MML_O_UPRIGHT && mml_state(&k) == MML_FREE && mml_scale(&k) == 100); /* the first reading is believed at once */
        vec(10, 0); run(&k, 0, 0, 90, 2000);
        CHECK(k.orient == MML_O_UPRIGHT); /* 10 degrees: upright */
        vec(20, 0); run(&k, 0, 0, 90, 300);
        CHECK(k.orient == MML_O_UPRIGHT); /* a bump: a worse band is believed after 0.5 s */
        run(&k, 0, 0, 90, 400);
        CHECK(k.orient == MML_O_TILTED && mml_state(&k) == MML_ORIENT && mml_scale(&k) == 30 && mml_speed_cap(&k) == 400 && mml_dance_max(&k) == 2);
        CHECK(mml_angle(&k, 300, 0) == 90);
        vec(12, 0); run(&k, 0, 0, 90, 2000);
        CHECK(k.orient == MML_O_TILTED); /* back over 10 degrees: the hysteresis keeps tilted */
        vec(8, 0); run(&k, 0, 0, 90, 900);
        CHECK(k.orient == MML_O_TILTED); /* better only after 1 s */
        run(&k, 0, 0, 90, 300);
        CHECK(k.orient == MML_O_UPRIGHT && mml_state(&k) == MML_FREE);
        vec(40, 0); run(&k, 0, 0, 90, 1000);
        CHECK(k.orient == MML_O_TILTED && mml_scale(&k) == 30);
        vec(60, 0); run(&k, 0, 0, 90, 700);
        CHECK(k.orient == MML_O_SIDE && mml_scale(&k) == 0 && mml_angle(&k, 300, 5) == 5 && mml_dance_max(&k) == 0);
        vec(42, 0); run(&k, 0, 0, 90, 2000);
        CHECK(k.orient == MML_O_SIDE); /* between 40 and 45: stays on its side */
        vec(35, 0); run(&k, 0, 0, 90, 1200);
        CHECK(k.orient == MML_O_TILTED);
        vec(0, 90); run(&k, 0, 0, 90, 2000);
        CHECK(k.orient == MML_O_SIDE && mml_scale(&k) == 0);
        vec(0, 180); run(&k, 0, 0, 90, 700);
        CHECK(k.orient == MML_O_INVERTED && mml_scale(&k) == 0 && mml_state(&k) == MML_ORIENT);
        /* the USB off switch and a cable never lift it */
        run(&k, 0, 1, 90, 2200);
        k.usb_limit = 0;
        CHECK(mml_scale(&k) == 0);
        k.usb_limit = 1;
        /* back upright: the orientation is free again, the cable is the USB rule */
        vec(0, 0); run(&k, 0, 1, 90, 1200);
        CHECK(k.orient == MML_O_UPRIGHT && mml_state(&k) == MML_USB && mml_scale(&k) == 50);
        /* tilted on USB: the most restrictive of the two (30 and 50) */
        vec(25, 0); run(&k, 0, 1, 90, 800);
        CHECK(mml_scale(&k) == 30 && mml_speed_cap(&k) == 400 && mml_dance_max(&k) == 2);
        /* tilted on a low battery band 2: still 30 percent; band 3 minimal 25 percent wins over a tilt */
        run(&k, 0, 0, 25, 2300);
        CHECK(k.band == 2 && mml_scale(&k) == 30);
        run(&k, 0, 0, 12, 100);
        CHECK(k.band == 3 && mml_scale(&k) == 25 && mml_dance_max(&k) == 0);
        /* carried beats everything */
        vec(0, 0); run(&k, 1, 0, 90, 1200);
        CHECK(mml_state(&k) == MML_CARRIED && mml_scale(&k) == 0);
        run(&k, 0, 0, 90, 1500);
        CHECK(mml_state(&k) == MML_FREE);
        /* stale data: unknown, limited, at once; fresh data brings it back */
        STALE = 1;
        run(&k, 0, 0, 90, 1900);
        CHECK(mml_orient(&k, k.now) == MML_O_UPRIGHT);
        run(&k, 0, 0, 90, 300);
        CHECK(mml_orient(&k, k.now) == MML_O_UNKNOWN && mml_scale(&k) == 50 && mml_speed_cap(&k) == 600 && mml_dance_max(&k) == 3);
        STALE = 0; vec(0, 0); run(&k, 0, 0, 90, 100);
        CHECK(mml_state(&k) == MML_FREE);
        /* a reading stamped a few ms after the clock the state was read with is fresh, not stale (found on the unit) */
        vec(0, 0); STALE = 0; run(&k, 0, 0, 90, 100);
        k.now = k.acc_ms - 5u;
        CHECK(mml_orient(&k, k.now) == MML_O_UPRIGHT);
        /* a reading that is not 1 g leaves the band alone */
        mml_orient_feed(&k, T + 20, 30.0f, -30.0f, 0.0f, 0.0f);
        CHECK(k.orient == MML_O_UPRIGHT);
        /* the bench force */
        k.force_orient = MML_O_INVERTED;
        CHECK(mml_scale(&k) == 0 && mml_state(&k) == MML_ORIENT);
        k.force_orient = -1;
    }
    /* the status must say what is applied (patch SF31): over every combination of carried, orientation, cable, USB rule and battery band, the state
     * is "free" exactly when scale, speed and dance step are all at their full values, and a limited state names a source that really limits */
    for (int carried = 0; carried < 2; carried++) {
        for (int orient = 0; orient < 5; orient++) {
            for (int usb = 0; usb < 2; usb++) {
                for (int usb_rule = 0; usb_rule < 2; usb_rule++) {
                    for (int band = 0; band < 5; band++) {
                        mml_t g;
                        memset(&g, 0, sizeof g);
                        g.force_carried = g.force_usb = g.force_level = -1;
                        g.force_orient = (int8_t)orient;
                        g.carried = (uint8_t)carried;
                        g.usb = (uint8_t)usb;
                        g.usb_limit = (uint8_t)usb_rule;
                        g.band = (uint8_t)band;
                        g.now = 1000;
                        g.acc_ms = 1000;
                        int s, v, d;
                        mml_source_limits(&g, &s, &v, &d);
                        const int full = s == 100 && v == 100 && d == 4;
                        CHECK((mml_state(&g) == MML_FREE) == full);
                        CHECK(mml_scale(&g) == s && mml_speed_pct(&g) == v && mml_dance_max(&g) == d);
                        if (mml_state(&g) == MML_USB) CHECK(usb && usb_rule && s <= 50);
                        if (mml_state(&g) == MML_CARRIED) CHECK(s == 0);
                    }
                }
            }
        }
    }
    /* fail closed: at boot the cable is not known, and the limited state applies until a reading says otherwise */
    {
        mml_t b;
        mml_init(&b);
        b.force_orient = MML_O_UPRIGHT; /* the orientation rule is its own test */
        for (uint32_t t = 0; t < 3000; t += 20) mml_step(&b, t, 0, -1, -1);
        CHECK(mml_state(&b) == MML_USB && mml_scale(&b) == 50 && mml_speed_pct(&b) == 60);
        mml_step(&b, 3020, 0, 0, -1); /* the first reading: no cable, believed at once */
        CHECK(mml_state(&b) == MML_FREE && mml_scale(&b) == 100);
        mml_step(&b, 3040, 0, 1, -1); /* a cable goes in: limited at once, no 2 s wait */
        CHECK(mml_state(&b) == MML_USB);
        mml_step(&b, 3060, 0, 0, -1); /* out again: held for 2 s */
        CHECK(mml_state(&b) == MML_USB);
        mml_step(&b, 5100, 0, 0, -1);
        CHECK(mml_state(&b) == MML_FREE);
        mml_t c; /* a first reading that says cable in */
        mml_init(&c);
        c.force_orient = MML_O_UPRIGHT;
        mml_step(&c, 20, 0, 1, -1);
        CHECK(mml_state(&c) == MML_USB);
    }
    /* a reading taken while the head's pitch moves is held, not used: the band stays upright, and the data stays fresh */
    {
        mml_t h;
        mml_init(&h);
        mml_orient_feed(&h, 1000, 0.0f, 9.8f, 0.0f, 0.0f);
        CHECK(mml_orient(&h, 1000) == MML_O_UPRIGHT);
        for (uint32_t t = 1020; t < 2000; t += 20) mml_orient_hold(&h, t); /* tilted readings would have come here */
        CHECK(mml_orient(&h, 2000) == MML_O_UPRIGHT && h.orient_raw == MML_O_UPRIGHT);
        CHECK(!strcmp(mml_state_name_of(MML_USB), "usb_limited") && !strcmp(mml_state_name_of(MML_FREE), "free"));
    }
    STALE = 0; vec(0, 0);
    if (failures) { printf("%d failure(s)\n", failures); return 1; }
    printf("all passed\n");
    return 0;
}
