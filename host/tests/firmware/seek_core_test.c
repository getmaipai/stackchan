/* Host test for turning toward a person (patch S10): the frame difference, the seek state machine and the owner lease, against
 * synthetic frame sequences and a simulated head. cc -std=c99 -Wall -Wextra -Werror -I<dir with the header> seek_core_test.c -lm
 *
 * The world: people stand at angles (degrees, left negative); the head has a pan and a speed; a rendered frame is a gentle
 * gradient with a little noise plus, for each person in view, a bright block whose texture shifts every frame when the person
 * moves (a still person renders the same block every time, so the frame difference cannot see them: that is the honest limit of
 * a motion-first search, and the test says so). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maipai_seek_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

#define MAXP 4
typedef struct {
    int present;
    float angle;
    int moving;
    int width;      /* pixels */
    int bright;     /* contrast */
} person_t;

typedef struct {
    ms_t* s;
    uint32_t now;
    float pan, goal;
    float speed_dps;
    person_t p[MAXP];
    /* mode and gates */
    uint8_t mode, awake, muted, privacy, vision_off, full_quiet, quiet, denied, conversation;
    int drop_frames;     /* the camera delivers nothing */
    float flicker;       /* added to every pixel on odd frames */
    int detector_faces;  /* the detector build finds a face when a person is within 6 degrees of the optical axis */
    /* counters */
    int bursts, moves, cues_missing, camera_when_blocked, move_when_blocked, frame_no;
    uint32_t last_burst_at;
    uint32_t min_burst_gap;
    float last_goal;
    uint8_t last_speed;
    int pending[8];      /* frames due: time */
    uint32_t due_at[8];
    int due_n;
    float seen_goal[16];
    int goals_n;
} world_t;

static uint32_t rng = 7;
static int noise(void)
{
    rng = rng * 1664525u + 1013904223u;
    return (int)((rng >> 24) % 7) - 3;
}

static void render(world_t* w, uint8_t* f)
{
    for (int y = 0; y < MS_H; y++) {
        for (int x = 0; x < MS_W; x++) {
            int v = 80 + x + y * 2 + noise();
            if (w->flicker != 0.0f && (w->frame_no & 1)) {
                v += (int)w->flicker;
            }
            f[y * MS_W + x] = (uint8_t)(v < 0 ? 0 : (v > 255 ? 255 : v));
        }
    }
    for (int k = 0; k < MAXP; k++) {
        person_t* p = &w->p[k];
        if (!p->present) {
            continue;
        }
        float cx = 19.5f + (p->angle - w->pan) / (MS_FOV_DEG / MS_W) * MS_IMAGE_X_SIGN;
        for (int y = 6; y < 26; y++) {
            for (int x = 0; x < MS_W; x++) {
                if (fabsf((float)x - cx) <= (float)p->width * 0.5f) {
                    int v = f[y * MS_W + x] + p->bright;
                    if (p->moving) {
                        v += ((x + y + w->frame_no) & 1) ? 40 : -40;
                    }
                    f[y * MS_W + x] = (uint8_t)(v < 0 ? 0 : (v > 255 ? 255 : v));
                }
            }
        }
    }
    w->frame_no++;
}

static void world_init(world_t* w, ms_t* s, uint8_t mode)
{
    memset(w, 0, sizeof(*w));
    w->s = s;
    w->mode = mode;
    w->awake = 1;
    w->speed_dps = 150.0f;
    w->min_burst_gap = 0xFFFFFFFFu;
    w->now = 100000;
}

static int blocked(world_t* w) { return !w->awake || w->muted || w->privacy || w->vision_off || w->full_quiet || w->mode == MS_MODE_OFF; }

/* one 50 ms step; addressed is the wake word edge */
static void step(world_t* w, int addressed)
{
    ms_in_t in;
    memset(&in, 0, sizeof(in));
    uint8_t frame[MS_PIX];
    int deliver = 0;
    for (int i = 0; i < w->due_n; i++) {
        if (w->due_at[i] <= w->now) {
            deliver = 1;
            w->due_at[i] = w->due_at[--w->due_n];
            i--;
        }
    }
    /* the head moves toward its goal */
    float d = w->goal - w->pan, stepd = w->speed_dps * 0.05f;
    if (fabsf(d) <= stepd) {
        w->pan = w->goal;
    } else {
        w->pan += d > 0 ? stepd : -stepd;
    }
    in.now_ms = w->now;
    in.pan_deg = w->pan;
    in.head_settled = fabsf(w->goal - w->pan) < 0.5f;
    in.addressed = (uint8_t)addressed;
    in.conversation = w->conversation;
    in.awake = w->awake;
    in.muted = w->muted;
    in.privacy_sleep = w->privacy;
    in.vision_off = w->vision_off;
    in.full_quiet = w->full_quiet;
    in.quiet_or_night = w->quiet;
    in.camera_denied = w->denied;
    in.mode = w->mode;
    if (deliver && !w->drop_frames) {
        render(w, frame);
        in.frame = frame;
        if (w->detector_faces) {
            for (int k = 0; k < MAXP; k++) {
                if (w->p[k].present && fabsf(w->p[k].angle - w->pan) < 20.0f) {
                    in.face_valid = 1;
                    in.face_cx = 0.5f + (w->p[k].angle - w->pan) / MS_FOV_DEG;
                }
            }
        }
    }
    ms_out_t out;
    ms_tick(w->s, &in, &out);
    if (out.camera) {
        w->bursts++;
        if (blocked(w) || w->s->lease.held) {
            w->camera_when_blocked++;
        }
        if (out.cue_ms == 0) {
            w->cues_missing++;
        }
        if (w->bursts > 1 && w->now - w->last_burst_at < w->min_burst_gap) {
            w->min_burst_gap = w->now - w->last_burst_at;
        }
        w->last_burst_at = w->now;
        w->due_at[w->due_n++] = w->now + 50;
        if (out.frames > 1) {
            w->due_at[w->due_n++] = w->now + 50 + out.gap_ms;
        }
    }
    if (out.move) {
        w->moves++;
        if (blocked(w)) {
            w->move_when_blocked++;
        }
        w->goal = out.pan_deg;
        w->last_goal = out.pan_deg;
        w->last_speed = out.speed_pct;
        w->speed_dps = 150.0f * (float)out.speed_pct / 100.0f;
        if (w->goals_n < 16) {
            w->seen_goal[w->goals_n++] = out.pan_deg;
        }
    }
    w->now += 50;
}

static void run(world_t* w, int seconds, int addressed_first)
{
    int n = seconds * 20;
    for (int i = 0; i < n; i++) {
        step(w, addressed_first && i == 0);
    }
}

static void person(world_t* w, int k, float angle, int moving, int width, int bright)
{
    w->p[k].present = 1;
    w->p[k].angle = angle;
    w->p[k].moving = moving;
    w->p[k].width = width;
    w->p[k].bright = bright;
}

/* ---- the frame difference ---- */
static void test_blob(void)
{
    static ms_scratch_t sc;
    uint8_t a[MS_PIX], b[MS_PIX];
    ms_blob_t r;
    for (int i = 0; i < MS_PIX; i++) {
        a[i] = (uint8_t)(100 + (i % 5));
    }
    memcpy(b, a, sizeof(a));
    ms_blob(a, b, &sc, &r);
    CHECK(r.kind == MS_BLOB_NONE);                       /* a still scene */
    for (int y = 8; y < 20; y++) {
        for (int x = 28; x < 34; x++) {
            b[y * MS_W + x] = (uint8_t)(b[y * MS_W + x] + 70);
        }
    }
    ms_blob(a, b, &sc, &r);
    CHECK(r.kind == MS_BLOB_FOUND && r.area == 72 && fabsf(r.cx - 30.5f) < 0.1f);
    CHECK(fabsf(ms_offset_deg(30.5f) - 11.0f * MS_FOV_DEG / (float)MS_W) < 0.1f); /* 11 columns right of the middle; the field of view is the measured one */
    CHECK(fabsf(ms_offset_deg(19.5f)) < 0.01f);
    /* two blobs: the larger one wins */
    for (int y = 4; y < 8; y++) {
        for (int x = 2; x < 5; x++) {
            b[y * MS_W + x] = (uint8_t)(b[y * MS_W + x] + 70);
        }
    }
    ms_blob(a, b, &sc, &r);
    CHECK(r.kind == MS_BLOB_FOUND && r.cx > 28.0f);
    /* a light change of the whole picture: not a person */
    for (int i = 0; i < MS_PIX; i++) {
        b[i] = (uint8_t)(a[i] + 30);
    }
    ms_blob(a, b, &sc, &r);
    CHECK(r.kind == MS_BLOB_LIGHT);
    /* a small shift (auto exposure) with a person in it: the shift is removed, the person stays */
    for (int i = 0; i < MS_PIX; i++) {
        b[i] = (uint8_t)(a[i] + 12);
    }
    for (int y = 8; y < 20; y++) {
        for (int x = 10; x < 15; x++) {
            b[y * MS_W + x] = (uint8_t)(b[y * MS_W + x] + 70);
        }
    }
    ms_blob(a, b, &sc, &r);
    CHECK(r.kind == MS_BLOB_FOUND && fabsf(r.cx - 12.0f) < 0.6f);
    /* speckle: isolated noisy pixels are no blob */
    memcpy(b, a, sizeof(a));
    for (int i = 0; i < MS_PIX; i += 13) {
        b[i] = (uint8_t)(b[i] + 60);
    }
    ms_blob(a, b, &sc, &r);
    CHECK(r.kind == MS_BLOB_NONE);
    /* more than half the picture changed: the camera moved, not a person */
    for (int i = 0; i < MS_PIX; i++) {
        b[i] = (uint8_t)(a[i] + ((i & 1) ? 50 : -50));   /* the whole picture slid: half up, half down, no mean shift */
    }
    ms_blob(a, b, &sc, &r);
    CHECK(r.kind == MS_BLOB_BIG);
}

/* ---- the lease ---- */
static void test_lease(void)
{
    ms_lease_t l;
    memset(&l, 0, sizeof(l));
    CHECK(!ms_lease_active(&l, 1000));
    CHECK(ms_lease_claim(&l, "home-hub", 15, 1000) == MS_LEASE_OK);
    CHECK(ms_lease_active(&l, 1000) && ms_lease_active(&l, 15999));
    CHECK(!ms_lease_active(&l, 16000));                       /* expiry is exact: ttl 15 s */
    CHECK(ms_lease_claim(&l, "home-hub", 15, 20000) == MS_LEASE_OK);
    CHECK(ms_lease_claim(&l, "home-hub", 15, 25000) == MS_LEASE_RENEWED);   /* the heartbeat, every 5 s */
    CHECK(ms_lease_claim(&l, "home-hub", 15, 30000) == MS_LEASE_RENEWED);
    CHECK(ms_lease_active(&l, 44999) && !ms_lease_active(&l, 45000));       /* renewed to 30 s + 15 s */
    CHECK(ms_lease_claim(&l, "home-hub", 15, 50000) == MS_LEASE_OK);
    CHECK(ms_lease_claim(&l, "other-host", 15, 51000) == MS_LEASE_BUSY);    /* two claimants: the first keeps it */
    CHECK(strcmp(l.owner, "home-hub") == 0);
    CHECK(ms_lease_release(&l, "other-host", 52000) == MS_LEASE_BUSY);      /* only the holder can release */
    CHECK(ms_lease_active(&l, 52000));
    CHECK(ms_lease_release(&l, "home-hub", 52000) == MS_LEASE_OK);
    CHECK(!ms_lease_active(&l, 52000));
    CHECK(ms_lease_release(&l, "home-hub", 53000) == MS_LEASE_OK);          /* nothing held: still fine */
    CHECK(ms_lease_claim(&l, "other-host", 15, 53000) == MS_LEASE_OK);   /* the second takes it after release */
    CHECK(ms_lease_claim(&l, "home-hub", 15, 60000) == MS_LEASE_BUSY);
    CHECK(ms_lease_claim(&l, "home-hub", 15, 70000) == MS_LEASE_OK);        /* ... and the first after the second expired (its 15 s are over) */
    CHECK(ms_lease_claim(&l, "", 15, 1) == MS_LEASE_BAD);
    CHECK(ms_lease_claim(&l, "Has Space", 15, 1) == MS_LEASE_BAD);
    CHECK(ms_lease_claim(&l, "ok", -1, 1) == MS_LEASE_BAD);
    CHECK(ms_lease_claim(&l, "this-owner-name-is-way-too-long-for-it", 15, 1) == MS_LEASE_BAD);
    /* ttl bounds: 1 s becomes 5 s, 1000 s becomes 60 s, 0 is the default 15 s */
    memset(&l, 0, sizeof(l));
    ms_lease_claim(&l, "a", 1, 0);
    CHECK(ms_lease_active(&l, 4999) && !ms_lease_active(&l, 5000));
    memset(&l, 0, sizeof(l));
    ms_lease_claim(&l, "a", 1000, 0);
    CHECK(ms_lease_active(&l, 59999) && !ms_lease_active(&l, 60000));
    memset(&l, 0, sizeof(l));
    ms_lease_claim(&l, "a", 0, 0);
    CHECK(ms_lease_active(&l, 14999) && !ms_lease_active(&l, 15000));
    /* the clock wraps: a lease claimed near the end of the 32 bit range still expires */
    memset(&l, 0, sizeof(l));
    ms_lease_claim(&l, "a", 15, 0xFFFFFFFFu - 5000u);
    CHECK(ms_lease_active(&l, 0xFFFFFFFFu) && ms_lease_active(&l, 5000));
    CHECK(!ms_lease_active(&l, 10001));
    /* a reboot: the lease is not kept */
    ms_t s;
    ms_init(&s, 0);
    ms_lease_claim(&s.lease, "home-hub", 60, 0);
    ms_init(&s, 0);
    CHECK(!ms_lease_active(&s.lease, 1));
    CHECK(ms_owner(&s, MS_MODE_TALK, 1) == 1 && ms_owner(&s, MS_MODE_OFF, 1) == 0);
    ms_lease_claim(&s.lease, "home-hub", 15, 1);
    CHECK(ms_owner(&s, MS_MODE_TALK, 2) == 2 && ms_owner(&s, MS_MODE_OFF, 2) == 2);
    char buf[300];
    ms_status_json(&s, MS_MODE_TALK, 2, buf, sizeof(buf));
    CHECK(strstr(buf, "\"owner\":\"host\"") && strstr(buf, "\"lease_owner\":\"home-hub\"") && strstr(buf, "\"setting\":\"talk\""));
    ms_status_json(&s, MS_MODE_TALK, 20000, buf, sizeof(buf));
    CHECK(strstr(buf, "\"owner\":\"unit\"") && strstr(buf, "\"last_face_ago_ms\":-1"));
}

static ms_t S;

/* ---- address ---- */
static void test_address_finds_a_mover_in_view(void)
{
    world_t w;
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    person(&w, 0, 20.0f, 1, 6, 50);
    w.conversation = 1;
    run(&w, 6, 1);
    CHECK(S.state == MS_HOLD);
    CHECK(fabsf(w.pan - 20.0f) < 4.0f);                       /* turned to the middle of the person */
    CHECK(S.turns_total == 1 && S.searches_total == 1);
    CHECK(w.moves == 1);                                      /* no sweep: one move */
    CHECK(w.bursts >= 1 && w.bursts <= 8);
    CHECK(w.cues_missing == 0);
}

static void test_address_sweeps_to_a_person_out_of_view(void)
{
    world_t w;
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    person(&w, 0, -55.0f, 1, 6, 50);                          /* visible from the -60 stop only */
    w.conversation = 1;
    run(&w, 12, 1);
    CHECK(S.state == MS_HOLD);
    CHECK(fabsf(w.pan - -55.0f) < 4.0f);
    CHECK(w.goals_n >= 2 && fabsf(w.seen_goal[0] - -60.0f) < 0.1f);   /* from center it starts at the left end */
    CHECK(S.turns_total == 1);
    /* a person on the right: the sweep starts at the right end when the head already looks right */
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    w.pan = w.goal = 30.0f;
    person(&w, 0, 75.0f, 1, 6, 50);
    w.conversation = 1;
    run(&w, 12, 1);
    CHECK(fabsf(w.seen_goal[0] - 60.0f) < 0.1f);
    CHECK(fabsf(w.pan - 75.0f) < 4.0f);
}

static void test_nobody_search_gives_up_and_returns(void)
{
    world_t w;
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    run(&w, 30, 1);                                           /* nobody; no talk keeps it wanted */
    CHECK(S.state == MS_IDLE);
    CHECK(fabsf(w.pan) < 1.0f);                               /* back at center */
    CHECK(S.turns_total == 0 && S.searches_total == 1);
    CHECK(w.bursts == 5);                                     /* the first look plus the four stops that were not at the first look's pose */
    CHECK(w.goals_n == 5 && fabsf(w.seen_goal[0] + 60.0f) < 0.1f && fabsf(w.seen_goal[1] + 30.0f) < 0.1f
          && fabsf(w.seen_goal[2] - 30.0f) < 0.1f && fabsf(w.seen_goal[3] - 60.0f) < 0.1f && fabsf(w.seen_goal[4]) < 0.1f);
    CHECK(w.min_burst_gap >= MS_BURST_SPACING_MS);
    /* quiet: slower */
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    w.quiet = 1;
    run(&w, 40, 1);
    CHECK(w.last_speed > 0 && w.last_speed < 40);             /* the return is 60 percent of the quiet speed */
    CHECK(w.goals_n >= 1);
}

static void test_a_still_person_is_not_seen_by_motion(void)
{
    world_t w;
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    person(&w, 0, 20.0f, 0, 6, 50);                           /* sits perfectly still */
    run(&w, 30, 1);
    CHECK(S.turns_total == 0);                                /* limit of the motion-first search; the face detector build closes it */
}

static void test_light_flicker_makes_no_turn(void)
{
    world_t w;
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_ALWAYS);
    w.flicker = 40.0f;
    run(&w, 40, 0);
    CHECK(S.turns_total == 0 && w.moves == 0);
    w.flicker = 14.0f;                                        /* a mild flicker: the shift is removed */
    run(&w, 40, 0);
    CHECK(S.turns_total == 0 && w.moves == 0);
    w.flicker = 40.0f;
    run(&w, 20, 1);                                           /* ... and an address in a flickering room finds nobody and goes home */
    CHECK(S.turns_total == 0);
    CHECK(fabsf(w.pan) < 1.0f);
}

static void test_two_people_the_bigger_mover_wins(void)
{
    world_t w;
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    person(&w, 0, -12.0f, 1, 3, 50);
    person(&w, 1, 22.0f, 1, 8, 50);
    w.conversation = 1;
    run(&w, 6, 1);
    CHECK(fabsf(w.pan - 22.0f) < 4.0f);
}

/* ---- the notice (always) ---- */
static void test_notice_turns_once_and_goes_home_after_twenty_seconds(void)
{
    world_t w;
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_ALWAYS);
    run(&w, 10, 0);
    CHECK(w.moves == 0 && S.turns_total == 0);                /* empty room: only the one frame a second */
    CHECK(w.bursts >= 9 && w.bursts <= 11 && w.cues_missing == 0);
    person(&w, 0, 25.0f, 1, 6, 50);
    run(&w, 6, 0);
    CHECK(S.state == MS_HOLD && fabsf(w.pan - 25.0f) < 4.0f);
    CHECK(S.turns_total == 1 && S.searches_total == 0);       /* no sweep */
    w.p[0].present = 0;                                       /* leaves */
    run(&w, 18, 0);
    CHECK(S.state == MS_HOLD);                                /* still holding: less than twenty seconds */
    run(&w, 6, 0);
    CHECK(S.state != MS_HOLD && fabsf(w.pan) < 1.0f);
    run(&w, 5, 0);
    CHECK(S.state == MS_IDLE && fabsf(w.pan) < 1.0f);
    /* the setting "talk": an idle room and a walk-in cost no camera and no move */
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    person(&w, 0, 25.0f, 1, 6, 50);
    run(&w, 60, 0);
    CHECK(w.bursts == 0 && w.moves == 0);
    /* quiet and night: one frame every two seconds */
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_ALWAYS);
    w.quiet = 1;
    run(&w, 20, 0);
    CHECK(w.bursts >= 9 && w.bursts <= 11);
}

static void test_follow_is_gentle_and_capped(void)
{
    world_t w;
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    person(&w, 0, 15.0f, 1, 6, 50);
    w.conversation = 1;
    run(&w, 6, 1);
    CHECK(fabsf(w.pan - 15.0f) < 4.0f);
    int before = w.moves;
    w.p[0].angle = 30.0f;                                     /* she moves 15 degrees */
    run(&w, 6, 0);
    CHECK(w.moves > before && fabsf(w.pan - 30.0f) < 5.0f);
    CHECK(w.last_speed < 100);                                /* a gentle follow */
    /* a person pacing back and forth: turns stay at or under 4 a minute */
    for (int i = 0; i < 40; i++) {
        w.p[0].angle = (i & 1) ? -30.0f : 30.0f;
        run(&w, 3, 0);
    }
    CHECK(S.turns_total <= 4 + 2);                            /* 2 minutes: two windows of four, with the first already spent */
}

/* ---- the limits ---- */
static void test_four_turns_a_minute_and_stale_targets(void)
{
    world_t w;
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    for (int k = 0; k < 6; k++) {                             /* six wake words ten seconds apart, nobody in the room */
        run(&w, 1, 1);
        run(&w, 9, 0);
    }
    CHECK(S.searches_total == 4);                             /* the fifth and sixth did nothing: four a minute */
    CHECK(w.bursts <= 4 * 5);
    run(&w, 1, 1);                                            /* the first one is a minute old now: a slot is free again */
    run(&w, 9, 0);
    CHECK(S.searches_total == 5);
    /* never a turn for something seen more than 3 s ago */
    ms_t t;
    ms_init(&t, 0);
    t.state = MS_TURN;
    t.reason = MS_REASON_NOTICE;
    t.have_target = 1;
    t.target_pan = 40.0f;
    t.target_at = 1000;
    t.turn_issued = 0;
    ms_in_t in;
    ms_out_t out;
    memset(&in, 0, sizeof(in));
    in.mode = MS_MODE_ALWAYS;
    in.awake = 1;
    in.head_settled = 0;                                      /* the head is busy with the unit's own move */
    int moved = 0;
    for (uint32_t ms = 2000; ms <= 5500; ms += 50) {
        in.now_ms = ms;
        in.head_settled = ms >= 4500;                         /* free after 3.5 s: the target is stale by then */
        ms_tick(&t, &in, &out);
        moved += out.move && fabsf(out.pan_deg - 40.0f) < 0.1f;
    }
    CHECK(moved == 0);
    /* the same target, free after 1 s: fresh, the turn happens */
    ms_init(&t, 0);
    t.state = MS_TURN;
    t.reason = MS_REASON_NOTICE;
    t.have_target = 1;
    t.target_pan = 40.0f;
    t.target_at = 2000;
    moved = 0;
    for (uint32_t ms = 2000; ms <= 3500; ms += 50) {
        in.now_ms = ms;
        in.head_settled = ms >= 3000;
        ms_tick(&t, &in, &out);
        moved += out.move && fabsf(out.pan_deg - 40.0f) < 0.1f;
    }
    CHECK(moved == 1);
}

static void test_gates_keep_the_camera_and_the_head_still(void)
{
    for (int g = 0; g < 7; g++) {
        world_t w;
        ms_init(&S, 0);
        world_init(&w, &S, MS_MODE_ALWAYS);
        person(&w, 0, 20.0f, 1, 6, 50);
        switch (g) {
        case 0: w.mode = MS_MODE_OFF; break;
        case 1: w.muted = 1; break;
        case 2: w.privacy = 1; break;
        case 3: w.vision_off = 1; break;
        case 4: w.full_quiet = 1; break;
        case 5: w.awake = 0; break;
        default: w.denied = 1; break;
        }
        run(&w, 60, 1);
        run(&w, 1, 1);
        CHECK(w.bursts == 0 && w.moves == 0);
        CHECK(w.camera_when_blocked == 0 && w.move_when_blocked == 0);
    }
    /* a mute pressed in the middle of a search stops it at once */
    world_t w;
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    run(&w, 2, 1);
    CHECK(S.state != MS_IDLE);
    w.muted = 1;
    int b = w.bursts, m = w.moves;
    run(&w, 20, 0);
    CHECK(w.bursts == b && w.moves == m && S.state == MS_IDLE);
}

static void test_camera_refused_stays_away(void)
{
    world_t w;
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    run(&w, 2, 1);
    w.denied = 1;
    run(&w, 1, 0);
    w.denied = 0;
    int b = w.bursts;
    run(&w, 8, 0);
    CHECK(w.bursts == b);                                     /* ten seconds of peace after a refusal */
    run(&w, 5, 1);
    CHECK(w.bursts > b);
}

static void test_a_camera_that_delivers_nothing_does_not_hang_the_search(void)
{
    world_t w;
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    w.drop_frames = 1;
    person(&w, 0, 20.0f, 1, 6, 50);
    run(&w, 30, 1);
    CHECK(S.state == MS_IDLE && fabsf(w.pan) < 1.0f);
}

/* ---- the lease against the seeker ---- */
static void test_a_lease_stops_the_head_and_the_camera(void)
{
    world_t w;
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_ALWAYS);
    person(&w, 0, 20.0f, 1, 6, 50);
    CHECK(ms_lease_claim(&S.lease, "home-hub", 15, w.now) == MS_LEASE_OK);
    for (int i = 0; i < 12; i++) {                            /* the host renews every 5 s for a minute */
        run(&w, 5, i % 3 == 0);
        CHECK(ms_lease_claim(&S.lease, "home-hub", 15, w.now) == MS_LEASE_RENEWED);
    }
    CHECK(w.bursts == 0 && w.moves == 0 && S.turns_total == 0);
    CHECK(ms_owner(&S, w.mode, w.now) == 2);
    /* the host dies: after the ttl the unit seeks again */
    run(&w, 14, 0);
    CHECK(w.moves == 0);
    run(&w, 10, 0);
    CHECK(w.moves >= 1 && ms_owner(&S, w.mode, w.now) == 1 && S.turns_total >= 1);
    /* a claim in the middle of a sweep stops it */
    ms_init(&S, 0);
    world_init(&w, &S, MS_MODE_TALK);
    run(&w, 2, 1);
    CHECK(S.state != MS_IDLE);
    int b = w.bursts, m = w.moves;
    ms_lease_claim(&S.lease, "home-hub", 15, w.now);
    run(&w, 10, 0);
    CHECK(w.bursts == b && w.moves == m && S.state == MS_IDLE);
    /* a release gives it back */
    ms_lease_release(&S.lease, "home-hub", w.now);
    person(&w, 0, 20.0f, 1, 6, 50);
    run(&w, 8, 1);
    CHECK(w.bursts > b && S.turns_total == 1);
}

/* ---- the detector build ---- */
static void test_detector_build_blob_then_face(void)
{
    world_t w;
    ms_init(&S, 1);
    world_init(&w, &S, MS_MODE_TALK);
    w.detector_faces = 1;
    person(&w, 0, 28.0f, 1, 6, 50);
    w.conversation = 1;
    run(&w, 10, 1);
    CHECK(S.state == MS_HOLD && fabsf(w.pan - 28.0f) < 4.0f);
    CHECK(S.last_face_any == 1);
    CHECK(S.turns_total == 1);
    /* a still person: the detector sees the face with no motion, at the first look */
    ms_init(&S, 1);
    world_init(&w, &S, MS_MODE_TALK);
    w.detector_faces = 1;
    person(&w, 0, 12.0f, 0, 6, 50);
    w.conversation = 1;
    run(&w, 10, 1);
    CHECK(S.state == MS_HOLD && fabsf(w.pan - 12.0f) < 4.0f);
}

int main(void)
{
    test_blob();
    test_lease();
    test_address_finds_a_mover_in_view();
    test_address_sweeps_to_a_person_out_of_view();
    test_nobody_search_gives_up_and_returns();
    test_a_still_person_is_not_seen_by_motion();
    test_light_flicker_makes_no_turn();
    test_two_people_the_bigger_mover_wins();
    test_notice_turns_once_and_goes_home_after_twenty_seconds();
    test_follow_is_gentle_and_capped();
    test_four_turns_a_minute_and_stale_targets();
    test_gates_keep_the_camera_and_the_head_still();
    test_camera_refused_stays_away();
    test_a_camera_that_delivers_nothing_does_not_hang_the_search();
    test_a_lease_stops_the_head_and_the_camera();
    test_detector_build_blob_then_face();
    printf("sizeof(ms_t) = %u bytes\n", (unsigned)sizeof(ms_t));
    if (failures) {
        printf("seek_core_test: %d FAILED\n", failures);
        return 1;
    }
    printf("seek_core_test: all passed\n");
    return 0;
}
