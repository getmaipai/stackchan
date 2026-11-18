/* Host test of the question and answer game screens' core (patch UX17): every target is finger size on the 8 px margin and gap, taps land on the right button, the words fit the rules. */
#include <stdio.h>
#include <string.h>
#include "maipai_qa_core.h"

static int failures = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); failures++; } } while (0)

static void check_layout(const mqa_rect_t* r, int n)
{
    for (int i = 0; i < n; i++) {
        CHECK(r[i].h >= MQA_BTN_H && r[i].w >= 96);                                   /* the primary target of the screen standard */
        CHECK(r[i].x >= MQA_MARGIN && r[i].x + r[i].w <= MQA_W - MQA_MARGIN);
        CHECK(r[i].y >= 100 && r[i].y + r[i].h <= MQA_H - MQA_MARGIN);                /* under the words, an 8 px margin at the bottom */
        for (int j = 0; j < i; j++) {
            CHECK(r[i].x + r[i].w + MQA_GAP <= r[j].x || r[j].x + r[j].w + MQA_GAP <= r[i].x || r[i].y + r[i].h + MQA_GAP <= r[j].y || r[j].y + r[j].h + MQA_GAP <= r[i].y);
        }
        CHECK(mqa_hit(r, n, r[i].x + 1, r[i].y + 1) == r[i].id && mqa_hit(r, n, r[i].x + r[i].w - 1, r[i].y + r[i].h - 1) == r[i].id);
    }
    CHECK(mqa_hit(r, n, 2, 150) == MQA_B_NONE && mqa_hit(r, n, 160, 40) == MQA_B_NONE);   /* a margin and the words hit nothing */
}

int main(void)
{
    mqa_rect_t r[6];
    for (int has = 0; has <= 1; has++) {
        for (int rev = 0; rev <= 1; rev++) {
            const int n = mqa_riddle_buttons(has, rev, r);
            check_layout(r, n);
            CHECK(n == 2 && r[1].id == MQA_B_STOP);
            CHECK(r[0].id == ((has && !rev) ? MQA_B_REVEAL : MQA_B_NEXT));          /* Reveal only while there is an answer to reveal */
        }
    }
    for (int a = 2; a <= 4; a++) {
        const int n = mqa_trivia_buttons(a, r);
        check_layout(r, n);
        CHECK(n == a);
        for (int i = 0; i < n; i++) CHECK(r[i].id == MQA_B_ANSWER0 + i);
    }
    CHECK(mqa_trivia_buttons(9, r) == 4 && mqa_trivia_buttons(0, r) == 2);           /* clamped */
    { const int n = mqa_trivia_buttons(3, r); CHECK(r[2].w == 304 && r[2].x == MQA_MARGIN && r[2].y > r[0].y && n == 3); }   /* the third answer takes the second row's full width */
    { const int n = mqa_twenty_buttons(r); check_layout(r, n); CHECK(n == 5 && r[0].id == MQA_B_YES && r[1].id == MQA_B_NO && r[2].id == MQA_B_MAYBE && r[3].id == MQA_B_GIVE_UP && r[4].id == MQA_B_STOP); }
    /* the words box: the header at y 30, the words y 50 to 108, the first buttons at y 112 */
    CHECK(MQA_HEADER_Y >= 28 && MQA_HEADER_Y + 19 <= MQA_BODY_Y && MQA_BODY_Y + MQA_TEXT_H <= 112);
    CHECK(mqa_font_px(10) == 20 && mqa_font_px(MQA_LONG) == 20 && mqa_font_px(MQA_LONG + 1) == 16 && MQA_MAX >= MQA_LONG);
    CHECK(mqa_typed_chars(50, 0, 20) == 0 && mqa_typed_chars(50, 1000, 20) == 20 && mqa_typed_chars(50, 9000, 20) == 50 && mqa_typed_chars(50, 1000, 0) == 1);
    for (int es = 0; es <= 1; es++) {
        for (int id = MQA_B_NEXT; id <= MQA_B_GIVE_UP; id++) {
            const char* w = mqa_word(id, es);
            if (id >= MQA_B_ANSWER0 && id <= MQA_B_ANSWER3) { CHECK(w[0] == '\0'); continue; }   /* an answer tile shows the game's own words */
            CHECK(w[0] != '\0');
            for (const char* p = w; *p; p++) CHECK((unsigned char)*p < 128);          /* plain ASCII: the games' fonts have no accents */
        }
        const char* all[] = {mqa_kind_word(0, es), mqa_kind_word(1, es), mqa_say_hint(es), mqa_right_word(es), mqa_wrong_word(es)};
        for (unsigned i = 0; i < sizeof(all) / sizeof(all[0]); i++) for (const char* p = all[i]; *p; p++) CHECK((unsigned char)*p < 128);
    }
    if (failures == 0) printf("all passed\n");
    return failures == 0 ? 0 : 1;
}
