#!/usr/bin/env python3
"""Builds firmware/patches/UXF03-cartoon-eyes.patch: a glossy-eye design (a white eye with a colored iris, a dark pupil and a small highlight that looks up and to the side), three color slots
(iris, eye white, tongue) read from a recipe's two spare bytes, and a tongue in an open smile. The base is the reference tree with UXF01 and UXF02 applied.
Usage: python3 scripts/face-kit/make_patch_gloss.py [--tree TREE]. Placement: host-side development tool; the patch it writes is a unit patch on branch ux/faces. Upstream: none."""
from __future__ import annotations

import argparse
import difflib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SK = "firmware/main/stackchan/avatar/skins/default/"
FILES = ["firmware/main/hal/maipai_look_core.h", SK + "eyes.cpp", SK + "default.cpp", SK + "default.h", SK + "mouth.cpp", "firmware/main/stackchan/avatar/avatar/elements/emotion.h"]
EDITED = FILES[:5]
HEADER = """# Intent: A cartoon face style as data (docs/design/face-styles.md, owner request 2026-11-19): a glossy eye design, three color slots and a tongue. The eye is a white oval, a colored iris that follows the gaze and rests looking up and to the side, a dark pupil and one small highlight. A recipe carries the iris color, the eye-white color and the tongue color in its two spare bytes (byte 14 the iris, byte 15 the tongue in the high four bits and the white in the low four; each is an index into one 15-color table, 0 meaning the style's default), so the recipe stays 44 bytes and older recipes (both bytes zero) read as before. The shape list gains three color slots; the avatar fills them when the style or the face color changes. An open smile (a thick mouth stroke) draws a small tongue in its lower middle. The iris is the face color unless that is white, then brown; the eye white is near-white; the tongue is pink. Original shapes only.
# Placement: unit
# Upstream: firmware/main/hal/maipai_look_core.h and firmware/main/stackchan/avatar/skins/default/ (ours, patches X01, V10, UXF01)
# Check after a flash: install the cartoon style asset and apply it; the eyes are white with a colored iris looking up and aside, the smile shows a pink tongue when it opens, a happy eye closes to an arch, a sleepy lid covers the top; a recipe with both color bytes zero draws the default colors; the memory row is the same as for any other recipe.
# Kconfig: none
# Memory cost: three colors (6 bytes of internal RAM), no objects. Flash about 0.4 KB.

"""


def edit(t: str, old: str, new: str, count: int = 1) -> str:
    if t.count(old) != count:
        raise SystemExit(f"edit expected {count} match(es), found {t.count(old)}: {old[:70]!r}")
    return t.replace(old, new)


def look(t: str) -> str:
    t = edit(t, "#define ML_LOOK_HEART 4 /* the eye is a heart */\n#define ML_LOOK_MAX 4", "#define ML_LOOK_HEART 4 /* the eye is a heart */\n#define ML_LOOK_GLOSS 5 /* a white eye, a colored iris, a dark pupil and a highlight */\n#define ML_LOOK_MAX 5")
    t = edit(t, "#define ML_MAX_SHAPES 48\n", "#define ML_COL_IRIS 3   /* patch UXF03: the style's iris, eye white and tongue colors */\n#define ML_COL_WHITE 4\n#define ML_COL_TONGUE 5\n#define ML_MAX_SHAPES 48\n")
    t = edit(t, "    uint8_t lid_min;    /* the lid never opens past 100 minus this, percent (a sleepy look) */\n} ml_style_t;", "    uint8_t lid_min;    /* the lid never opens past 100 minus this, percent (a sleepy look) */\n    uint8_t iris;       /* ML_PAL index of the iris color, 0 the default (patch UXF03) */\n    uint8_t tongue;     /* of the tongue */\n    uint8_t white;      /* of the eye white */\n} ml_style_t;")
    for row in ("big_eyes", "eyes_only", "stock", "classic", "minimal", "recipe"):   # the three new trailing fields, written out so -Wextra stays quiet
        i = t.index('    {"%s", ' % row)
        j = t.index(", 0, 0, 0},", i)
        t = t[:j] + ", 0, 0, 0, 0, 0, 0}," + t[j + len(", 0, 0, 0},"):]
    t = edit(t, "/* The writable row: one instance for the whole program", """/* The 15 colors a recipe may name for its iris, tongue and eye white; index 0 is the style's default. */
#define ML_PAL_COUNT 16
static const char* const ML_PAL_NAMES[ML_PAL_COUNT] = {"default", "white", "ice", "cream", "brown", "hazel", "green", "teal", "blue", "violet", "pink", "red", "coral", "amber", "gray", "ink"};
static const uint8_t ML_PAL_RGB[ML_PAL_COUNT][3] = {
    {0, 0, 0}, {0xF8, 0xFA, 0xFF}, {0xDD, 0xEB, 0xFF}, {0xF4, 0xEA, 0xD0}, {0x8A, 0x5A, 0x3C}, {0x9A, 0x7A, 0x3A}, {0x4F, 0xA6, 0x6A}, {0x3A, 0xAF, 0xA9},
    {0x4A, 0x86, 0xE8}, {0x8A, 0x63, 0xD2}, {0xF0, 0x7A, 0xA0}, {0xE0, 0x48, 0x4E}, {0xF2, 0x84, 0x6C}, {0xF2, 0xB2, 0x4A}, {0x7A, 0x84, 0x94}, {0x1B, 0x1F, 0x2A},
};

/* The writable row: one instance for the whole program""")
    t = edit(t, " *   0 \"MPS1\"  4 version (1)  5 look  6 extras  7 lid_min  8 mouth  9 r_pct  10 pupil  11 brows  12 drift  13 blw  14 to 15 zero", " *   0 \"MPS1\"  4 version (1)  5 look  6 extras  7 lid_min  8 mouth  9 r_pct  10 pupil  11 brows  12 drift  13 blw  14 iris  15 tongue (high 4 bits) and eye white (low 4)")
    t = edit(t, "if (look > ML_LOOK_MAX || extras", "if (look > ML_LOOK_MAX || b[14] > 15 || extras")
    t = edit(t, "    out->drift = (uint8_t)drift; out->blw = (uint8_t)blw; out->look = (uint8_t)look; out->extras = (uint8_t)extras; out->lid_min = (uint8_t)lid_min;\n",
             "    out->drift = (uint8_t)drift; out->blw = (uint8_t)blw; out->look = (uint8_t)look; out->extras = (uint8_t)extras; out->lid_min = (uint8_t)lid_min;\n    out->iris = b[14]; out->tongue = (uint8_t)(b[15] >> 4); out->white = (uint8_t)(b[15] & 15);\n")
    t = edit(t, "        ml_shape_t* e = ml_sh(out, &n, max, ML_SH_RRECT, ML_COL_FG, eyeA);", "        ml_shape_t* e = ml_sh(out, &n, max, ML_SH_RRECT, look == ML_LOOK_GLOSS ? ML_COL_WHITE : ML_COL_FG, eyeA);")
    t = edit(t, "        } else if (look == ML_LOOK_SLIT) { /* a vertical slit that follows the gaze */", """        } else if (look == ML_LOOK_GLOSS) { /* a colored iris with a dark pupil and a small highlight, resting up and to the side, moving with the gaze */
            const float ir = sm * 0.30f * (1.0f - bl * 0.15f);
            float px = in->gx * 1.5f - sm * 0.10f, py = in->gy * 1.5f - sm * 0.13f;
            const float lim = sm * 0.5f - ir - 2.0f, dist = sqrtf(px * px + py * py);
            if (lim > 0.0f && dist > lim) { px *= lim / dist; py *= lim / dist; }
            if (bl < 0.7f) {
                ml_shape_t* c = ml_sh(out, &n, max, ML_SH_CIRCLE, ML_COL_IRIS, eyeA);
                if (c) { c->v[0] = px; c->v[1] = py; c->v[2] = ir; }
                c = ml_sh(out, &n, max, ML_SH_CIRCLE, ML_COL_BG, eyeA);
                if (c) { c->v[0] = px; c->v[1] = py; c->v[2] = ir * 0.52f; }
                c = ml_sh(out, &n, max, ML_SH_CIRCLE, ML_COL_WHITE, eyeA);
                if (c) { c->v[0] = px - ir * 0.36f; c->v[1] = py - ir * 0.40f; c->v[2] = ir * 0.26f; }
            }
        } else if (look == ML_LOOK_SLIT) { /* a vertical slit that follows the gaze */""")
    t = edit(t, "t[MP_BROW] = st->brows ? s.brow : 0.0f;", "t[MP_BROW] = st->brows ? (st->look == ML_LOOK_GLOSS && s.brow < 0.55f ? 0.55f : s.brow) : 0.0f;   /* patch UXF03: the cartoon eye keeps soft brows at rest */")
    return t


def eyes(t: str) -> str:
    t = edit(t, "uint32_t stackchan::avatar::g_ml_wink_until_ms = 0;  // patch MD02\n", "uint32_t stackchan::avatar::g_ml_wink_until_ms = 0;  // patch MD02\nlv_color_t stackchan::avatar::g_ml_iris_c;           // patch UXF03: the style's iris, eye white and tongue colors\nlv_color_t stackchan::avatar::g_ml_white_c;\nlv_color_t stackchan::avatar::g_ml_tongue_c;\n")
    t = edit(t, "static void draw_shapes(lv_layer_t* layer, const ml_shape_t* sh, int n, int cx, int cy, lv_color_t fg, lv_color_t bg)", """static lv_color_t slot_color(int col, lv_color_t fg)
{
    switch (col) {
        case ML_COL_IRIS: return stackchan::avatar::g_ml_iris_c;
        case ML_COL_WHITE: return stackchan::avatar::g_ml_white_c;
        case ML_COL_TONGUE: return stackchan::avatar::g_ml_tongue_c;
        default: return fg;
    }
}

static void draw_shapes(lv_layer_t* layer, const ml_shape_t* sh, int n, int cx, int cy, lv_color_t fg, lv_color_t bg)""")
    t = edit(t, "        const lv_color_t col = s.col == ML_COL_BG ? bg : fg;\n        switch (s.kind) {", "        const lv_color_t col = s.col == ML_COL_BG ? bg : slot_color(s.col, fg);\n        switch (s.kind) {")
    # the picture path (patch V23) knows two colors only: an eye that names the iris, white or tongue slot is drawn from its shape list
    return edit(t, "    msp_box_t b;\n    if (!msp_eye_plain(_sh, _nsh, &b)) {\n        return;\n    }", "    for (int i = 0; i < _nsh; i++) {\n        if (_sh[i].col >= ML_COL_IRIS) {\n            return;   // patch UXF03: the picture holds two colors\n        }\n    }\n    msp_box_t b;\n    if (!msp_eye_plain(_sh, _nsh, &b)) {\n        return;\n    }")


def default_cpp(t: str) -> str:
    t = edit(t, "// The colour the face is drawn in after the tint: set on the eyes, the mouth and the thinking dots.\nvoid DefaultAvatar::apply_color()", """// Patch UXF03: the colors a style's shapes name (iris, eye white, tongue). A palette index of 0 is the default: the iris is the face color unless that is
// white (then brown), the eye white is near white, the tongue is pink.
static void gloss_colors(const ml_style_t* st, lv_color_t fg)
{
    auto pal = [](int i) { return lv_color_make(ML_PAL_RGB[i][0], ML_PAL_RGB[i][1], ML_PAL_RGB[i][2]); };
    g_ml_white_c  = st->white ? pal(st->white) : lv_color_make(0xF8, 0xFA, 0xFF);
    g_ml_tongue_c = st->tongue ? pal(st->tongue) : lv_color_make(0xF0, 0x6A, 0x8A);
    const bool light = fg.red > 235 && fg.green > 235 && fg.blue > 235;
    g_ml_iris_c   = st->iris ? pal(st->iris) : (light ? lv_color_make(0x8A, 0x5A, 0x3C) : fg);
}

// The colour the face is drawn in after the tint: set on the eyes, the mouth and the thinking dots.
void DefaultAvatar::apply_color()""")
    t = edit(t, "        lv_obj_invalidate(_extras);   // patch UXF01: the decorations follow the face color\n    }\n", "        lv_obj_invalidate(_extras);   // patch UXF01: the decorations follow the face color\n    }\n    gloss_colors(ml_style(_style), c);\n")
    return edit(t, "    rebuild_extras();\n}\n", "    rebuild_extras();\n    gloss_colors(ml_style(_style), shownColor());\n}\n")


def default_h(t: str) -> str:
    return edit(t, "extern float g_ml_voice;\n", "extern float g_ml_voice;\n// Patch UXF03: the colors the shape slots ML_COL_IRIS, ML_COL_WHITE and ML_COL_TONGUE draw in.\nextern lv_color_t g_ml_iris_c;\nextern lv_color_t g_ml_white_c;\nextern lv_color_t g_ml_tongue_c;\n")


def mouth(t: str) -> str:
    return edit(t, "        for (int i = 0; i < n; i++) {\n            for (int k = 0; k < 8; k++) {\n                tmp[i].v[k] = roundf(tmp[i].v[k]);", """        if (st->look == ML_LOOK_GLOSS && (P[MP_MOPEN] > 0.2f || (speaking && _cur.t >= 10.0f)) && n > 0) {  // patch UXF03: an open smile shows a tongue in its lower middle
            float low = -1.0e9f;
            for (int i = 0; i < n; i++) {
                if (tmp[i].kind == ML_SH_LINE) {
                    low = fmaxf(low, fmaxf(tmp[i].v[1], tmp[i].v[3]) + tmp[i].v[4] * 0.5f);
                }
            }
            ml_shape_t* tg = low > -1.0e8f ? ml_sh(tmp, &n, ML_MAX_SHAPES, ML_SH_RRECT, ML_COL_TONGUE, 1.0f) : nullptr;
            if (tg != nullptr) {
                tg->v[0] = 0.0f;
                tg->v[1] = low - 4.0f;
                tg->v[2] = 18.0f;
                tg->v[3] = 11.0f;
                tg->v[4] = 5.5f;
            }
        }
        for (int i = 0; i < n; i++) {
            for (int k = 0; k < 8; k++) {
                tmp[i].v[k] = roundf(tmp[i].v[k]);""")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", default=str(Path.home() / "esp" / "stackchan-rebuild" / "main-ref"))
    a = ap.parse_args()
    tree = Path(a.tree)
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        for rel in FILES:
            (base / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(tree / rel, base / rel)
        for name in ("UXF01-face-style-recipes.patch", "UXF02-extended-moods.patch"):
            done = subprocess.run(["patch", "-p1", "-s", "-f"], input=(ROOT / "firmware" / "patches" / name).read_text(), cwd=base, capture_output=True, text=True)
            if done.returncode != 0:
                raise SystemExit(f"{name} does not apply to the base: {done.stdout}{done.stderr}")
        out = [HEADER]
        for rel, fn in zip(EDITED, (look, eyes, default_cpp, default_h, mouth)):
            old = (base / rel).read_text()
            out.append(f"diff --git a/{rel} b/{rel}\n" + "".join(difflib.unified_diff(old.splitlines(True), fn(old).splitlines(True), f"a/{rel}", f"b/{rel}", n=3)))
    dest = ROOT / "firmware" / "patches" / "UXF03-cartoon-eyes.patch"
    dest.write_text("".join(out))
    print(f"wrote {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
