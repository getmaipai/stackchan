/* Host test for the dance session of patch SF51: a dance chosen by hand runs the whole ladder on a synthetic beat. cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include <string.h>
#include "maipai_dance_ladder_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

int main(void)
{
    /* the tempo of each named dance: a session for four, none for a gesture */
    CHECK(mdl_synth_bpm_for("happy") == 90 && mdl_synth_bpm_for("robot") == 120 && mdl_synth_bpm_for("panic") == 140 && mdl_synth_bpm_for("look_around") == 80);
    CHECK(mdl_synth_bpm_for("bow") == -1 && mdl_synth_bpm_for("") == -1 && mdl_synth_bpm_for(NULL) == -1);

    /* the whole ladder with no microphone: 1, 2, 3, 4, then 3, 2, 1, 0, once a second, at 120 BPM and 45 s of music */
    mdl_synth_t y;
    mdl_t s;
    mdl_synth_start(&y, 1000, 120, 45000);
    CHECK(y.period_ms == 500);
    mdl_start(&s, 4, 1000);
    int seq[16], n = 0, last = 1;
    seq[n++] = 1;
    uint32_t reached4 = 0, left4 = 0, over = 0;
    for (uint32_t now = 2000; now < 200000 && over == 0; now += 1000) {
        mdl_in_t in;
        mdl_synth_input(&y, now, &in);
        const int stage = mdl_step(&s, &in);
        if (stage != last) {
            if (n < 16) seq[n++] = stage;
            if (stage == 4 && reached4 == 0) reached4 = now;
            if (last == 4 && stage < 4) left4 = now;
            if (stage == 0) over = now;
            last = stage;
        }
    }
    const int want[] = {1, 2, 3, 4, 3, 2, 1, 0};
    CHECK(n == 8);
    for (int i = 0; i < 8 && i < n; i++) CHECK(seq[i] == want[i]);
    CHECK(over != 0 && over - 1000 < 75000);           /* it ends by itself, inside the cycle cap */
    CHECK(reached4 - 1000 >= 1500 + 4000 + 4000);       /* it climbed no faster than the dwell table: eyes 3 beats (1.5 s), two steps of 8 beats (4 s each at 500 ms) */
    /* the peak holds its 24 beats and then the first down dwell is spent at step 4 before the stage drops: 12 s + 2 s at 120 BPM */
    CHECK(left4 - reached4 >= 12000u && left4 - reached4 <= 14500u);

    /* the cycle with a quiet first step: a session with max_stage 2 never goes past the nod */
    mdl_synth_start(&y, 0, 90, 30000);
    mdl_start(&s, 2, 0);
    int top = 0;
    for (uint32_t now = 1000; now < 120000; now += 1000) {
        mdl_in_t in;
        mdl_synth_input(&y, now, &in);
        const int st = mdl_step(&s, &in);
        if (st > top) top = st;
        if (st == 0) break;
    }
    CHECK(top == 2);

    /* the show at each step */
    mdl_show_t sh;
    mdl_show_for_step(0, 1, &sh);
    CHECK(sh.notes == 0 && sh.disco == 0 && !sh.confetti && !sh.clear_overlays);
    mdl_show_for_step(1, 2, &sh);
    CHECK(sh.notes == 1 && sh.disco == 0);
    mdl_show_for_step(2, 3, &sh);
    CHECK(sh.notes == 2 && sh.disco == 1 && !sh.confetti);
    mdl_show_for_step(3, 4, &sh);
    CHECK(sh.notes == 3 && sh.disco == 2 && sh.confetti == 1);
    mdl_show_for_step(4, 3, &sh);
    CHECK(sh.disco == 1 && sh.confetti == 0 && !sh.clear_overlays);
    mdl_show_for_step(3, 2, &sh);
    CHECK(sh.clear_overlays == 1 && sh.disco == 0 && sh.notes == 1);
    mdl_show_for_step(2, 1, &sh);
    CHECK(!sh.clear_overlays);

    /* the faces: from the step's list, never one of the last two */
    uint32_t rng = 12345;
    uint8_t hist[2] = {0xff, 0xff};
    int prev1 = -1, prev2 = -1;
    for (int i = 0; i < 200; i++) {
        const int stage = 2 + (i % 3);
        const int f = mdl_face_next(&rng, stage, hist);
        CHECK(f >= 0 && f < MDL_FACE_COUNT);
        int in_pool = 0;
        for (int k = 0; k < MDL_FACE_POOL_N[stage]; k++) in_pool |= (MDL_FACE_POOL[stage][k] == f);
        CHECK(in_pool);
        if (i > 1) CHECK(f != prev1 && f != prev2);
        prev2 = prev1;
        prev1 = f;
    }

    /* the ring: the breath stays between 10 and 18 percent of full and under the 50 percent cap, the chase between 8 and 30, always under the cap */
    uint8_t px[MDL_RING_PIXELS][3];
    int max_breath = 0, min_breath = 255;
    for (uint32_t t = 0; t < 8000; t += 37) {
        mdl_ring_breath(px, t, 500, 1);
        for (int i = 0; i < MDL_RING_PIXELS; i++) for (int k = 0; k < 3; k++) {
            if (px[i][k] > max_breath) max_breath = px[i][k];
            if (px[i][1] != 0 && px[i][1] < min_breath) min_breath = px[i][1];
        }
    }
    CHECK(max_breath <= MDL_RING_CHANNEL_MAX * 18 / 100 + 1 && max_breath > MDL_RING_CHANNEL_MAX * 17 / 100 - 5);
    CHECK(min_breath >= MDL_RING_CHANNEL_MAX * 10 / 100 * 77 / 255 - 1);
    mdl_ring_breath(px, 1000, 0, 0);  /* an unknown beat is 600 ms; a quiet room uses 60 percent of the swell */
    int cap = MDL_RING_CHANNEL_MAX * MDL_RING_CAP_PCT / 100;
    for (uint32_t b = 0; b < 40; b++) {
        for (int level = 0; level <= 100; level += 25) {
            for (int down = 0; down < 2; down++) {
                mdl_ring_chase(px, b, level, down);
                for (int i = 0; i < MDL_RING_PIXELS; i++) {
                    for (int k = 0; k < 3; k++) CHECK(px[i][k] <= cap);
                }
                const int head = (int)(b % MDL_RING_PIXELS), far = (head + 5) % MDL_RING_PIXELS;
                int hmax = px[head][0] > px[head][1] ? px[head][0] : px[head][1];
                int fmax = px[far][0] > px[far][1] ? px[far][0] : px[far][1];
                CHECK(hmax > fmax);   /* the head is brighter than the wash, on the way up and down at any level */
            }
        }
    }
    mdl_ring_chase(px, 5, 50, 0);                                   /* the head is gold at pixel 5 and lime at pixel 4 */
    CHECK(px[5][0] > px[5][2] && px[4][1] > px[4][0]);
    if (failures) return 1;
    printf("dance synth ok\n");
    return 0;
}
