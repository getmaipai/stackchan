/* Host test of maipai_hilo_core.h (patch UX21, Higher or Lower): the deck, the three answers, the end, the odds hint and the finger-size targets. Placement: host-side test. Upstream: none. */
#include <stdio.h>
#include <string.h>
#include "maipai_hilo_core.h"

#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); return 1; } } while (0)

int main(void)
{
    /* every seed gives a full deck: each of the 52 cards once */
    for (uint32_t seed = 1; seed < 200; seed++) {
        hl_t g;
        hl_init(&g, seed);
        int seen[HL_DECK] = {0};
        for (int i = 0; i < HL_DECK; i++) { CHECK(g.deck[i] < HL_DECK); seen[g.deck[i]]++; }
        for (int i = 0; i < HL_DECK; i++) CHECK(seen[i] == 1);
        CHECK(g.phase == HL_PLAY && g.streak == 0 && g.pos == 0);
    }
    { /* the same seed gives the same deck, another seed another */
        hl_t a, b, c;
        hl_init(&a, 7); hl_init(&b, 7); hl_init(&c, 8);
        CHECK(memcmp(a.deck, b.deck, HL_DECK) == 0 && memcmp(a.deck, c.deck, HL_DECK) != 0);
    }
    { /* the rank and suit of a card; aces low */
        CHECK(hl_rank(0) == 1 && hl_rank(12) == 13 && hl_rank(13) == 1 && hl_suit(13) == 1 && hl_suit(51) == 3);
        CHECK(!hl_red(0) && hl_red(13) && hl_red(26) && !hl_red(39));
        CHECK(strcmp(hl_rank_text(0), "A") == 0 && strcmp(hl_rank_text(9), "10") == 0 && strcmp(hl_rank_text(12), "K") == 0);
    }
    { /* a hand-made deck: ranks 5, 9, 9, 3 and then 8 */
        hl_t g;
        hl_init(&g, 1);
        const int ranks[] = {5, 9, 9, 3, 8};
        for (int i = 0; i < 5; i++) g.deck[i] = (uint8_t)(ranks[i] - 1 + 13 * (i % 4));
        CHECK(hl_guess(&g, 1) == HL_RIGHT && g.streak == 1 && g.pos == 1 && g.last_result == HL_RIGHT && g.phase == HL_PLAY);   /* 5 then 9: higher is right */
        CHECK(hl_guess(&g, 0) == HL_PUSH && g.streak == 1 && g.pushes == 1 && g.pos == 2 && g.phase == HL_PLAY);               /* 9 then 9: the same rank, a push */
        CHECK(hl_guess(&g, 0) == HL_RIGHT && g.streak == 2 && g.pos == 3);                                                      /* 9 then 3: lower is right */
        CHECK(hl_guess(&g, 0) == HL_WRONG && g.streak == 2 && g.phase == HL_OVER && g.last_result == HL_WRONG);                 /* 3 then 8: lower is wrong, the game ends */
        CHECK(hl_guess(&g, 1) == HL_IGNORED && g.streak == 2);                                                                  /* nothing after the end */
    }
    { /* the odds hint counts what is left after the current card */
        hl_t g;
        hl_init(&g, 3);
        int o[3];
        hl_remaining(&g, o);
        CHECK(o[0] + o[1] + o[2] == HL_DECK - 1);
        const int a = hl_rank(g.deck[0]);
        CHECK(o[2] == 3 || o[2] <= 3);                       /* at most the three other cards of the same rank */
        CHECK(o[0] <= (13 - a) * 4 && o[1] <= (a - 1) * 4);
    }
    { /* always saying higher on a deck sorted up reaches the end of the deck: the game ends with the streak at the card count minus one minus the pushes */
        hl_t g;
        hl_init(&g, 5);
        int k = 0;
        for (int r = 1; r <= 13; r++) for (int s = 0; s < 4; s++) g.deck[k++] = (uint8_t)(s * 13 + r - 1);
        int guesses = 0;
        while (g.phase == HL_PLAY && guesses < 100) { CHECK(hl_guess(&g, 1) != HL_WRONG); guesses++; }
        CHECK(g.phase == HL_OVER && guesses == HL_DECK - 1 && g.streak + g.pushes == HL_DECK - 1);
    }
    { /* a long random game never reads outside the deck */
        for (uint32_t seed = 1; seed < 300; seed++) {
            hl_t g;
            hl_init(&g, seed);
            int n = 0;
            while (g.phase == HL_PLAY) { const int cur = hl_rank(hl_current(&g)); hl_guess(&g, cur <= 7); n++; CHECK(n < 60); }
            CHECK(g.pos < HL_DECK && g.streak <= HL_DECK - 1);
        }
    }
    { /* the strategy of the better side wins more than a coin: higher on low cards, lower on high ones, beats always-higher over many games */
        long smart = 0, naive = 0;
        for (uint32_t seed = 1; seed < 1000; seed++) {
            hl_t a, b;
            hl_init(&a, seed); hl_init(&b, seed);
            while (a.phase == HL_PLAY) hl_guess(&a, hl_rank(hl_current(&a)) <= 7);
            while (b.phase == HL_PLAY) hl_guess(&b, 1);
            smart += a.streak; naive += b.streak;
        }
        CHECK(smart > naive);
    }
    { /* finger size: two buttons 148 by 56, 8 px apart, 8 px from the glass edge; the cards stay 8 px clear of them */
        hl_rect_t r[2];
        CHECK(hl_buttons(r) == 2);
        CHECK(r[0].w >= 70 && r[0].h >= 56 && r[1].w >= 70 && r[1].h >= 56);
        CHECK(r[1].x - (r[0].x + r[0].w) >= 8 && r[0].x >= 8 && r[1].x + r[1].w <= 312 && r[0].y + r[0].h + 8 <= 240);
        CHECK(hl_hit(r, 2, 20, 190) == HL_B_HIGHER && hl_hit(r, 2, 300, 190) == HL_B_LOWER && hl_hit(r, 2, 160, 190) == HL_B_NONE && hl_hit(r, 2, 20, 100) == HL_B_NONE);
        for (int w = 0; w < 2; w++) {
            int x, y, cw, ch;
            hl_card_box(w, &x, &y, &cw, &ch);
            CHECK(y + ch + 8 <= r[0].y && x >= 8 && x + cw <= 312);
        }
    }
    puts("hilo_core_test: all passed");
    return 0;
}
