/* Host test of the analog tilt core (patch SF107): the properties of docs/design/accelerometer-games.md section 5, and the packed word the games read. */
#include <stdio.h>
#include <math.h>
#include "maipai_games_analog_core.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)
static void feed(mga_t* a, float x, float y, float z, const float rest[3], int n, int quiet) { for (int i = 0; i < n; i++) mga_update(a, x, y, z, rest, quiet); }

int main(void)
{
    const float rest[3] = {0.0f, 9.80665f, 0.0f};
    mga_t a = {0};
    feed(&a, 0.0f, 9.80665f, 0.0f, rest, 20, 0);
    CHECK(a.valid && a.roll_pm == 0 && a.pitch_pm == 0);                                       /* still: flat */
    feed(&a, 0.05f * 9.80665f, 9.8f, 0.0f, rest, 40, 0);
    CHECK(a.valid && a.roll_pm == 0);                                                           /* under the dead zone: flat */
    mga_t b = {0};
    feed(&b, 0.30f * 9.80665f, sqrtf(9.80665f * 9.80665f - (0.30f * 9.80665f) * (0.30f * 9.80665f)), 0.0f, rest, 60, 0);
    CHECK(b.valid && b.roll_pm > 450 && b.roll_pm < 550 && b.pitch_pm == 0);                    /* 0.30 g: half scale */
    mga_t c = {0};
    feed(&c, -0.45f * 9.80665f, 8.7f, 0.0f, rest, 60, 0);
    CHECK(c.roll_pm < -800);                                                                    /* a roll to the left reads negative */
    mga_t d = {0};
    feed(&d, 0.0f, 8.8f, -0.45f * 9.80665f, rest, 60, 0);
    CHECK(d.pitch_pm > 800 && d.roll_pm == 0);                                                  /* forward is toward -z and reads positive */
    mga_t f = {0};
    feed(&f, 0.0f, 18.0f, 0.0f, rest, 40, 0);
    CHECK(!f.valid && f.roll_pm == 0 && f.pitch_pm == 0);                                       /* carried or shaken: no reading */
    mga_t g2 = {0};
    feed(&g2, 0.4f * 9.80665f, 8.9f, 0.0f, rest, 40, 1);
    CHECK(!g2.valid && g2.roll_pm == 0);                                                        /* the quiet time after a shake: no reading */
    mga_t h = {0};
    feed(&h, 0.0f, 9.80665f, 0.0f, rest, 20, 0);
    mga_update(&h, 0.6f * 9.80665f, 7.8f, 0.0f, rest, 0);
    CHECK(h.roll_pm < 700);                                                                     /* one sample does not jump to the end */
    /* the packed word: every value from -1000 to 1000 on both axes comes back, and an invalid reading is the zero word */
    for (int r = -1000; r <= 1000; r += 37) {
        for (int p = -1000; p <= 1000; p += 41) {
            mga_t t = {0};
            t.valid = 1; t.roll_pm = r; t.pitch_pm = p;
            int rr = 77, pp = 77;
            CHECK(mga_unpack(mga_pack(&t), &rr, &pp) == 1 && rr == r && pp == p);
        }
    }
    mga_t inv = {0};
    inv.roll_pm = 500;
    int rr = 5, pp = 5;
    CHECK(mga_pack(&inv) == 0u && mga_unpack(0u, &rr, &pp) == 0 && rr == 0 && pp == 0);
    mga_t ex = {0};
    ex.valid = 1; ex.roll_pm = 1000; ex.pitch_pm = -1000;
    CHECK(mga_unpack(mga_pack(&ex), &rr, &pp) == 1 && rr == 1000 && pp == -1000);               /* the ends fit in 12 bits */
    /* a lean held for 3 s reaches the end, flat stops it again in under half a second */
    mga_t k = {0};
    feed(&k, 0.0f, 9.80665f, 0.0f, rest, 10, 0);
    feed(&k, 0.55f * 9.80665f, 8.2f, 0.0f, rest, 150, 0);
    CHECK(k.roll_pm == 1000);
    feed(&k, 0.0f, 9.80665f, 0.0f, rest, 25, 0);
    CHECK(k.roll_pm == 0);
    printf(fails ? "accel_analog_core_test FAILED\n" : "accel_analog_core_test ok\n");
    return fails ? 1 : 0;
}
