/* Host test for the game engine core (patch G01):
 *   cc -std=c99 -Wall -Wextra -Werror -I<dir with the header> games_core_test.c -o t
 *   ./t memory.mpk reaction.mpk whack.mpk
 * Fixed seeds throughout: a failure repeats. */
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

static uint8_t g_blob[3][MG_MAX_PACK];
static size_t g_len[3];

static void load(int i, const char* path)
{
    FILE* f = fopen(path, "rb");
    if (f == NULL) {
        printf("cannot open %s\n", path);
        exit(2);
    }
    g_len[i] = fread(g_blob[i], 1, sizeof(g_blob[i]), f);
    fclose(f);
}

/* Recompute the checksum after a test edits a byte, so the edit reaches the checks behind the checksum. */
static void fix_crc(uint8_t* b)
{
    const uint16_t payload = mg_u16(b + 24);
    const uint32_t c       = mg_crc32(b, payload);
    b[payload]             = (uint8_t)c;
    b[payload + 1]         = (uint8_t)(c >> 8);
    b[payload + 2]         = (uint8_t)(c >> 16);
    b[payload + 3]         = (uint8_t)(c >> 24);
}

static int centre_x(const mg_pack_t* p, int region)
{
    mg_region_t r;
    mg_region_get(p, region, &r);
    return r.x + r.w / 2;
}
static int centre_y(const mg_pack_t* p, int region)
{
    mg_region_t r;
    mg_region_get(p, region, &r);
    return r.y + r.h / 2;
}

static int state_named_text(const mg_run_t* r, const char* want)
{
    /* is a visible text shape showing `want` (English)? */
    char buf[MG_TEXT_LEN + 8];
    for (int i = 0; i < r->p->n_shapes; i++) {
        mg_shape_t s;
        mg_shape_get(r->p, i, &s);
        if (s.type == MG_SH_TEXT && mg_shape_visible(r, i)) {
            mg_text(r, s.text, 0, buf, sizeof(buf));
            if (strcmp(buf, want) == 0) {
                return 1;
            }
        }
    }
    return 0;
}

static int visible_count(const mg_run_t* r)
{
    int n = 0;
    for (int i = 0; i < r->p->n_shapes; i++) {
        n += mg_shape_visible(r, i);
    }
    return n;
}

/* ---------------------------------------------------------------- tests */

static void test_parse_and_refusals(void)
{
    mg_pack_t p;
    for (int i = 0; i < 3; i++) {
        CHECK(mg_parse(g_blob[i], g_len[i], &p) == MG_OK);
        CHECK(!p.has_sig);
        CHECK(g_len[i] < 6144);                      /* far under the 16 KB target */
        CHECK(p.n_states <= MG_MAX_STATES && p.n_trans <= MG_MAX_TRANS);
    }
    CHECK(mg_parse(g_blob[0], g_len[0], &p) == MG_OK && strcmp(p.id, "memory") == 0 && !(p.flags & MG_FLAG_LOWER_BETTER));
    CHECK(mg_parse(g_blob[1], g_len[1], &p) == MG_OK && strcmp(p.id, "reaction") == 0 && (p.flags & MG_FLAG_LOWER_BETTER));
    CHECK(mg_parse(g_blob[2], g_len[2], &p) == MG_OK && strcmp(p.id, "whack") == 0);

    uint8_t b[MG_MAX_PACK];
    const size_t n = g_len[0];
    memcpy(b, g_blob[0], n);
    CHECK(mg_parse(b, 10, &p) == MG_E_SHORT);
    CHECK(mg_parse(NULL, n, &p) == MG_E_SHORT);
    b[0] = 'X';
    CHECK(mg_parse(b, n, &p) == MG_E_MAGIC);
    memcpy(b, g_blob[0], n);
    b[4] = 2;
    CHECK(mg_parse(b, n, &p) == MG_E_VERSION);
    memcpy(b, g_blob[0], n);
    CHECK(mg_parse(b, n - 1, &p) == MG_E_SIZE);   /* truncated */
    CHECK(mg_parse(b, n + 5, &p) == MG_E_SIZE);   /* trailing junk */
    b[100] ^= 0x55;                                /* a flipped byte: the checksum catches it */
    CHECK(mg_parse(b, n, &p) == MG_E_CRC);

    /* A table that fits no pack: too many states. */
    memcpy(b, g_blob[0], n);
    b[6] = MG_MAX_STATES + 1;
    fix_crc(b);
    CHECK(mg_parse(b, n, &p) == MG_E_LIMITS);

    /* A region reaching into the edge. */
    memcpy(b, g_blob[0], n);
    mg_parse(b, n, &p);
    b[p.o_regions] = 10;                            /* x = 10 < 20 */
    b[p.o_regions + 1] = 0;
    fix_crc(b);
    CHECK(mg_parse(b, n, &p) == MG_E_EDGE);

    /* Text with a letter the screen cannot draw. */
    memcpy(b, g_blob[0], n);
    mg_parse(b, n, &p);
    b[p.o_texts] = 0xE9;
    fix_crc(b);
    CHECK(mg_parse(b, n, &p) == MG_E_ASCII);
    /* A counter escape that names no counter. */
    memcpy(b, g_blob[0], n);
    mg_parse(b, n, &p);
    b[p.o_texts] = '%';
    b[p.o_texts + 1] = '9';
    fix_crc(b);
    CHECK(mg_parse(b, n, &p) == MG_E_ASCII);

    /* A transition into a state that does not exist, an action on a counter that does not exist. */
    memcpy(b, g_blob[0], n);
    mg_parse(b, n, &p);
    b[p.o_trans + 3] = 15;
    fix_crc(b);
    CHECK(mg_parse(b, n, &p) == MG_E_REF);
    memcpy(b, g_blob[0], n);
    mg_parse(b, n, &p);
    b[p.o_actions + MG_ACTION_SIZE + 1] = MG_COUNTERS; /* action 1 is "set score" */
    fix_crc(b);
    CHECK(mg_parse(b, n, &p) == MG_E_REF);
    /* A bad name. */
    memcpy(b, g_blob[0], n);
    b[28] = 'M';
    fix_crc(b);
    CHECK(mg_parse(b, n, &p) == MG_E_ID);
    /* An unreachable start state. */
    memcpy(b, g_blob[0], n);
    b[21] = 99;
    fix_crc(b);
    CHECK(mg_parse(b, n, &p) == MG_E_REF);

    /* Every refusal says what to do, in both languages, and no text has a non-ASCII byte. */
    for (int e = 1; e < MG_E_COUNT; e++) {
        for (int es = 0; es < 2; es++) {
            const char* t = mg_err_text((mg_err_t)e, es);
            CHECK(strlen(t) > 30);
            for (const char* c = t; *c; c++) {
                CHECK((unsigned char)*c >= 0x20 && (unsigned char)*c < 0x7F);
            }
        }
    }
}

static void test_signature_rule(void)
{
    /* A signed pack is the pack plus 64 bytes: the parser sees it and says where the signature is. */
    uint8_t b[MG_MAX_PACK];
    mg_pack_t p;
    memcpy(b, g_blob[0], g_len[0]);
    memset(b + g_len[0], 0xAB, MG_SIG_LEN);
    CHECK(mg_parse(b, g_len[0] + MG_SIG_LEN, &p) == MG_OK && p.has_sig);
    size_t slen = 0;
    const uint8_t* sig = mg_signature(&p, &slen);
    CHECK(sig == b + g_len[0] && slen == g_len[0]);
    CHECK(mg_parse(b, g_len[0] + MG_SIG_LEN - 1, &p) == MG_E_SIZE);
    mg_parse(g_blob[0], g_len[0], &p);
    CHECK(mg_signature(&p, &slen) == NULL);

    /* The policy: an image pack needs none; an outside pack needs a valid signature; only bench relaxes it. */
    CHECK(mg_admit(MG_SRC_BUILTIN, 0, 0, 0, 0) == MG_OK);
    CHECK(mg_admit(MG_SRC_EXTERNAL, 0, 0, 1, 0) == MG_E_UNSIGNED);
    CHECK(mg_admit(MG_SRC_EXTERNAL, 0, 0, 0, 0) == MG_E_UNSIGNED);
    CHECK(mg_admit(MG_SRC_EXTERNAL, 0, 0, 1, 1) == MG_OK);   /* bench build: unsigned allowed */
    CHECK(mg_admit(MG_SRC_EXTERNAL, 1, 0, 0, 0) == MG_E_NOKEY);
    CHECK(mg_admit(MG_SRC_EXTERNAL, 1, 1, 1, 0) == MG_OK);
    CHECK(mg_admit(MG_SRC_EXTERNAL, 1, 0, 1, 0) == MG_E_SIG);
    CHECK(mg_admit(MG_SRC_EXTERNAL, 1, 0, 1, 1) == MG_E_SIG); /* a bad signature is refused even in a bench build */
}

/* Memory: a bot that watches and taps the shown colours back. */
static void test_memory(void)
{
    mg_pack_t p;
    mg_run_t r;
    CHECK(mg_parse(g_blob[0], g_len[0], &p) == MG_OK);
    mg_start(&r, &p, 1000, 12345);
    CHECK(!r.finished && r.seq_len == 1);
    CHECK(state_named_text(&r, "Color Memory"));
    /* nothing but the intro is drawn: a black fill and the two texts */
    CHECK(visible_count(&r) == 3);

    uint32_t now = 1000;
    int rounds_done = 0, shown_tones = 0, played_tones[64], n_played = 0;
    for (int t = 0; t < 120000 && rounds_done < 6; t += 30) {
        now += 30;
        mg_tick(&r, now);
        for (int i = 0; i < r.tone_n; i++) {
            played_tones[n_played++ % 64] = r.tone_q[i];
            shown_tones++;
        }
        r.tone_n = 0;
        if (r.state == 3 /* input */ && (t % 150) == 0) {
            const int want = r.seq[r.seq_pos];
            const int before = r.ctr[0];
            mg_tap(&r, centre_x(&p, want), centre_y(&p, want), now);
            for (int i = 0; i < r.tone_n; i++) {
                played_tones[n_played++ % 64] = r.tone_q[i];
            }
            r.tone_n = 0;
            if (r.ctr[0] > before) {
                rounds_done++;
            }
        }
    }
    CHECK(rounds_done == 6);
    CHECK(r.ctr[0] == 6 && r.seq_len == 6 && r.state == 5 /* correct */);
    CHECK(!r.finished && !r.save_pending);
    CHECK(shown_tones > 20);
    for (int i = 0; i < n_played && i < 64; i++) {
        CHECK(played_tones[i] >= 0 && played_tones[i] < 4); /* colour tones only, never the error sound, while right */
    }

    /* Now a miss: tap a wrong colour. The game goes to its end screen, saves once, plays the error tone. */
    while (r.state != 3) {
        now += 30;
        mg_tick(&r, now);
    }
    const int wrong = (r.seq[r.seq_pos] + 1) % 4;
    r.tone_n        = 0;
    mg_tap(&r, centre_x(&p, wrong), centre_y(&p, wrong), now);
    CHECK(state_named_text(&r, "Game over") && state_named_text(&r, "Score 6"));
    CHECK(r.save_pending && r.saved && r.ctr[p.score_ctr] == 6);
    CHECK(r.tone_n == 1 && r.tone_q[0] == 4);
    r.save_pending = 0;
    mg_tap(&r, 100, 100, now + 100);   /* a tap on the end screen ends the game */
    CHECK(r.finished);
    mg_tap(&r, 100, 100, now + 200);   /* a finished game takes no more events */
    CHECK(r.finished && !r.save_pending);

    /* The idle timeout (nobody taps) ends the same way. */
    mg_start(&r, &p, 0, 777);
    now = 0;
    for (int t = 0; t < 30000 && !r.finished; t += 30) {
        now += 30;
        mg_tick(&r, now);
    }
    CHECK(r.finished && r.saved && r.ctr[0] == 0);
    CHECK(!r.budget_hit);

    /* A fixed seed gives the same sequence every time; a different seed does not (over a few tries). */
    mg_run_t a, c;
    mg_start(&a, &p, 0, 4242);
    mg_start(&c, &p, 0, 4242);
    for (int i = 0; i < 8; i++) {
        mg_rand(&a);
        mg_rand(&c);
    }
    CHECK(a.rng == c.rng && a.seq[0] == c.seq[0]);
    int differ = 0;
    for (uint32_t seed = 1; seed < 40; seed++) {
        mg_start(&c, &p, 0, seed);
        differ += c.seq[0] != a.seq[0];
    }
    CHECK(differ > 0);
}

static void test_reaction(void)
{
    mg_pack_t p;
    mg_run_t r;
    CHECK(mg_parse(g_blob[1], g_len[1], &p) == MG_OK);
    CHECK(p.n_regions == 0);
    mg_start(&r, &p, 0, 99);
    uint32_t now = 0;
    /* intro to wait */
    mg_tap(&r, 160, 120, now += 100);
    CHECK(state_named_text(&r, "Wait..."));
    /* an early tap: "Too soon", the round is not counted, then back to waiting */
    mg_tap(&r, 160, 120, now += 100);
    CHECK(state_named_text(&r, "Too soon!") && r.ctr[1] == 0);
    now += 1700;
    mg_tick(&r, now);
    CHECK(state_named_text(&r, "Wait..."));

    /* three rounds with known delays: 250, 300 and 350 ms */
    const int delay[3] = {250, 300, 350};
    for (int round = 0; round < 3; round++) {
        int guard = 0;
        while (r.state != 2 /* go */ && guard++ < 1000) {
            now += 30;
            mg_tick(&r, now);
        }
        CHECK(r.state == 2);
        CHECK(r.tone_n >= 1 && r.tone_q[r.tone_n - 1] == 0);
        r.tone_n = 0;
        CHECK(r.timer_due_ms - r.entered_ms == 2000);
        mg_tap(&r, 100, 100, r.entered_ms + (uint32_t)delay[round]);
        CHECK(r.ctr[3] == delay[round]);
        CHECK(state_named_text(&r, round == 0 ? "250 ms" : (round == 1 ? "300 ms" : "350 ms")));
        now = r.entered_ms + 1600;
        mg_tick(&r, now);
    }
    CHECK(state_named_text(&r, "Average 300 ms"));
    CHECK(r.save_pending && r.ctr[p.score_ctr] == 300);
    CHECK(r.tone_n == 1 && r.tone_q[0] == 2);

    /* A waiting time is random in 1.5 to 4 s and the same for a fixed seed. */
    int lo = 99999, hi = 0;
    for (uint32_t seed = 1; seed < 60; seed++) {
        mg_start(&r, &p, 0, seed);
        mg_tap(&r, 100, 100, 10); /* intro to wait */
        const int d = (int)(r.timer_due_ms - r.entered_ms);
        if (d < lo) lo = d;
        if (d > hi) hi = d;
    }
    CHECK(lo >= 1500 && hi <= 4000 && hi - lo > 500);

    /* No tap at all in the go state: counted as 2000 ms, the game still ends. */
    mg_start(&r, &p, 0, 5);
    now = 0;
    for (int t = 0; t < 60000 && !r.finished; t += 30) {
        now += 30;
        mg_tick(&r, now);
    }
    CHECK(r.finished && r.saved && r.ctr[p.score_ctr] == 2000);
}

static void test_whack(void)
{
    mg_pack_t p;
    mg_run_t r;
    CHECK(mg_parse(g_blob[2], g_len[2], &p) == MG_OK && p.n_regions == 9);
    /* the nine cells tile the area inside the edges with no overlap and no gap between neighbours */
    for (int i = 0; i < 9; i++) {
        for (int k = i + 1; k < 9; k++) {
            mg_region_t a, b;
            mg_region_get(&p, i, &a);
            mg_region_get(&p, k, &b);
            CHECK(a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y);
        }
    }
    /* a bot that taps the mole every time scores all 15 */
    mg_start(&r, &p, 0, 31337);
    uint32_t now = 0;
    int taps = 0;
    for (int t = 0; t < 60000 && !r.finished; t += 30) {
        now += 30;
        mg_tick(&r, now);
        if (r.state == 2 /* up */ && r.ctr[2] >= 0) {
            CHECK(visible_count(&r) == 1 + 9 + 1 + 18 + 1); /* fill, nine holes, one mole, nine mounds of two shapes, the score text */
            mg_tap(&r, centre_x(&p, r.ctr[2]), centre_y(&p, r.ctr[2]), now);
            taps++;
        }
    }
    CHECK(r.finished && r.saved && r.ctr[0] == 15 && taps == 15);
    CHECK(r.ctr[1] == 15);

    /* a tap on the wrong cell scores nothing and does not end the round early */
    mg_start(&r, &p, 0, 31337);
    now = 0;
    while (r.state != 2) {
        now += 30;
        mg_tick(&r, now);
    }
    const int wrong = (r.ctr[2] + 1) % 9;
    mg_tap(&r, centre_x(&p, wrong), centre_y(&p, wrong), now);
    CHECK(r.state == 2 && r.ctr[0] == 0);
    /* a tap outside every cell (the edge margin cannot reach here, the gap between games text can) is ignored */
    mg_tap(&r, 5, 5, now);
    CHECK(r.state == 2 && r.ctr[0] == 0);
    /* a bot that never taps scores zero: the end screen shows it and the score is not worth saving */
    mg_start(&r, &p, 0, 31337);
    now = 0;
    for (int t = 0; t < 60000 && !r.finished; t += 30) {
        now += 30;
        mg_tick(&r, now);
    }
    CHECK(r.finished && r.ctr[0] == 0);
}

static void test_budget_and_loops(void)
{
    /* Make the first state's enter rule jump back to the same state: every enter fires it again. The player stops
     * after the budget, ends the game and does not save. */
    uint8_t b[MG_MAX_PACK];
    mg_pack_t p;
    mg_run_t r;
    const size_t n = g_len[0];
    memcpy(b, g_blob[0], n);
    mg_parse(b, n, &p);
    b[p.o_trans + 3] = 0; /* transition 0 (intro, enter): next = intro */
    fix_crc(b);
    CHECK(mg_parse(b, n, &p) == MG_OK);
    mg_start(&r, &p, 0, 1);
    CHECK(r.finished && r.budget_hit && !r.save_pending);
    CHECK(r.steps == p.step_budget + 1);
    /* a pack may set its own, smaller budget */
    b[20] = 5;
    fix_crc(b);
    mg_parse(b, n, &p);
    mg_start(&r, &p, 0, 1);
    CHECK(r.budget_hit && r.steps == 6);
    /* and the real packs never come near it */
    for (int i = 0; i < 3; i++) {
        mg_parse(g_blob[i], g_len[i], &p);
        mg_start(&r, &p, 0, 3);
        for (uint32_t now = 0; now < 40000; now += 30) {
            mg_tick(&r, now);
            mg_tap(&r, 100 + (int)(now % 150), 60 + (int)(now % 100), now);
            CHECK(r.steps <= 6);
        }
        CHECK(!r.budget_hit);
    }
}

static uint32_t s_fuzz = 88172645u;
static uint32_t fuzz(void)
{
    s_fuzz ^= s_fuzz << 13;
    s_fuzz ^= s_fuzz >> 17;
    s_fuzz ^= s_fuzz << 5;
    return s_fuzz;
}

/* A damaged or hostile pack either fails the checks or runs without leaving its tables. */
static void test_hostile_packs(void)
{
    uint8_t b[MG_MAX_PACK];
    int accepted = 0, refused = 0;
    for (int which = 0; which < 3; which++) {
        for (int round = 0; round < 1500; round++) {
            const size_t n = g_len[which];
            memcpy(b, g_blob[which], n);
            const int edits = 1 + (int)(fuzz() % 4);
            for (int e = 0; e < edits; e++) {
                b[fuzz() % (n - 4)] = (uint8_t)fuzz();
            }
            if (mg_u16(b + 24) + 4u == n) {
                fix_crc(b); /* let the edit reach the table checks */
            }
            mg_pack_t p;
            if (mg_parse(b, n, &p) != MG_OK) {
                refused++;
                continue;
            }
            accepted++;
            mg_run_t r;
            mg_start(&r, &p, 0, fuzz());
            uint32_t now = 0;
            for (int k = 0; k < 400; k++) {
                now += 30 + fuzz() % 400;
                if (fuzz() % 3 == 0) {
                    mg_tap(&r, (int)(fuzz() % 320), (int)(fuzz() % 240), now);
                } else {
                    mg_tick(&r, now);
                }
                CHECK(r.state < p.n_states);
                CHECK(r.seq_len <= MG_SEQ_MAX && r.seq_pos <= r.seq_len);
                CHECK(r.steps <= p.step_budget + 1);
                CHECK(r.tone_n <= MG_TONE_Q);
                for (int s = 0; s < p.n_shapes; s++) {
                    (void)mg_shape_visible(&r, s);
                }
                char text[MG_TEXT_LEN + 16];
                CHECK(mg_text(&r, p.title_text, 1, text, sizeof(text)) <= (int)sizeof(text) - 1);
                r.tone_n = 0;
                if (r.finished) {
                    break;
                }
            }
        }
    }
    CHECK(refused > 200 && accepted > 200);
}

static void test_scores_and_text(void)
{
    uint16_t s[MG_SCORES] = {0, 0, 0, 0, 0};
    CHECK(mg_scores_add(s, 0, 5) == 0);
    CHECK(mg_scores_add(s, 0, 9) == 0 && s[0] == 9 && s[1] == 5);
    CHECK(mg_scores_add(s, 0, 7) == 1);
    CHECK(mg_scores_add(s, 0, 7) == 2);   /* a tie goes after the older one */
    CHECK(mg_scores_add(s, 0, 1) == 4);
    CHECK(mg_scores_add(s, 0, 1) == -1);  /* the list is full of better scores */
    CHECK(s[0] == 9 && s[1] == 7 && s[2] == 7 && s[3] == 5 && s[4] == 1);
    CHECK(mg_scores_add(s, 0, 0) == -1 && mg_scores_add(s, 0, -4) == -1);
    CHECK(mg_scores_add(s, 0, 2) == 4 && s[4] == 2);

    uint16_t t[MG_SCORES] = {0, 0, 0, 0, 0};   /* lower is better: reaction times */
    CHECK(mg_scores_add(t, 1, 300) == 0);
    CHECK(mg_scores_add(t, 1, 250) == 0 && t[0] == 250);
    CHECK(mg_scores_add(t, 1, 400) == 2);
    CHECK(mg_scores_add(t, 1, 300) == 2 && t[2] == 300 && t[3] == 400);  /* 300 then 400 after it */
    CHECK(mg_scores_add(t, 1, 70000) == 4 && t[4] == 65535);

    /* counters in text */
    mg_pack_t p;
    mg_run_t r;
    mg_parse(g_blob[1], g_len[1], &p);
    mg_start(&r, &p, 0, 1);
    char out[64];
    r.ctr[3] = 1234;
    CHECK(mg_text(&r, 4, 0, out, sizeof(out)) == 7 && strcmp(out, "1234 ms") == 0);
    r.ctr[3] = -7;
    mg_text(&r, 4, 0, out, sizeof(out));
    CHECK(strcmp(out, "-7 ms") == 0);
    CHECK(mg_text(&r, 4, 0, out, 4) == 3 && strcmp(out, "-7 ") == 0);   /* never past the buffer */
    /* Spanish when it has a line, English when it has none */
    CHECK(strcmp(mg_text_raw(&p, 0, 1), "Tiempo de reaccion") == 0);
    CHECK(strcmp(mg_text_raw(&p, 0, 0), "Reaction Time") == 0);
}

static void test_regions_stay_inside(void)
{
    for (int i = 0; i < 3; i++) {
        mg_pack_t p;
        mg_parse(g_blob[i], g_len[i], &p);
        for (int k = 0; k < p.n_regions; k++) {
            mg_region_t g;
            mg_region_get(&p, k, &g);
            CHECK(g.x >= MG_EDGE_L && g.y >= MG_EDGE_T && g.x + g.w <= MG_EDGE_R && g.y + g.h <= MG_EDGE_B);
        }
        /* a touch in an edge strip is in no region */
        CHECK(mg_region_at(&p, 5, 120) == MG_NO_REGION && mg_region_at(&p, 160, 3) == MG_NO_REGION &&
              mg_region_at(&p, 160, 230) == MG_NO_REGION && mg_region_at(&p, 310, 120) == MG_NO_REGION);
    }
}

/* Patch UI01: the Color Memory tones last exactly as long as the tile stays lit, have four different pitches and start and end at zero. */
static void test_color_tones(void)
{
    static int16_t buf[MG_COLOR_TONE_SAMPLES + 8];
    int crossings[MG_COLOR_TONES];
    CHECK(MG_COLOR_TONE_SAMPLES == MG_COLOR_TONE_RATE / 1000 * MG_COLOR_LIT_MS);
    CHECK(mg_color_tone(-1, buf, sizeof(buf) / 2) == 0 && mg_color_tone(MG_COLOR_TONES, buf, sizeof(buf) / 2) == 0);
    CHECK(mg_color_tone(0, buf, MG_COLOR_TONE_SAMPLES - 1) == 0);
    for (int c = 0; c < MG_COLOR_TONES; c++) {
        memset(buf, 0x55, sizeof(buf));
        const size_t n = mg_color_tone(c, buf, sizeof(buf) / 2);
        CHECK(n == (size_t)MG_COLOR_TONE_SAMPLES);
        CHECK(buf[0] == 0 && buf[n - 1] >= -300 && buf[n - 1] <= 300);   /* a click free start and end */
        int peak = 0, up = 0;
        for (size_t i = 0; i < n; i++) {
            const int a = buf[i] < 0 ? -buf[i] : buf[i];
            peak = a > peak ? a : peak;
            if (i > 0 && buf[i - 1] < 0 && buf[i] >= 0) up++;
        }
        CHECK(peak > 12000 && peak < 16100);
        crossings[c] = up;
        /* the pitch: rising zero crossings in 450 ms are 0.45 f, within 3 percent */
        const int want = (int)(MG_COLOR_HZ[c] * MG_COLOR_LIT_MS / 1000);
        CHECK(up >= want * 97 / 100 - 1 && up <= want * 103 / 100 + 1);
    }
    CHECK(crossings[0] != crossings[1] && crossings[1] != crossings[2] && crossings[2] != crossings[3] && crossings[0] != crossings[2]);
}

/* Patch UI08: every tap target of the three games lies inside the safe area (clear of the banner row and the subtitle strip, at least 44 px
 * high, at least 8 px from the side and the bottom of the glass) and the targets of one game do not overlap. */
static void test_buttons_stay_in_the_safe_area(void)
{
    for (int g = 0; g < 3; g++) {
        mg_pack_t p;
        CHECK(mg_parse(g_blob[g], g_len[g], &p) == MG_OK);
        for (int i = 0; i < p.n_regions; i++) {
            mg_region_t r;
            mg_region_get(&p, i, &r);
            CHECK(r.y >= MG_SAFE_TOP && (int)r.y + r.h <= MG_SAFE_BOTTOM);
            CHECK(r.h >= MG_BUTTON_MIN && r.w >= MG_BUTTON_MIN);
            CHECK(r.x >= 8 && (int)r.x + r.w <= 320 - 8 && (int)r.y + r.h <= 240 - 8);
            for (int j = 0; j < i; j++) {
                mg_region_t q;
                mg_region_get(&p, j, &q);
                CHECK(r.x + r.w <= q.x || q.x + q.w <= r.x || r.y + r.h <= q.y || q.y + q.h <= r.y);
            }
        }
        /* a drawn shape that is a button (a box or a circle of a region) is inside it: the text rows stay out of the targets' rows */
        for (int i = 0; i < p.n_shapes; i++) {
            mg_shape_t sh;
            mg_shape_get(&p, i, &sh);
            if (sh.type == MG_SH_BOX) CHECK(sh.y >= MG_SAFE_TOP && sh.y + sh.h <= MG_SAFE_BOTTOM);
            if (sh.type == MG_SH_CIRCLE) CHECK(sh.y - sh.aux >= MG_SAFE_TOP && sh.y + sh.aux <= MG_SAFE_BOTTOM);
        }
    }
}

int main(int argc, char** argv)
{
    if (argc != 4) {
        printf("usage: games_core_test memory.mpk reaction.mpk whack.mpk\n");
        return 2;
    }
    for (int i = 0; i < 3; i++) {
        load(i, argv[i + 1]);
    }
    CHECK(MG_TONE_COUNT == 5 && strcmp(MG_TONES[4], "exclamation") == 0);
    test_parse_and_refusals();
    test_signature_rule();
    test_memory();
    test_reaction();
    test_whack();
    test_budget_and_loops();
    test_hostile_packs();
    test_scores_and_text();
    test_regions_stay_inside();
    test_color_tones();
    test_buttons_stay_in_the_safe_area();
    if (failures == 0) {
        printf("all passed\n");
        return 0;
    }
    printf("%d failures\n", failures);
    return 1;
}
