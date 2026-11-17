/* Prints the face model of maipai_look_core.h as JSON (patch V10), for the preview of the settings page.
 *   look_shapes_dump table      the style rows, the emotion rows and the pose targets: host/maipai_body/face_table.json is this output
 *   look_shapes_dump scenarios  inputs and the shapes the core makes of them: the parity test feeds the same inputs to the page's JavaScript
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> look_shapes_dump.c -lm */
#include <stdio.h>
#include <string.h>

#include "maipai_look_core.h"

static const char* EMO[ML_COUNT] = {"neutral", "happy", "angry", "sad", "doubt", "sleepy", "surprised", "tired", "closing", "sleeping", "love", "content"};
static const char* TINT[5] = {"", "red", "blue", "pink", "dim"};

static void f(float v) { printf("%.4f", (double)v); }

static void table(void)
{
    printf("{\n \"zone_cy\": %d,\n \"zone_eye_top\": %d,\n \"emotions\": [", ML_ZONE_CENTER_Y, ML_ZONE_EYE_TOP);
    for (int e = 0; e < ML_COUNT; e++) printf("%s\"%s\"", e ? ", " : "", EMO[e]);
    printf("],\n \"styles\": [\n");
    for (int i = 0; i < ML_STYLE_COUNT; i++) {
        const ml_style_t* s = ml_style(i);
        printf("  {\"name\": \"%s\", \"eye_d\": %d, \"eye_x\": %d, \"eye_y\": %d, \"mouth_y\": %d, \"mouth\": %d, \"mouth_w\": %d, \"mouth_t\": %d, \"stock\": %d, \"ew\": %d, \"eh\": %d, \"r_pct\": %d, \"pupil\": %d, \"brows\": %d, \"drift\": %d, \"blw\": %d}%s\n",
               s->name, s->eye_d, s->eye_x, s->eye_y, s->mouth_y, s->mouth, s->mouth_w, s->mouth_t, s->stock_look, s->ew, s->eh, s->r_pct, s->pupil, s->brows, s->drift, s->blw, i + 1 < ML_STYLE_COUNT ? "," : "");
    }
    printf(" ],\n \"looks\": [\n"); /* the stock skin's own looks, as shipped, and the tint of every emotion */
    for (int e = 0; e < ML_COUNT; e++) {
        const ml_look_t l = ml_look(ML_STYLE_STOCK, e), g = ML_LOOKS[e];
        printf("  {\"stock\": {\"lid\": "); f(l.lid); printf(", \"from_bottom\": %d, \"tilt\": ", l.from_bottom); f(l.tilt); printf(", \"scale\": "); f(l.scale);
        printf(", \"mouth\": [");
        const float m[6] = {l.mouth.w, l.mouth.bend, l.mouth.t, l.mouth.wob, l.mouth.split, l.mouth.tilt};
        for (int k = 0; k < 6; k++) { if (k) printf(", "); f(m[k]); }
        printf("]}, \"tint\": \"%s\"}%s\n", TINT[g.tint], e + 1 < ML_COUNT ? "," : "");
    }
    printf(" ],\n \"drift_scale\": [");
    for (int e = 0; e < ML_COUNT; e++) { if (e) printf(", "); f(ml_pose_drift_scale(e)); }
    printf("],\n \"pose\": {\n");
    for (int i = 0; i < ML_STYLE_COUNT; i++) {
        const ml_style_t* s = ml_style(i);
        printf("  \"%s\": {\n", s->name);
        for (int e = 0; e < ML_COUNT; e++) {
            for (int th = 0; th < 2; th++) {
                float t[MP_N];
                ml_pose_target(s, e, th, t);
                printf("   \"%s%s\": [", EMO[e], th ? "+thinking" : "");
                for (int k = 0; k < MP_N; k++) { if (k) printf(", "); f(t[k]); }
                printf("]%s\n", (e + 1 < ML_COUNT || !th) ? "," : "");
            }
        }
        printf("  }%s\n", i + 1 < ML_STYLE_COUNT ? "," : "");
    }
    printf(" }\n}\n");
}

static void shapes(const ml_shape_t* s, int n)
{
    printf("[");
    for (int i = 0; i < n; i++) {
        printf("%s[%d, %d, %d", i ? ", " : "", s[i].kind, s[i].col, s[i].opa);
        for (int k = 0; k < 8; k++) { printf(", "); f(s[i].v[k]); }
        printf("]");
    }
    printf("]");
}

static int first = 1;
static void rec(void) { printf("%s\n ", first ? "" : ","); first = 0; }

static void scenarios(void)
{
    printf("[");
    ml_shape_t out[ML_MAX_SHAPES];
    const float lids[] = {0.0f, 0.16f, 0.3f, 0.55f};
    const float slants[] = {-0.55f, 0.0f, 0.85f};
    const float gaze[][2] = {{0, 0}, {8, -4}, {-12, 6}, {12, -10}, {30, 20}};
    for (int si = 0; si < ML_STYLE_COUNT; si++) {
        const ml_style_t* st = ml_style(si);
        if (st->stock_look) continue;
        for (int side = -1; side <= 1; side += 2) {
            for (unsigned a = 0; a < 4; a++) for (unsigned b = 0; b < 3; b++) for (unsigned g = 0; g < 5; g++) for (int bl = 0; bl < 2; bl++) {
                ml_eye_in_t in;
                memset(&in, 0, sizeof(in));
                in.st = st; in.side = side; in.ew = (float)st->ew * (side > 0 ? 0.88f : 1.0f); in.eh = (float)st->eh * (side > 0 ? 0.88f : 1.0f);
                in.lid = lids[a]; in.slant = slants[b]; in.cheek = (g == 1) ? 1.0f : 0.0f; in.blink = bl ? 0.5f : 0.0f; in.beat = 1.0f;
                in.gx = gaze[g][0]; in.gy = gaze[g][1]; in.voice = (g == 2) ? 0.7f : 0.0f;
                const int n = ml_eye_shapes(&in, out, ML_MAX_SHAPES);
                rec();
                printf("{\"k\": \"eye\", \"style\": %d, \"in\": {\"side\": %d, \"ew\": ", si, side); f(in.ew); printf(", \"eh\": "); f(in.eh);
                printf(", \"lid\": "); f(in.lid); printf(", \"slant\": "); f(in.slant); printf(", \"cheek\": "); f(in.cheek); printf(", \"blink\": "); f(in.blink);
                printf(", \"heart\": 0, \"beat\": 1, \"closed\": 0, \"gx\": "); f(in.gx); printf(", \"gy\": "); f(in.gy); printf(", \"voice\": "); f(in.voice);
                printf("}, \"shapes\": "); shapes(out, n); printf("}");
            }
            for (int k = 0; k < 3; k++) { /* hearts and closed arcs */
                ml_eye_in_t in;
                memset(&in, 0, sizeof(in));
                in.st = st; in.side = side; in.ew = (float)st->ew; in.eh = (float)st->eh; in.beat = 1.0f + 0.07f * (float)k;
                in.heart = k == 0 ? 1.0f : 0.0f; in.closed = k == 1 ? 1.0f : (k == 2 ? 0.5f : 0.0f);
                const int n = ml_eye_shapes(&in, out, ML_MAX_SHAPES);
                rec();
                printf("{\"k\": \"eye\", \"style\": %d, \"in\": {\"side\": %d, \"ew\": ", si, side); f(in.ew); printf(", \"eh\": "); f(in.eh);
                printf(", \"lid\": 0, \"slant\": 0, \"cheek\": 0, \"blink\": 0, \"heart\": "); f(in.heart); printf(", \"beat\": "); f(in.beat);
                printf(", \"closed\": "); f(in.closed); printf(", \"gx\": 0, \"gy\": 0, \"voice\": 0}, \"shapes\": "); shapes(out, n); printf("}");
            }
            for (int bt = 0; bt < 4; bt++) { /* brows */
                const float on = bt == 0 ? 0.0f : 1.0f, tilt = bt == 2 ? -1.0f : 1.0f, lift = bt == 3 ? 12.0f : -2.0f;
                const int n = ml_brow_shapes(st, side, (float)st->ew, (float)st->eh, side > 0 ? 0.62f : 1.0f, 3.0f, side > 0 ? -12.0f : 0.0f, side > 0 ? 12.0f : 0.0f, on, lift, tilt, out, ML_MAX_SHAPES);
                rec();
                printf("{\"k\": \"brow\", \"style\": %d, \"in\": {\"side\": %d, \"ew\": ", si, side); f((float)st->ew); printf(", \"eh\": "); f((float)st->eh);
                printf(", \"es\": "); f(side > 0 ? 0.62f : 1.0f); printf(", \"gx\": 3, \"rlift\": "); f(side > 0 ? -12.0f : 0.0f);
                printf(", \"br\": "); f(side > 0 ? 12.0f : 0.0f); printf(", \"on\": "); f(on); printf(", \"blift\": "); f(lift); printf(", \"btilt\": "); f(tilt);
                printf("}, \"shapes\": "); shapes(out, n); printf("}");
            }
        }
        /* the mouth (patch V12): the target of every emotion under every rule (calm, speaking at three opens, a yawn time), eased one frame, as shapes */
        const float opens[] = {0.0f, 0.0f, 0.3f, 0.9f};
        const int speak[] = {0, 1, 1, 1};
        const uint32_t times[] = {0u, 1800u};
        for (int e = 0; e < ML_COUNT; e++) for (int sealed = 0; sealed < 2; sealed++) for (unsigned o = 0; o < 4; o++) for (unsigned ti = 0; ti < 2; ti++) {
            const ml_mouth_t base = ML_LOOKS[ML_NEUTRAL].mouth;
            const ml_mouth_t target = ml_mouth_target(st, e, sealed, speak[o], opens[o], times[ti]);
            const ml_mouth_t cur = ml_mouth_follow(base, target, 33.0f, ml_mouth_tau(&base, &target, speak[o], opens[o]));
            const float on = (e + (int)o) % 5 == 4 ? 0.0f : 1.0f; /* some rows are hidden: the thinking dots take the mouth's place */
            const int n = ml_mouth_shapes(&cur, 0.3f, on, out, ML_MAX_SHAPES);
            const float tv[6] = {target.w, target.bend, target.t, target.wob, target.split, target.tilt};
            rec();
            printf("{\"k\": \"mouth\", \"style\": %d, \"in\": {\"emo\": %d, \"sealed\": %d, \"speaking\": %d, \"open\": ", si, e, sealed, speak[o]); f(opens[o]);
            printf(", \"ms\": %u, \"phase\": 0.3000, \"on\": ", (unsigned)times[ti]); f(on); printf("}, \"target\": [");
            for (int k = 0; k < 6; k++) { if (k) printf(", "); f(tv[k]); }
            printf("], \"shapes\": "); shapes(out, n); printf("}");
        }
    }
    for (int si = 0; si < ML_STYLE_COUNT; si++) for (uint32_t t = 0; t < 1200; t += 150) for (int i = 0; i < ML_DOT_COUNT; i++) {
        const ml_dot_t d = ml_dot(ml_style(si), i, t);
        rec();
        printf("{\"k\": \"dot\", \"style\": %d, \"i\": %d, \"t\": %u, \"dot\": [%d, %d, %d, %d]}", si, i, (unsigned)t, d.x, d.y, d.d, d.opa);
    }
    for (uint32_t t = 0; t < 200; t += 10) {
        rec();
        printf("{\"k\": \"blink\", \"t\": %u, \"v\": ", (unsigned)t); f(ml_blink_factor(t)); printf("}");
    }
    { /* the spring: neutral to surprised and back, 33 ms steps */
        float a[MP_N], b[MP_N];
        ml_pose_target(ml_style(0), ML_NEUTRAL, 0, a);
        ml_pose_target(ml_style(0), ML_SURPRISED, 0, b);
        ml_spring_t sp;
        ml_spring_snap(&sp, a);
        for (int i = 0; i < 40; i++) {
            ml_spring_step(&sp, i < 20 ? b : a, 0.033f);
            if (i % 5 == 4) {
                rec();
                printf("{\"k\": \"spring\", \"step\": %d, \"x\": [", i);
                for (int k = 0; k < MP_N; k++) { if (k) printf(", "); f(sp.x[k]); }
                printf("]}");
            }
        }
    }
    printf("\n]\n");
}

int main(int argc, char** argv)
{
    if (argc > 1 && strcmp(argv[1], "table") == 0) table();
    else if (argc > 1 && strcmp(argv[1], "scenarios") == 0) scenarios();
    else { fprintf(stderr, "usage: look_shapes_dump table|scenarios\n"); return 2; }
    return 0;
}
