/* Host test of the shared game-over screen's core (patch UX15): the layout meets the screen standard, taps land on the right button, the texts and cues are right.
 * Build: cc -std=c99 -Wall -Wextra -Werror -I<dir with maipai_game_over_core.h> game_over_core_test.c */
#include <stdio.h>
#include <string.h>
#include "maipai_game_over_core.h"

static int failures = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); failures++; } } while (0)

int main(void)
{
    int x1, y1, w1, h1, x2, y2, w2, h2;
    mgo_button(MGO_BTN_AGAIN, &x1, &y1, &w1, &h1);
    mgo_button(MGO_BTN_QUIT, &x2, &y2, &w2, &h2);
    CHECK(w1 >= 56 && h1 >= 56 && w2 >= 56 && h2 >= 56);                 /* the primary target of the screen standard */
    CHECK(x1 >= 8 && x2 + w2 <= MGO_W - 8 && y1 + h1 <= MGO_H - 8);      /* an 8 px margin */
    CHECK(x2 - (x1 + w1) >= 8);                                           /* an 8 px gap between the buttons */
    CHECK(y1 == y2 && h1 == h2);
    /* the words stack above the buttons without touching: icon, title, score, best */
    CHECK(MGO_ICON_CY + MGO_ICON_R + 4 <= MGO_TITLE_Y && MGO_TITLE_Y + 28 <= MGO_SCORE_Y && MGO_SCORE_Y + 23 <= MGO_BEST_Y && MGO_BEST_Y + 19 <= MGO_BTN_Y - 4);
    CHECK(MGO_ICON_CY - MGO_ICON_R >= 28);                                /* under the banner row */
    /* touches */
    CHECK(mgo_hit(x1 + 1, y1 + 1) == MGO_BTN_AGAIN && mgo_hit(x1 + w1 - 1, y1 + h1 - 1) == MGO_BTN_AGAIN);
    CHECK(mgo_hit(x2 + 1, y2 + 1) == MGO_BTN_QUIT && mgo_hit(x2 + w2 - 1, y2 + h2 - 1) == MGO_BTN_QUIT);
    CHECK(mgo_hit(x1 + w1 + 3, y1 + 20) == MGO_BTN_NONE);                /* the gap hits nothing */
    CHECK(mgo_hit(2, y1 + 20) == MGO_BTN_NONE && mgo_hit(318, y1 + 20) == MGO_BTN_NONE);
    CHECK(mgo_hit(160, 100) == MGO_BTN_NONE && mgo_hit(100, y1 - 1) == MGO_BTN_NONE);
    /* texts */
    CHECK(strcmp(mgo_title(MGO_WON, 0), "You won!") == 0 && strcmp(mgo_title(MGO_LOST, 0), "You lost") == 0 && strcmp(mgo_title(MGO_DRAW, 0), "Draw") == 0);
    CHECK(strcmp(mgo_title(MGO_OVER, 0), "Game over") == 0 && strcmp(mgo_title(MGO_TIMEUP, 0), "Time's up") == 0 && strcmp(mgo_title(MGO_OVER, 1), "Fin del juego") == 0);   /* no verdict words for a score-only game (decision 33) */
    CHECK(strstr(mgo_title(MGO_OVER, 0), "won") == NULL && strstr(mgo_title(MGO_OVER, 0), "lost") == NULL && strstr(mgo_title(MGO_TIMEUP, 0), "won") == NULL);
    CHECK(strcmp(mgo_title(MGO_DRAW, 1), "Empate") == 0 && strcmp(mgo_button_label(MGO_BTN_QUIT, 1), "Salir") == 0 && strcmp(mgo_button_label(MGO_BTN_AGAIN, 0), "Play again") == 0);
    for (int es = 0; es <= 1; es++) {
        const char* all[] = {mgo_title(MGO_WON, es), mgo_title(MGO_LOST, es), mgo_title(MGO_DRAW, es), mgo_title(MGO_OVER, es), mgo_title(MGO_TIMEUP, es), mgo_button_label(MGO_BTN_AGAIN, es), mgo_button_label(MGO_BTN_QUIT, es), mgo_new_best_label(es)};
        for (unsigned i = 0; i < sizeof(all) / sizeof(all[0]); i++) {
            for (const char* p = all[i]; *p; p++) CHECK((unsigned char)*p < 128);   /* plain ASCII: the games' fonts have no accents */
        }
    }
    /* best scores */
    CHECK(mgo_beats_best(10, 0, 0) == 1 && mgo_beats_best(10, 9, 0) == 1 && mgo_beats_best(9, 10, 0) == 0 && mgo_beats_best(10, 10, 0) == 0);
    CHECK(mgo_beats_best(82, 96, 1) == 1 && mgo_beats_best(96, 82, 1) == 0 && mgo_beats_best(5, 0, 1) == 1 && mgo_beats_best(0, 0, 0) == 0 && mgo_beats_best(-1, 5, 1) == 0);
    /* cues and the pop */
    CHECK(mgo_cue(MGO_WON) == MGO_CUE_WIN && mgo_cue(MGO_LOST) == MGO_CUE_LOSE && mgo_cue(MGO_DRAW) == MGO_CUE_DRAW);
    CHECK(mgo_icon_scale(0) == 1000 && mgo_icon_scale(MGO_POP_MS / 2) == 1120 && mgo_icon_scale(MGO_POP_MS) == 1000 && mgo_icon_scale(5000) == 1000);
    for (uint32_t t = 0; t <= MGO_POP_MS; t += 8) CHECK(mgo_icon_scale(t) >= 1000 && mgo_icon_scale(t) <= 1120);
    if (failures == 0) printf("all passed\n");
    return failures == 0 ? 0 : 1;
}
