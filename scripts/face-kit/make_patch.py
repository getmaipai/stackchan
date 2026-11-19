#!/usr/bin/env python3
"""Builds firmware/patches/UXF01-face-style-recipes.patch from the reference tree: copies the three files it changes,
applies the edits below (each asserted to match exactly once) and writes a unified diff.
Usage: python3 scripts/face-kit/make_patch.py [--tree TREE]   (default ~/esp/stackchan-rebuild/main-ref)
Placement: host-side development tool; the patch it writes is a unit patch on branch ux/faces. Upstream: none."""
from __future__ import annotations

import argparse
import difflib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = ["firmware/main/hal/maipai_look_core.h", "firmware/main/stackchan/avatar/skins/default/default.cpp", "firmware/main/stackchan/avatar/skins/default/default.h"]
HEADER = """# Intent: Face styles as recipes (docs/plan/face-parts.md phases 1 and 2, owner request 2026-11-19): a style is 44 bytes of numbers that any unit reads, so the old styles (round, cat, robot, sleepy, retro pixel, heart eyes) and new ones (rubber hose, neon anime) are installable assets and cost nothing until installed. The look core gains one writable style row (ML_STYLE_RECIPE) that a recipe fills; four eye designs a recipe may ask for (pie eyes, a hollow neon ring with a glow, slit pupils, heart eyes); a lid floor (sleepy); and a short list of fixed decorations (cat ears and whiskers, a robot antenna and bolts, blush, a hose tuft, neon sparkles) drawn by one object that exists only while a recipe with decorations is active. The three base styles are unchanged and draw the same pixels.
# Placement: unit
# Upstream: firmware/main/hal/maipai_look_core.h and firmware/main/stackchan/avatar/skins/default/ (ours, patches X01, V10)
# Check after a flash: install a style asset with self.assets.install kind style and apply it; the face draws that look in every emotion and while speaking; remove it and the face goes back to the saved style; a bad recipe answers a plain sentence and changes nothing; the memory row (self.memory) is the same before and after with no recipe installed.
# Kconfig: none
# Memory cost: with no recipe active, one writable style row (about 70 bytes of internal RAM, built on first use) and no objects. An active recipe with decorations holds one LVGL object (about 160 bytes internal). Flash about 2 KB.

"""


def edit(text: str, old: str, new: str, count: int = 1) -> str:
    n = text.count(old)
    if n != count:
        raise SystemExit(f"edit expected {count} match(es), found {n}: {old[:70]!r}")
    return text.replace(old, new)


def edit_look(t: str) -> str:
    t = edit(t, "#define ML_STYLE_COUNT 5\n", """#define ML_STYLE_RECIPE 5 /* the one writable row: a recipe (ml_recipe_apply) fills it */
#define ML_STYLE_COUNT 6

/* Patch UXF01: the eye design a style asks for, and its fixed decorations. */
#define ML_LOOK_STD 0   /* the eye of the base styles */
#define ML_LOOK_PIE 1   /* a big dark pupil with a wedge cut out, the eye a tall oval */
#define ML_LOOK_NEON 2  /* a hollow ring with a soft glow, an iris and a spark */
#define ML_LOOK_SLIT 3  /* a vertical slit pupil */
#define ML_LOOK_HEART 4 /* the eye is a heart */
#define ML_LOOK_MAX 4
#define ML_X_NONE 0
#define ML_X_CAT 1    /* ears and whiskers */
#define ML_X_ROBOT 2  /* an antenna and two bolts */
#define ML_X_BLUSH 3  /* two soft cheeks */
#define ML_X_HOSE 4   /* soft cheeks and a three-hair tuft */
#define ML_X_NEON 5   /* four small sparkles */
#define ML_X_MAX 5
""")
    t = edit(t, "    uint8_t blw;\n} ml_style_t;", "    uint8_t blw;\n    uint8_t look;       /* ML_LOOK_*, patch UXF01 */\n    uint8_t extras;     /* ML_X_* */\n    uint8_t lid_min;    /* the lid never opens past 100 minus this, percent (a sleepy look) */\n} ml_style_t;")
    t = edit(t, '    {"minimal", 40, 62, -10, 56, ML_MOUTH_CUTE, 44, 3, 0, 28, 40, 100, 0, 0, 5, 4},\n};',
             '    {"minimal", 40, 62, -10, 56, ML_MOUTH_CUTE, 44, 3, 0, 28, 40, 100, 0, 0, 5, 4},\n    {"recipe", 85, 70, -14, 56, ML_MOUTH_CUTE, 38, 7, 0, 79, 85, 100, 1, 1, 5, 7},   /* the template of the writable row */\n};')
    for row in ("big_eyes", "eyes_only", "stock", "classic", "minimal", "recipe"):   # the three new trailing fields, written out so -Wextra stays quiet
        i = t.index('    {"%s", ' % row)
        j = t.index("},", i)
        t = t[:j] + ", 0, 0, 0" + t[j:]
    t = edit(t, "static inline const ml_style_t* ml_style(int id) { return &ML_STYLES[(id >= 0 && id < ML_STYLE_COUNT) ? id : ML_STYLE_BIG_EYES]; }",
"""/* The writable row: one instance for the whole program (an inline function's static is shared by every file that includes this). */
#ifdef __cplusplus
#define ML_INLINE inline
#else
#define ML_INLINE static inline
#endif
typedef struct { ml_style_t st; char name[13]; int ready; } ml_slot_t;
ML_INLINE ml_slot_t* ml_slot(void)
{
    static ml_slot_t s;
    if (!s.ready) { s.st = ML_STYLES[ML_STYLE_RECIPE]; s.name[0] = 'r'; s.name[1] = 'e'; s.name[2] = 'c'; s.name[3] = 'i'; s.name[4] = 'p'; s.name[5] = 'e'; s.name[6] = 0; s.st.name = s.name; s.ready = 1; }
    return &s;
}
static inline const ml_style_t* ml_style(int id)
{
    if (id == ML_STYLE_RECIPE) return &ml_slot()->st;
    return &ML_STYLES[(id >= 0 && id < ML_STYLE_RECIPE) ? id : ML_STYLE_BIG_EYES];
}

/* A recipe: 44 bytes (a style asset holds up to 256). Little endian.
 *   0 "MPS1"  4 version (1)  5 look  6 extras  7 lid_min  8 mouth  9 r_pct  10 pupil  11 brows  12 drift  13 blw  14 to 15 zero
 *   16 name (12 bytes, ASCII, NUL padded)  28 eight int16: eye_d, eye_x, eye_y, mouth_y, mouth_w, mouth_t, ew, eh
 * ml_recipe_parse checks every number against what the face can draw, so a recipe cannot put a shape outside the face zone. */
#define ML_RECIPE_BYTES 44
#define ML_RECIPE_MAX_BYTES 256
static inline int ml_rcp_i16(const uint8_t* p) { return (int)(int16_t)(uint16_t)(p[0] | (p[1] << 8)); }
static inline int ml_rcp_between(int v, int lo, int hi) { return v >= lo && v <= hi; }
/* 0 on success (out is filled), else 1 to 6 and *why is a plain sentence. */
static inline int ml_recipe_parse(const uint8_t* b, int n, ml_style_t* out, char* name_out, const char** why)
{
    const char* none = "";
    if (why == NULL) why = &none;
    if (b == NULL || n < ML_RECIPE_BYTES || n > ML_RECIPE_MAX_BYTES) { *why = "This face recipe is the wrong size: it must be 44 to 256 bytes. Make it again with scripts/face-recipe.py."; return 1; }
    if (b[0] != 'M' || b[1] != 'P' || b[2] != 'S' || b[3] != '1') { *why = "This is not a face recipe: it does not start with MPS1. Make it with scripts/face-recipe.py."; return 2; }
    if (b[4] != 1) { *why = "This face recipe is a newer version than this unit reads. Update the unit, then install it again."; return 3; }
    const int look = b[5], extras = b[6], lid_min = b[7], mouth = b[8], r_pct = b[9], pupil = b[10], brows = b[11], drift = b[12], blw = b[13];
    const int eye_d = ml_rcp_i16(b + 28), eye_x = ml_rcp_i16(b + 30), eye_y = ml_rcp_i16(b + 32), mouth_y = ml_rcp_i16(b + 34);
    const int mouth_w = ml_rcp_i16(b + 36), mouth_t = ml_rcp_i16(b + 38), ew = ml_rcp_i16(b + 40), eh = ml_rcp_i16(b + 42);
    if (look > ML_LOOK_MAX || extras > ML_X_MAX || mouth > ML_MOUTH_BAR || r_pct > 100 || pupil > 1 || brows > 1 || lid_min > 70 || drift > 12 || blw > 12) {
        *why = "A choice in this face recipe is not one this unit knows (eye design, decoration, mouth, roundness, brows or lid). Make it again with scripts/face-recipe.py."; return 4;
    }
    if (!ml_rcp_between(ew, 10, 120) || !ml_rcp_between(eh, 10, 110) || !ml_rcp_between(eye_d, 10, 120) || !ml_rcp_between(eye_x, 30, 110) || !ml_rcp_between(eye_y, -60, 40)) {
        *why = "The eyes in this face recipe are too small, too big or too far out for the screen. Keep each size between 10 and 120 pixels."; return 5;
    }
    if (!ml_rcp_between(mouth_y, 20, 70) || !ml_rcp_between(mouth_w, 0, 90) || !ml_rcp_between(mouth_t, 0, 14) || (float)eye_y - (float)eh * 0.64f < -76.0f) {
        *why = "The mouth or the top of the eyes in this face recipe would leave the face zone. Move the mouth up or the eyes down."; return 6;
    }
    memset(out, 0, sizeof(*out));
    out->eye_d = (int16_t)eye_d; out->eye_x = (int16_t)eye_x; out->eye_y = (int16_t)eye_y; out->mouth_y = (int16_t)mouth_y;
    out->mouth = (uint8_t)mouth; out->mouth_w = (int16_t)mouth_w; out->mouth_t = (int16_t)mouth_t; out->stock_look = 0;
    out->ew = (int16_t)ew; out->eh = (int16_t)eh; out->r_pct = (uint8_t)r_pct; out->pupil = (uint8_t)pupil; out->brows = (uint8_t)brows;
    out->drift = (uint8_t)drift; out->blw = (uint8_t)blw; out->look = (uint8_t)look; out->extras = (uint8_t)extras; out->lid_min = (uint8_t)lid_min;
    if (name_out != NULL) {
        int i = 0;
        for (; i < 12 && b[16 + i] >= 32 && b[16 + i] < 127; i++) name_out[i] = (char)b[16 + i];
        name_out[i] = 0;
    }
    return 0;
}
/* Parse and, when it is good, make it the writable row. The caller then selects ML_STYLE_RECIPE. */
static inline int ml_recipe_apply(const uint8_t* b, int n, const char** why)
{
    ml_style_t st;
    char name[13];
    const int rc = ml_recipe_parse(b, n, &st, name, why);
    if (rc != 0) return rc;
    ml_slot_t* s = ml_slot();
    int i = 0;
    for (; name[i] != 0 && i < 12; i++) s->name[i] = name[i];
    s->name[i] = 0;
    s->st = st;
    s->st.name = s->name;
    return 0;
}""")
    # lid floor and the hearts / pie / neon / slit eye designs
    t = edit(t, """    const float bl = in->blink;
    if (in->heart > 0.02f) {
        const float sz = (ew < eh ? ew : eh) * (st->ew <= 28 ? 1.5f : 1.05f) * in->beat;
        ml_shape_t* h = ml_sh(out, &n, max, ML_SH_HEART, ML_COL_FG, ml_clamp01f(in->heart));""",
"""    const float bl = in->blink;
    const int look = st->look;
    const float lm = (float)st->lid_min / 100.0f;
    const float lidv = in->lid < lm ? lm : in->lid;   /* patch UXF01: a sleepy style never opens fully */
    const float heartv = look == ML_LOOK_HEART ? (1.0f - in->closed) : in->heart;   /* the heart-eyed style draws a heart for every open eye; it does not blink (a blink redraws both hearts, about 48,000 pixels) */
    if (heartv > 0.02f) {
        const float sz = (ew < eh ? ew : eh) * (st->ew <= 28 ? 1.5f : 1.05f) * (look == ML_LOOK_HEART ? 1.0f : in->beat);   /* the heart-eyed style does not beat: a beat redraws both hearts every frame */
        ml_shape_t* h = ml_sh(out, &n, max, ML_SH_HEART, ML_COL_FG, ml_clamp01f(heartv));""")
    t = edit(t, "    const float eyeA = 1.0f - (in->heart > in->closed ? in->heart : in->closed);", "    const float eyeA = look == ML_LOOK_HEART ? 0.0f : 1.0f - (in->heart > in->closed ? in->heart : in->closed);")
    t = edit(t, """        ml_shape_t* e = ml_sh(out, &n, max, ML_SH_RRECT, ML_COL_FG, eyeA);
        if (e) { e->v[0] = 0; e->v[1] = 0; e->v[2] = ww; e->v[3] = hh; e->v[4] = rad; }
        if (st->pupil) {""",
"""        if (look == ML_LOOK_NEON) { /* a soft glow behind the ring */
            ml_shape_t* g = ml_sh(out, &n, max, ML_SH_RRECT, ML_COL_FG, eyeA * 0.28f);
            if (g) { g->v[0] = 0; g->v[1] = 0; g->v[2] = ww + 8.0f; g->v[3] = hh + 8.0f; g->v[4] = rad + 4.0f; }
        }
        ml_shape_t* e = ml_sh(out, &n, max, ML_SH_RRECT, ML_COL_FG, eyeA);
        if (e) { e->v[0] = 0; e->v[1] = 0; e->v[2] = ww; e->v[3] = hh; e->v[4] = rad; }
        if (look == ML_LOOK_NEON) { /* hollow: the screen color inside the ring, then an iris that follows the gaze, a pupil and a spark */
            float tk = sm * 0.12f; tk = tk < 4.0f ? 4.0f : (tk > 9.0f ? 9.0f : tk);
            ml_shape_t* inr = ml_sh(out, &n, max, ML_SH_RRECT, ML_COL_BG, eyeA);
            if (inr) { inr->v[0] = 0; inr->v[1] = 0; inr->v[2] = ww - 2.0f * tk; inr->v[3] = hh - 2.0f * tk; inr->v[4] = rad > tk ? rad - tk : 0.0f; }
            const float ir = (sm - 2.0f * tk) * 0.40f * (1.0f - bl * 0.2f);
            float px = in->gx * 1.0f, py = in->gy * 1.0f;
            const float lim = (sm - 2.0f * tk) * 0.5f - ir * 0.55f, dist = sqrtf(px * px + py * py);
            if (lim > 0.0f && dist > lim) { px *= lim / dist; py *= lim / dist; }
            if (bl < 0.6f) {
                ml_shape_t* c = ml_sh(out, &n, max, ML_SH_CIRCLE, ML_COL_FG, eyeA * 0.9f);
                if (c) { c->v[0] = px; c->v[1] = py; c->v[2] = ir; }
                c = ml_sh(out, &n, max, ML_SH_CIRCLE, ML_COL_BG, eyeA);
                if (c) { c->v[0] = px + ir * 0.12f; c->v[1] = py + ir * 0.14f; c->v[2] = ir * 0.46f; }
                c = ml_sh(out, &n, max, ML_SH_CIRCLE, ML_COL_HL, eyeA);
                if (c) { c->v[0] = px - ir * 0.40f; c->v[1] = py - ir * 0.44f; c->v[2] = ir * 0.24f; }
            }
        } else if (look == ML_LOOK_SLIT) { /* a vertical slit that follows the gaze */
            float px = in->gx * 1.0f, py = in->gy * 0.6f;
            const float lim = sm * 0.18f, dist = sqrtf(px * px + py * py);
            if (dist > lim) { px *= lim / dist; py *= lim / dist; }
            ml_shape_t* sl = ml_sh(out, &n, max, ML_SH_RRECT, ML_COL_BG, eyeA);
            const float sw = sm * 0.16f < 5.0f ? 5.0f : sm * 0.16f;
            if (sl) { sl->v[0] = px; sl->v[1] = py; sl->v[2] = sw; sl->v[3] = hh * 0.78f * (1.0f - bl * 0.8f); sl->v[4] = sw * 0.5f; }
            ml_shape_t* hl = ml_sh(out, &n, max, ML_SH_CIRCLE, ML_COL_HL, eyeA);
            if (hl) { hl->v[0] = px - sw * 1.4f; hl->v[1] = py - hh * 0.2f; hl->v[2] = sm * 0.06f; }
        } else if (look == ML_LOOK_PIE) { /* a big dark pupil with a wedge of eye color cut out of it, the rubber-hose pie eye */
            const float pr = sm * 0.46f * (1.0f - bl * 0.2f);
            float px = in->gx * 0.8f, py = in->gy * 0.8f + hh * 0.04f;
            const float lim = sm * 0.5f - pr + 8.0f, dist = sqrtf(px * px + py * py);
            if (dist > lim) { px *= lim / dist; py *= lim / dist; }
            ml_shape_t* p = ml_sh(out, &n, max, ML_SH_CIRCLE, ML_COL_BG, eyeA);
            if (p) { p->v[0] = px; p->v[1] = py; p->v[2] = pr; }
            ml_shape_t* w = ml_sh(out, &n, max, ML_SH_QUAD, ML_COL_FG, eyeA);   /* the wedge: a triangle from the pupil's middle past its upper right edge */
            if (w) {
                const float k = pr * 1.25f;
                w->v[0] = px; w->v[1] = py; w->v[2] = px + k * 0.34f; w->v[3] = py - k * 0.94f; w->v[4] = px + k * 0.97f; w->v[5] = py - k * 0.26f; w->v[6] = px; w->v[7] = py;
            }
            if (sqrtf(px * px + py * py) + pr > sm * 0.5f - 0.5f) {
                ml_shape_t* r = ml_sh(out, &n, max, ML_SH_RING, ML_COL_BG, 1.0f);
                if (r) { r->v[0] = 0; r->v[1] = 0; r->v[2] = ww; r->v[3] = hh; r->v[4] = rad; r->v[5] = 18; }
            }
        }
        if (st->pupil && look == ML_LOOK_STD) {""")
    t = edit(t, "        if (in->lid > 0.005f || fabsf(in->slant) > 0.005f) {", "        if (lidv > 0.005f || fabsf(in->slant) > 0.005f) {")
    t = edit(t, "            const float y0 = top + in->lid * hh + k * x0, y1 = top + in->lid * hh + k * x1, T = top - 6.0f;", "            const float y0 = top + lidv * hh + k * x0, y1 = top + lidv * hh + k * x1, T = top - 6.0f;")
    # decorations
    t = edit(t, "/* A brow, around the eye's resting centre (the caller adds the eye's place). es is the right eye's scale. */",
"""/* The fixed decorations of a style (ML_X_*), around the middle of the face zone (patch UXF01). Plain shapes, no mask: the face draws them under the eyes. */
static inline int ml_extras(int id, ml_shape_t* out, int max)
{
    int n = 0;
    ml_shape_t* s;
    if (id == ML_X_CAT) {
        for (int side = -1; side <= 1; side += 2) {
            s = ml_sh(out, &n, max, ML_SH_QUAD, ML_COL_FG, 1.0f);   /* an ear: a triangle on the top of the head, outer side */
            if (s) { s->v[0] = side * 32.0f; s->v[1] = -44.0f; s->v[2] = side * 62.0f; s->v[3] = -74.0f; s->v[4] = side * 92.0f; s->v[5] = -44.0f; s->v[6] = side * 32.0f; s->v[7] = -44.0f; }
            s = ml_sh(out, &n, max, ML_SH_QUAD, ML_COL_BG, 1.0f);   /* the inside of the ear */
            if (s) { s->v[0] = side * 54.0f; s->v[1] = -46.0f; s->v[2] = side * 62.0f; s->v[3] = -58.0f; s->v[4] = side * 70.0f; s->v[5] = -46.0f; s->v[6] = side * 54.0f; s->v[7] = -46.0f; }
            for (int k = 0; k < 3; k++) {                           /* three whiskers */
                s = ml_sh(out, &n, max, ML_SH_LINE, ML_COL_FG, 0.9f);
                if (s) { s->v[0] = side * 58.0f; s->v[1] = 52.0f + k * 5.0f; s->v[2] = side * 108.0f; s->v[3] = 40.0f + k * 13.0f; s->v[4] = 3.0f; }
            }
        }
    } else if (id == ML_X_ROBOT) {
        s = ml_sh(out, &n, max, ML_SH_LINE, ML_COL_FG, 1.0f);
        if (s) { s->v[0] = 0; s->v[1] = -46.0f; s->v[2] = 0; s->v[3] = -62.0f; s->v[4] = 5.0f; }
        s = ml_sh(out, &n, max, ML_SH_CIRCLE, ML_COL_FG, 1.0f);
        if (s) { s->v[0] = 0; s->v[1] = -66.0f; s->v[2] = 6.0f; }
        for (int side = -1; side <= 1; side += 2) {
            s = ml_sh(out, &n, max, ML_SH_CIRCLE, ML_COL_FG, 1.0f);
            if (s) { s->v[0] = side * 136.0f; s->v[1] = 0; s->v[2] = 8.0f; }
            s = ml_sh(out, &n, max, ML_SH_CIRCLE, ML_COL_BG, 1.0f);
            if (s) { s->v[0] = side * 136.0f; s->v[1] = 0; s->v[2] = 3.0f; }
        }
    } else if (id == ML_X_BLUSH || id == ML_X_HOSE) {
        for (int side = -1; side <= 1; side += 2) {
            s = ml_sh(out, &n, max, ML_SH_CIRCLE, ML_COL_FG, 0.30f);
            if (s) { s->v[0] = side * (id == ML_X_HOSE ? 112.0f : 100.0f); s->v[1] = 36.0f; s->v[2] = id == ML_X_HOSE ? 15.0f : 13.0f; }
        }
        if (id == ML_X_HOSE) {
            for (int k = -1; k <= 1; k++) {                          /* a tuft of three curved hairs between the eyes */
                s = ml_sh(out, &n, max, ML_SH_LINE, ML_COL_FG, 1.0f);
                if (s) { s->v[0] = k * 8.0f; s->v[1] = -42.0f; s->v[2] = k * 15.0f; s->v[3] = -64.0f; s->v[4] = 5.0f; }
            }
        }
    } else if (id == ML_X_NEON) {
        for (int side = -1; side <= 1; side += 2) {
            const float cx = side * 126.0f, cy = -44.0f;             /* a four-point spark, and a small one beside it */
            s = ml_sh(out, &n, max, ML_SH_LINE, ML_COL_FG, 0.85f);
            if (s) { s->v[0] = cx - 9.0f; s->v[1] = cy; s->v[2] = cx + 9.0f; s->v[3] = cy; s->v[4] = 3.0f; }
            s = ml_sh(out, &n, max, ML_SH_LINE, ML_COL_FG, 0.85f);
            if (s) { s->v[0] = cx; s->v[1] = cy - 9.0f; s->v[2] = cx; s->v[3] = cy + 9.0f; s->v[4] = 3.0f; }
            s = ml_sh(out, &n, max, ML_SH_CIRCLE, ML_COL_FG, 0.6f);
            if (s) { s->v[0] = side * 140.0f; s->v[1] = -22.0f; s->v[2] = 3.0f; }
        }
    }
    return n;
}

/* A brow, around the eye's resting centre (the caller adds the eye's place). es is the right eye's scale. */""")
    return t


def edit_default_h(t: str) -> str:
    t = edit(t, "    void setLook(int style);\n    int look() const { return _style; }", "    void setLook(int style);\n    int look() const { return _style; }\n    // The fixed decorations of the style (patch UXF01), drawn by one object that exists only while the style has any.\n    void drawExtras(lv_event_t* e);")
    t = edit(t, "    lv_obj_t* _dots[ML_DOT_COUNT] = {};", "    lv_obj_t* _dots[ML_DOT_COUNT] = {};\n    lv_obj_t* _extras = nullptr;   // patch UXF01\n    void rebuild_extras();")
    return t


def edit_default_cpp(t: str) -> str:
    t = edit(t, """    for (auto& k : _dot_key) {
        k = -1;
    }
}
""", """    for (auto& k : _dot_key) {
        k = -1;
    }
    rebuild_extras();
}

// Patch UXF01: the decorations of the style, one object in the face zone that draws a short shape list; it is deleted when the style has none.
void DefaultAvatar::rebuild_extras()
{
    const int id = ml_style(_style)->extras;
    if (_extras != nullptr) {
        lv_obj_delete(_extras);
        _extras = nullptr;
    }
    if (id == ML_X_NONE || !_zone) {
        return;
    }
    _extras = lv_obj_create(_zone->get());
    lv_obj_remove_style_all(_extras);
    lv_obj_remove_flag(_extras, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_remove_flag(_extras, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_size(_extras, 320, 156);
    lv_obj_set_pos(_extras, 0, 0);
    lv_obj_move_background(_extras);
    lv_obj_add_event_cb(
        _extras, [](lv_event_t* e) { static_cast<DefaultAvatar*>(lv_event_get_user_data(e))->drawExtras(e); }, LV_EVENT_DRAW_MAIN, this);
}

void DefaultAvatar::drawExtras(lv_event_t* e)
{
    lv_layer_t* layer = lv_event_get_layer(e);
    if (layer == nullptr || _extras == nullptr) {
        return;
    }
    ml_shape_t sh[24];
    const int n = ml_extras(ml_style(_style)->extras, sh, 24);
    lv_area_t a;
    lv_obj_get_coords(_extras, &a);
    ml_draw_shape_list(layer, sh, n, (a.x1 + a.x2) / 2, (a.y1 + a.y2) / 2, shownColor(), secondaryColor);
}
""")
    t = edit(t, "    _drawn_rgb      = packed;\n    const lv_color_t c = shownColor();", "    _drawn_rgb      = packed;\n    const lv_color_t c = shownColor();\n    if (_extras != nullptr) {\n        lv_obj_invalidate(_extras);   // patch UXF01: the decorations follow the face color\n    }")
    return t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", default=str(Path.home() / "esp" / "stackchan-rebuild" / "main-ref"), help="the pristine reference tree (scripts/ref-tree.py), never the overlay tree the renderer builds")
    a = ap.parse_args()
    tree = Path(a.tree).resolve()
    funcs = {FILES[0]: edit_look, FILES[1]: edit_default_cpp, FILES[2]: edit_default_h}
    out = [HEADER]
    for rel in FILES:
        old = (tree / rel).read_text()
        new = funcs[rel](old)
        out.append("".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), f"a/{rel}", f"b/{rel}", n=3)).replace("\n\\ No newline at end of file", ""))
        out[-1] = f"diff --git a/{rel} b/{rel}\n" + out[-1]
    dest = ROOT / "firmware" / "patches" / "UXF01-face-style-recipes.patch"
    dest.write_text("".join(out))
    print(f"wrote {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
