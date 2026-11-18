/* Soak test for the 24.9 day (2^31 ms) and 49.7 day (2^32 ms) wrap class, over every core that uses the stamp helper.
 * cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the headers> wrap_soak_test.c -lm
 *
 * Method: a core must not know what time it is, only how long ago things happened. Each scenario below is a fixed script of
 * events at times relative to a start time. It runs once at a reference start (1000 ms after boot) and again at start times
 * that sit on the wrap points: just before and after 2^31 ms, and just before and after 2^32 ms (so the clock passes the
 * point in the middle of the script). Every observable answer goes into a hash. The hash must equal the reference hash.
 * Then "stale" checks: a deadline armed once is read again after 2^31 ms and 2^32 ms of silence, and must not read pending. */
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "maipai_time_core.h"
#include "maipai_lock_core.h"
#include "maipai_pickup_core.h"
#include "maipai_games_input_core.h"
#include "maipai_status_core.h"
#include "maipai_fx_core.h"
#include "maipai_face_track_core.h"
#include "maipai_remote_core.h"

static int failures;
#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);       \
            failures++;                                                  \
        }                                                                \
    } while (0)

typedef struct { uint64_t h; } hash_t;
static void feed(hash_t* x, uint32_t v)
{
    x->h ^= v;
    x->h *= 1099511628211ull;
}
#define NEW_HASH ((hash_t){1469598103934665603ull})

/* ---- the scenarios: each takes the start time and returns a hash of what it saw ---- */

static uint64_t scen_time(uint32_t base)
{
    hash_t x = NEW_HASH;
    uint32_t at = mt_stamp(base + 500u, 90000u), ext = 0;
    for (uint32_t t = 0; t <= 200000u; t += 250u) {
        feed(&x, (uint32_t)mt_pending(base + t, at));
        feed(&x, (uint32_t)mt_reached(base + t, at));
        feed(&x, mt_elapsed(base + t, base));
        if (t == 1000u) mt_extend(base + t, &ext, mt_stamp(base + t, 30000u));
        if (t == 20000u) mt_extend(base + t, &ext, mt_stamp(base + t, 5000u)); /* earlier: must not shorten */
        feed(&x, (uint32_t)mt_pending(base + t, ext));
    }
    return x.h;
}

static uint64_t scen_lock(uint32_t base)
{
    hash_t x = NEW_HASH;
    uint8_t salt[LK_SALT_LEN] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};
    mlk_t s;
    mlk_init(&s);
    mlk_set(&s, "1234", NULL, salt);
    mlk_set_auto(&s, 1);
    mlk_activity(&s, base);
    for (uint32_t t = 0; t <= 130000u; t += 5000u) feed(&x, (uint32_t)mlk_idle_due(&s, base + t, 0, 0)); /* due at 60 s */
    for (uint32_t t = 0; t <= 130000u; t += 5000u) { /* a busy turn keeps resetting the timer */
        feed(&x, (uint32_t)mlk_idle_due(&s, base + 200000u + t, 0, t < 70000u));
    }
    feed(&x, (uint32_t)mlk_lock_now(&s, base + 400000u));
    mlk_screen_touch(&s, base + 400100u);
    const char wrong[] = "000000";
    for (int i = 0; i < 6; i++) feed(&x, (uint32_t)mlk_key(&s, wrong[i], base + 401000u + (uint32_t)i * 50u));
    const char right[] = "1234";
    for (int i = 0; i < 4; i++) feed(&x, (uint32_t)mlk_key(&s, right[i], base + 402000u + (uint32_t)i * 50u));
    feed(&x, (uint32_t)s.locked);
    /* the tool lockouts: 60 s, 120 s, a save and a restore in the middle */
    mlk_t k;
    mlk_init(&k);
    mlk_set(&k, "1234", NULL, salt);
    uint32_t t0 = base + 500000u;
    for (int round = 0; round < 3; round++) {
        for (int i = 0; i < LK_TOOL_MAX_FAILS; i++) mlk_tool_note(&k, t0, MLK_R_WRONG_CURRENT);
        for (uint32_t d = 0; d <= 400000u; d += 10000u) feed(&x, (uint32_t)mlk_tool_open(&k, t0 + d));
        if (round == 1) {
            mlk_tool_saved_t saved;
            mlk_tool_save(&k, t0 + 30000u, &saved);
            feed(&x, saved.block_ms);
            feed(&x, (uint32_t)saved.strikes);
            mlk_tool_restore(&k, &saved, t0 + 31000u);
            for (uint32_t d = 31000u; d <= 400000u; d += 10000u) feed(&x, (uint32_t)mlk_tool_open(&k, t0 + d));
        }
        t0 += 500000u;
    }
    return x.h;
}

static uint64_t scen_pickup(uint32_t base)
{
    hash_t x = NEW_HASH;
    mp_t d;
    mp_init(&d);
    uint32_t t = 0;
    const float g = 9.80665f;
    for (int i = 0; i < 400; i++, t += 20) feed(&x, (uint32_t)mp_update(&d, 0.0f, 0.0f, g, base + t));
    for (int i = 0; i < 200; i++, t += 20) { /* tilted 80 degrees with its own motion renewed */
        if (i % 20 == 0) mp_note_own(&d, base + t, MP_OWN_HOLD_MS, 0);
        feed(&x, (uint32_t)mp_update(&d, 0.0f, g * sinf(1.396f), g * cosf(1.396f), base + t));
    }
    for (int i = 0; i < 300; i++, t += 20) feed(&x, (uint32_t)mp_update(&d, 0.0f, 0.0f, g, base + t));
    feed(&x, (uint32_t)mp_is_held(&d));
    feed(&x, (uint32_t)mt_pending(base + t, d.own_until));
    return x.h;
}

static uint64_t scen_games_input(uint32_t base)
{
    hash_t x = NEW_HASH;
    mgi_t t;
    mgi_init(&t);
    uint32_t n = 0;
    for (int i = 0; i < 150; i++, n += 20) feed(&x, (uint32_t)mgi_update(&t, 0.0f, 0.0f, 1.0f, base + n));
    mgi_note_shake(&t, base + n);
    for (int i = 0; i < 100; i++, n += 20) feed(&x, (uint32_t)mgi_update(&t, 0.35f, 0.0f, 0.94f, base + n)); /* quiet after a shake, then tilt */
    mgi_shake_t k;
    memset(&k, 0, sizeof k);
    for (int i = 0; i < 120; i++, n += 20) feed(&x, (uint32_t)mgi_shake_update(&k, (i / 4) % 2 ? 3.0f : -3.0f, 0.0f, 1.0f, base + n));
    return x.h;
}

static uint64_t scen_status(uint32_t base)
{
    hash_t x = NEW_HASH;
    const uint32_t hold = mst_mic_hold_until(base + 1000u);
    uint32_t last = 0;
    for (uint32_t t = 0; t <= 20000u; t += 250u) {
        feed(&x, (uint32_t)mst_mic_shown(0, hold, base + t, 0));
        if (mst_face_due(last, base + t)) {
            last = base + t;
            feed(&x, 1u);
        }
    }
    return x.h;
}

static uint64_t scen_fx(uint32_t base)
{
    hash_t x = NEW_HASH;
    mg_t g;
    mg_init(&g);
    uint32_t t = 0;
    mg_note_start(&g, base);
    for (int i = 0; i < 400; i++, t += 33) { /* slow frames for a while, then fast ones: the level sheds and comes back */
        const uint32_t us = (i > 40 && i < 120) ? 60000u : 20000u;
        feed(&x, (uint32_t)mg_feed(&g, base + t, us));
        feed(&x, (uint32_t)mg_try_restore(&g, base + t));
        feed(&x, (uint32_t)mg_in_grace(&g, base + t));
        feed(&x, (uint32_t)g.level);
    }
    return x.h;
}

static uint64_t scen_face_track(uint32_t base)
{
    hash_t x = NEW_HASH;
    ft_cfg_t cfg;
    memset(&cfg, 0, sizeof cfg);
    ft_t f;
    ft_init(&f, &cfg);
    uint32_t t = 0;
    for (int i = 0; i < 80; i++, t += 100) {
        ft_hist_add(&f, base + t, (float)i, 0.5f * (float)i);
        ft_account(&f, base + t);
        if (i % 7 == 0 && ft_budget_free(&f, base + t)) ft_budget_spend(&f, base + t);
        feed(&x, (uint32_t)ft_budget_free(&f, base + t));
        feed(&x, f.hour_acc);
        float pan, tilt;
        ft_hist_at(&f, base + t - 150u, 0.0f, 0.0f, &pan, &tilt);
        feed(&x, (uint32_t)(int32_t)(pan * 10.0f));
    }
    return x.h;
}

static uint64_t scen_remote(uint32_t base)
{
    hash_t x = NEW_HASH;
    mr_t r;
    mr_init(&r);
    uint32_t token = 0;
    mr_session(&r, 1, "remote", base);
    mr_set_host(&r, 77);
    feed(&x, (uint32_t)mr_session_on(&r, base + 1000u));
    feed(&x, (uint32_t)mr_action(&r, "photo", base + 1500u, &token));
    mr_set_window(&r, 5);
    feed(&x, (uint32_t)mr_gate(&r, "photo", token, base + 2000u));
    for (uint32_t t = 2000u; t <= 12000u; t += 500u) {
        mr_session(&r, 1, "remote", base + t - (t % 3000u)); /* a heartbeat about every 3 s */
        feed(&x, (uint32_t)mr_grant_open(&r, 1, base + t));
        feed(&x, (uint32_t)mr_session_on(&r, base + t));
    }
    for (uint32_t t = 12000u; t <= 40000u; t += 1000u) feed(&x, (uint32_t)mr_session_on(&r, base + t)); /* the dead man timeout */
    feed(&x, (uint32_t)mr_action(&r, "photo", base + 41000u, &token));
    return x.h;
}

/* ---- the drivers ---- */

typedef uint64_t (*scenario_fn)(uint32_t base);
static const struct { const char* name; scenario_fn run; } SCENARIOS[] = {
    {"time", scen_time}, {"lock", scen_lock}, {"pickup", scen_pickup}, {"games_input", scen_games_input},
    {"status", scen_status}, {"fx", scen_fx}, {"face_track", scen_face_track}, {"remote", scen_remote},
};
#define N_SCEN ((int)(sizeof SCENARIOS / sizeof SCENARIOS[0]))

/* Start times chosen so that every script, which runs for under 15 minutes, starts, ends or passes across a wrap point. */
static const uint32_t STARTS[] = {
    MT_HALF - 3000u,         /* crosses 2^31 early in the script */
    MT_HALF - 300000u,       /* crosses 2^31 in the middle */
    MT_HALF - 800000u,       /* crosses 2^31 near the end */
    MT_HALF,                 /* starts on 2^31 */
    MT_HALF + 5000u,         /* already past 2^31 */
    0xFFFFFFFFu - 3000u,     /* crosses 2^32 early */
    0xFFFFFFFFu - 300000u,   /* crosses 2^32 in the middle */
    0xFFFFFFFFu - 800000u,   /* crosses 2^32 near the end */
    0xFFFFFFFFu,             /* starts one before the wrap */
    0xFFFFFFFFu - 1u,
};

int main(void)
{
    for (int i = 0; i < N_SCEN; i++) {
        const uint64_t ref = SCENARIOS[i].run(1000u);
        for (size_t s = 0; s < sizeof STARTS / sizeof STARTS[0]; s++) {
            if (SCENARIOS[i].run(STARTS[s]) != ref) {
                printf("FAIL %s: the answers at start %u ms differ from the answers at 1000 ms\n", SCENARIOS[i].name, (unsigned)STARTS[s]);
                failures++;
            }
        }
    }

    /* stale deadlines: armed once, read again after 2^31 and 2^32 ms of silence, never pending (the only window where a deadline
     * can read pending again is the last hour before the counter itself returns to the stamp, 49.7 days after it was armed). */
    static const uint32_t STALE_BASES[] = {1000u, MT_HALF - 7000u, 0xFFFFFF00u};
    for (size_t b = 0; b < sizeof STALE_BASES / sizeof STALE_BASES[0]; b++) {
        const uint32_t base = STALE_BASES[b];
        uint32_t at = mt_stamp(base, 30000u);
        CHECK(mt_pending(base + 1u, at));
        for (uint64_t gap = 40000u; gap < 0xFFFFFFFFull - MT_MAX_AHEAD_MS - 40000u; gap += 0x01000000u) {
            if (mt_pending(base + (uint32_t)gap, at)) {
                printf("FAIL stale: a deadline armed at %u reads pending %u ms later\n", (unsigned)base, (unsigned)(uint32_t)gap);
                failures++;
                break;
            }
        }
        mlk_t k;
        mlk_init(&k);
        for (int i = 0; i < LK_TOOL_MAX_FAILS; i++) mlk_tool_note(&k, base, MLK_R_WRONG_CURRENT);
        CHECK(mlk_tool_open(&k, base + 1000u) == MLK_R_TOO_MANY);
        CHECK(mlk_tool_open(&k, base + MT_HALF) == MLK_R_OK);       /* the lockout ended long ago */
        CHECK(mlk_tool_open(&k, base + MT_HALF + 5u) == MLK_R_OK);
        mr_t r;
        mr_init(&r);
        mr_session(&r, 1, "remote", base);
        CHECK(mr_session_on(&r, base + 1000u));
        CHECK(!mr_session_on(&r, base + MT_HALF)); /* a controller that went silent is not connected 24.9 days later */
    }

    if (failures == 0) printf("wrap soak ok\n");
    return failures == 0 ? 0 : 1;
}
