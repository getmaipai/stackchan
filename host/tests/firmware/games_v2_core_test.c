/* Host test for the game engine additions of patches UI12 and UI13: the new inputs, the board, the timer from a counter, the sound clips,
 * the tilt detector and the four new games plus the redrawn whack-a-mole, each played by a scripted bot with a fixed seed.
 *   cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> games_v2_core_test.c -o t
 *   ./t memory.mpk whack.mpk tictactoe.mpk bopit.mpk rps.mpk eightball.mpk dice.mpk   (patch GM04: seven games, no Reaction Time; Do It and Rock Paper Scissors have games_gm_test.c)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maipai_games_core.h"
#include "maipai_games_input_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

enum { N_PACKS = 7, P_MEMORY = 0, P_WHACK, P_TTT, P_BOPIT, P_RPS, P_BALL, P_DICE };
static uint8_t g_blob[N_PACKS][MG_MAX_PACK];
static size_t g_len[N_PACKS];
static mg_pack_t g_pack[N_PACKS];

static void load(int i, const char* path)
{
    FILE* f = fopen(path, "rb");
    if (f == NULL) {
        printf("cannot open %s\n", path);
        exit(2);
    }
    g_len[i] = fread(g_blob[i], 1, sizeof(g_blob[i]), f);
    fclose(f);
    CHECK(mg_parse(g_blob[i], g_len[i], &g_pack[i]) == MG_OK);
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

/* advances a run to `until` ms in 30 ms ticks */
static uint32_t run_to(mg_run_t* r, uint32_t now, uint32_t until)
{
    while (now < until && !r->finished) {
        now += 30;
        mg_tick(r, now);
    }
    return now;
}

static int shipped_tone(int id) { return id >= 0 && id < 5; }

/* ------------------------------------------------------------------ the format */
static void test_all_packs_parse_and_stay_in_the_safe_area(void)
{
    for (int g = 0; g < N_PACKS; g++) {
        const mg_pack_t* p = &g_pack[g];
        CHECK(p->n_shapes <= MG_MAX_SHAPES && p->n_texts <= MG_MAX_TEXTS && g_len[g] < 8192);
        for (int i = 0; i < p->n_regions; i++) {
            mg_region_t r;
            mg_region_get(p, i, &r);
            CHECK(r.y >= MG_SAFE_TOP && (int)r.y + r.h <= MG_SAFE_BOTTOM);
            CHECK(r.h >= MG_BUTTON_MIN && r.w >= MG_BUTTON_MIN);
            CHECK(r.x >= 8 && (int)r.x + r.w <= 320 - 8 && (int)r.y + r.h <= 240 - 8);
            for (int j = 0; j < i; j++) {
                mg_region_t q;
                mg_region_get(p, j, &q);
                CHECK(r.x + r.w <= q.x || q.x + q.w <= r.x || r.y + r.h <= q.y || q.y + q.h <= r.y);
            }
        }
        for (int i = 0; i < p->n_shapes; i++) { /* a drawn box, line or ring that is a button part lies in the safe area too */
            mg_shape_t s;
            mg_shape_get(p, i, &s);
            if (s.type == MG_SH_BOX && s.w < 320) {
                CHECK(s.y >= MG_SAFE_TOP && s.y + s.h <= MG_SAFE_BOTTOM);
            }
            if (s.type == MG_SH_LINE) {
                CHECK(s.y >= MG_SAFE_TOP && s.h >= MG_SAFE_TOP && s.y <= MG_SAFE_BOTTOM && s.h <= MG_SAFE_BOTTOM);
            }
        }
    }
    CHECK((g_pack[P_BOPIT].flags & MG_FLAG_TAP_ON_RELEASE) != 0 && (g_pack[P_TTT].flags & MG_FLAG_TAP_ON_RELEASE) == 0);
    CHECK(g_pack[P_TTT].n_regions == 9 && g_pack[P_RPS].n_regions == 5);
    CHECK(g_pack[P_BOPIT].n_regions == 1);   /* patch GM04: Do It is one big button the size of the play area */
}

static void test_new_refusals(void)
{
    static uint8_t b[MG_MAX_PACK];
    mg_pack_t p;
    const size_t n = g_len[P_BOPIT];
    /* a timer that names a counter that does not exist */
    memcpy(b, g_blob[P_BOPIT], n);
    for (int i = 0; i < g_pack[P_BOPIT].n_states; i++) {
        uint8_t* st = b + g_pack[P_BOPIT].o_states + i * MG_STATE_SIZE;
        if (mg_u16(st) == MG_TIMER_FROM_CTR) {
            st[2] = 9;
        }
    }
    mg_pack_t q;
    mg_parse(g_blob[P_BOPIT], n, &q);
    {
        uint16_t payload = mg_u16(b + 24);
        uint32_t c       = mg_crc32(b, payload);
        memcpy(b + payload, &c, 4);
    }
    CHECK(mg_parse(b, n, &p) == MG_E_REF);
    /* a shape condition on a board cell that does not exist (counter 25) */
    memcpy(b, g_blob[P_TTT], g_len[P_TTT]);
    mg_parse(g_blob[P_TTT], g_len[P_TTT], &q);
    for (int i = 0; i < q.n_shapes; i++) {
        uint8_t* sh = b + q.o_shapes + i * MG_SHAPE_SIZE;
        if (sh[1] == MG_BOARD_CTR0 + 8) {
            sh[1] = MG_BOARD_CTR0 + 9;
            break;
        }
    }
    {
        uint16_t payload = mg_u16(b + 24);
        uint32_t c       = mg_crc32(b, payload);
        memcpy(b + payload, &c, 4);
    }
    CHECK(mg_parse(b, g_len[P_TTT], &p) == MG_E_REF);
    /* a tone that is neither a sound, a clip nor a group */
    memcpy(b, g_blob[P_WHACK], g_len[P_WHACK]);
    mg_parse(g_blob[P_WHACK], g_len[P_WHACK], &q);
    int hit = 0;
    for (int i = 0; i < q.n_actions; i++) {
        uint8_t* a = b + q.o_actions + i * MG_ACTION_SIZE;
        if (a[0] == MG_OP_TONE) {
            a[1] = 0x70;
            hit++;
            break;
        }
    }
    CHECK(hit == 1);
    {
        uint16_t payload = mg_u16(b + 24);
        uint32_t c       = mg_crc32(b, payload);
        memcpy(b + payload, &c, 4);
    }
    CHECK(mg_parse(b, g_len[P_WHACK], &p) == MG_E_REF);
}

/* ------------------------------------------------------------------ the sounds */
static void test_sound_clips(void)
{
    static int16_t buf[MGS_SFX_MAX_SAMPLES];
    CHECK(MGS_CLIPS == 32 && MGS_GROUPS == 3 && MGS_TONE_SHIPPED == 5);
    for (int c = 0; c < MGS_CLIPS; c++) {
        const size_t want = mgs_clip_samples(c);
        CHECK(want > 0 && want <= (size_t)MGS_SFX_MAX_SAMPLES);
        CHECK(mgs_render(c, buf, want - 1) == 0);   /* a buffer too small renders nothing */
        const size_t n = mgs_render(c, buf, sizeof(buf) / sizeof(buf[0]));
        CHECK(n == want);
        int peak = 0, loud = 0;
        for (size_t i = 0; i < n; i++) {
            const int a = buf[i] < 0 ? -buf[i] : buf[i];
            peak        = a > peak ? a : peak;
            loud += a > 1000;
        }
        CHECK(peak > 1500 && peak <= MGS_SFX_PEAK);     /* it makes sound, and never louder than the ceiling (patch GM03) */
        CHECK(loud > (int)(n / 10));
        CHECK(buf[0] == 0 && buf[n - 1] >= -400 && buf[n - 1] <= 400); /* a click free start and end */
        CHECK(MGS_CLIP[c].n >= 1 && MGS_CLIP[c].n <= MGS_SFX_MAX_SEGS && MGS_CLIP[c].name[0] != 0);
    }
    CHECK(mgs_render(-1, buf, 10) == 0 && mgs_render(MGS_CLIPS, buf, sizeof(buf) / 2) == 0 && mgs_render(0, NULL, 99999) == 0);
    /* the groups: a hit has four sounds, a miss and an escape three; each clip of a group is a different sound */
    CHECK(MGS_GROUP[MGS_G_HIT].n == 4 && MGS_GROUP[MGS_G_MISS].n == 3 && MGS_GROUP[MGS_G_ESCAPE].n == 3);
    for (int g = 0; g < MGS_GROUPS; g++) {
        for (int i = 0; i < MGS_GROUP[g].n; i++) {
            for (int k = i + 1; k < MGS_GROUP[g].n; k++) {
                CHECK(MGS_GROUP[g].clip[i] != MGS_GROUP[g].clip[k]);
            }
        }
    }
    /* the tone ids */
    CHECK(mgs_tone_ok(0) && mgs_tone_ok(4) && mgs_tone_ok(5) && mgs_tone_ok(5 + MGS_CLIPS - 1) && !mgs_tone_ok(5 + MGS_CLIPS));
    CHECK(mgs_tone_ok(0x80) && mgs_tone_ok(0x82) && !mgs_tone_ok(0x83) && !mgs_tone_ok(-1) && !mgs_tone_ok(0x7f));
    /* a group asked for with a fixed seed picks the same clips every time, and every clip of the group turns up */
    mg_pack_t* p = &g_pack[P_WHACK];
    mg_run_t r;
    int seen[MGS_CLIPS];
    memset(seen, 0, sizeof(seen));
    mg_start(&r, p, 0, 99);
    for (int i = 0; i < 200; i++) {
        r.tone_n = 0;
        mg_tone(&r, MGS_TONE_GROUP + MGS_G_HIT);
        CHECK(r.tone_n == 1 && r.tone_q[0] >= MGS_TONE_SHIPPED);
        seen[r.tone_q[0] - MGS_TONE_SHIPPED]++;
    }
    for (int i = 0; i < MGS_GROUP[MGS_G_HIT].n; i++) {
        CHECK(seen[MGS_GROUP[MGS_G_HIT].clip[i]] > 20);
    }
    mg_run_t r2;
    mg_start(&r2, p, 0, 99);
    mg_run_t r3;
    mg_start(&r3, p, 0, 99);
    r2.tone_n = r3.tone_n = 0;
    mg_tone(&r2, MGS_TONE_GROUP + MGS_G_MISS);
    mg_tone(&r3, MGS_TONE_GROUP + MGS_G_MISS);
    CHECK(r2.tone_q[0] == r3.tone_q[0]);
}

/* ------------------------------------------------------------------ the tilt detector */
static int feed(mgi_t* t, uint32_t* now, float x, float y, float z, int n)
{
    int ev = MGI_NONE;
    for (int i = 0; i < n; i++) {
        *now += 100;
        const int e = mgi_update(t, x, y, z, *now);
        if (e != MGI_NONE) {
            ev = e;
        }
    }
    return ev;
}

static void test_tilt_detector(void)
{
    const float g = MGI_G;
    mgi_t t;
    uint32_t now = 0;
    mgi_init(&t);
    CHECK(feed(&t, &now, 0, g, 0, 30) == MGI_NONE);            /* standing still: nothing */
    CHECK(feed(&t, &now, 1.5f, 9.7f, 0, 10) == MGI_NONE);       /* 9 degrees: not a tilt */
    CHECK(feed(&t, &now, 4.6f, 8.6f, 0, 4) == MGI_RIGHT);       /* 28 degrees to the right: +x */
    CHECK(feed(&t, &now, 4.6f, 8.6f, 0, 20) == MGI_NONE);       /* held: only one event */
    CHECK(feed(&t, &now, 0, g, 0, 6) == MGI_NONE);              /* back to level re-arms */
    CHECK(feed(&t, &now, -4.6f, 8.6f, 0, 4) == MGI_LEFT);
    feed(&t, &now, 0, g, 0, 6);
    CHECK(feed(&t, &now, 0, 8.6f, -4.6f, 4) == MGI_FORWARD);    /* face down: -z */
    feed(&t, &now, 0, g, 0, 6);
    CHECK(feed(&t, &now, 0, 8.6f, 4.6f, 4) == MGI_BACK);        /* on its back: +z */
    feed(&t, &now, 0, g, 0, 6);
    /* shaking (the pull is not one g) is not a tilt, and a tilt right after a shake is part of the shake */
    CHECK(feed(&t, &now, 9.0f, 14.0f, 3.0f, 6) == MGI_NONE);
    mgi_note_shake(&t, now);
    CHECK(feed(&t, &now, 4.6f, 8.6f, 0, 3) == MGI_NONE);
    feed(&t, &now, 0, g, 0, 10);
    CHECK(feed(&t, &now, 4.6f, 8.6f, 0, 4) == MGI_RIGHT);       /* and it works again after the quiet time */
    /* the rest pose is the pose the game started in: a head looking up 20 degrees is still level for the game */
    mgi_init(&t);
    now = 0;
    const float up_y = g * 0.94f, up_z = g * 0.34f;
    CHECK(feed(&t, &now, 0, up_y, up_z, 30) == MGI_NONE);
    CHECK(feed(&t, &now, 5.0f, up_y * 0.95f, up_z, 4) == MGI_RIGHT);
    /* a moving unit (the pull is far from one g) never counts */
    mgi_init(&t);
    now = 0;
    feed(&t, &now, 0, g, 0, 10);
    CHECK(feed(&t, &now, 3.0f, 15.0f, 3.0f, 8) == MGI_NONE);
}

/* ------------------------------------------------------------------ the board */
static void test_board(void)
{
    uint8_t b[9] = {0};
    CHECK(mg_board_result(b) == 0);
    b[0] = b[1] = b[2] = 1;
    CHECK(mg_board_result(b) == 1);
    memset(b, 0, sizeof(b));
    b[2] = b[4] = b[6] = 2;
    CHECK(mg_board_result(b) == 2);
    const uint8_t draw[9] = {1, 2, 1, 1, 2, 2, 2, 1, 1};
    CHECK(mg_board_result(draw) == 3);
    mg_run_t r;
    memset(&r, 0, sizeof(r));
    r.rng = 12345;
    /* level 1 takes a win and blocks one */
    memset(r.board, 0, sizeof(r.board));
    r.board[3] = r.board[4] = 2;   /* the unit can win at 5 */
    r.board[0] = r.board[1] = 1;   /* and the person threatens 2 */
    CHECK(mg_board_bot(&r, 1) == 5 && mg_board_bot(&r, 2) == 5);
    memset(r.board, 0, sizeof(r.board));
    r.board[0] = r.board[1] = 1;
    CHECK(mg_board_bot(&r, 1) == 2 && mg_board_bot(&r, 2) == 2);
    /* level 0 only ever picks a free cell */
    memset(r.board, 0, sizeof(r.board));
    r.board[4] = 1;
    r.board[0] = 2;
    for (int i = 0; i < 200; i++) {
        const int c = mg_board_bot(&r, 0);
        CHECK(c >= 0 && c < 9 && r.board[c] == 0);
    }
    /* a full board has no move */
    memcpy(r.board, draw, sizeof(draw));
    CHECK(mg_board_bot(&r, 2) == -1);
    /* perfect play never loses: 4000 games against a random person who goes first */
    int unit_lost = 0, unit_won = 0, draws = 0;
    for (int game = 0; game < 4000; game++) {
        memset(r.board, 0, sizeof(r.board));
        for (;;) {
            int free_c[9], n = 0;
            for (int i = 0; i < 9; i++) {
                if (r.board[i] == 0) free_c[n++] = i;
            }
            if (n == 0) break;
            r.board[free_c[mg_rand(&r) % (uint32_t)n]] = 1;
            if (mg_board_result(r.board) != 0) break;
            const int c = mg_board_bot(&r, 2);
            CHECK(c >= 0 && r.board[c] == 0);
            if (c < 0) break;
            r.board[c] = 2;
            if (mg_board_result(r.board) != 0) break;
        }
        const int res = mg_board_result(r.board);
        unit_lost += res == 1;
        unit_won += res == 2;
        draws += res == 3;
    }
    CHECK(unit_lost == 0 && unit_won > 2500 && draws > 0);
    /* the easy level does lose to a random person sometimes (it is random too) */
    int easy_lost = 0;
    for (int game = 0; game < 2000; game++) {
        memset(r.board, 0, sizeof(r.board));
        for (;;) {
            int free_c[9], n = 0;
            for (int i = 0; i < 9; i++) {
                if (r.board[i] == 0) free_c[n++] = i;
            }
            if (n == 0) break;
            r.board[free_c[mg_rand(&r) % (uint32_t)n]] = 1;
            if (mg_board_result(r.board) != 0) break;
            const int c = mg_board_bot(&r, 0);
            if (c < 0) break;
            r.board[c] = 2;
            if (mg_board_result(r.board) != 0) break;
        }
        easy_lost += mg_board_result(r.board) == 1;
    }
    CHECK(easy_lost > 300);
}

/* ------------------------------------------------------------------ whack-a-mole, redrawn */
enum { W_INTRO = 0, W_DOWN, W_UP, W_HIT, W_OVER };

static void test_whack(void)
{
    const mg_pack_t* p = &g_pack[P_WHACK];
    mg_run_t r;
    mg_start(&r, p, 0, 4242);
    uint32_t now = run_to(&r, 0, 2100);
    CHECK(r.state == W_DOWN);
    int faces[MG_FACE_COUNT] = {0};
    int hits = 0, hit_tones = 0;
    int hit_clips[MGS_CLIPS] = {0};
    while (!r.finished && now < 90000) {
        now += 30;
        r.tone_n = 0;
        mg_tick(&r, now);
        if (r.state == W_UP) {
            CHECK(r.ctr[3] >= 0 && r.ctr[3] <= 3);          /* a funny face, never the dazed one while it is up */
            faces[r.ctr[3]]++;
            /* the mole is one shape and it stands in the cell of its counter */
            int moles = 0;
            for (int i = 0; i < p->n_shapes; i++) {
                mg_shape_t s;
                mg_shape_get(p, i, &s);
                if (s.type == MG_SH_MOLE && mg_shape_visible(&r, i)) {
                    moles++;
                    CHECK(mg_mole_region(&r, &s) == r.ctr[2]);
                }
            }
            CHECK(moles == 1);
            r.tone_n = 0;
            mg_tap(&r, cx(p, r.ctr[2]), cy(p, r.ctr[2]), now);
            CHECK(r.state == W_HIT && r.ctr[3] == MG_FACE_DAZED);  /* the dazed face with stars */
            CHECK(r.sync_region == r.ctr[2]);                       /* the sound waits for the mole's cell */
            CHECK(r.tone_n == 1 && r.tone_q[0] >= MGS_TONE_SHIPPED);
            hit_clips[r.tone_q[0] - MGS_TONE_SHIPPED]++;
            hit_tones++;
            hits++;
            /* a second tap while it is dazed does nothing */
            r.tone_n = 0;
            mg_tap(&r, cx(p, r.ctr[2]), cy(p, r.ctr[2]), now);
            CHECK(r.tone_n == 0 && r.state == W_HIT);
        }
    }
    CHECK(r.finished && r.ctr[0] == 15 && hits == 15 && hit_tones == 15);
    for (int f = 0; f < 4; f++) {
        CHECK(faces[f] > 0);                                       /* all four funny faces turned up in one game */
    }
    int kinds = 0;
    for (int c = 0; c < MGS_CLIPS; c++) {
        kinds += hit_clips[c] > 0;
        if (hit_clips[c] > 0) {
            int in_group = 0;
            for (int i = 0; i < MGS_GROUP[MGS_G_HIT].n; i++) in_group |= MGS_GROUP[MGS_G_HIT].clip[i] == c;
            CHECK(in_group);
        }
    }
    CHECK(kinds >= 2);
    /* a miss: a tap on a wrong cell sounds a miss sound, marks that cell, and the mole stays */
    mg_start(&r, p, 0, 4242);
    now = run_to(&r, 0, 2100);
    while (r.state != W_UP) {
        now += 30;
        mg_tick(&r, now);
    }
    const int cell = r.ctr[2], wrong = (cell + 4) % 9;
    r.tone_n = 0;
    mg_tap(&r, cx(p, wrong), cy(p, wrong), now);
    CHECK(r.state == W_UP && r.ctr[0] == 0 && r.ctr[4] == wrong && r.sync_region == wrong);
    CHECK(r.tone_n == 1);
    {
        int in_group = 0;
        for (int i = 0; i < MGS_GROUP[MGS_G_MISS].n; i++) in_group |= MGS_TONE_SHIPPED + MGS_GROUP[MGS_G_MISS].clip[i] == r.tone_q[0];
        CHECK(in_group);
    }
    mg_tap(&r, 5, 5, now);                                          /* nowhere: silent */
    CHECK(r.tone_n == 1);
    /* the mole escapes: an escape sound, synced to its cell, and the miss mark is gone when the next one comes */
    r.tone_n = 0;
    int guard = 0;
    while (r.state == W_UP && guard++ < 100) {
        now += 30;
        mg_tick(&r, now);
    }
    CHECK(r.state == W_DOWN && r.tone_n == 1 && r.sync_region == cell);
    {
        int in_group = 0;
        for (int i = 0; i < MGS_GROUP[MGS_G_ESCAPE].n; i++) in_group |= MGS_TONE_SHIPPED + MGS_GROUP[MGS_G_ESCAPE].clip[i] == r.tone_q[0];
        CHECK(in_group);
    }
    /* a tap on a hole while no mole is up is a miss too */
    r.tone_n = 0;
    mg_tap(&r, cx(p, 3), cy(p, 3), now);
    CHECK(r.state == W_DOWN && r.tone_n == 1 && r.ctr[4] == 3);
    /* a bot that never taps sees every mole escape: fifteen escape sounds and a score of zero */
    mg_start(&r, p, 0, 4242);
    now = 0;
    int escapes = 0;
    while (!r.finished && now < 90000) {
        now += 30;
        r.tone_n = 0;
        const int was_up = r.state == W_UP;
        mg_tick(&r, now);
        escapes += was_up && r.state == W_DOWN && r.tone_n == 1;
    }
    CHECK(r.finished && r.ctr[0] == 0 && escapes == 15);
}

/* ------------------------------------------------------------------ tic-tac-toe */
enum { T_MENU = 0, T_TURN, T_PCHECK, T_THINK, T_BCHECK, T_WIN, T_LOSE, T_DRAW };

static int count_visible_type(const mg_run_t* r, int type)
{
    int n = 0;
    for (int i = 0; i < r->p->n_shapes; i++) {
        mg_shape_t s;
        mg_shape_get(r->p, i, &s);
        n += s.type == type && mg_shape_visible(r, i);
    }
    return n;
}

/* plays one game: the person picks a level (0 to 2), then `policy` chooses cells: 0 random, 1 smart (win, block, centre) */
static int ttt_game(uint32_t seed, int level, int policy, uint32_t* score_out, int* saved_out)
{
    const mg_pack_t* p = &g_pack[P_TTT];
    mg_run_t r;
    mg_start(&r, p, 0, seed);
    uint32_t now = 0;
    uint32_t rng = seed * 2654435761u + 7u;
    CHECK(r.state == T_MENU && r.p->n_regions == 9);
    mg_tap(&r, cx(p, level * 3 + 1), cy(p, level * 3 + 1), now);  /* the row picks the level */
    CHECK(r.state == T_TURN && r.ctr[1] == level);
    int guard = 0;
    while (r.state != T_WIN && r.state != T_LOSE && r.state != T_DRAW && guard++ < 40) {
        CHECK(r.state == T_TURN);
        int free_c[9], n = 0, choice = -1;
        for (int i = 0; i < 9; i++) {
            if (r.board[i] == 0) free_c[n++] = i;
        }
        if (policy == 1) {
            for (int pass = 0; pass < 2 && choice < 0; pass++) {
                for (int k = 0; k < n && choice < 0; k++) {
                    uint8_t b[9];
                    memcpy(b, r.board, 9);
                    b[free_c[k]] = pass == 0 ? 1 : 2;
                    if (mg_board_win(b, pass == 0 ? 1 : 2)) choice = free_c[k];
                }
            }
            if (choice < 0 && r.board[4] == 0) choice = 4;
        }
        if (choice < 0) {
            rng    = rng * 1664525u + 1013904223u;
            choice = free_c[(rng >> 8) % (uint32_t)n];
        }
        /* a tap on a cell that is taken does nothing */
        for (int i = 0; i < 9; i++) {
            if (r.board[i] != 0) {
                const int before = r.state;
                r.tone_n = 0;
                mg_tap(&r, cx(p, i), cy(p, i), now);
                CHECK(r.state == before && r.tone_n == 0);
                break;
            }
        }
        r.tone_n = 0;
        mg_tap(&r, cx(p, choice), cy(p, choice), now);
        CHECK(r.board[choice] == 1 && r.sync_region == choice && r.tone_n >= 1);   /* the mark's tone, and a result tone when it ends the game */
        if (r.state == T_THINK) {
            now = run_to(&r, now, now + 700);            /* the unit thinks a moment, then plays */
            CHECK(r.state == T_TURN || r.state == T_WIN || r.state == T_LOSE || r.state == T_DRAW);
            if (r.ctr[3] >= 0) {
                CHECK(r.board[r.ctr[3]] == 2 && r.ctr[5] == 1);
                CHECK(r.ctr[6] == r.ctr[3] / 3 + 1 && r.ctr[7] == r.ctr[3] % 3 + 1);  /* the row and column it says */
            }
        }
    }
    /* what is drawn: one mark per taken cell */
    int x_marks = 0, o_marks = 0;
    for (int i = 0; i < 9; i++) {
        x_marks += r.board[i] == 1;
        o_marks += r.board[i] == 2;
    }
    CHECK(count_visible_type(&r, MG_SH_LINE) == 2 * x_marks && count_visible_type(&r, MG_SH_RING) == o_marks);
    CHECK(x_marks == o_marks || x_marks == o_marks + 1);
    const int end = r.state;
    if (score_out != NULL) *score_out = (uint32_t)r.ctr[0];
    if (saved_out != NULL) *saved_out = r.save_pending;
    now = run_to(&r, now, now + 4000);
    CHECK(r.finished);
    return end;
}

static void test_tictactoe(void)
{
    /* every level plays whole games; the unit's mark is drawn for each of its moves */
    int wins[3] = {0}, loses[3] = {0}, draws[3] = {0};
    for (int level = 0; level < 3; level++) {
        for (uint32_t g = 0; g < 300; g++) {
            uint32_t score = 0;
            int saved      = 0;
            const int end  = ttt_game(g + 1 + level * 1000, level, g % 2, &score, &saved);
            wins[level] += end == T_WIN;
            loses[level] += end == T_LOSE;
            draws[level] += end == T_DRAW;
            if (end == T_WIN) CHECK(score == (uint32_t)(10 * (level + 1)) && saved);
            if (end == T_DRAW) CHECK(score == (uint32_t)(3 * (level + 1)) && saved);
            if (end == T_LOSE) CHECK(score == 0);
        }
    }
    CHECK(wins[0] > 50 && loses[0] > 20);          /* random: it loses often */
    CHECK(wins[1] < wins[0]);                      /* it blocks and takes wins, so it loses less */
    CHECK(wins[2] == 0);                           /* perfect never loses */
    CHECK(draws[2] > 20 && loses[2] > 100);
    /* the menu draws three level buttons and no marks */
    mg_run_t r;
    mg_start(&r, &g_pack[P_TTT], 0, 5);
    CHECK(count_visible_type(&r, MG_SH_LINE) == 0 && count_visible_type(&r, MG_SH_RING) == 0);
    /* a tap outside every cell (the side edge) does nothing in the menu */
    mg_tap(&r, 10, 100, 0);
    CHECK(r.state == T_MENU);
}

/* Patch GM04: the Do It and Rock Paper Scissors state machines are tested in games_gm_test.c. */
enum { B_INTRO = 0, B_WAIT, B_SHOW, B_OK, B_OVER };

/* ------------------------------------------------------------------ the new guard, ops and the timer */
static void test_engine_bits(void)
{
    mg_run_t r;
    mg_start(&r, &g_pack[P_BOPIT], 0, 9);
    uint8_t a[4];
    /* floor, sub */
    r.ctr[0] = 5;
    r.ctr[1] = 9;
    a[0] = MG_OP_FLOOR; a[1] = 0; a[2] = 8; a[3] = 0;
    mg_act(&r, a, 0);
    CHECK(r.ctr[0] == 8);
    a[0] = MG_OP_SUB_CTR; a[1] = 1; a[2] = 0; a[3] = 0;
    mg_act(&r, a, 0);
    CHECK(r.ctr[1] == 1);
    /* patch GM04: ceil keeps a counter at most the value, and leaves a smaller one alone */
    r.ctr[4] = 40;
    a[0] = MG_OP_CEIL; a[1] = 4; a[2] = 5; a[3] = 0;
    mg_act(&r, a, 0);
    CHECK(r.ctr[4] == 5);
    r.ctr[4] = 3;
    mg_act(&r, a, 0);
    CHECK(r.ctr[4] == 3);
    /* sync with -1 is none */
    r.ctr[3] = -1;
    a[0] = MG_OP_SYNC; a[1] = 3; a[2] = 0; a[3] = 0;
    mg_act(&r, a, 0);
    CHECK(r.sync_region == MG_NO_REGION);
    /* a timer from a counter is held between 80 ms and 30 s */
    mg_run_t t;
    mg_start(&t, &g_pack[P_BOPIT], 0, 9);
    t.state  = B_SHOW;
    t.ctr[2] = 5;
    mg_enter(&t, 1000);
    CHECK(t.timer_due_ms == 1000 + MG_TIMER_MIN_MS);
    t.ctr[2] = 32000;
    mg_enter(&t, 1000);
    CHECK(t.timer_due_ms == 1000 + MG_TIMER_MAX_MS);
    CHECK(shipped_tone(0) && !shipped_tone(5));
}

/* ------------------------------------------------------------------ the gentle shake (patch UI15) */
/* Fifty samples a second of a wobble on x around one g on y: `amp` m/s^2 at `hz`, for `ms` milliseconds. Returns the first result that is not none. */
static int wobble(mgi_shake_t* k, uint32_t* now, float amp, float hz, int ms, int* shakes, int* easies)
{
    int first = MGI_SHAKE_NONE;
    for (int t = 0; t < ms; t += 20) {
        *now += 20;
        const float ph = 6.2831853f * hz * (float)t / 1000.0f;
        /* a sine from a small polynomial so the test needs no libm */
        float x = ph;
        while (x > 6.2831853f) x -= 6.2831853f;
        float v = x < 3.1415926f ? x : x - 6.2831853f;  /* -pi to pi */
        const float s = v - v * v * v / 6.0f + v * v * v * v * v / 120.0f - v * v * v * v * v * v * v / 5040.0f;
        const int r = mgi_shake_update(k, amp * s, 9.80665f, 0.0f, *now);
        if (r == MGI_SHAKE_OK) { (*shakes)++; }
        if (r == MGI_SHAKE_EASY) { (*easies)++; }
        if (r != MGI_SHAKE_NONE && first == MGI_SHAKE_NONE) first = r;
    }
    return first;
}

static void test_gentle_shake(void)
{
    int shakes = 0, easies = 0;
    uint32_t now = 0;
    mgi_shake_t k;
    /* the numbers the game uses: strokes of 2.2 m/s^2, three within 0.9 s, too hard at 20 m/s^2 */
    CHECK(MGI_SHAKE_STROKE > 2.19f && MGI_SHAKE_STROKE < 2.21f && MGI_SHAKE_STROKES == 3 && MGI_SHAKE_TOO_HARD > 19.9f && MGI_SHAKE_TOO_HARD < 20.1f);
    /* a gentle wobble of a few centimeters triggers: 3 cm at 3 Hz is about 10 m/s^2, 1.5 cm at 3 Hz about 5, 1 cm at 2.5 Hz about 2.5 */
    const float amps[3] = {10.0f, 5.0f, 3.0f};
    const float hzs[3]  = {3.0f, 3.0f, 2.5f};
    for (int i = 0; i < 3; i++) {
        mgi_shake_init(&k);
        shakes = easies = 0;
        now += 5000;
        for (int t = 0; t < 30; t++) { now += 20; mgi_shake_update(&k, 0, 9.80665f, 0, now); }
        const int r = wobble(&k, &now, amps[i], hzs[i], 1000, &shakes, &easies);
        CHECK(r == MGI_SHAKE_OK && shakes >= 1 && easies == 0);
    }
    /* it triggers fast: within half a second of a 5 m/s^2 wobble */
    {
        mgi_shake_init(&k);
        shakes = easies = 0;
        for (int t = 0; t < 30; t++) { now += 20; mgi_shake_update(&k, 0, 9.80665f, 0, now); }
        wobble(&k, &now, 5.0f, 3.0f, 500, &shakes, &easies);
        CHECK(shakes == 1);
    }
    /* a tiny tremor (1 m/s^2), the table being tapped (a lone 8 m/s^2 bump), a slow tilt and standing still do not count */
    mgi_shake_init(&k);
    shakes = easies = 0;
    wobble(&k, &now, 1.0f, 3.0f, 3000, &shakes, &easies);
    CHECK(shakes == 0 && easies == 0);
    for (int t = 0; t < 40; t++) { now += 20; mgi_shake_update(&k, 0, 9.80665f, 0, now); }
    for (int t = 0; t < 2; t++) { now += 20; mgi_shake_update(&k, 8.0f, 9.80665f, 0, now); }
    for (int t = 0; t < 100; t++) { now += 20; if (mgi_shake_update(&k, 0, 9.80665f, 0, now) != MGI_SHAKE_NONE) shakes++; }
    CHECK(shakes == 0);
    for (int t = 0; t < 100; t++) {   /* a slow roll of 25 degrees over two seconds */
        now += 20;
        const float a = 0.436f * (float)t / 100.0f;
        const float sa = a - a * a * a / 6.0f, ca = 1.0f - a * a / 2.0f + a * a * a * a / 24.0f;
        if (mgi_shake_update(&k, 9.80665f * sa, 9.80665f * ca, 0, now) != MGI_SHAKE_NONE) shakes++;
    }
    CHECK(shakes == 0 && easies == 0);
    /* a hard fling does not count as a shake: 40 m/s^2 (4 g) at 3 Hz is "too hard" and the game answers Easy */
    mgi_shake_init(&k);
    shakes = easies = 0;
    now += 5000;
    for (int t = 0; t < 30; t++) { now += 20; mgi_shake_update(&k, 0, 9.80665f, 0, now); }
    const int r = wobble(&k, &now, 40.0f, 3.0f, 1000, &shakes, &easies);
    CHECK(r == MGI_SHAKE_EASY && easies >= 1 && shakes == 0);
    /* and a violent single swing with its rebound is easy too, not a score */
    mgi_shake_init(&k);
    shakes = easies = 0;
    for (int t = 0; t < 30; t++) { now += 20; mgi_shake_update(&k, 0, 9.80665f, 0, now); }
    for (int t = 0; t < 3; t++) { now += 20; if (mgi_shake_update(&k, 30.0f, 9.80665f, 0, now) == MGI_SHAKE_OK) shakes++; }
    for (int t = 0; t < 3; t++) { now += 20; if (mgi_shake_update(&k, -30.0f, 9.80665f, 0, now) == MGI_SHAKE_EASY) easies++; }
    CHECK(shakes == 0 && easies == 1);
    /* after a shake the detector keeps quiet for 0.8 s (one wobble is one event) */
    mgi_shake_init(&k);
    shakes = easies = 0;
    for (int t = 0; t < 30; t++) { now += 20; mgi_shake_update(&k, 0, 9.80665f, 0, now); }
    wobble(&k, &now, 6.0f, 3.0f, 700, &shakes, &easies);
    CHECK(shakes == 1);
}

/* ------------------------------------------------------------------ magic 8 ball */
enum { E_READY = 0, E_SHAKE, E_ANSWER, E_EASY };

static void test_eightball(void)
{
    const mg_pack_t* p = &g_pack[P_BALL];
    mg_run_t r;
    int seen[20] = {0};
    CHECK(p->n_regions == 1);
    {
        mg_region_t g;
        mg_region_get(p, 0, &g);
        CHECK(g.w >= 140 && g.h >= 140 && g.y >= MG_SAFE_TOP && g.y + g.h <= MG_SAFE_BOTTOM);
    }
    for (uint32_t seed = 1; seed < 600; seed++) {
        mg_start(&r, p, 0, seed);
        CHECK(r.state == E_READY && r.ctr[1] == -1);
        r.tone_n = 0;
        if (seed % 2) {
            mg_tap(&r, 160, 100, 10);
        } else {
            mg_input(&r, MG_EV_SHAKE, 10);   /* the gentle shake the sensors post */
        }
        CHECK(r.state == E_SHAKE && r.light_new == 1 && r.light == 1 && r.tone_n == 1);  /* a hum and a blue light, together */
        mg_tap(&r, 160, 100, 40);            /* a tap while the ball is thinking does nothing */
        CHECK(r.state == E_SHAKE);
        uint32_t now = run_to(&r, 10, 1300);
        CHECK(r.state == E_ANSWER);
        const int a = r.ctr[1];
        CHECK(a >= 0 && a < 20);
        seen[a]++;
        CHECK(r.ctr[2] == (a < 10 ? 0 : (a < 15 ? 1 : 2)) && r.light == (a < 10 ? 2 : (a < 15 ? 3 : 4)));
        int answers = 0;
        for (int i = 0; i < p->n_shapes; i++) {
            mg_shape_t sh;
            mg_shape_get(p, i, &sh);
            if (sh.type == MG_SH_TEXT && sh.cond_ctr == 1 && mg_shape_visible(&r, i)) answers++;
        }
        CHECK(answers == 1);
        /* ask again: a tap or a shake from the answer starts a new one; a too-hard shake is "Easy!" and changes nothing */
        mg_run_t again = r;
        mg_input(&again, MG_EV_EASY, now + 10);
        CHECK(again.state == E_EASY);
        again.tone_n = 0;
        now = run_to(&again, now + 10, now + 1300);
        CHECK(again.state == E_READY);
        mg_input(&r, MG_EV_SHAKE, now + 20);
        CHECK(r.state == E_SHAKE);
    }
    for (int a = 0; a < 20; a++) CHECK(seen[a] > 5);   /* all twenty answers turn up */
    /* twenty answers in English and Spanish, each short enough for two lines, and the hint says gently */
    int texts_ok = 0;
    for (int i = 0; i < 20; i++) {
        const char* en = mg_text_raw(p, i, 0);
        const char* es = mg_text_raw(p, i, 1);
        texts_ok += strlen(en) > 1 && strlen(en) <= 30 && strlen(es) > 1 && strlen(es) <= 30 && strcmp(en, es) != 0;
    }
    CHECK(texts_ok >= 19);   /* "Yes" and "Si" differ; every answer is translated */
}

/* ------------------------------------------------------------------ dice and coin */
enum { D_IDLE = 0, D_R1, D_R2, D_R3, D_R4, D_R5, D_R6, D_LAND, D_EASY };

static void test_dice(void)
{
    const mg_pack_t* p = &g_pack[P_DICE];
    mg_run_t r;
    CHECK(p->n_regions == 4);
    for (int i = 0; i < 3; i++) {   /* the mode tiles */
        mg_region_t g;
        mg_region_get(p, i, &g);
        CHECK(g.h >= 44 && g.w >= 88 && g.y >= MG_SAFE_TOP && g.y + g.h <= MG_SAFE_BOTTOM);
    }
    int six = 0, heads = 0, tails = 0;
    for (uint32_t seed = 1; seed < 400; seed++) {
        mg_start(&r, p, 0, seed);
        const int mode = (int)(seed % 3);
        r.tone_n = 0;
        if (seed % 4 == 0) {
            mg_input(&r, MG_EV_SHAKE, 10);   /* a gentle shake rolls the last mode (the first is one die) */
        } else {
            mg_tap(&r, cx(p, mode), cy(p, mode), 10);
        }
        const int the_mode = seed % 4 == 0 ? 0 : mode;
        CHECK(r.state == D_R1 && r.ctr[0] == the_mode && r.tone_n == 1 && r.sync_region == 3);   /* the rattle, at once */
        int frames = 1;
        uint32_t now = 10;
        int values_seen[7] = {0};
        for (int st = D_R2; st <= D_LAND; st++) {
            r.tone_n = 0;
            while (r.state != st && !r.finished) { now += 30; mg_tick(&r, now); }
            CHECK(r.state == st);
            if (st != D_LAND) { frames++; values_seen[r.ctr[1]]++; }
        }
        CHECK(frames == 6);   /* six tumbling frames, then the landing */
        CHECK(r.tone_n == 1 && r.sync_region == 3);            /* the thud (or a ting for the coin), with the picture */
        const int d1 = r.ctr[1], d2 = r.ctr[2];
        CHECK(d1 >= 1 && d1 <= 6 && d2 >= 1 && d2 <= 6);
        if (the_mode == 0) { CHECK(r.ctr[7] == 1 && r.ctr[5] == d1); six += d1 == 6; }
        if (the_mode == 1) { CHECK(r.ctr[7] == 2 && r.ctr[5] == d1 + d2); }
        if (the_mode == 2) {
            CHECK((r.ctr[7] == 3 || r.ctr[7] == 4) && r.ctr[3] == r.ctr[4] && r.ctr[7] == 3 + r.ctr[4]);
            heads += r.ctr[7] == 3;
            tails += r.ctr[7] == 4;
        }
        /* the picture: one big die, two dice or the coin is drawn, and exactly one result text */
        int dice_shapes = 0, coin_shapes = 0, results = 0;
        for (int i = 0; i < p->n_shapes; i++) {
            mg_shape_t sh;
            mg_shape_get(p, i, &sh);
            if (!mg_shape_visible(&r, i)) continue;
            dice_shapes += sh.type == MG_SH_DIE;
            coin_shapes += sh.type == MG_SH_COIN;
            results += sh.type == MG_SH_TEXT && sh.cond_ctr == 7 && sh.cond_val != 0;
        }
        CHECK(dice_shapes == (the_mode == 0 ? 1 : (the_mode == 1 ? 2 : 0)) && coin_shapes == (the_mode == 2 ? 1 : 0) && results == 1);
        /* roll again from the landing; a too-hard shake is Easy and does not roll */
        mg_run_t easy = r;
        mg_input(&easy, MG_EV_EASY, now + 10);
        CHECK(easy.state == D_EASY);
        mg_input(&r, MG_EV_SHAKE, now + 20);
        CHECK(r.state == D_R1);
        /* taps while it tumbles change nothing */
        mg_tap(&r, cx(p, 2), cy(p, 2), now + 30);
        CHECK(r.state == D_R1 && r.ctr[0] == the_mode);
    }
    CHECK(six > 5 && heads > 20 && tails > 20);
}

/* ------------------------------------------------------------------ celebrations (patch UI15) */
/* A win the rules name asks for confetti; a loss, a draw and a tie ask for nothing; a new best (place 0) is the big one, nothing else is. */
static void test_celebration(void)
{
    CHECK(mg_celebration_for_rank(0) == 2 && mg_celebration_for_rank(1) == 0 && mg_celebration_for_rank(4) == 0 && mg_celebration_for_rank(-1) == 0);
    uint16_t scores[MG_SCORES] = {0};
    CHECK(mg_celebration_for_rank(mg_scores_add(scores, 0, 5)) == 2);    /* the first score is a best */
    CHECK(mg_celebration_for_rank(mg_scores_add(scores, 0, 3)) == 0);    /* lower than the best: no */
    CHECK(mg_celebration_for_rank(mg_scores_add(scores, 0, 9)) == 2);    /* a new best: yes */
    CHECK(mg_celebration_for_rank(mg_scores_add(scores, 0, 9)) == 0);    /* a tie keeps the older first: not a new best */
    CHECK(mg_celebration_for_rank(mg_scores_add(scores, 0, 0)) == 0);    /* a score of zero is not saved */
    uint16_t times[MG_SCORES] = {0};                                      /* a time: lower is better */
    CHECK(mg_celebration_for_rank(mg_scores_add(times, 1, 400)) == 2 && mg_celebration_for_rank(mg_scores_add(times, 1, 450)) == 0 &&
          mg_celebration_for_rank(mg_scores_add(times, 1, 380)) == 2);
    /* Tic-Tac-Toe: only the win celebrates (a draw and a loss do not), whatever the level */
    int wins = 0, others = 0;
    for (int level = 0; level < 3; level++) {
        for (uint32_t g = 0; g < 200; g++) {
            const mg_pack_t* p = &g_pack[P_TTT];
            mg_run_t r;
            mg_start(&r, p, 0, g + 77 + (uint32_t)level * 500);
            uint32_t now = 0;
            mg_tap(&r, cx(p, level * 3 + 1), cy(p, level * 3 + 1), now);
            int guard = 0;
            int celebrated = 0;
            while (r.state != T_WIN && r.state != T_LOSE && r.state != T_DRAW && guard++ < 40) {
                int free_c[9], n = 0;
                for (int i = 0; i < 9; i++) if (r.board[i] == 0) free_c[n++] = i;
                const int c = free_c[(g * 7 + (uint32_t)guard) % (uint32_t)n];
                mg_tap(&r, cx(p, c), cy(p, c), now);
                celebrated |= r.celebrate;
                if (r.state == T_THINK) {
                    now = run_to(&r, now, now + 700);
                    celebrated |= r.celebrate;
                }
            }
            if (r.state == T_WIN) { wins++; CHECK(celebrated == 1); } else { others++; CHECK(celebrated == 0); }
        }
    }
    CHECK(wins > 20 && others > 20);
    /* the other games never celebrate by rule (a new best does it, in the player) */
    for (int g = 0; g < N_PACKS; g++) {
        if (g == P_TTT || g == P_RPS) continue;
        mg_run_t r;
        mg_start(&r, &g_pack[g], 0, 3);
        uint32_t now = 0;
        for (int i = 0; i < 400 && !r.finished; i++) {
            now += 30;
            mg_tick(&r, now);
            if (i % 9 == 0) mg_tap(&r, 100, 100, now);
            if (i % 13 == 0) mg_input(&r, MG_EV_SHAKE, now);
            CHECK(r.celebrate == 0);
        }
    }
}

/* ------------------------------------------------------------------ hostile packs */
static uint32_t s_fz = 2463534242u;
static uint32_t fz(void)
{
    s_fz ^= s_fz << 13;
    s_fz ^= s_fz >> 17;
    s_fz ^= s_fz << 5;
    return s_fz;
}

/* Damaged copies of the new packs (with the checksum repaired so the damage reaches the checks) are refused or run 300 random events,
 * every input kind and the board included, without leaving their tables (run under the address sanitizer). */
static void test_hostile_new_packs(void)
{
    static uint8_t b[MG_MAX_PACK];
    int ran = 0, refused = 0;
    for (int g = P_WHACK; g < N_PACKS; g++) {
        for (int round = 0; round < 1200; round++) {
            memcpy(b, g_blob[g], g_len[g]);
            const int edits = 1 + (int)(fz() % 4);
            for (int e = 0; e < edits; e++) {
                b[MG_HEADER + fz() % (g_len[g] - MG_HEADER - MG_CRC_LEN)] = (uint8_t)fz();
            }
            const uint16_t payload = mg_u16(b + 24);
            const uint32_t c       = mg_crc32(b, payload);
            memcpy(b + payload, &c, 4);
            mg_pack_t p;
            if (mg_parse(b, g_len[g], &p) != MG_OK) {
                refused++;
                continue;
            }
            ran++;
            mg_run_t r;
            mg_start(&r, &p, 0, fz());
            uint32_t now = 0;
            for (int i = 0; i < 300 && !r.finished; i++) {
                now += 30 + fz() % 400;
                switch (fz() % 5) {
                    case 0: mg_tick(&r, now); break;
                    case 1: mg_tap(&r, (int)(fz() % 320), (int)(fz() % 240), now); break;
                    case 2: mg_input(&r, MG_EV_SWIPE_L + (int)(fz() % 8), now); break;
                    case 3: mg_tick(&r, now + 5000); break;
                    default: mg_tap(&r, 160, 100, now); break;
                }
                for (int k = 0; k < p.n_shapes; k++) {
                    (void)mg_shape_visible(&r, k);
                    mg_shape_t sh;
                    mg_shape_get(&p, k, &sh);
                    if (sh.type == MG_SH_MOLE && mg_shape_visible(&r, k)) {
                        CHECK(mg_mole_region(&r, &sh) < p.n_regions);
                    }
                }
                r.tone_n = 0;
                CHECK(r.steps <= p.step_budget + 1u);
            }
        }
    }
    CHECK(ran > 100 && refused > 100);
}

int main(int argc, char** argv)
{
    if (argc != 1 + N_PACKS) {
        printf("usage: games_v2_core_test memory.mpk whack.mpk tictactoe.mpk bopit.mpk rps.mpk eightball.mpk dice.mpk\n");
        return 2;
    }
    for (int i = 0; i < N_PACKS; i++) {
        load(i, argv[i + 1]);
    }
    test_all_packs_parse_and_stay_in_the_safe_area();
    test_new_refusals();
    test_sound_clips();
    test_tilt_detector();
    test_board();
    test_whack();
    test_tictactoe();
    test_engine_bits();
    test_gentle_shake();
    test_eightball();
    test_dice();
    test_celebration();
    test_hostile_new_packs();
    if (failures == 0) {
        printf("all passed\n");
        return 0;
    }
    printf("%d failures\n", failures);
    return 1;
}
