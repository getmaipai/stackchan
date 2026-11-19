/* Host test for the face recipes (patch UXF01): the reader, the writable style row, the four eye designs and the decorations.
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with the patched headers> face_recipe_core_test.c -lm   then run with the .rcp files as arguments. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "maipai_look_core.h"

static int fails;
#define CHECK(c)                                        \
    do {                                                \
        if (!(c)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #c); \
            fails++;                                    \
        }                                               \
    } while (0)

static int load(const char* path, uint8_t* buf, int cap)
{
    FILE* f = fopen(path, "rb");
    if (!f) return -1;
    const int n = (int)fread(buf, 1, (size_t)cap, f);
    fclose(f);
    return n;
}

static void bad_recipes(const uint8_t* good)
{
    uint8_t b[ML_RECIPE_BYTES];
    ml_style_t st;
    char name[13];
    const char* why = "";
    CHECK(ml_recipe_parse(good, ML_RECIPE_BYTES, &st, name, &why) == 0);
    CHECK(ml_recipe_parse(good, ML_RECIPE_BYTES - 1, &st, name, &why) == 1 && strstr(why, "wrong size") != NULL);
    CHECK(ml_recipe_parse(NULL, 0, &st, name, &why) == 1);
    memcpy(b, good, sizeof(b)); b[0] = 'X';
    CHECK(ml_recipe_parse(b, sizeof(b), &st, name, &why) == 2 && strstr(why, "MPS1") != NULL);
    memcpy(b, good, sizeof(b)); b[4] = 2;
    CHECK(ml_recipe_parse(b, sizeof(b), &st, name, &why) == 3 && strstr(why, "Update the unit") != NULL);
    memcpy(b, good, sizeof(b)); b[5] = 9;   /* an eye design this unit does not know */
    CHECK(ml_recipe_parse(b, sizeof(b), &st, name, &why) == 4);
    memcpy(b, good, sizeof(b)); b[6] = 9;   /* a decoration it does not know */
    CHECK(ml_recipe_parse(b, sizeof(b), &st, name, &why) == 4);
    memcpy(b, good, sizeof(b)); b[40] = 5; b[41] = 0;   /* an eye 5 pixels wide */
    CHECK(ml_recipe_parse(b, sizeof(b), &st, name, &why) == 5 && strstr(why, "eyes") != NULL);
    memcpy(b, good, sizeof(b)); b[34] = 99; b[35] = 0;  /* a mouth below the zone */
    CHECK(ml_recipe_parse(b, sizeof(b), &st, name, &why) == 6 && strstr(why, "face zone") != NULL);
    memcpy(b, good, sizeof(b)); b[32] = (uint8_t)(-60 & 255); b[33] = 0xFF; b[42] = 110; b[43] = 0;   /* a tall eye high up: its top would leave the zone when surprised */
    CHECK(ml_recipe_parse(b, sizeof(b), &st, name, &why) == 6);
    CHECK(strlen(why) > 20 && why[strlen(why) - 1] == '.');   /* every refusal is a sentence with a next step */
}

static void shapes_fit(const ml_style_t* st, const char* name)
{
    for (int emo = 0; emo < ML_COUNT; emo++) {
        const ml_spec_t sp = ml_spec(emo, 0);
        (void)sp;
        for (int side = -1; side <= 1; side += 2) {
            for (int variant = 0; variant < 3; variant++) {
                ml_eye_in_t in;
                memset(&in, 0, sizeof(in));
                in.st = st; in.side = side;
                in.ew = (float)st->ew * (emo == ML_SURPRISED ? 1.1f : 1.0f); in.eh = (float)st->eh * (emo == ML_SURPRISED ? 1.28f : 1.0f);
                in.lid = emo == ML_SLEEPY ? 0.55f : (emo == ML_ANGRY ? 0.3f : 0.0f);
                in.slant = emo == ML_ANGRY ? 0.85f : 0.0f;
                in.cheek = emo == ML_HAPPY ? 1.0f : 0.0f;
                in.blink = variant == 1 ? 1.0f : 0.0f;
                in.closed = (emo == ML_SLEEPING || variant == 2) ? 1.0f : 0.0f;
                in.heart = emo == ML_LOVE ? 1.0f : 0.0f;
                in.beat = 1.0f; in.gx = 6.0f; in.gy = -4.0f;
                ml_shape_t out[ML_MAX_SHAPES];
                const int n = ml_eye_shapes(&in, out, ML_MAX_SHAPES);
                if (n >= ML_MAX_SHAPES) { printf("FAIL %s emotion %d fills the shape list\n", name, emo); fails++; }
                CHECK(n > 0 || in.closed == 0.0f);
            }
        }
    }
}

static void decorations_fit_the_zone(void)
{
    for (int id = 0; id <= ML_X_MAX; id++) {
        ml_shape_t sh[24];
        const int n = ml_extras(id, sh, 24);
        CHECK(id == ML_X_NONE ? n == 0 : n > 0);
        CHECK(n < 24);
        for (int i = 0; i < n; i++) {
            const ml_shape_t* s = &sh[i];
            float x0 = 0, y0 = 0, x1 = 0, y1 = 0;
            if (s->kind == ML_SH_CIRCLE) { x0 = s->v[0] - s->v[2]; x1 = s->v[0] + s->v[2]; y0 = s->v[1] - s->v[2]; y1 = s->v[1] + s->v[2]; }
            else if (s->kind == ML_SH_LINE) {
                const float h = s->v[4] / 2;
                x0 = fminf(s->v[0], s->v[2]) - h; x1 = fmaxf(s->v[0], s->v[2]) + h; y0 = fminf(s->v[1], s->v[3]) - h; y1 = fmaxf(s->v[1], s->v[3]) + h;
            } else if (s->kind == ML_SH_QUAD) {
                x0 = x1 = s->v[0]; y0 = y1 = s->v[1];
                for (int k = 2; k < 8; k += 2) { x0 = fminf(x0, s->v[k]); x1 = fmaxf(x1, s->v[k]); y0 = fminf(y0, s->v[k + 1]); y1 = fmaxf(y1, s->v[k + 1]); }
            }
            /* the face zone is 320 by 156 around its middle: nothing starts above y 32 on the screen (zone y -74) or ends below its edge */
            if (!(x0 >= -160 && x1 <= 160 && y0 >= -75.5f && y1 <= 78)) { printf("FAIL decoration %d shape %d leaves the face zone: %.0f %.0f %.0f %.0f\n", id, i, x0, y0, x1, y1); fails++; }
        }
    }
}

int main(int argc, char** argv)
{
    CHECK(ML_STYLE_COUNT == 6 && ML_STYLE_RECIPE == 5);
    CHECK(strcmp(ml_style(ML_STYLE_RECIPE)->name, "recipe") == 0);   /* before any recipe: the writable row is a big-eyes copy */
    CHECK(ml_style(ML_STYLE_RECIPE)->look == ML_LOOK_STD && ml_style(ML_STYLE_BIG_EYES)->look == ML_LOOK_STD && ml_style(ML_STYLE_BIG_EYES)->lid_min == 0);
    CHECK(ml_style(ML_STYLE_RECIPE) == ml_style(ML_STYLE_RECIPE));   /* one row, always the same address */
    uint8_t buf[ML_RECIPE_MAX_BYTES + 1];
    int seen = 0;
    for (int a = 1; a < argc; a++) {
        const int n = load(argv[a], buf, sizeof(buf));
        CHECK(n == ML_RECIPE_BYTES);
        const char* why = "";
        CHECK(ml_recipe_apply(buf, n, &why) == 0);
        const ml_style_t* st = ml_style(ML_STYLE_RECIPE);
        char want[13];
        memcpy(want, buf + 16, 12); want[12] = 0;
        CHECK(strcmp(st->name, want) == 0);
        CHECK(st->ew == ml_rcp_i16(buf + 40) && st->eh == ml_rcp_i16(buf + 42) && st->look == buf[5] && st->extras == buf[6] && st->lid_min == buf[7]);
        shapes_fit(st, argv[a]);
        seen++;
        if (a == 1) bad_recipes(buf);
        { /* a bad recipe changes nothing: the row still holds the last good one */
            uint8_t bad[ML_RECIPE_BYTES];
            memcpy(bad, buf, sizeof(bad)); bad[0] = 'Z';
            CHECK(ml_recipe_apply(bad, sizeof(bad), &why) != 0);
            CHECK(strcmp(ml_style(ML_STYLE_RECIPE)->name, want) == 0);
        }
    }
    CHECK(argc == 1 || seen == argc - 1);
    for (int i = 0; i < ML_STYLE_RECIPE; i++) shapes_fit(ml_style(i), ml_style(i)->name);   /* the base styles still fit */
    decorations_fit_the_zone();
    if (fails) { printf("%d failed\n", fails); return 1; }
    printf("face recipe core: all passed (%d recipes)\n", seen);
    return 0;
}
