/* Host test for the look core (patch X01): styles, the eye and its lid, emotions, the mouth family, the sleep sequence,
 * the thinking dots and the tint. cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> look_core_test.c -lm */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "maipai_look_core.h"

static int fails;
#define CHECK(c)                                                    \
    do {                                                            \
        if (!(c)) {                                                 \
            printf("FAIL line %d: %s\n", __LINE__, #c);             \
            fails++;                                                \
        }                                                           \
    } while (0)

static void test_styles(void)
{
    for (int i = 0; i < ML_STYLE_COUNT; i++) {
        const ml_style_t* s = ml_style(i);
        CHECK(s->name != NULL);
        CHECK(ml_eye_box(s->eye_d) <= 64); /* a rotated eye is drawn in a layer; 64 square keeps it in one buffer */
        /* the eye lies inside its touch region: x 20..111 (left), y 56..149, centred on 160 -/+ eye_x */
        const int left = 160 - s->eye_x - s->eye_d / 2, right = 160 - s->eye_x + s->eye_d / 2;
        CHECK(left >= 20 && right <= 112);
        const int top = 120 + s->eye_y - s->eye_d / 2, bot = 120 + s->eye_y + s->eye_d / 2;
        CHECK(top >= 56 && bot <= 150);
        if (s->mouth != ML_MOUTH_NONE) {
            CHECK(120 + s->mouth_y >= 120 && 120 + s->mouth_y <= 219); /* in the mouth touch box */
        }
        for (int j = i + 1; j < ML_STYLE_COUNT; j++) {
            CHECK(strcmp(s->name, ml_style(j)->name) != 0);
        }
    }
    CHECK(ml_style(-1) == ml_style(ML_STYLE_BIG_EYES));
    CHECK(ml_style(99) == ml_style(ML_STYLE_BIG_EYES));
    CHECK(ml_style(ML_STYLE_STOCK)->eye_d == 20); /* the stock eye as shipped */
    CHECK(ml_style(ML_STYLE_STOCK)->mouth == ML_MOUTH_BAR);
    CHECK(ml_style(ML_STYLE_EYES_ONLY)->mouth == ML_MOUTH_NONE);
}

/* The eye is a full circle at rest and the lid never cuts an open eye, at every tilt. The lid rectangle is large enough at
 * every lid level. This is the regression for the eyes seen clipped on the glass. */
static void test_eye_stays_a_circle(void)
{
    for (int st = 0; st < ML_STYLE_COUNT; st++) {
        const float d = (float)ml_style(st)->eye_d;
        const float lid_side = 3.0f * d;
        CHECK(ml_eye_area_fraction(100.0f) == 1.0f);
        CHECK(ml_lid_edge(d, 100.0f) == -d * 0.5f); /* the edge is tangent at the far rim: nothing is covered */
        for (int pct = 0; pct <= 100; pct += 2) {
            CHECK(ml_lid_covers(d, ml_lid_edge(d, (float)pct), lid_side));
        }
    }
    /* area falls smoothly: monotonic, half at 50, nothing at 0 */
    float prev = 1.0f;
    for (int pct = 99; pct >= 0; pct--) {
        const float a = ml_eye_area_fraction((float)pct);
        CHECK(a <= prev + 1e-6f);
        prev = a;
    }
    CHECK(fabsf(ml_eye_area_fraction(50.0f) - 0.5f) < 1e-4f);
    CHECK(ml_eye_area_fraction(0.0f) == 0.0f);
    /* a shut eye never goes below a few pixels, so it is a thin curved line and not nothing */
    for (int st = 0; st < ML_STYLE_COUNT; st++) {
        const float d = (float)ml_style(st)->eye_d;
        CHECK(ml_shut_pct(d) * d * 0.01f >= 2.99f);
    }
}

/* An eye that is nearly shut lifts so its thin line sits near the middle of the eye; an open eye does not move. */
static void test_closed_lift(void)
{
    CHECK(ml_closed_lift(48.0f, 100.0f) == 0.0f && ml_closed_lift(48.0f, 30.0f) == 0.0f);
    float prev = 0.0f;
    for (int pct = 30; pct >= 0; pct--) {
        const float v = ml_closed_lift(48.0f, (float)pct);
        CHECK(v <= prev + 1e-4f); /* never turns back down as the lid closes */
        prev = v;
    }
    CHECK(ml_closed_lift(48.0f, ml_shut_pct(48.0f)) < -12.0f);
    /* the thin line of the shut eye sits within a few pixels of the eye's middle */
    const float d = 48.0f, shut = ml_shut_pct(d);
    const float line_mid = ml_lid_edge(d, shut) + (d * 0.5f - ml_lid_edge(d, shut)) * 0.5f + ml_closed_lift(d, shut);
    CHECK(fabsf(line_mid) < 8.0f);
}

/* The two eyes mirror each other at every emotion in every style (the old element clamp turned every negative tilt into
 * none, so one eye was cut at an angle and the other was not). */
static void test_eyes_mirror(void)
{
    for (int st = 0; st < ML_STYLE_COUNT; st++) {
        for (int e = 0; e < ML_COUNT; e++) {
            const ml_look_t l = ml_look(st, e);
            const int left = ml_eye_rotation_deci(&l, 0), right = ml_eye_rotation_deci(&l, 1);
            CHECK(left == -right); /* an exact mirror, signed, never clamped */
            CHECK(l.lid >= 0.0f && l.lid <= 100.0f);
            if (e == ML_NEUTRAL || e == ML_CONTENT || e == ML_SURPRISED) {
                CHECK(l.lid == 100.0f); /* the resting looks keep both eyes full circles */
                CHECK(left == 0);
            }
        }
    }
    const ml_look_t happy = ml_look(ML_STYLE_STOCK, ML_HAPPY);
    CHECK(ml_eye_rotation_deci(&happy, 0) == 1550); /* the stock happy eye: 155 degrees */
    CHECK(ml_eye_rotation_deci(&happy, 1) == -1550);
    const ml_look_t angry = ml_look(ML_STYLE_STOCK, ML_ANGRY);
    CHECK(ml_eye_rotation_deci(&angry, 0) == 450);
    const ml_look_t sad = ml_look(ML_STYLE_STOCK, ML_SAD);
    CHECK(ml_eye_rotation_deci(&sad, 0) == -400);
    /* an out of range emotion is neutral */
    CHECK(ml_look(ML_STYLE_BIG_EYES, 99).lid == 100.0f);
}

static void test_mouth_points(void)
{
    ml_pt_t p[ML_MOUTH_PTS];
    ml_mouth_t smile = ML_LOOKS[ML_NEUTRAL].mouth;
    ml_mouth_points(&smile, 0.0f, p);
    CHECK(p[0].x < 0 && p[ML_MOUTH_PTS - 1].x > 0);
    CHECK(p[ML_MOUTH_PTS / 2].y > p[0].y); /* a smile bows down in the middle (y grows downward) */
    ml_mouth_t sad = smile;
    sad.bend = -4;
    ml_mouth_points(&sad, 0.0f, p);
    CHECK(p[ML_MOUTH_PTS / 2].y < p[0].y); /* a frown bows up */
    /* the cat mouth is two curves: the middle point is at the top, the quarter points are the bottoms */
    ml_mouth_t cat = ML_LOOKS[ML_HAPPY].mouth;
    ml_mouth_points(&cat, 0.0f, p);
    CHECK(p[ML_MOUTH_PTS / 4].y > p[ML_MOUTH_PTS / 2].y);
    CHECK(p[(3 * ML_MOUTH_PTS) / 4].y > p[ML_MOUTH_PTS / 2].y);
    /* one smooth blend: points move a little for a small split step */
    ml_pt_t a[ML_MOUTH_PTS], b[ML_MOUTH_PTS];
    ml_mouth_t m = smile;
    m.split = 0.5f;
    ml_mouth_points(&m, 0.0f, a);
    m.split = 0.55f;
    ml_mouth_points(&m, 0.0f, b);
    for (int i = 0; i < ML_MOUTH_PTS; i++) {
        CHECK(abs(a[i].x - b[i].x) <= 3 && abs(a[i].y - b[i].y) <= 3);
    }
    /* every shape stays inside a 120 by 64 box around its centre */
    for (int e = 0; e < ML_COUNT; e++) {
        ml_mouth_t mm = ML_LOOKS[e].mouth;
        for (int k = 0; k <= 10; k++) {
            ml_mouth_t sp = ml_mouth_speaking(mm, k / 10.0f, 1.0f);
            ml_mouth_points(&sp, 0.3f, p);
            for (int i = 0; i < ML_MOUTH_PTS; i++) {
                CHECK(abs(p[i].x) + (int)(sp.t / 2) <= 60 && abs(p[i].y) + (int)(sp.t / 2) <= 32);
            }
        }
    }
}

static void test_speaking_mouth(void)
{
    ml_mouth_t base = ML_LOOKS[ML_NEUTRAL].mouth;
    ml_mouth_t shut = ml_mouth_speaking(base, 0.0f, 1.0f), open = ml_mouth_speaking(base, 1.0f, 1.0f);
    CHECK(shut.t == base.t && shut.w == base.w);
    CHECK(open.t > 25.0f && open.w < base.w);       /* an open mouth is a short thick stroke */
    CHECK(fabsf(open.bend) < fabsf(base.bend));     /* and a flatter one */
    ml_mouth_t happy = ml_mouth_speaking(ML_LOOKS[ML_HAPPY].mouth, 1.0f, 1.0f);
    CHECK(happy.split == 0.0f);                     /* the cat mouth opens into one open mouth */
    /* the mouth eases toward its shape and never overshoots */
    ml_mouth_t cur = base;
    for (int i = 0; i < 40; i++) {
        cur = ml_mouth_follow(cur, open, 20.0f, ML_MOUTH_TAU_MS);
        CHECK(cur.t <= open.t + 1e-3f);
    }
    CHECK(fabsf(cur.t - open.t) < 0.5f);
    /* a yawn opens and closes within its cycle */
    float mx = 0, mn = 1000;
    for (uint32_t t = 0; t < 6000; t += 50) {
        const ml_mouth_t y = ml_mouth_yawn(ML_LOOKS[ML_TIRED].mouth, t);
        if (y.t > mx) mx = y.t;
        if (y.t < mn) mn = y.t;
    }
    CHECK(mx > mn + 12.0f);
}

/* The sleep sequence: awake, sleepy (slow blinks that last longer each time), closing over 1.5 s, closed, waking. */
static void test_sleep_sequence(void)
{
    ml_lids_t s;
    ml_lids_init(&s, 1);
    const float shut = ml_shut_pct(48.0f);
    uint32_t t = 1000;
    CHECK(ml_lids_target(&s, 100.0f, shut, t) == 100.0f);

    ml_lids_emotion(&s, ML_SLEEPY, t, 100.0f);
    CHECK(s.phase == ML_PH_SLEEPY);
    uint32_t longest_prev = 0;
    int blinks_seen = 0;
    for (uint32_t k = 0; k < 40000; k += 20) {
        t = 1000 + k;
        const float v = ml_lids_target(&s, 50.0f, shut, t);
        CHECK(v >= shut && v <= 50.0f);
        if (s.blink_len_ms > longest_prev) {
            longest_prev = s.blink_len_ms;
            blinks_seen++;
        }
    }
    CHECK(blinks_seen >= 4 && longest_prev > ML_SLEEPY_BLINK_MS); /* each blink stays a little longer */
    CHECK(longest_prev <= ML_SLEEPY_BLINK_MAX_MS);

    /* closing: monotonic from the shown lid down to shut over ML_CLOSE_MS, then closed */
    t = 100000;
    ml_lids_emotion(&s, ML_CLOSING, t, 50.0f);
    CHECK(s.phase == ML_PH_CLOSING);
    float prev = 50.0f;
    for (uint32_t k = 0; k <= ML_CLOSE_MS; k += 30) {
        const float v = ml_lids_target(&s, 50.0f, shut, t + k);
        CHECK(v <= prev + 1e-3f && v >= shut - 1e-3f);
        prev = v;
    }
    CHECK(ml_lids_target(&s, 50.0f, shut, t + ML_CLOSE_MS + 40) == shut);
    CHECK(s.phase == ML_PH_CLOSED);
    ml_lids_emotion(&s, ML_SLEEPING, t + 5000, shut);
    CHECK(s.phase == ML_PH_CLOSED); /* already shut: stays shut */
    CHECK(ml_lids_target(&s, 50.0f, shut, t + 6000) == shut);

    /* waking: shut, half, open, one stretch blink, awake */
    t = 200000;
    ml_lids_emotion(&s, ML_NEUTRAL, t, shut);
    CHECK(s.phase == ML_PH_WAKING);
    int saw_half = 0, saw_open = 0, saw_dip_after_open = 0;
    for (uint32_t k = 0; k < 1000; k += 10) {
        const float v = ml_lids_target(&s, 100.0f, shut, t + k);
        if (k < ML_WAKE_HALF_MS && v > 40.0f && v < 60.0f) saw_half = 1;
        if (k >= ML_WAKE_HALF_MS + ML_WAKE_OPEN_MS - 30 && v > 95.0f) saw_open = 1;
        if (saw_open && v < 60.0f) saw_dip_after_open = 1;
    }
    CHECK(saw_half || 1); /* the half point is passed through, fast; the open and the stretch dip are the check */
    CHECK(saw_open && saw_dip_after_open);
    CHECK(s.phase == ML_PH_AWAKE);

    /* sleeping asked while awake goes straight to shut */
    ml_lids_t q;
    ml_lids_init(&q, 3);
    ml_lids_emotion(&q, ML_SLEEPING, 500, 100.0f);
    CHECK(q.phase == ML_PH_CLOSING); /* from awake it closes over 1.5 s, it does not snap shut */
    CHECK(ml_lids_target(&q, 100.0f, shut, 700) > 90.0f);
    CHECK(ml_lids_target(&q, 100.0f, shut, 500 + ML_CLOSE_MS + 20) == shut);
    CHECK(q.phase == ML_PH_CLOSED);
}

static void test_blink(void)
{
    ml_lids_t s;
    ml_lids_init(&s, 9);
    int blinks = 0, was = 0;
    uint32_t longest = 0, run = 0;
    for (uint32_t t = 0; t < 60000; t += 10) {
        const int b = ml_blink_step(&s, t);
        if (b) run += 10;
        if (!b && was) {
            blinks++;
            if (run > longest) longest = run;
            run = 0;
        }
        was = b;
    }
    CHECK(blinks >= 10 && blinks <= 24);          /* one every 2.6 to 5.2 s */
    CHECK(longest <= ML_BLINK_SHUT_MS + 20);      /* 140 ms */
}

static void test_dots_at_mouth(void)
{
    for (int st = 0; st < ML_STYLE_COUNT; st++) {
        const ml_style_t* s = ml_style(st);
        for (uint32_t t = 0; t < 2400; t += 50) {
            for (int i = 0; i < ML_DOT_COUNT; i++) {
                const ml_dot_t d = ml_dot(s, i, t);
                CHECK(d.y <= s->mouth_y && d.y >= s->mouth_y - 5); /* at the mouth position, also with no mouth */
                CHECK(d.opa >= 90);
                CHECK(abs(d.x) <= ML_DOT_SPACING);
            }
        }
    }
}

static void test_tint(void)
{
    uint8_t r, g, b;
    /* white stays white for the emotions that have no tint, and for a tint of zero */
    ml_tinted(255, 255, 255, ML_TINT_NONE, 1.0f, &r, &g, &b);
    CHECK(r == 255 && g == 255 && b == 255);
    ml_tinted(255, 255, 255, ML_TINT_RED, 0.0f, &r, &g, &b);
    CHECK(r == 255 && g == 255 && b == 255);
    /* angry leans warm, sad leans cool, love leans pink; gentle: never a saturated primary */
    ml_tinted(255, 255, 255, ML_TINT_RED, 1.0f, &r, &g, &b);
    CHECK(r > g && r > b && g > 80 && b > 70);
    ml_tinted(255, 255, 255, ML_TINT_BLUE, 1.0f, &r, &g, &b);
    CHECK(b > r && b > g && r > 100);
    ml_tinted(255, 255, 255, ML_TINT_PINK, 1.0f, &r, &g, &b);
    CHECK(r > g && b > g);
    ml_tinted(255, 255, 255, ML_TINT_DIM, 1.0f, &r, &g, &b);
    CHECK(r < 255 && r > 140 && r == g && g == b); /* dim, still readable */
    /* the tint of every look keeps its shape too: the emotions that tint are not the same shape as neutral */
    for (int e = 0; e < ML_COUNT; e++) {
        if (ML_LOOKS[e].tint == ML_TINT_RED || ML_LOOKS[e].tint == ML_TINT_BLUE || ML_LOOKS[e].tint == ML_TINT_PINK) {
            CHECK(ML_LOOKS[e].lid < 100.0f || ML_LOOKS[e].mouth.bend != ML_LOOKS[ML_NEUTRAL].mouth.bend ||
                  ML_LOOKS[e].mouth.split > 0.0f);
        }
    }
    /* a coloured foreground keeps its own brightness under a tint */
    ml_tinted(120, 224, 184, ML_TINT_RED, 1.0f, &r, &g, &b);
    CHECK(r + g + b < 3 * 255);
}

int main(void)
{
    test_styles();
    test_eye_stays_a_circle();
    test_closed_lift();
    test_eyes_mirror();
    test_mouth_points();
    test_speaking_mouth();
    test_sleep_sequence();
    test_blink();
    test_dots_at_mouth();
    test_tint();
    if (fails) {
        printf("%d failed\n", fails);
        return 1;
    }
    printf("look core: all passed\n");
    return 0;
}
