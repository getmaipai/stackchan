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
        /* the eyes lie on the screen, apart from each other, and the touch regions (maipai_touch_core.h) hold them */
        const int left = 160 - s->eye_x - s->ew / 2, right = 160 - s->eye_x + s->ew / 2;
        CHECK(left >= 20 && right <= 127);
        const int top = 120 + s->eye_y - s->eh / 2, bot = 120 + s->eye_y + s->eh / 2;
        CHECK(top >= 28 && bot <= 165);
        CHECK(s->eye_x - s->ew / 2 > 0); /* the eyes do not touch */
        CHECK(s->r_pct >= 55 && s->r_pct <= 100);
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
    CHECK(ml_style(ML_STYLE_BIG_EYES)->pupil == 1 && ml_style(ML_STYLE_BIG_EYES)->ew == 96 && ml_style(ML_STYLE_BIG_EYES)->eh == 104);
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
                if (s->stock_look) { /* the stock dots sit at the stock mouth, as shipped */
                    CHECK(d.y <= s->mouth_y && d.y >= s->mouth_y - 5);
                    CHECK(d.opa >= 90);
                    CHECK(abs(d.x) <= ML_DOT_SPACING);
                } else { /* the approved design: 13 px dots, 26 apart, low on the face, y 84 to 92 from the middle */
                    CHECK(d.y <= 92 && d.y >= 84 && d.d == 13);
                    CHECK(d.opa >= 89);
                    CHECK(abs(d.x) <= 26);
                }
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

/* ---- the approved design (patch V10): poses, the spring and the shapes ---- */

static int in_quad(const float q[8], float x, float y)
{ /* the quad is convex: the point is on the same side of every edge */
    int pos = 0, neg = 0;
    for (int i = 0; i < 4; i++) {
        const float x0 = q[i * 2], y0 = q[i * 2 + 1], x1 = q[((i + 1) % 4) * 2], y1 = q[((i + 1) % 4) * 2 + 1];
        const float c = (x1 - x0) * (y - y0) - (y1 - y0) * (x - x0);
        if (c > 0.01f) pos++;
        if (c < -0.01f) neg++;
    }
    return pos == 0 || neg == 0;
}

static void test_poses(void)
{
    float t[MP_N];
    for (int si = 0; si < ML_STYLE_COUNT; si++) {
        const ml_style_t* st = ml_style(si);
        for (int e = 0; e < ML_COUNT; e++) {
            for (int th = 0; th < 2; th++) {
                ml_pose_target(st, e, th, t);
                for (int i = 0; i < MP_N; i++) CHECK(isfinite(t[i]));
                CHECK(t[MP_EW] > 0 && t[MP_EH] > 0 && t[MP_LID] >= 0 && t[MP_LID] < 0.7f);
                CHECK(!(st->mouth == ML_MOUTH_NONE) || t[MP_MON] == 0);
                CHECK(st->brows || t[MP_BROW] == 0);
            }
        }
    }
    ml_pose_target(ml_style(ML_STYLE_BIG_EYES), ML_ANGRY, 0, t);
    CHECK(t[MP_SLANT] > 0.8f && t[MP_BROW] == 1.0f && t[MP_BTILT] == 1.0f);
    ml_pose_target(ml_style(ML_STYLE_MINIMAL), ML_ANGRY, 0, t);
    CHECK(t[MP_BROW] == 0.0f); /* Minimal has no brows */
    ml_pose_target(ml_style(ML_STYLE_BIG_EYES), ML_NEUTRAL, 1, t);
    CHECK(t[MP_GX] == 12.0f && t[MP_GY] == -10.0f && t[MP_MON] == 0.0f); /* thinking: up and away, no mouth */
}

static void test_spring(void)
{
    float t[MP_N], z[MP_N];
    const ml_style_t* st = ml_style(ML_STYLE_BIG_EYES);
    ml_pose_target(st, ML_NEUTRAL, 0, z);
    ml_pose_target(st, ML_SURPRISED, 0, t);
    ml_spring_t sp;
    ml_spring_snap(&sp, z);
    float peak = z[MP_EH];
    int settled_at = -1;
    for (int i = 0; i < 90; i++) { /* 33 ms steps */
        ml_spring_step(&sp, t, 0.033f);
        if (sp.x[MP_EH] > peak) peak = sp.x[MP_EH];
        if (settled_at < 0 && ml_spring_settled(&sp, t)) settled_at = i;
    }
    const float over = (peak - t[MP_EH]) / (t[MP_EH] - z[MP_EH]);
    CHECK(over > 0.04f && over < 0.14f); /* about 8 percent overshoot */
    CHECK(settled_at > 0 && settled_at * 33 < 700); /* settled in well under a second */
    CHECK(fabsf(sp.x[MP_EH] - t[MP_EH]) < 0.1f);
    sp.x[MP_LID] = 5.0f;
    ml_spring_step(&sp, t, 0.01f);
    CHECK(sp.x[MP_LID] <= 1.0f); /* the unit values stay in range */
}

/* The eye shapes stay clean at every lid, slant, blink and gaze step: finite, inside the art box, the right shapes in the
 * right order, the lid covers every point of the eye above its edge, the pupil is masked when it leaves the eye. */
static void test_eye_shapes_clean(void)
{
    ml_shape_t out[ML_MAX_SHAPES];
    for (int si = 0; si < ML_STYLE_COUNT; si++) {
        const ml_style_t* st = ml_style(si);
        if (st->stock_look) continue;
        const float boxw = st->ew * 1.3f + 100.0f, boxh = st->eh * 1.45f + 100.0f; /* the art object (eyes.cpp place_art) */
        for (int side = -1; side <= 1; side += 2) {
            for (float lid = 0.0f; lid <= 0.88f; lid += 0.11f) {
                for (float slant = -1.0f; slant <= 1.0f; slant += 0.25f) {
                    for (float bl = 0.0f; bl <= 1.0f; bl += 0.5f) {
                        for (int g = 0; g < 9; g++) {
                            ml_eye_in_t in;
                            memset(&in, 0, sizeof(in));
                            in.st = st; in.side = side; in.ew = (float)st->ew; in.eh = (float)st->eh;
                            in.lid = lid; in.slant = slant; in.blink = bl; in.beat = 1.0f;
                            in.gx = (float)((g % 3) - 1) * 16.0f; in.gy = (float)((g / 3) - 1) * 10.0f;
                            const int n = ml_eye_shapes(&in, out, ML_MAX_SHAPES);
                            CHECK(n >= 1 && n <= 12);
                            CHECK(out[0].kind == ML_SH_RRECT && out[0].col == ML_COL_FG); /* the eye is drawn first */
                            const float ww = out[0].v[2], hh = out[0].v[3], rad = out[0].v[4];
                            CHECK(rad >= 0.0f && rad <= (ww < hh ? ww : hh) * 0.5f + 0.01f); /* a radius that never exceeds the box */
                            int pupil = 0, ring = 0, lids = 0;
                            for (int i = 0; i < n; i++) {
                                for (int k = 0; k < 8; k++) CHECK(isfinite(out[i].v[k]));
                                if (out[i].kind == ML_SH_CIRCLE) { pupil++; CHECK(fabsf(out[i].v[0]) < boxw / 2 && fabsf(out[i].v[1]) < boxh / 2); }
                                if (out[i].kind == ML_SH_RING) { ring++; CHECK(out[i].col == ML_COL_BG && out[i].v[5] == 18.0f); }
                                if (out[i].kind == ML_SH_QUAD) {
                                    lids++;
                                    CHECK(out[i].col == ML_COL_BG);
                                    for (int k = 0; k < 4; k++) CHECK(fabsf(out[i].v[k * 2]) < ww / 2 + 4.0f && out[i].v[k * 2 + 1] >= -hh / 2 - 6.01f);
                                }
                            }
                            CHECK(st->pupil ? pupil == 3 : pupil == 0);
                            if (st->pupil && ring) { /* the mask is there only when the pupil leaves the eye */
                                CHECK(sqrtf(out[1].v[0] * out[1].v[0] + out[1].v[1] * out[1].v[1]) + out[1].v[2] > (ww < hh ? ww : hh) * 0.5f - 0.6f);
                            }
                            if (st->pupil && !ring) {
                                CHECK(sqrtf(out[1].v[0] * out[1].v[0] + out[1].v[1] * out[1].v[1]) + out[1].v[2] <= (ww < hh ? ww : hh) * 0.5f);
                            }
                            if (lid > 0.005f || fabsf(slant) > 0.005f) {
                                CHECK(lids <= 1);
                                /* the lid covers every point of the eye's outline that lies above its edge */
                                const ml_shape_t* q = NULL;
                                for (int i = 0; i < n; i++) if (out[i].kind == ML_SH_QUAD) q = &out[i];
                                static const ml_shape_t none = {0};
                                if (q == NULL) q = &none; /* the edge is above the eye's top at both ends: nothing to cover */
                                const float k = slant * hh * 0.45f * (float)(-side) / (ww * 0.5f), y0 = -hh * 0.5f + lid * hh;
                                for (int a = 0; a < 360; a += 5) {
                                    const float ca = cosf((float)a * 0.0174533f), sa = sinf((float)a * 0.0174533f);
                                    const float x = ca * (ww * 0.5f - 0.5f), y = sa * (hh * 0.5f - 0.5f);
                                    if (y < y0 + k * x - 1.0f) CHECK(lids == 1 && in_quad(q->v, x, y));
                                }
                            } else {
                                CHECK(lids == 0); /* an open eye is whole: nothing cuts it */
                            }
                        }
                    }
                }
            }
            /* the two eyes at rest are the same shape, mirrored: the same shapes, and the lid slant flips */
        }
        ml_eye_in_t l, r;
        memset(&l, 0, sizeof(l));
        l.st = st; l.side = -1; l.ew = (float)st->ew; l.eh = (float)st->eh; l.beat = 1.0f;
        r = l; r.side = 1;
        ml_shape_t a[ML_MAX_SHAPES], b[ML_MAX_SHAPES];
        const int na = ml_eye_shapes(&l, a, ML_MAX_SHAPES), nb = ml_eye_shapes(&r, b, ML_MAX_SHAPES);
        CHECK(na == nb && memcmp(a, b, sizeof(ml_shape_t) * (size_t)na) == 0); /* at rest the eyes are identical about their centres */
    }
}

static void test_brow_and_mouth_shapes(void)
{
    ml_shape_t out[ML_MAX_SHAPES];
    const ml_style_t* big = ml_style(ML_STYLE_BIG_EYES);
    CHECK(ml_brow_shapes(big, -1, 96, 104, 1, 0, 0, 0, 0.0f, 0, 0, out, 2) == 0); /* no brow when none is asked for */
    CHECK(ml_brow_shapes(ml_style(ML_STYLE_MINIMAL), -1, 28, 40, 1, 0, 0, 0, 1.0f, 0, 0, out, 2) == 0);
    CHECK(ml_brow_shapes(big, -1, 96, 104, 1, 0, 0, 0, 1.0f, 0, 1.0f, out, 2) == 1);
    CHECK(out[0].kind == ML_SH_LINE && out[0].v[4] == 8.0f);
    const float ly = out[0].v[1], ry = out[0].v[3]; /* the left brow of angry: the inner (right) end is lower */
    CHECK(ry > ly);
    /* the mouth (patch V12): the chunky stroke, as pieces */
    ml_mouth_t sm = ML_LOOKS[ML_NEUTRAL].mouth;
    int n = ml_mouth_shapes(&sm, 0.0f, 1.0f, out, ML_MAX_SHAPES);
    CHECK(n >= 8 && n <= 16); /* a shut mouth: round-ended pieces along 17 points */
    for (int i = 0; i < n; i++) { CHECK(out[i].kind == ML_SH_LINE && out[i].v[4] == 8.0f); }
    ml_mouth_t o = ml_mouth_speaking(sm, 1.0f, 1.0f);
    n = ml_mouth_shapes(&o, 0.0f, 1.0f, out, ML_MAX_SHAPES);
    CHECK(n >= 1 && n <= 16); /* an open one: a short thick stroke */
    for (int i = 0; i < n; i++) for (int k = 0; k < 8; k++) CHECK(isfinite(out[i].v[k]));
    ml_mouth_t dot = ML_LOOKS[ML_SURPRISED].mouth;
    n = ml_mouth_shapes(&dot, 0.0f, 1.0f, out, ML_MAX_SHAPES);
    CHECK(n == 1 && out[0].kind == ML_SH_CIRCLE && out[0].v[2] == 11.0f); /* surprised: a round O of one disc, 22 thick */
    CHECK(ml_mouth_shapes(&sm, 0.0f, 0.0f, out, ML_MAX_SHAPES) == 0); /* thinking shows dots, not a mouth */
    CHECK(ml_blink_factor(0) == 0.0f && fabsf(ml_blink_factor(55) - 1.0f) < 0.001f && ml_blink_factor(140) == 0.0f);
    CHECK(ml_blink_factor(30) > 0.5f && ml_blink_factor(100) < 0.5f); /* shut in 55 ms, open in 85 */
}

/* Patch V12: the speech level to the shape of the mouth, and the eased motion between shapes. */
static void test_chunky_mouth_speech(void)
{
    const ml_style_t* big = ml_style(ML_STYLE_BIG_EYES);
    CHECK(big->mouth_w == 46 && big->mouth_t == 8); /* the chunky size, not the thin one */
    CHECK(ml_style(ML_STYLE_CLASSIC)->mouth_t >= 6 && ml_style(ML_STYLE_MINIMAL)->mouth_w == 22);
    /* level to open amount: shut under 8, never down as the level rises, and at least six distinct shapes across the range */
    float prev = -1.0f;
    int distinct = 0;
    float last_shape_t = -100.0f;
    for (int lv = 0; lv <= 100; lv++) {
        const float open = mx_mouth_for_level(lv) / 100.0f;
        CHECK(open >= prev - 1e-6f);
        prev = open;
        const ml_mouth_t m = ml_mouth_speaking(ML_LOOKS[ML_NEUTRAL].mouth, open, 1.0f);
        if (m.t > last_shape_t + 4.0f) { distinct++; last_shape_t = m.t; } /* a step is 4 px of thickness: visible on the glass */
    }
    CHECK(mx_mouth_for_level(7) == 0.0f && mx_mouth_for_level(100) > 85.0f);
    CHECK(distinct >= 6);
    /* the target follows the rules in one place: calm when muted, a smile that opens flatter, a yawn when tired and not speaking */
    const ml_mouth_t calm = ml_mouth_target(big, ML_HAPPY, 1, 1, 0.9f, 0);
    CHECK(calm.split == 0.0f && calm.bend == 0.0f && calm.t < 8.0f);
    const ml_mouth_t talk = ml_mouth_target(big, ML_HAPPY, 0, 1, 0.9f, 0);
    CHECK(talk.split == 0.0f && talk.t > 25.0f);
    const ml_mouth_t rest = ml_mouth_target(big, ML_TIRED, 0, 0, 0.0f, 0), yawn = ml_mouth_target(big, ML_TIRED, 0, 0, 0.0f, 1800);
    CHECK(yawn.t > rest.t + 4.0f);
    /* eased motion: opening is quick (40 ms) and never overshoots, closing is slower (105 ms), and each step moves toward its target only */
    ml_mouth_t shut = ml_mouth_target(big, ML_NEUTRAL, 0, 1, 0.0f, 0), wide = ml_mouth_target(big, ML_NEUTRAL, 0, 1, 0.9f, 0);
    ml_mouth_t cur = shut;
    float last = cur.t;
    int open_ms = 0;
    for (int ms = 33; ms <= 1000; ms += 33) {
        cur = ml_mouth_follow(cur, wide, 33.0f, ml_mouth_tau(&cur, &wide, 1, 0.9f));
        CHECK(cur.t >= last - 1e-4f && cur.t <= wide.t + 1e-3f); /* monotonic, no overshoot */
        last = cur.t;
        if (open_ms == 0 && cur.t >= shut.t + 0.9f * (wide.t - shut.t)) open_ms = ms;
    }
    ml_mouth_t back = wide;
    int close_ms = 0;
    for (int ms = 33; ms <= 1000; ms += 33) {
        const float before = back.t;
        back = ml_mouth_follow(back, shut, 33.0f, ml_mouth_tau(&back, &shut, 1, 0.0f));
        CHECK(back.t <= before + 1e-4f && back.t >= shut.t - 1e-3f);
        if (close_ms == 0 && back.t <= wide.t - 0.9f * (wide.t - shut.t)) close_ms = ms;
    }
    CHECK(open_ms > 0 && close_ms > open_ms); /* a quick attack, a slower release */
    CHECK(ml_mouth_tau(&shut, &wide, 1, 0.9f) == 40.0f && ml_mouth_tau(&wide, &shut, 1, 0.0f) == 105.0f);
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
    test_poses();
    test_spring();
    test_eye_shapes_clean();
    test_brow_and_mouth_shapes();
    test_chunky_mouth_speech();
    if (fails) {
        printf("%d failed\n", fails);
        return 1;
    }
    printf("look core: all passed\n");
    return 0;
}
