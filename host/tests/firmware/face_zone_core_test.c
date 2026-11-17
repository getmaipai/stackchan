/* Host test for the fixed zones of the screen (patches N01, N04): the banner zone (y 0 to 28), the face zone (y 28 to 184) and the
 * subtitle zone (y 184 to 240). Over every style, every emotion (with thinking), the lid, the blink, the voice and the extreme
 * gaze offsets, no lit shape of the eyes, the brows or the mouth reaches the banner or the subtitle zone, and the eye tops are at
 * y 32 or lower and the tallest open mouth ends by y 180.
 * cc -std=c99 -Wall -Wextra -Werror -I<headers> face_zone_core_test.c -lm */
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "maipai_banner_core.h"
#include "maipai_look_core.h"

static int fails;
#define CHECK(c)                                        \
    do {                                                \
        if (!(c)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #c); \
            fails++;                                    \
        }                                               \
    } while (0)

static float worst_top = 1000, worst_bottom = -1000, worst_mouth_end = -1000;
static int checked;

static void note_box(const float b[4], float centre_y, int is_mouth)
{
    mb_rect_t r = mb_rect(0, (int)floorf(centre_y + b[1]), 320, (int)ceilf(centre_y + b[3]));
    CHECK(!mb_rect_overlap(r, mb_zone_banner()));
    CHECK(!mb_rect_overlap(r, mb_zone_sub()));
    if (centre_y + b[1] < worst_top) worst_top = centre_y + b[1];
    if (is_mouth) {
        if (centre_y + b[3] > worst_mouth_end) worst_mouth_end = centre_y + b[3];
    } else if (centre_y + b[3] > worst_bottom) {
        worst_bottom = centre_y + b[3];
    }
    checked++;
}

int main(void)
{
    const float ext[] = {-10.0f, 0.0f, 10.0f}; /* the external gaze range of eyes.cpp */
    const float lids[] = {0.0f, 0.5f, 1.0f};
    const float blinks[] = {0.0f, 1.0f};
    for (int si = 0; si < ML_STYLE_COUNT; si++) {
        const ml_style_t* st = ml_style(si);
        for (int emo = 0; emo < ML_COUNT; emo++)
            for (int think = 0; think < 2; think++) {
                float t[MP_N];
                ml_pose_target(st, emo, think, t);
                const float drift = (float)st->drift * ml_pose_drift_scale(emo);
                for (int side = -1; side <= 1; side += 2)
                    for (unsigned gxi = 0; gxi < 3; gxi++)
                        for (unsigned gyi = 0; gyi < 3; gyi++)
                            for (unsigned dd = 0; dd < 3; dd++)
                                for (unsigned li = 0; li < 3; li++)
                                    for (unsigned bi = 0; bi < 2; bi++) {
                                        const float dsx = (dd == 0 ? -drift : (dd == 1 ? 0.0f : drift));
                                        const float dsy = dsx;
                                        const float es = side > 0 ? t[MP_RSCALE] : 1.0f;
                                        ml_eye_in_t in;
                                        memset(&in, 0, sizeof(in));
                                        in.st = st; in.side = side; in.ew = t[MP_EW] * es; in.eh = t[MP_EH] * es;
                                        in.lid = lids[li]; in.slant = t[MP_SLANT]; in.cheek = t[MP_CHEEK]; in.blink = blinks[bi];
                                        in.heart = t[MP_HEART]; in.beat = 1.14f; in.closed = 0.0f;
                                        in.gx = ext[gxi] + dsx + t[MP_GX]; in.gy = ext[gyi] + dsy + t[MP_GY]; in.voice = 1.0f;
                                        ml_shape_t sh[ML_MAX_SHAPES];
                                        const int n = ml_eye_shapes(&in, sh, ML_MAX_SHAPES);
                                        float bb[4];
                                        if (!ml_shapes_bbox(sh, n, bb)) continue;
                                        int oy = (int)lroundf(t[MP_DY] + in.gy + (side > 0 ? t[MP_RLIFT] : 0.0f));
                                        oy = ml_zone_clamp_oy(st, oy, bb[1], bb[3]); /* what eyes.cpp does */
                                        note_box(bb, (float)ML_ZONE_CENTER_Y + (float)st->eye_y + (float)oy, 0);
                                        /* the brow, around the eye's resting centre */
                                        ml_shape_t br[2];
                                        const int bn = ml_brow_shapes(st, side, t[MP_EW] * es, t[MP_EH] * es, es, in.gx, side > 0 ? t[MP_RLIFT] : 0.0f, t[MP_BR],
                                                                      t[MP_BROW], t[MP_BLIFT], t[MP_BTILT], br, 2);
                                        float bbb[4];
                                        if (bn > 0 && ml_shapes_bbox(br, bn, bbb)) note_box(bbb, (float)ML_ZONE_CENTER_Y + (float)st->eye_y, 0);
                                    }
                /* the mouth: every open amount, the yawn, the resting shapes, the mouth's own offset of 2 px at most */
                if (st->mouth != ML_MOUTH_NONE && st->mouth != ML_MOUTH_BAR) {
                    for (int op = 0; op <= 10; op++)
                        for (int dy = -2; dy <= 2; dy += 4)
                            for (int yawn = 0; yawn < 2; yawn++) {
                                ml_mouth_t m = ml_mouth_target(st, emo, 0, op > 0, (float)op / 10.0f, yawn ? 1800u : 0u);
                                ml_shape_t sh[ML_MOUTH_PTS + 2];
                                const int n = ml_mouth_shapes(&m, 0.25f, 1.0f, sh, ML_MOUTH_PTS + 2);
                                float bb[4];
                                if (n > 0 && ml_shapes_bbox(sh, n, bb)) note_box(bb, (float)ML_ZONE_CENTER_Y + (float)st->mouth_y + (float)dy, 1);
                            }
                }
            }
        if (st->mouth == ML_MOUTH_BAR) { /* the stock bar: 90 by 6 resting, 60 by 50 open, centred at the zone centre plus 46, offset 2 at most */
            const float c = (float)ML_ZONE_CENTER_Y + 46.0f;
            CHECK(c + 25.0f + 2.0f <= (float)ML_ZONE_MOUTH_END);
            worst_mouth_end = worst_mouth_end > c + 27.0f ? worst_mouth_end : c + 27.0f;
            checked++;
        }
    }
    CHECK(worst_top >= (float)ML_ZONE_EYE_TOP - 0.01f);
    CHECK(worst_bottom <= (float)(ML_ZONE_Y1 - 4) + 0.01f);
    CHECK(worst_mouth_end <= (float)ML_ZONE_MOUTH_END + 0.01f);
    CHECK(checked > 20000);
    printf("checked %d boxes: highest lit y %.1f (limit %d), lowest eye y %.1f (limit %d), lowest mouth y %.1f (limit %d)\n", checked, (double)worst_top,
           ML_ZONE_EYE_TOP, (double)worst_bottom, ML_ZONE_Y1 - 4, (double)worst_mouth_end, ML_ZONE_MOUTH_END);
    if (fails) {
        printf("%d failures\n", fails);
        return 1;
    }
    printf("face_zone_core_test: all passed\n");
    return 0;
}
