/* Host test for patch GM04: the Do It reaction game and the best-of-three Rock Paper Scissors, each driven by a scripted player through the
 * engine's own entries (taps, inputs, ticks at exact times), with the packs the compiler makes.
 *   cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> games_gm_test.c -o t
 *   ./t bopit.mpk rps.mpk
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maipai_games_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static uint8_t g_blob[2][MG_MAX_PACK];
static size_t g_len[2];
static mg_pack_t g_bop, g_rps;

static void load(int i, const char* path, mg_pack_t* p)
{
    FILE* f = fopen(path, "rb");
    if (f == NULL) {
        printf("cannot open %s\n", path);
        exit(2);
    }
    g_len[i] = fread(g_blob[i], 1, sizeof(g_blob[i]), f);
    fclose(f);
    CHECK(mg_parse(g_blob[i], g_len[i], p) == MG_OK);
}

static int cx(const mg_pack_t* p, int region)
{
    mg_region_t r;
    mg_region_get(p, region, &r);
    return r.x + r.w / 2;
}
static int cy(const mg_pack_t* p, int region)
{
    mg_region_t r;
    mg_region_get(p, region, &r);
    return r.y + r.h / 2;
}

/* The time jumps to when the present timer is due, and the timer fires. Returns that time. */
static uint32_t due(mg_run_t* r)
{
    const uint32_t t = r->timer_due_ms;
    mg_tick(r, t);
    return t;
}

static int texts_visible(const mg_run_t* r, const char* want, int es)
{
    char buf[MG_TEXT_LEN + 8];
    int n = 0;
    for (int i = 0; i < r->p->n_shapes; i++) {
        mg_shape_t s;
        mg_shape_get(r->p, i, &s);
        if (s.type == MG_SH_TEXT && mg_shape_visible(r, i)) {
            mg_text(r, s.text, es, buf, sizeof(buf));
            n += strcmp(buf, want) == 0;
        }
    }
    return n;
}

static int count_visible(const mg_run_t* r, int type)
{
    int n = 0;
    for (int i = 0; i < r->p->n_shapes; i++) {
        mg_shape_t s;
        mg_shape_get(r->p, i, &s);
        n += s.type == type && mg_shape_visible(r, i);
    }
    return n;
}

/* ------------------------------------------------------------------ Do It */
enum { B_INTRO = 0, B_WAIT, B_SHOW, B_OK, B_OVER };
enum { A_TAP = 0, A_SWL, A_SWR, A_SHAKE, A_PET, A_TILT };
#define CTR_SCORE 0
#define CTR_ACT 1
#define CTR_LIMIT 2
#define CTR_REASON 3 /* the "tmp" counter holds why the run ended: 0 too early, 1 wrong move, 2 too slow */
#define CTR_CUE 4

/* Does action `act` the way a person would: the matching gesture. */
static void bop_do(mg_run_t* r, int act, uint32_t now)
{
    switch (act) {
        case A_TAP: mg_tap(r, 160, 120, now); break;
        case A_SWL: mg_input(r, MG_EV_SWIPE_L, now); break;
        case A_SWR: mg_input(r, MG_EV_SWIPE_R, now); break;
        case A_SHAKE: mg_input(r, MG_EV_SHAKE, now); break;
        case A_PET: mg_input(r, MG_EV_PET, now); break;
        default: mg_input(r, MG_EV_TILT_L + (int)(now / 30) % 4, now); break;
    }
}

/* A gesture that is not the one called for `act`. */
static void bop_wrong(mg_run_t* r, int act, uint32_t now)
{
    if (act == A_SWL) {
        mg_input(r, MG_EV_SWIPE_R, now);
    } else {
        mg_input(r, MG_EV_SWIPE_L, now);
    }
}

static int doit_limit_after(int rounds)
{
    int limit = 3000;
    for (int i = 0; i < rounds; i++) {
        limit -= limit / 7;
        if (limit < 650) limit = 650;
    }
    return limit;
}
static int doit_base_after(int rounds)
{
    int base = 2200;
    for (int i = 0; i < rounds; i++) {
        base -= base / 10;
        if (base < 600) base = 600;
    }
    return base;
}

/* The schedule: the time to answer starts at 3000 ms and shrinks by a seventh each round down to 650 ms; the wait before the reveal starts at
 * 2200 ms plus a random 0 to 699 and shrinks by a tenth each round down to 600 ms; the cue (the tone and the color) rises one step a round for
 * five rounds. A person who plays perfectly sees exactly these numbers. */
static void test_doit_schedule(void)
{
    const mg_pack_t* p = &g_bop;
    CHECK(p->n_regions == 1 && (p->flags & MG_FLAG_TAP_ON_RELEASE) != 0);
    mg_region_t big;
    mg_region_get(p, 0, &big);
    CHECK(big.x == 20 && big.y == 28 && big.w == 280 && big.h == 196 && big.y + big.h == MG_SAFE_BOTTOM);
    printf("Do It speed schedule (round, time to answer ms, wait before the reveal ms, cue):\n");
    int prev_limit = 99999, prev_base = 99999, lo_delay = 99999, hi_delay = 0;
    for (uint32_t seed = 1; seed <= 40; seed++) {
        mg_run_t r;
        mg_start(&r, p, 0, seed * 7919u);
        CHECK(r.state == B_INTRO && r.ctr[CTR_SCORE] == 0 && r.ctr[CTR_LIMIT] == 3000);
        uint32_t now = due(&r); /* the intro ends */
        for (int round = 1; round <= 16 && !r.finished; round++) {
            CHECK(r.state == B_WAIT);
            const int base = doit_base_after(round - 1), limit = doit_limit_after(round - 1);
            const int delay = (int)(r.timer_due_ms - r.entered_ms);
            CHECK(delay >= base && delay < base + 700);
            if (round == 1) {
                if (delay < lo_delay) lo_delay = delay;
                if (delay > hi_delay) hi_delay = delay;
            }
            CHECK(r.ctr[CTR_LIMIT] == limit);
            r.tone_n = 0;
            now = due(&r); /* the wait is over: the action is shown */
            CHECK(r.state == B_SHOW && r.ctr[CTR_ACT] >= 0 && r.ctr[CTR_ACT] < 6);
            CHECK((int)(r.timer_due_ms - r.entered_ms) == limit);
            const int level = round - 1 > 5 ? 5 : round - 1;
            CHECK(r.ctr[CTR_CUE] == 18 + level);
            CHECK(r.tone_n == 1 && r.tone_q[0] == 18 + level); /* the cue tone: a rising pitch (clips cue0 to cue5) */
            CHECK(r.sync_region == 0);                           /* it starts with the picture */
            if (seed == 1) {
                printf("  round %2d: %4d ms to answer, wait %4d to %4d ms, cue %d\n", round, limit, base, base + 699, level);
            }
            if (seed == 1) {
                CHECK(limit <= prev_limit && base <= prev_base);
                if (round > 1 && prev_limit > 650) CHECK(limit < prev_limit);
                if (round > 1 && prev_base > 600) CHECK(base < prev_base);
                prev_limit = limit;
                prev_base  = base;
            }
            bop_do(&r, r.ctr[CTR_ACT], now + 100);
            CHECK(r.state == B_OK && r.ctr[CTR_SCORE] == round);
            now = due(&r);
        }
    }
    CHECK(lo_delay >= 2200 && hi_delay < 2900 && hi_delay - lo_delay > 300); /* the first wait is random, 2200 to 2899 ms */
    CHECK(doit_limit_after(0) == 3000 && doit_limit_after(9) == 751 && doit_limit_after(10) == 650 && doit_limit_after(40) == 650);
    CHECK(doit_base_after(0) == 2200 && doit_base_after(1) == 1980 && doit_base_after(40) == 600);
}

static void test_doit_inputs(void)
{
    const mg_pack_t* p = &g_bop;
    for (int act = 0; act < 6; act++) {
        /* the right gesture scores */
        mg_run_t r;
        mg_start(&r, p, 0, 5u + (uint32_t)act);
        uint32_t now = due(&r);
        now = due(&r);
        r.ctr[CTR_ACT] = act; /* the scripted player picks the action */
        bop_do(&r, act, now + 50);
        CHECK(r.state == B_OK && r.ctr[CTR_SCORE] == 1);
        /* the matching big on-screen button counts too, whichever action is shown */
        mg_start(&r, p, 0, 50u + (uint32_t)act);
        now = due(&r);
        now = due(&r);
        r.ctr[CTR_ACT] = act;
        mg_tap(&r, cx(p, 0), cy(p, 0), now + 50);
        CHECK(r.state == B_OK && r.ctr[CTR_SCORE] == 1);
        /* a different gesture ends the run: wrong move */
        mg_start(&r, p, 0, 90u + (uint32_t)act);
        now = due(&r);
        now = due(&r);
        r.ctr[CTR_ACT] = act;
        r.save_pending = 0;
        bop_wrong(&r, act, now + 50);
        CHECK(r.state == B_OVER && r.ctr[CTR_REASON] == 1 && r.save_pending == 1);
        CHECK(texts_visible(&r, "Wrong move!", 0) == 1 && texts_visible(&r, "Movimiento incorrecto!", 1) == 1);
    }
    /* a tap while it waits is too early; a shake, a tilt or a swipe while it waits is ignored (a bump on the table is not a miss) */
    mg_run_t r;
    mg_start(&r, p, 0, 3);
    uint32_t now = due(&r);
    CHECK(r.state == B_WAIT);
    mg_input(&r, MG_EV_SHAKE, now + 10);
    mg_input(&r, MG_EV_TILT_F, now + 20);
    mg_input(&r, MG_EV_SWIPE_L, now + 30);
    mg_input(&r, MG_EV_PET, now + 40);
    CHECK(r.state == B_WAIT);
    mg_tap(&r, 160, 120, now + 50);
    CHECK(r.state == B_OVER && r.ctr[CTR_REASON] == 0 && r.ctr[CTR_SCORE] == 0 && texts_visible(&r, "Too early!", 0) == 1);
    /* no answer in time: too slow, after exactly the time to answer */
    mg_start(&r, p, 0, 4);
    now = due(&r);
    now = due(&r);
    const uint32_t shown = r.entered_ms, limit = (uint32_t)r.ctr[CTR_LIMIT];
    mg_tick(&r, shown + limit - 1);
    CHECK(r.state == B_SHOW);
    mg_tick(&r, shown + limit);
    CHECK(r.state == B_OVER && r.ctr[CTR_REASON] == 2 && texts_visible(&r, "Too slow!", 0) == 1);
    /* the answer just inside the time still scores */
    mg_start(&r, p, 0, 4);
    now = due(&r);
    now = due(&r);
    mg_tick(&r, r.entered_ms + (uint32_t)r.ctr[CTR_LIMIT] - 1);
    bop_do(&r, r.ctr[CTR_ACT], r.entered_ms + (uint32_t)r.ctr[CTR_LIMIT] - 1);
    CHECK(r.state == B_OK);
    /* an input in the pause after a good answer is ignored; the over screen ends the game and saves the score once */
    mg_start(&r, p, 0, 8);
    now = due(&r);
    now = due(&r);
    bop_do(&r, r.ctr[CTR_ACT], now + 10);
    mg_input(&r, MG_EV_SHAKE, now + 20);
    mg_tap(&r, 160, 120, now + 30);
    CHECK(r.state == B_OK && r.ctr[CTR_SCORE] == 1);
    now = due(&r);
    now = due(&r);
    bop_wrong(&r, r.ctr[CTR_ACT], now + 10);
    CHECK(r.state == B_OVER && r.save_pending == 1 && r.ctr[CTR_SCORE] == 1 && !r.finished);
    due(&r);
    CHECK(r.finished);
}

static void test_doit_screens(void)
{
    const mg_pack_t* p = &g_bop;
    static const char* const en[6] = {"Tap!", "Swipe left!", "Swipe right!", "Gentle shake!", "Pet my head!", "Tilt me!"};
    static const char* const es[6] = {"Toca!", "Desliza izq!", "Desliza der!", "Agita suave!", "Acaricia!", "Inclina!"};
    mg_run_t r;
    mg_start(&r, p, 0, 2);
    CHECK(count_visible(&r, MG_SH_ICON) == 0);
    (void)due(&r);
    /* the waiting screen: a calm word and no icon */
    CHECK(r.state == B_WAIT && count_visible(&r, MG_SH_ICON) == 0 && texts_visible(&r, "Wait...", 0) == 1 && texts_visible(&r, "Espera...", 1) == 1);
    int wait_fill_level[6] = {0}, show_fill_level[6] = {0};
    for (int level = 0; level < 6; level++) {
        r.state = B_WAIT;
        r.ctr[CTR_CUE] = 18 + level;
        for (int i = 0; i < p->n_shapes; i++) {
            mg_shape_t s;
            mg_shape_get(p, i, &s);
            if (s.type == MG_SH_FILL && s.cond_ctr == CTR_CUE && mg_shape_visible(&r, i)) wait_fill_level[level]++;
        }
        r.state = B_SHOW;
        for (int i = 0; i < p->n_shapes; i++) {
            mg_shape_t s;
            mg_shape_get(p, i, &s);
            if (s.type == MG_SH_FILL && s.cond_ctr == CTR_CUE && mg_shape_visible(&r, i)) show_fill_level[level]++;
        }
    }
    for (int level = 0; level < 6; level++) CHECK(wait_fill_level[level] == 1 && show_fill_level[level] == 1); /* one background color per level, in both screens */
    /* the reveal: one large icon whose number is the action, and the action in large text, in both languages */
    for (int act = 0; act < 6; act++) {
        r.state = B_SHOW;
        r.ctr[CTR_ACT] = act;
        CHECK(count_visible(&r, MG_SH_ICON) == 1);
        for (int i = 0; i < p->n_shapes; i++) {
            mg_shape_t s;
            mg_shape_get(p, i, &s);
            if (s.type == MG_SH_ICON && mg_shape_visible(&r, i)) {
                CHECK(r.ctr[s.cond_ctr] + s.text == act && s.w >= 120 && (s.h & MG_ICON_POP));
            }
            if (s.type == MG_SH_TEXT && mg_shape_visible(&r, i) && s.aux == 3) {
                char buf[MG_TEXT_LEN + 8];
                mg_text(&r, s.text, 0, buf, sizeof(buf));
                CHECK(strcmp(buf, en[act]) == 0);
                mg_text(&r, s.text, 1, buf, sizeof(buf));
                CHECK(strcmp(buf, es[act]) == 0); /* the extra large text */
            }
        }
    }
}

/* ------------------------------------------------------------------ Rock Paper Scissors, best of three */
enum { R_INTRO = 0, R_C1, R_C2, R_C3, R_SHOOT, R_EARLY, R_REVEAL, R_WON, R_LOST, R_WIN, R_LOSE, R_TIE, R_SLOW, R_MWIN, R_MLOSE };
enum { RC_SCORE = 0, RC_ME, RC_BOT, RC_D, RC_MW, RC_BW, RC_Z, RC_ROUND };
enum { G_ROCK = 0, G_PAPER, G_SCISSORS, G_AGAIN, G_QUIT };

/* The result of a round for the person: 1 win, 0 tie, -1 loss. */
static int rps_result(int me, int bot) { return me == bot ? 0 : (((me - bot + 3) % 3) == 1 ? 1 : -1); }

/* From the first count state (c1) to SHOOT, one beat at a time. The unit's pick is forced to `bot` once the round has started. */
static uint32_t rps_to_shoot(mg_run_t* r, uint32_t now, int bot)
{
    CHECK(r->state == R_C1);
    r->ctr[RC_BOT] = bot;
    now = due(r);
    now = due(r);
    now = due(r);
    CHECK(r->state == R_SHOOT);
    return now;
}

/* Plays one decided or tied round from c1: the person picks `me` right at SHOOT against `bot`. Returns the time of the result state. */
static uint32_t rps_round(mg_run_t* r, uint32_t now, int me, int bot)
{
    r->celebrate = 0; /* the player (not the engine) clears a celebration once it has started it */
    now = rps_to_shoot(r, now, bot);
    mg_tap(r, cx(r->p, me), cy(r->p, me), now + 150);
    CHECK(r->state == R_REVEAL && r->ctr[RC_ME] == me);
    now = due(r);
    return now;
}

static void test_rps_layout(void)
{
    const mg_pack_t* p = &g_rps;
    CHECK(p->n_regions == 5 && p->n_states == 15 && p->n_shapes <= 48);
    int x_end = 20;
    for (int i = 0; i < 3; i++) { /* three large tiles side by side across the whole width, each at least 93 by 94 */
        mg_region_t g;
        mg_region_get(p, i, &g);
        CHECK(g.x == x_end && g.w >= 93 && g.h >= 94 && g.y >= 60 && g.y + g.h <= MG_SAFE_BOTTOM);
        x_end = g.x + g.w;
        CHECK(mg_region_at(p, g.x + 1, g.y + 1) == i && mg_region_at(p, g.x + g.w - 1, g.y + g.h - 1) == i);
    }
    CHECK(x_end == 300);
    for (int i = 3; i < 5; i++) { /* the two big buttons: wide, at least 44 px high, to the bottom of the play area */
        mg_region_t g;
        mg_region_get(p, i, &g);
        CHECK(g.w >= 130 && g.h >= MG_BUTTON_MIN && g.y + g.h == MG_SAFE_BOTTOM);
    }
}

/* The count: three beats with their sounds while the tiles are dimmed and inactive, then SHOOT with the window of 1.2 s. */
static void test_rps_count_and_window(void)
{
    const mg_pack_t* p = &g_rps;
    mg_run_t r;
    mg_start(&r, p, 0, 11);
    CHECK(r.state == R_INTRO);
    (void)due(&r);
    CHECK(r.state == R_C1 && r.ctr[RC_ROUND] == 1 && r.ctr[RC_ME] == -1);
    int beat_clip[4] = {-1, -1, -1, -1};
    CHECK(r.tone_n == 1);
    beat_clip[0] = r.tone_q[0];
    for (int beat = 1; beat <= 3; beat++) {
        r.tone_n = 0;
        CHECK((int)(r.timer_due_ms - r.entered_ms) == 560); /* a beat is 560 ms */
        (void)due(&r);
        CHECK(r.state == R_C1 + beat && r.tone_n == 1);
        beat_clip[beat] = r.tone_q[0];
    }
    CHECK(r.state == R_SHOOT);
    CHECK(beat_clip[0] != beat_clip[1] && beat_clip[1] != beat_clip[2] && beat_clip[2] != beat_clip[3] && beat_clip[3] > MGS_TONE_SHIPPED);
    CHECK(beat_clip[3] - MGS_TONE_SHIPPED == MGS_C_CUE5 && beat_clip[0] - MGS_TONE_SHIPPED == MGS_C_CUE0);
    CHECK((int)(r.timer_due_ms - r.entered_ms) == 1200); /* the window */
    /* the dimmed overlay (the only see-through fill) shows in the three count states and is gone at SHOOT */
    for (int st = R_C1; st <= R_SHOOT; st++) {
        r.state = (uint8_t)st;
        int dimmer = 0;
        for (int i = 0; i < p->n_shapes; i++) {
            mg_shape_t s;
            mg_shape_get(p, i, &s);
            dimmer += s.type == MG_SH_FILL && s.h > 0 && mg_shape_visible(&r, i);
        }
        CHECK(dimmer == (st == R_SHOOT ? 0 : 1));
        CHECK(count_visible(&r, MG_SH_ICON) == 4); /* the three choice icons and the bumping fist */
    }
    r.state = R_SHOOT;
    CHECK(texts_visible(&r, "SHOOT!", 0) == 1 && texts_visible(&r, "YA!", 1) == 1);
    /* the tap just inside the window counts, just outside it is too slow */
    mg_run_t a = r;
    const uint32_t t0 = r.entered_ms;
    mg_tap(&a, cx(p, G_PAPER), cy(p, G_PAPER), t0 + 1199);
    CHECK(a.state == R_REVEAL && a.ctr[RC_ME] == 1);
    mg_run_t b = r;
    mg_tick(&b, t0 + 1199);
    CHECK(b.state == R_SHOOT);
    mg_tick(&b, t0 + 1200);
    CHECK(b.state == R_SLOW && b.ctr[RC_BW] == 1 && b.ctr[RC_MW] == 0);
    mg_tap(&b, cx(p, G_ROCK), cy(p, G_ROCK), t0 + 1300); /* a tap on a tile after the window does nothing */
    CHECK(b.state == R_SLOW && b.ctr[RC_ME] == -1);
    CHECK(texts_visible(&b, "Too slow!", 0) == 1);
    /* the buttons are not part of the choice: a tap on them at SHOOT does nothing */
    mg_run_t c = r;
    mg_tap(&c, cx(p, G_AGAIN), cy(p, G_AGAIN), t0 + 100);
    mg_tap(&c, cx(p, G_QUIT), cy(p, G_QUIT), t0 + 110);
    CHECK(c.state == R_SHOOT && !c.finished);
}

static void test_rps_early(void)
{
    const mg_pack_t* p = &g_rps;
    for (int beat = 0; beat < 3; beat++) {
        for (int region = 0; region < 5; region++) {
            mg_run_t r;
            mg_start(&r, p, 0, 21);
            uint32_t now = due(&r);
            for (int k = 0; k < beat; k++) now = due(&r);
            CHECK(r.state == R_C1 + beat);
            r.tone_n = 0;
            mg_tap(&r, cx(p, region), cy(p, region), now + 20);
            CHECK(r.state == R_EARLY && r.ctr[RC_ME] == -1 && r.ctr[RC_MW] == 0 && r.ctr[RC_BW] == 0 && r.ctr[RC_SCORE] == 0);
            CHECK(r.tone_n == 1 && r.tone_q[0] == MGS_TONE_SHIPPED + MGS_C_BAD);
            CHECK(texts_visible(&r, "Too early!", 0) == 1 && texts_visible(&r, "Muy pronto!", 1) == 1);
            CHECK(count_visible(&r, MG_SH_ICON) == 0);
            now = due(&r); /* the round restarts: no point for anyone, the same round number */
            CHECK(r.state == R_C1 && r.ctr[RC_ROUND] == 1 && r.ctr[RC_MW] == 0 && r.ctr[RC_BW] == 0);
        }
    }
    /* a tap on the edges (no region) is not a tap at all */
    mg_run_t r;
    mg_start(&r, p, 0, 22);
    uint32_t now = due(&r);
    mg_tap(&r, 10, 100, now + 10);
    CHECK(r.state == R_C1);
}

/* The unit's pick is drawn when the round starts and no screen before the reveal shows it or depends on it. */
static void test_rps_no_peeking(void)
{
    const mg_pack_t* p = &g_rps;
    int seen[3] = {0, 0, 0};
    for (uint32_t seed = 1; seed <= 90; seed++) {
        mg_run_t r;
        mg_start(&r, p, 0, seed * 104729u);
        uint32_t now = due(&r);
        CHECK(r.state == R_C1);
        const int bot = r.ctr[RC_BOT];
        CHECK(bot >= 0 && bot < 3);
        seen[bot]++;
        for (int beat = 0; beat < 4; beat++) { /* every count state and SHOOT: nothing that is drawn reads the unit's pick, and it never changes */
            CHECK(r.state == R_C1 + beat && r.ctr[RC_BOT] == bot);
            for (int i = 0; i < p->n_shapes; i++) {
                mg_shape_t s;
                mg_shape_get(p, i, &s);
                if (mg_shape_visible(&r, i)) {
                    CHECK(!((s.type == MG_SH_ICON && s.cond_ctr == RC_BOT) || (s.type != MG_SH_TEXT && s.type != MG_SH_ICON && s.cond_ctr == RC_BOT)));
                }
            }
            if (beat < 3) now = due(&r);
        }
        mg_tap(&r, cx(p, (int)(seed % 3)), cy(p, (int)(seed % 3)), now + 50); /* the tap does not change it */
        CHECK(r.state == R_REVEAL && r.ctr[RC_BOT] == bot);
        due(&r);
        CHECK(r.ctr[RC_BOT] == bot);
        /* and the picture shows it now: both hands, the person's on the left and the unit's on the right */
        int mine = 0, theirs = 0;
        for (int i = 0; i < p->n_shapes; i++) {
            mg_shape_t s;
            mg_shape_get(p, i, &s);
            if (s.type == MG_SH_ICON && mg_shape_visible(&r, i)) {
                if (s.cond_ctr == RC_ME) { mine++; CHECK(s.x < 160); }
                if (s.cond_ctr == RC_BOT) { theirs++; CHECK(s.x > 160 && (s.h & MG_ICON_MIRROR)); }
            }
        }
        CHECK(mine == 1 && theirs == 1);
    }
    CHECK(seen[0] > 15 && seen[1] > 15 && seen[2] > 15);
    /* a round restart after "too early" draws a new pick (nothing was shown), and a tie replays the round with a new pick */
    mg_run_t r;
    mg_start(&r, p, 0, 77);
    uint32_t now = due(&r);
    int differ = 0;
    for (int k = 0; k < 20; k++) {
        const int before = r.ctr[RC_BOT];
        mg_tap(&r, 160, 120, now + 5);
        now = due(&r);
        differ += r.ctr[RC_BOT] != before;
    }
    CHECK(differ > 3);
}

static void test_rps_outcomes(void)
{
    const mg_pack_t* p = &g_rps;
    for (int me = 0; me < 3; me++) {
        for (int bot = 0; bot < 3; bot++) {
            mg_run_t r;
            mg_start(&r, p, 0, 100u + (uint32_t)(me * 3 + bot));
            uint32_t now = due(&r);
            r.tone_n = 0;
            now = rps_to_shoot(&r, now, bot);
            r.tone_n = 0;
            mg_tap(&r, cx(p, me), cy(p, me), now + 100);
            CHECK(r.state == R_REVEAL && r.sync_region == 0 && r.tone_n == 1);
            r.tone_n = 0;
            now = due(&r);
            const int res = rps_result(me, bot);
            CHECK(r.state == (res == 0 ? R_TIE : (res > 0 ? R_WIN : R_LOSE)));
            CHECK(r.ctr[RC_MW] == (res > 0) && r.ctr[RC_BW] == (res < 0) && r.ctr[RC_SCORE] == 0);
            CHECK(r.celebrate == (res > 0 ? 1 : 0) && r.tone_n == 1); /* a won round celebrates; a tie and a loss do not */
            CHECK(r.tone_q[0] == MGS_TONE_SHIPPED + (res > 0 ? MGS_C_FANFARE : (res == 0 ? MGS_C_WAH : MGS_C_HAHA)));
            CHECK(!r.finished && r.ctr[RC_ME] == me && r.ctr[RC_BOT] == bot);
            /* the result screen: its words, both hands and the two big buttons, in both languages */
            CHECK(texts_visible(&r, res > 0 ? "You win!" : (res == 0 ? "Tie!" : "I win!"), 0) == 1);
            CHECK(texts_visible(&r, res > 0 ? "Ganas!" : (res == 0 ? "Empate!" : "Gano yo!"), 1) == 1);
            CHECK(texts_visible(&r, "Play again", 0) == 1 && texts_visible(&r, "Quit", 0) == 1 && texts_visible(&r, "Otra vez", 1) == 1 && texts_visible(&r, "Salir", 1) == 1);
            CHECK(count_visible(&r, MG_SH_ICON) == 2);
            /* a tie plays the same round again, a decided round goes on to the next one */
            mg_tap(&r, cx(p, G_AGAIN), cy(p, G_AGAIN), now + 50);
            CHECK(r.state == R_C1 && r.ctr[RC_ROUND] == (res == 0 ? 1 : 2) && r.ctr[RC_ME] == -1);
        }
    }
}

static void test_rps_match(void)
{
    const mg_pack_t* p = &g_rps;
    /* two wins in a row take the match: round 1, round 2, then the match screen with "Rematch" */
    mg_run_t r;
    mg_start(&r, p, 0, 31);
    uint32_t now = due(&r);
    now = rps_round(&r, now, 0, 2); /* rock beats scissors */
    CHECK(r.state == R_WIN && r.ctr[RC_MW] == 1 && r.ctr[RC_ROUND] == 1);
    CHECK(texts_visible(&r, "Round 1 of 3   You 1 - 0 Me", 0) == 1 && texts_visible(&r, "Ronda 1 de 3   Tu 1 - 0 Yo", 1) == 1);
    mg_tap(&r, cx(p, G_AGAIN), cy(p, G_AGAIN), now + 10);
    CHECK(r.state == R_C1 && r.ctr[RC_ROUND] == 2);
    now = rps_round(&r, now + 10, 1, 0); /* paper beats rock */
    CHECK(r.state == R_MWIN && r.ctr[RC_MW] == 2 && r.ctr[RC_BW] == 0 && r.ctr[RC_SCORE] == 1);
    CHECK(r.celebrate == 2 && !r.finished && r.save_pending == 0);
    CHECK(texts_visible(&r, "You win the match!", 0) == 1 && texts_visible(&r, "Rematch", 0) == 1 && texts_visible(&r, "Revancha", 1) == 1 && texts_visible(&r, "Quit", 0) == 1);
    CHECK(texts_visible(&r, "Play again", 0) == 0);
    /* a tap on a tile does nothing on the match screen; Rematch starts a fresh best of three and keeps the matches won */
    mg_tap(&r, cx(p, G_PAPER), cy(p, G_PAPER), now + 20);
    CHECK(r.state == R_MWIN);
    mg_tap(&r, cx(p, G_AGAIN), cy(p, G_AGAIN), now + 30);
    CHECK(r.state == R_C1 && r.ctr[RC_MW] == 0 && r.ctr[RC_BW] == 0 && r.ctr[RC_ROUND] == 1 && r.ctr[RC_SCORE] == 1);
    /* ties do not count and do not advance the round; a win, a loss and a win make 2 to 1 in three rounds */
    now = rps_round(&r, now + 40, 2, 2);
    CHECK(r.state == R_TIE && r.ctr[RC_MW] == 0 && r.ctr[RC_BW] == 0);
    mg_tap(&r, cx(p, G_AGAIN), cy(p, G_AGAIN), now + 10);
    CHECK(r.ctr[RC_ROUND] == 1);
    now = rps_round(&r, now + 10, 0, 1); /* rock loses to paper */
    CHECK(r.state == R_LOSE && r.ctr[RC_BW] == 1 && r.celebrate == 0);
    mg_tap(&r, cx(p, G_AGAIN), cy(p, G_AGAIN), now + 10);
    CHECK(r.ctr[RC_ROUND] == 2);
    now = rps_round(&r, now + 10, 1, 0);
    CHECK(r.state == R_WIN && r.ctr[RC_MW] == 1 && r.ctr[RC_BW] == 1);
    mg_tap(&r, cx(p, G_AGAIN), cy(p, G_AGAIN), now + 10);
    CHECK(r.ctr[RC_ROUND] == 3);
    now = rps_round(&r, now + 10, 2, 1); /* scissors beat paper */
    CHECK(r.state == R_MWIN && r.ctr[RC_MW] == 2 && r.ctr[RC_BW] == 1 && r.ctr[RC_SCORE] == 2);
    /* Quit ends the game and saves the matches won, once */
    mg_tap(&r, cx(p, G_QUIT), cy(p, G_QUIT), now + 20);
    CHECK(r.finished && r.save_pending == 1 && r.ctr[p->score_ctr] == 2 && r.saved == 1);

    /* two losses take the match for the unit: "I win the match!", no celebration; a slow round is a loss too */
    mg_start(&r, p, 0, 32);
    now = due(&r);
    now = rps_round(&r, now, 0, 1);
    CHECK(r.state == R_LOSE);
    mg_tap(&r, cx(p, G_AGAIN), cy(p, G_AGAIN), now + 10);
    now = rps_to_shoot(&r, now + 10, 0);
    mg_tick(&r, r.timer_due_ms); /* nobody taps: too slow */
    CHECK(r.state == R_MLOSE && r.ctr[RC_BW] == 2 && r.ctr[RC_SCORE] == 0 && r.celebrate == 0);
    CHECK(texts_visible(&r, "I win the match!", 0) == 1 && texts_visible(&r, "Gano la partida!", 1) == 1);
    mg_tap(&r, cx(p, G_QUIT), cy(p, G_QUIT), now + 5000);
    CHECK(r.finished && r.save_pending == 1 && r.ctr[p->score_ctr] == 0);
    /* a win, then too slow: the round counter and the score line say 1 - 1 and the buttons are there */
    mg_start(&r, p, 0, 33);
    now = due(&r);
    now = rps_round(&r, now, 1, 0);
    mg_tap(&r, cx(p, G_AGAIN), cy(p, G_AGAIN), now + 10);
    now = rps_to_shoot(&r, now + 10, 1);
    mg_tick(&r, r.timer_due_ms);
    CHECK(r.state == R_SLOW && r.ctr[RC_MW] == 1 && r.ctr[RC_BW] == 1 && r.tone_n >= 1);
    CHECK(texts_visible(&r, "Round 2 of 3   You 1 - 1 Me", 0) == 1 && texts_visible(&r, "Play again", 0) == 1);
    mg_tap(&r, cx(p, G_AGAIN), cy(p, G_AGAIN), now + 5000);
    CHECK(r.state == R_C1 && r.ctr[RC_ROUND] == 3);
}

/* Every text of both games has an English and a Spanish line, and no text is longer than the screen can hold. */
static void test_texts(void)
{
    const mg_pack_t* packs[2] = {&g_bop, &g_rps};
    for (int g = 0; g < 2; g++) {
        const mg_pack_t* p = packs[g];
        for (int i = 0; i < p->n_texts; i++) {
            const char* en = mg_text_raw(p, i, 0);
            const uint8_t* es = p->b + p->o_texts + (size_t)i * MG_TEXT_SIZE + MG_TEXT_LEN;
            CHECK(en[0] != 0 && es[0] != 0);
            CHECK(strlen(en) < MG_TEXT_LEN && strlen((const char*)es) < MG_TEXT_LEN);
        }
    }
}

int main(int argc, char** argv)
{
    if (argc != 3) {
        printf("usage: games_gm_test bopit.mpk rps.mpk\n");
        return 2;
    }
    load(0, argv[1], &g_bop);
    load(1, argv[2], &g_rps);
    CHECK(strcmp(g_bop.id, "bopit") == 0 && strcmp(g_rps.id, "rps") == 0);
    test_doit_schedule();
    test_doit_inputs();
    test_doit_screens();
    test_rps_layout();
    test_rps_count_and_window();
    test_rps_early();
    test_rps_no_peeking();
    test_rps_outcomes();
    test_rps_match();
    test_texts();
    if (failures == 0) {
        printf("all passed\n");
        return 0;
    }
    printf("%d failures\n", failures);
    return 1;
}
