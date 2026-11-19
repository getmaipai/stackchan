/* Host test for the new look of the shared game-over screen (patch UX15d): the words in six languages, the count-up, the confetti, the easings, the dirty rectangles and the tones. */
#include <stdio.h>
#include <string.h>
#include "maipai_game_over_core.h"

static int fails = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)

int main(void)
{
    /* every word exists in every language, in plain ASCII, and the old es functions give the same Spanish as the new table */
    for (int lang = 0; lang < MGO_LANGS; lang++) {
        for (int r = MGO_WON; r <= MGO_TIMEUP; r++) {
            const char* w = mgo_title_l(r, lang);
            CHECK(w != NULL && w[0] != '\0');
            for (const char* p = w; *p; p++) CHECK((unsigned char)*p < 128);
        }
        for (int b = MGO_BTN_AGAIN; b <= MGO_BTN_QUIT; b++) CHECK(mgo_button_label_l(b, lang)[0] != '\0');
        CHECK(mgo_new_best_label_l(lang)[0] != '\0');
    }
    for (int r = MGO_WON; r <= MGO_TIMEUP; r++) {
        CHECK(strcmp(mgo_title(r, 0), mgo_title_l(r, MGO_LANG_EN)) == 0);
        CHECK(strcmp(mgo_title(r, 1), mgo_title_l(r, MGO_LANG_ES)) == 0);
    }
    CHECK(strcmp(mgo_new_best_label(1), mgo_new_best_label_l(MGO_LANG_ES)) == 0 && strcmp(mgo_button_label(MGO_BTN_QUIT, 1), mgo_button_label_l(MGO_BTN_QUIT, MGO_LANG_ES)) == 0);
    CHECK(strcmp(mgo_title_l(MGO_WON, 99), "You won!") == 0);   /* an unknown language falls back to English */

    /* the easings stay in range and end where they should */
    CHECK(mgo_ease_out(0) == 0 && mgo_ease_out(1000) == 1000 && mgo_ease_out(500) > 500);
    CHECK(mgo_ease_back(0) == 0 && mgo_ease_back(1000) == 1000);
    int over = 0;
    for (int p = 0; p <= 1000; p += 10) if (mgo_ease_back(p) > 1000) over = 1;
    CHECK(over);   /* the back easing overshoots */
    CHECK(mgo_emblem_dy(0) < -20 && mgo_emblem_dy(MGO2_DROP_MS) == 0 && mgo_emblem_dy(5000) == 0);

    /* the count-up: starts at 0, never goes down, ends on the target and stays there */
    CHECK(mgo_countup(66, 0) == 0 && mgo_countup(66, MGO2_COUNT_START) == 0 && mgo_countup(66, 5000) == 66 && mgo_countup(0, 300) == 0);
    int prev = 0;
    for (uint32_t t = 0; t < 1400; t += 15) {
        const int v = mgo_countup(301, t);
        CHECK(v >= prev && v <= 301);
        prev = v;
    }
    int pos, len, val;
    CHECK(mgo_first_number("Score 66", &pos, &len, &val) && pos == 6 && len == 2 && val == 66);
    CHECK(mgo_first_number("Match 2 to 1", &pos, &len, &val) && pos == 6 && len == 1 && val == 2);
    CHECK(!mgo_first_number("Boom!", &pos, &len, &val) && !mgo_first_number("", &pos, &len, &val) && !mgo_first_number(NULL, &pos, &len, &val));
    CHECK(!mgo_first_number("Score 1234567", &pos, &len, &val));

    /* the confetti stays inside its band, never before it starts or after it ends, and fades out */
    int drawn = 0, faded = 0;
    for (int i = 0; i < MGO2_CONFETTI; i++) {
        for (uint32_t t = 0; t < 2500; t += 10) {
            int x, y, w, h, c, o;
            if (mgo_confetti(i, t, &x, &y, &w, &h, &c, &o)) {
                drawn++;
                CHECK(t < MGO2_CONFETTI_END);
                CHECK(y >= MGO2_BAND_Y && y + h <= MGO2_BAND_Y + MGO2_BAND_H);
                CHECK((i & 1) ? (x >= MGO2_COL_R_X && x + w <= MGO2_COL_R_X + MGO2_COL_W) : (x >= MGO2_COL_L_X && x + w <= MGO2_COL_L_X + MGO2_COL_W));   /* every piece stays in its own column */
                CHECK(c >= 0 && c < 6 && o >= 0 && o <= 255 && w >= 4 && h >= 6);
                if (o < 255) faded++;
            } else if (t > 600) {
                CHECK(t >= MGO2_CONFETTI_END);   /* after every piece has started, only the end stops it */
            }
        }
    }
    CHECK(MGO2_CONFETTI == 8 && drawn > 300 && faded > 10);
    CHECK(mgo_has_confetti(MGO_WON, 0) && mgo_has_confetti(MGO_LOST, 1) && !mgo_has_confetti(MGO_LOST, 0) && !mgo_has_confetti(MGO_DRAW, 0));

    /* the dirty rectangles: small, inside the glass, every one of them held by something that moves, nothing after the end, and the motion rule's numbers (mean at most 4,000 px, worst at most 9,000 px, and at most 3 rectangles a step) */
    for (int r = MGO_WON; r <= MGO_TIMEUP; r++) {
        for (int nb = 0; nb < 2; nb++) {
            long area = 0, worst = 0, frames = 0;
            uint32_t before = 0;
            for (uint32_t t = 0; t <= 1800; t += 30) {
                mgo_rect_t rr[MGO2_MAX_RECTS];
                const int n = mgo_dirty(r, nb, 2, 110, before, t, rr);
                long a = 0;
                static unsigned char mark[240][320];   /* the area of the union: overlapping rectangles count once */
                memset(mark, 0, sizeof(mark));
                CHECK(n <= 3);   /* each rectangle is a separate transfer on the unit: never more than three on a step */
                for (int i = 0; i < n; i++) {
                    CHECK(rr[i].w > 0 && rr[i].h > 0 && rr[i].x >= 0 && rr[i].y >= MGO2_BAND_Y - 2 && rr[i].x + rr[i].w <= 320 && rr[i].y + rr[i].h <= 240);
                    for (int y = rr[i].y; y < rr[i].y + rr[i].h && y < 240; y++)
                        for (int x = rr[i].x; x < rr[i].x + rr[i].w && x < 320; x++) mark[y][x] = 1;
                }
                for (int y = 0; y < 240; y++)
                    for (int x = 0; x < 320; x++) a += mark[y][x];
                area += a; if (a > worst) worst = a; frames++;
                before = t;
            }
            CHECK(area / frames <= 4000 && worst <= 9000);
        }
    }
    {   /* nothing after the end */
        mgo_rect_t rr[MGO2_MAX_RECTS];
        CHECK(mgo_dirty(MGO_WON, 0, 2, 110, MGO2_ANIM_MS, MGO2_ANIM_MS + 100, rr) == 0);
    }
    CHECK(mgo_q60(0) == 0 && mgo_q60(59) == 0 && mgo_q60(60) == 60 && mgo_q60(125) == 120);
    {   int dx; CHECK(!mgo_glint(420, &dx) && mgo_glint(480, &dx) && dx == -14 && mgo_glint(840, &dx) && dx > -14 && dx <= 10 && !mgo_glint(900, &dx)); }
    CHECK(mgo_bump(0) == 0 && mgo_bump(600) == 4 && mgo_bump(720) == 0);

    /* the flourish: every outcome has one, rising for a win, falling for a loss, short */
    for (int r = MGO_WON; r <= MGO_TIMEUP; r++) {
        for (int nb = 0; nb < 2; nb++) {
            const mgo_tone_t* t;
            const int n = mgo_tones(r, nb, &t);
            int ms = 0;
            CHECK(n >= 2);
            int tone_ms = 0;
            for (int i = 0; i < n; i++) { CHECK(t[i].hz >= 200 && t[i].hz <= 4000 && t[i].ms > 0); ms += t[i].ms + 20; tone_ms += t[i].ms; }
            CHECK(ms <= 700 && tone_ms <= 600);
        }
    }
    const mgo_tone_t* w; const mgo_tone_t* l;
    const int nw = mgo_tones(MGO_WON, 0, &w), nl = mgo_tones(MGO_LOST, 0, &l);
    CHECK(w[nw - 1].hz > w[0].hz && l[nl - 1].hz < l[0].hz);
    /* the games keep calling set_pop until MGO_POP_MS + 40: it must be after the motion ends, and the old pop is still the first 160 ms */
    CHECK(MGO_POP_MS > MGO2_ANIM_MS + 40 && MGO_FACE_POP_MS == 160u && mgo_icon_scale(0) == 1000 && mgo_icon_scale(80) > 1100 && mgo_icon_scale(160) == 1000);
    if (fails == 0) printf("all passed\n");
    return fails == 0 ? 0 : 1;
}
