/* Host test of Dice Poker's core (patch UX18): every hand ranks as the poker-dice counts say, the rolls and holds follow the rules, five rounds end the game, the targets are finger size. */
#include <stdio.h>
#include "maipai_dicepoker_core.h"

static int failures = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); failures++; } } while (0)

int main(void)
{
    /* all 7776 hands: the counts of a standard poker dice table */
    int count[DP_RANKS] = {0};
    uint8_t d[DP_DICE];
    for (int n = 0; n < 7776; n++) {
        int x = n;
        for (int i = 0; i < DP_DICE; i++) { d[i] = (uint8_t)(1 + x % 6); x /= 6; }
        count[dp_rank(d)]++;
    }
    CHECK(count[DP_FIVE] == 6 && count[DP_FOUR] == 150 && count[DP_FULL] == 300 && count[DP_THREE] == 1200 && count[DP_TWO_PAIR] == 1800 && count[DP_PAIR] == 3600);
    CHECK(count[DP_STRAIGHT] == 240 && count[DP_HIGH] == 480);
    { const uint8_t s1[5] = {1, 2, 3, 4, 5}, s2[5] = {6, 5, 4, 3, 2}, no[5] = {1, 2, 3, 4, 6}; CHECK(dp_rank(s1) == DP_STRAIGHT && dp_rank(s2) == DP_STRAIGHT && dp_rank(no) == DP_HIGH); }
    for (int r = 1; r < DP_RANKS; r++) CHECK(DP_POINTS[r] > DP_POINTS[r - 1]);   /* a better hand always scores more */
    /* the round: roll, hold, re-roll twice, keep */
    dp_t g;
    dp_init(&g, 42);
    CHECK(g.phase == DP_PHASE_ROLL && g.round == 1 && g.score == 0 && dp_keep(&g) == -1 && dp_toggle_hold(&g, 0) == 0);
    CHECK(dp_roll(&g) == 1 && g.phase == DP_PHASE_HOLD && g.rolls_left == 2);
    for (int i = 0; i < DP_DICE; i++) CHECK(g.d[i] >= 1 && g.d[i] <= 6);
    CHECK(dp_toggle_hold(&g, 1) == 1 && dp_toggle_hold(&g, 3) == 1 && g.held == ((1u << 1) | (1u << 3)));
    { const uint8_t keep1 = g.d[1], keep3 = g.d[3]; CHECK(dp_roll(&g) == 1 && g.d[1] == keep1 && g.d[3] == keep3 && g.rolls_left == 1); }
    CHECK(dp_toggle_hold(&g, 1) == 1 && g.held == (1u << 3));
    CHECK(dp_roll(&g) == 1 && g.rolls_left == 0);
    CHECK(dp_roll(&g) == 0 && dp_toggle_hold(&g, 0) == 0);                       /* no more re-rolls: keep is all that is left */
    { const int pts = dp_keep(&g); CHECK(pts >= 0 && g.score == pts && g.round == 2 && g.phase == DP_PHASE_ROLL); }
    /* holding all five leaves nothing to re-roll */
    dp_init(&g, 7);
    dp_roll(&g);
    for (int i = 0; i < DP_DICE; i++) dp_toggle_hold(&g, i);
    CHECK(g.held == 0x1F && dp_roll(&g) == 0);
    /* five rounds end the game; the same seed plays the same game */
    dp_t a, b;
    dp_init(&a, 99); dp_init(&b, 99);
    for (int r = 0; r < DP_ROUNDS; r++) { dp_roll(&a); dp_roll(&b); CHECK(dp_keep(&a) == dp_keep(&b)); }
    CHECK(a.phase == DP_PHASE_DONE && a.score == b.score && dp_roll(&a) == 0);
    /* the targets: 8 px margin, 8 px gaps, finger size, nothing off the glass */
    dp_init(&g, 1);
    dp_rect_t r[8];
    int n = dp_buttons(&g, r);
    CHECK(n == 1 && r[0].id == DP_B_ROLL && r[0].h >= 56 && r[0].x >= 8 && r[0].x + r[0].w <= 312 && r[0].y + r[0].h + 8 <= 240);
    dp_roll(&g);
    n = dp_buttons(&g, r);
    CHECK(n == DP_DICE + 2);
    for (int i = 0; i < n; i++) {
        CHECK(r[i].w >= 48 && r[i].h >= 48 && r[i].x >= 8 && r[i].x + r[i].w <= 320 - 8 && r[i].y >= 52 && r[i].y + r[i].h + 8 <= 240);
        for (int j = 0; j < i; j++) CHECK(r[i].x + r[i].w + 8 <= r[j].x || r[j].x + r[j].w + 8 <= r[i].x || r[i].y + r[i].h + 8 <= r[j].y || r[j].y + r[j].h + 8 <= r[i].y);
        CHECK(dp_hit(r, n, r[i].x + 1, r[i].y + 1) == r[i].id);
    }
    CHECK(r[DP_DICE].h >= 56 && r[DP_DICE + 1].h >= 56);                          /* Roll again and Keep are primary targets */
    CHECK(dp_hit(r, n, 2, 100) == DP_B_NONE && dp_hit(r, n, 160, 150) == DP_B_NONE);
    for (int es = 0; es <= 1; es++) for (int k = 0; k < DP_RANKS; k++) for (const char* p = dp_rank_name(k, es); *p; p++) CHECK((unsigned char)*p < 128);   /* plain ASCII */
    if (failures == 0) printf("all passed\n");
    return failures == 0 ? 0 : 1;
}
