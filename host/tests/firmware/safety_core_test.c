/* Host test for the safety fixes of patches SF01 and SF02.
 * cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the headers> safety_core_test.c -lm.
 * Every case that names a time past 2^31 ms stands for a unit that has run for more than 24.9 days. */
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
#include "maipai_touch_core.h"
#include "maipai_prefs_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static const uint32_t LATE = 0x90000000u; /* about 25.8 days */
static const uint32_t WRAP = 0xFFFFFF00u; /* just before the 32-bit counter wraps */

static void test_time(void)
{
    CHECK(mt_stamp(10, 5) == 15);
    CHECK(mt_stamp(0xFFFFFFFFu, 1) == 1); /* 0 is "not armed", never a deadline */
    CHECK(!mt_pending(LATE, 0));          /* not armed: never pending, even past 2^31 */
    CHECK(mt_pending(100, 200));
    CHECK(!mt_pending(200, 200));
    CHECK(mt_pending(WRAP, mt_stamp(WRAP, 1000))); /* across the wrap */
    CHECK(!mt_pending(WRAP + 2000u, mt_stamp(WRAP, 1000)));
    CHECK(mt_elapsed(5, WRAP) == 261u);
    uint32_t at = mt_stamp(1000, 50);
    CHECK(mt_pending_clear(1010, &at) == 1 && at != 0);
    CHECK(mt_pending_clear(1100, &at) == 0 && at == 0); /* reached: disarmed so it cannot flip back */
    CHECK(mt_pending_clear(1100u + MT_HALF, &at) == 0);
    at = mt_stamp(1000, 50);
    CHECK(mt_pending_clear(1000u + MT_HALF, &at) == 0 && at == 0); /* read first at +2^31: disarmed, not pending */
    /* a stamp that was armed and has passed is not pending again 2^31 ms later (a unit up for 25 days) */
    {
        const uint32_t armed = mt_stamp(5000, 1500);
        CHECK(mt_pending(5100, armed));
        CHECK(!mt_pending(armed + 10, armed));
        CHECK(!mt_pending(armed + MT_HALF, armed));
        CHECK(!mt_pending(armed + MT_HALF + 12345u, armed));
        CHECK(!mt_pending(armed + 2u * MT_MAX_AHEAD_MS, armed));
    }
    CHECK(mt_stamp(10, 0xFFFFFFFFu) == 10u + MT_MAX_AHEAD_MS); /* a delay longer than the limit is clamped */
    uint32_t e = 0;
    mt_extend(10, &e, 50);
    CHECK(e == 50);
    mt_extend(10, &e, 30); /* an earlier deadline never shortens a later one */
    CHECK(e == 50);
    mt_extend(10, &e, 90);
    CHECK(e == 90);
}

static void test_lock(void)
{
    uint8_t salt[LK_SALT_LEN] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};
    mlk_t s;
    mlk_init(&s);
    CHECK(mlk_set(&s, "1234", NULL, salt) == MLK_R_OK);
    /* the keypad on a unit that has run longer than 24.9 days takes digits. */
    CHECK(mlk_lock_now(&s, LATE) == MLK_R_OK);
    mlk_screen_touch(&s, LATE);
    CHECK(mlk_key(&s, '1', LATE + 10) == MLK_EV_NONE);
    CHECK(mlk_key(&s, '2', LATE + 20) == MLK_EV_NONE);
    CHECK(mlk_key(&s, '3', LATE + 30) == MLK_EV_NONE);
    CHECK(mlk_key(&s, '4', LATE + 40) == MLK_EV_UNLOCK);
    CHECK(!s.locked);

    /* five wrong current codes stop the tools for a minute; a good one in between resets the count. */
    mlk_t t;
    mlk_init(&t);
    CHECK(mlk_set(&t, "1234", NULL, salt) == MLK_R_OK);
    uint32_t now = 1000;
    for (int i = 0; i < LK_TOOL_MAX_FAILS; i++) {
        CHECK(mlk_tool_open(&t, now) == MLK_R_OK);
        int r = mlk_clear(&t, "0000");
        CHECK(r == MLK_R_WRONG_CURRENT);
        mlk_tool_note(&t, now, r);
        now += 100;
    }
    CHECK(mlk_tool_open(&t, now) == MLK_R_TOO_MANY);
    CHECK(mlk_tool_open(&t, now + LK_TOOL_LOCKOUT_MS - 200) == MLK_R_TOO_MANY);
    CHECK(mlk_tool_open(&t, now + LK_TOOL_LOCKOUT_MS + 200) == MLK_R_OK);
    mlk_tool_note(&t, now, MLK_R_WRONG_CURRENT);
    mlk_tool_note(&t, now, MLK_R_OK);
    CHECK(t.tool_fails == 0);
    CHECK(strcmp(MLK_REASONS[MLK_R_TOO_MANY], "too_many") == 0);
    /* the lockout also ends on a unit past 24.9 days */
    mlk_t u;
    mlk_init(&u);
    mlk_set(&u, "1234", NULL, salt);
    for (int i = 0; i < LK_TOOL_MAX_FAILS; i++) mlk_tool_note(&u, LATE, MLK_R_WRONG_CURRENT);
    CHECK(mlk_tool_open(&u, LATE + 1) == MLK_R_TOO_MANY);
    CHECK(mlk_tool_open(&u, LATE + LK_TOOL_LOCKOUT_MS + 1) == MLK_R_OK);

    /* the lockouts grow: 60 s, then 120 s, and a restart keeps the strikes */
    {
        mlk_t k;
        mlk_init(&k);
        mlk_set(&k, "1234", NULL, salt);
        uint32_t t0 = 1000;
        for (int i = 0; i < LK_TOOL_MAX_FAILS; i++) mlk_tool_note(&k, t0, MLK_R_WRONG_CURRENT);
        CHECK(mlk_tool_open(&k, t0 + 59000u) == MLK_R_TOO_MANY && mlk_tool_open(&k, t0 + 61000u) == MLK_R_OK);
        t0 += 61000u;
        for (int i = 0; i < LK_TOOL_MAX_FAILS; i++) mlk_tool_note(&k, t0, MLK_R_WRONG_CURRENT);
        CHECK(mlk_tool_open(&k, t0 + 119000u) == MLK_R_TOO_MANY && mlk_tool_open(&k, t0 + 121000u) == MLK_R_OK);
        CHECK(k.tool_strikes == 2);
        mlk_t r;
        mlk_init(&r);
        mlk_set(&r, "1234", NULL, salt);
        const mlk_tool_saved_t two = {2, 0};
        mlk_tool_restore(&r, &two, 100); /* after a restart */
        mlk_tool_note(&r, 500, MLK_R_WRONG_CURRENT);
        CHECK(mlk_tool_open(&r, 600) == MLK_R_TOO_MANY); /* one wrong code is enough */
        mlk_tool_note(&r, 9000000u, MLK_R_OK);
        CHECK(r.tool_strikes == 0);
    }
    /* turning the auto lock off needs the code; a longer or shorter time does not. */
    mlk_t v;
    mlk_init(&v);
    mlk_set(&v, "1234", NULL, salt);
    CHECK(mlk_set_auto_checked(&v, 5, NULL) == MLK_R_OK);
    CHECK(mlk_set_auto_checked(&v, 0, NULL) == MLK_R_CURRENT_NEEDED);
    CHECK(mlk_set_auto_checked(&v, 0, "9999") == MLK_R_WRONG_CURRENT);
    CHECK(v.auto_min == 5);
    CHECK(mlk_set_auto_checked(&v, 0, "1234") == MLK_R_OK && v.auto_min == 0);
    mlk_t w;
    mlk_init(&w); /* no code set: nothing to protect */
    CHECK(mlk_set_auto_checked(&w, 0, NULL) == MLK_R_OK);
}

/* a sensor sample at tilt theta (degrees) with the unit still: (0, sin, cos) in m/s^2 */
static mp_event_t still(mp_t* d, float theta, uint32_t now)
{
    const float r = theta * 3.14159265f / 180.0f;
    return mp_update(d, 0.0f, 9.80665f * sinf(r), 9.80665f * cosf(r), now);
}

static void test_pickup(void)
{
    /* an own-move hold, set while the unit has run past 24.9 days, ends. */
    mp_t d;
    mp_init(&d);
    uint32_t now = LATE;
    for (int i = 0; i < 60; i++, now += 20) still(&d, 0.0f, now);
    mp_note_own(&d, now, MP_OWN_HOLD_MS, 0);
    CHECK(d.own_until != 0);
    for (int i = 0; i < 100; i++, now += 20) still(&d, 0.0f, now); /* 2 s, hold is 1.5 s */
    CHECK(mt_pending(now, d.own_until) == 0);

    /* lifted and tilted far while the unit moves its own head. */
    mp_init(&d);
    now = 5000;
    for (int i = 0; i < 400; i++, now += 20) still(&d, 0.0f, now); /* resting pose learned */
    CHECK(d.ref_ok);
    int lifted = 0;
    for (int i = 0; i < 200; i++, now += 20) { /* 4 s tilted 80 degrees, own motion renewed every step */
        mp_note_own(&d, now, MP_OWN_HOLD_MS, 0);
        if (still(&d, 80.0f, now) == MP_LIFTED) lifted = 1;
    }
    CHECK(lifted);
    CHECK(mp_is_held(&d));

    /* the head alone tilts the unit by up to 45 degrees: no lift while it moves */
    mp_init(&d);
    now = 5000;
    for (int i = 0; i < 400; i++, now += 20) still(&d, 0.0f, now);
    lifted = 0;
    for (int i = 0; i < 300; i++, now += 20) {
        mp_note_own(&d, now, MP_OWN_HOLD_MS, 0);
        if (still(&d, 45.0f, now) == MP_LIFTED) lifted = 1;
    }
    CHECK(!lifted);
}

static void test_stamps_late(void)
{
    /* games input: a fresh tilt tracker settles and arms past 24.9 days */
    mgi_t t;
    mgi_init(&t);
    uint32_t now = LATE;
    int armed_seen = 0;
    for (int i = 0; i < 200; i++, now += 20) {
        mgi_update(&t, 0.0f, 0.0f, 1.0f, now);
        if (t.armed) armed_seen = 1;
    }
    CHECK(armed_seen);
    /* status: the mic hold ends */
    CHECK(mst_mic_shown(0, 0, LATE, 0) == 0);
    CHECK(mst_mic_shown(0, mst_mic_hold_until(LATE), LATE + 100, 0) == 1);
    CHECK(mst_mic_shown(0, mst_mic_hold_until(LATE), LATE + 100000, 0) == 0);
    /* fx: a unit that never started an overlay is not "in grace" */
    mg_t g;
    mg_init(&g);
    CHECK(mg_in_grace(&g, LATE) == 0);
    mg_note_start(&g, LATE);
    CHECK(mg_in_grace(&g, LATE + 10) == 1);
    CHECK(mg_in_grace(&g, LATE + MG_GRACE_MS + 10) == 0);
}

static void test_remote(void)
{
    /* a second heartbeat cannot swap the host id of a running session */
    mr_t r;
    mr_init(&r);
    mr_session(&r, 1, "remote", 1000);
    mr_set_host(&r, 111);
    CHECK(r.host_id == 111);
    mr_session(&r, 1, "remote", 2000);
    mr_set_host(&r, 222);
    CHECK(r.host_id == 111);
    mr_session(&r, 0, "remote", 3000); /* the session ends: the next one may bring its own id */
    mr_session(&r, 1, "remote", 4000);
    mr_set_host(&r, 222);
    CHECK(r.host_id == 222);
    /* the host process restarts with a new random id: its heartbeats are ignored for the id until the dead-man time has run, then taken */
    mr_t h;
    mr_init(&h);
    mr_session(&h, 1, "remote", 1000);
    mr_set_host(&h, 111);
    mr_session(&h, 1, "remote", 4000); /* the new host process, 3 s later */
    mr_set_host(&h, 222);
    CHECK(h.host_id == 111); /* a call stamped with 222 is refused for now: fail safe, at most MR_DEAD_MAN_MS */
    CHECK(mr_session_on(&h, 4000 + MR_DEAD_MAN_MS - 1) == 1);
    CHECK(mr_session_on(&h, 4000 + MR_DEAD_MAN_MS + 1) == 0); /* no heartbeat ... */
    mr_session(&h, 1, "remote", 4000 + MR_DEAD_MAN_MS + 2000); /* ... and the host that is still there starts a new session */
    mr_set_host(&h, 222);
    CHECK(h.host_id == 222);
    /* the dead-man timeout also clears it */
    CHECK(mr_session_on(&r, 4000 + MR_DEAD_MAN_MS + 1) == 0 && r.host_id == 0);
}

/* A fake flash: the two integers the unit keeps (tstrikes and tblock), written when a wrong code is sent and read at boot. */
static void test_lockout_survives_a_restart(void)
{
    uint8_t salt[LK_SALT_LEN] = {9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 1, 2, 3, 4, 5, 6};
    int nvs_strikes = 0;
    int nvs_block = 0;
    mlk_t a;
    mlk_init(&a);
    CHECK(mlk_set(&a, "4321", NULL, salt) == MLK_R_OK);
    uint32_t now = 500000;
    for (int i = 0; i < LK_TOOL_MAX_FAILS; i++) {
        CHECK(mlk_tool_open(&a, now) == MLK_R_OK);
        const int r = mlk_clear(&a, "0000");
        mlk_tool_note(&a, now, r);
        mlk_tool_saved_t sv; /* persist() after each wrong code */
        mlk_tool_save(&a, now, &sv);
        nvs_strikes = sv.strikes;
        nvs_block = (int)sv.block_ms;
        now += 200;
    }
    CHECK(mlk_tool_open(&a, now) == MLK_R_TOO_MANY);
    CHECK(nvs_strikes == 1 && nvs_block > 0);
    /* the unit restarts: a new state, the clock starts again near 0, the flash is read back */
    mlk_t b;
    mlk_init(&b);
    CHECK(mlk_set(&b, "4321", NULL, salt) == MLK_R_OK);
    const mlk_tool_saved_t saved = {nvs_strikes, (uint32_t)nvs_block};
    mlk_tool_restore(&b, &saved, 3000);
    CHECK(mlk_tool_open(&b, 3500) == MLK_R_TOO_MANY); /* the correct code is still refused by the tools */
    CHECK(mlk_tool_open(&b, 3000 + (uint32_t)nvs_block - 100) == MLK_R_TOO_MANY);
    CHECK(mlk_tool_open(&b, 3000 + (uint32_t)nvs_block + 100) == MLK_R_OK);
    /* and past 24.9 days of uptime after that restart */
    mlk_t c;
    mlk_init(&c);
    mlk_set(&c, "4321", NULL, salt);
    mlk_tool_restore(&c, &saved, LATE);
    CHECK(mlk_tool_open(&c, LATE + 10) == MLK_R_TOO_MANY && mlk_tool_open(&c, LATE + (uint32_t)nvs_block + 10) == MLK_R_OK);
}

static void test_privacy_tap_and_cues(void)
{
    /* a tap turns a switch on, a hold turns it off; the other way round does nothing */
    CHECK(mtc_toggle_ok(MTC_KIND_TAP, 0) == 1);
    CHECK(mtc_toggle_ok(MTC_KIND_TAP, 1) == 0);
    CHECK(mtc_toggle_ok(MTC_KIND_HOLD, 1) == 1);
    CHECK(mtc_toggle_ok(MTC_KIND_HOLD, 0) == 0);
    CHECK(mtc_toggle_ok(MTC_KIND_DRAG, 0) == 0 && mtc_toggle_ok(MTC_KIND_NONE, 1) == 0);
    /* at least one listening cue stays on */
    mp_prefs_t p;
    memset(&p, 0, sizeof p);
    CHECK(mp_all_cues_off(&p) == 1);
    p.v[MP_LISTEN_FACE] = 1;
    CHECK(mp_all_cues_off(&p) == 0);
    p.v[MP_LISTEN_FACE] = 0;
    p.v[MP_LISTEN_LIGHT] = 2;
    CHECK(mp_all_cues_off(&p) == 0);
}

int main(void)
{
    test_time();
    test_lock();
    test_pickup();
    test_stamps_late();
    test_remote();
    test_lockout_survives_a_restart();
    test_privacy_tap_and_cues();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("safety core ok\n");
    return 0;
}
