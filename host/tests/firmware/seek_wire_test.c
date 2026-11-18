/* Host test for the wiring of the seek core (patch S12): the real mw_step, mw_downsample, the admission rule, the lateness hold, the
 * lease, the status text and the calibration, driven with a simulated camera (QVGA frames in several pixel formats, shrunk by the real
 * mw_downsample), a simulated head with a speed, and a fake clock that also pays for the time a grab takes.
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> seek_wire_test.c -lm */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maipai_seek_wire_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

#define QW 320
#define QH 240
#define MAXP 3

typedef struct {
    int present;
    float angle;
    int moving;
    float width_deg;
} person_t;

typedef struct {
    mw_t* w;
    uint32_t now;
    /* the head */
    float pan, goal, speed_dps;
    uint32_t pan_at;
    uint32_t settle_until;
    /* the optics (ground truth) */
    float fov_true, sign_true;
    int textured;           /* the background has texture (calibration needs it); 2: a repeating pattern (blinds, tiles) */
    float undershoot;       /* the servo stops this many degrees short of a move (a different amount each way in a real one) */
    int glitch_grab;        /* the grab with this number (1 is the first) sees something else entirely (a person walks through) */
    int fmt;
    person_t p[MAXP];
    /* the gates and the world */
    uint8_t mode, awake, muted, privacy, vision_off, full_quiet, quiet, conversation, late;
    size_t free_int, largest_int;
    int addressed;          /* consumed by env */
    int grab_cost_ms;
    int busy_until;         /* grab answers 1 (busy) while now < this */
    int dead_camera;        /* grab answers 2 */
    /* what the test watches */
    uint8_t qbuf[QW * QH * 2];
    int frame_no;
    int grabs, cues, moves, blocked_grabs, grabs_without_cue, grabs_while_leased;
    uint32_t cue_until;
    uint32_t last_grab_at;
    int grab_log[256];
    uint32_t grab_t[256];
    int ngrab;
    int logs, log_too_long, log_no_stamp;
    float last_goal;
    uint8_t last_speed;
    int lock_depth, lock_bad;
} world_t;

static uint32_t rng = 11;
static int noise(void)
{
    rng = rng * 1664525u + 1013904223u;
    return (int)((rng >> 24) % 5) - 2;
}

static void head_advance(world_t* k)
{
    float dt = (float)(k->now - k->pan_at) / 1000.0f;
    float d = k->goal - k->pan, st = k->speed_dps * dt;
    if (fabsf(d) <= st) {
        k->pan = k->goal;
    } else {
        k->pan += d > 0 ? st : -st;
    }
    k->pan_at = k->now;
}

static int world_blocked(const world_t* k)
{
    return !k->awake || k->muted || k->privacy || k->vision_off || k->full_quiet;
}

/* the clock and ops */
static uint32_t op_now(void* c) { return ((world_t*)c)->now; }

static void op_env(void* c, mw_env_t* e)
{
    world_t* k = (world_t*)c;
    head_advance(k);
    e->now_ms = k->now;
    e->pan_deg = k->pan;
    e->head_settled = fabsf(k->goal - k->pan) < 0.5f;
    e->addressed = (uint8_t)k->addressed;
    k->addressed = 0;
    e->conversation = k->conversation;
    e->awake = k->awake;
    e->muted = k->muted;
    e->privacy_sleep = k->privacy;
    e->vision_off = k->vision_off;
    e->full_quiet = k->full_quiet;
    e->quiet_or_night = k->quiet;
    e->mode = k->mode;
    e->late = k->late;
    e->free_internal = k->free_int;
    e->largest_internal = k->largest_int;
}

static int luma_scene(const world_t* k, float angle, int y)
{
    int v = 90;
    if (k->textured == 2) {
        v += (int)(60.0f * sinf(angle * 6.2832f / 40.0f)) + (int)(10.0f * sinf((float)y * 0.05f));
    } else if (k->textured) {
        v += (int)(45.0f * sinf(angle * 0.33f)) + (int)(28.0f * sinf(angle * 0.91f + 1.0f)) + (int)(18.0f * sinf((float)y * 0.05f));
        /* a few sharp edges so the match is crisp */
        float m = fmodf(angle + 1000.0f, 23.0f);
        if (m < 3.0f) {
            v += 40;
        }
    }
    return v + noise();
}

/* render a QVGA frame in the world's pixel format into qbuf */
static void render(world_t* k)
{
    int bpp = mw_bpp(k->fmt);
    int glitch = k->glitch_grab != 0 && k->grabs == k->glitch_grab;
    for (int y = 0; y < QH; y++) {
        for (int x = 0; x < QW; x++) {
            float off = ((float)x - 159.5f) / (float)QW * k->fov_true * k->sign_true;
            int v = luma_scene(k, glitch ? (float)(x * 7 % 97) : k->pan + off, y);
            for (int i = 0; i < MAXP; i++) {
                const person_t* p = &k->p[i];
                if (!p->present || y < 48 || y > 208) {
                    continue;
                }
                float ox = (p->angle - k->pan) * k->sign_true / k->fov_true * (float)QW + 159.5f;
                float half = p->width_deg / k->fov_true * (float)QW * 0.5f;
                if (fabsf((float)x - ox) <= half) {
                    v += 60;
                    if (p->moving) {
                        v += (((x / 8) + (y / 8) + k->frame_no) & 1) ? 50 : -50;
                    }
                }
            }
            v = v < 0 ? 0 : (v > 255 ? 255 : v);
            uint8_t* o = k->qbuf + ((size_t)y * QW + (size_t)x) * (size_t)bpp;
            switch (k->fmt) {
            case MW_FMT_YUYV:
                o[0] = (uint8_t)v;
                o[1] = 128;
                break;
            case MW_FMT_UYVY:
                o[0] = 128;
                o[1] = (uint8_t)v;
                break;
            case MW_FMT_GREY:
                o[0] = (uint8_t)v;
                break;
            default: {
                int r5 = v >> 3, g6 = v >> 2, b5 = v >> 3;
                int pix = (r5 << 11) | (g6 << 5) | b5;
                o[0] = (uint8_t)(pix & 255);
                o[1] = (uint8_t)(pix >> 8);
            }
            }
        }
    }
    k->frame_no++;
}

static int op_grab(void* c, uint8_t* gray)
{
    world_t* k = (world_t*)c;
    if (k->ngrab < 256) {
        k->grab_t[k->ngrab] = k->now;
    }
    if ((int)k->now < k->busy_until) {
        return 1;
    }
    if (k->dead_camera) {
        return 2;
    }
    k->grabs++;
    if (world_blocked(k) || k->mode == MS_MODE_OFF) {
        k->blocked_grabs++;
    }
    if (ms_dt(k->cue_until, k->now) <= 0) {
        k->grabs_without_cue++;
    }
    if (ms_lease_active(&k->w->seek.lease, k->now)) {
        k->grabs_while_leased++;
    }
    head_advance(k);
    k->now += (uint32_t)k->grab_cost_ms;
    render(k);
    k->last_grab_at = k->now;
    if (k->ngrab < 256) {
        k->ngrab++;
    }
    return mw_downsample(k->qbuf, sizeof(k->qbuf), QW, QH, k->fmt, gray) == 0 ? 0 : 2;
}

static void op_head(void* c, float pan, uint8_t pct, uint8_t reason)
{
    (void)reason;
    world_t* k = (world_t*)c;
    head_advance(k);
    k->goal = pan;
    if (k->undershoot > 0 && fabsf(pan - k->pan) > 2.0f * k->undershoot) {
        float u = pan > k->pan ? k->undershoot : k->undershoot * 0.4f; /* one way more than the other */
        k->goal = pan > k->pan ? pan - u : pan + u;
    }
    k->speed_dps = 150.0f * (float)pct / 100.0f;
    k->moves++;
    k->last_goal = pan;
    k->last_speed = pct;
}

static float op_pan(void* c)
{
    world_t* k = (world_t*)c;
    head_advance(k);
    return k->pan;
}

static void op_cue(void* c, uint32_t ms)
{
    world_t* k = (world_t*)c;
    k->cues++;
    uint32_t until = k->now + ms;
    if (ms_dt(until, k->cue_until) > 0 || ms_dt(k->cue_until, k->now) <= 0) {
        k->cue_until = until;
    }
}

static void op_lock(void* c) { ((world_t*)c)->lock_depth++; }
static void op_unlock(void* c)
{
    world_t* k = (world_t*)c;
    if (--k->lock_depth < 0) {
        k->lock_bad++;
    }
}

static void op_log(void* c, const char* line)
{
    world_t* k = (world_t*)c;
    if (getenv("SEEK_V") != NULL) {
        printf("  %s\n", line);
    }
    k->logs++;
    if (strlen(line) >= 255) {
        k->log_too_long++;
    }
    if (strncmp(line, "seek ", 5) != 0) {
        k->log_no_stamp++;
    }
}

static mw_ops_t ops_for(world_t* k)
{
    mw_ops_t o;
    memset(&o, 0, sizeof(o));
    o.ctx = k;
    o.now = op_now;
    o.env = op_env;
    o.grab = op_grab;
    o.head = op_head;
    o.cue = op_cue;
    o.pan = op_pan;
    o.lock = op_lock;
    o.unlock = op_unlock;
    o.log = op_log;
    return o;
}

static mw_t* mw_new(void)
{
    mw_t* w = (mw_t*)malloc(sizeof(mw_t));
    mw_init(w, 0);
    return w;
}

static void world_init(world_t* k, mw_t* w, uint8_t mode)
{
    memset(k, 0, sizeof(*k));
    k->w = w;
    k->mode = mode;
    k->awake = 1;
    k->now = 100000;
    k->pan_at = k->now;
    k->fov_true = MS_FOV_DEG;
    k->sign_true = 1.0f;
    k->textured = 1;
    k->fmt = MW_FMT_YUYV;
    k->grab_cost_ms = 110;
    k->free_int = 60000;
    k->largest_int = 30000;
    k->cue_until = 0;
}

static void run_ms(world_t* k, mw_t* w, uint32_t ms)
{
    mw_ops_t o = ops_for(k);
    uint32_t end = k->now + ms;
    while (ms_dt(end, k->now) > 0) {
        k->now += MW_TICK_MS;
        mw_step(w, &o);
    }
}

/* ---- tests ------------------------------------------------------------------------------------------------------------------- */

static void test_downsample(void)
{
    static uint8_t src[640 * 480 * 2];
    uint8_t out[MS_PIX];
    /* a horizontal ramp, 0..255 across the width, in each format and size */
    int sizes[3][2] = {{320, 240}, {160, 120}, {640, 480}};
    for (int f = MW_FMT_YUYV; f <= MW_FMT_GREY; f++) {
        for (int s = 0; s < 3; s++) {
            int w = sizes[s][0], h = sizes[s][1], bpp = mw_bpp(f);
            for (int y = 0; y < h; y++) {
                for (int x = 0; x < w; x++) {
                    int v = x * 255 / (w - 1);
                    uint8_t* o = src + ((size_t)y * (size_t)w + (size_t)x) * (size_t)bpp;
                    if (f == MW_FMT_YUYV) {
                        o[0] = (uint8_t)v;
                        o[1] = 7;
                    } else if (f == MW_FMT_UYVY) {
                        o[0] = 7;
                        o[1] = (uint8_t)v;
                    } else if (f == MW_FMT_GREY) {
                        o[0] = (uint8_t)v;
                    } else {
                        int pix = ((v >> 3) << 11) | ((v >> 2) << 5) | (v >> 3);
                        o[0] = (uint8_t)(pix & 255);
                        o[1] = (uint8_t)(pix >> 8);
                    }
                }
            }
            CHECK(mw_downsample(src, (size_t)w * (size_t)h * (size_t)bpp, w, h, f, out) == 0);
            /* monotone left to right, first near 0, last near 255, rows alike */
            int mono = 1;
            for (int x = 1; x < MS_W; x++) {
                mono &= out[x] >= out[x - 1];
            }
            CHECK(mono);
            CHECK(out[0] < 16 && out[MS_W - 1] > 238);
            CHECK(out[10 * MS_W + 20] == out[20 * MS_W + 20]);
        }
    }
    CHECK(mw_downsample(src, 100, 320, 240, MW_FMT_YUYV, out) == -1);       /* buffer too short */
    CHECK(mw_downsample(src, sizeof(src), 32, 24, MW_FMT_YUYV, out) == -1); /* picture too small */
    CHECK(mw_downsample(src, sizeof(src), 320, 240, MW_FMT_NONE, out) == -1);
    CHECK(mw_downsample(NULL, sizeof(src), 320, 240, MW_FMT_YUYV, out) == -1);
}

static void test_admission(void)
{
    CHECK(mw_admit(60000, 30000, 0));
    CHECK(mw_admit(28000, 16000, 0));
    CHECK(!mw_admit(27999, 30000, 0));
    CHECK(!mw_admit(60000, 15999, 0));
    CHECK(!mw_admit(39999, 30000, 1) && !mw_admit(60000, 23999, 1) && mw_admit(40000, 24000, 1));
}

/* a mover at +25 degrees, talk mode, the wake word: the head turns to it (within a few degrees) and the invariants hold */
static void test_turn_to_mover(float sign_true, float fov_true, int fmt, int expect_ok)
{
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_TALK);
    k.sign_true = sign_true;
    k.fov_true = fov_true;
    k.fmt = fmt;
    k.p[0] = (person_t){1, 18.0f, 1, 8.0f};
    run_ms(&k, w, 1000);
    CHECK(k.grabs == 0 && k.moves == 0); /* talk mode at rest: the camera is not used */
    k.addressed = 1;
    run_ms(&k, w, 4000);
    CHECK(k.grabs >= 2);
    CHECK(k.grabs_without_cue == 0);
    CHECK(k.blocked_grabs == 0);
    if (expect_ok) {
        CHECK(fabsf(k.pan - 18.0f) < 7.0f);
    } else {
        CHECK(fabsf(k.pan - 18.0f) > 12.0f); /* a picture axis the wrong way turns the wrong way (what calibration is for) */
    }
    CHECK(k.lock_bad == 0 && k.lock_depth == 0);
    CHECK(k.log_too_long == 0 && k.log_no_stamp == 0 && k.logs >= 3);
    CHECK(w->seek.turns_total == 1);
    free(w);
}

static void test_nobody_sweeps_and_returns(void)
{
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_TALK);
    k.addressed = 1;
    run_ms(&k, w, 14000);
    CHECK(w->seek.searches_total == 1);
    CHECK(k.grabs >= 8 && k.grabs <= 12); /* the first look (2 frames) plus up to five stops of 2 frames */
    CHECK(fabsf(k.pan) < 3.0f);           /* back at center */
    CHECK(k.grabs_without_cue == 0);
    CHECK(w->seek.turns_total == 0);
    /* camera-on cue was asked for every burst */
    CHECK(k.cues >= (int)w->bursts_run);
    free(w);
}

static void test_gates(void)
{
    const char* names[] = {"mute", "privacy sleep", "vision off", "full quiet", "asleep", "setting off"};
    for (int g = 0; g < 6; g++) {
        mw_t* w = mw_new();
        world_t k;
        world_init(&k, w, MS_MODE_ALWAYS);
        k.p[0] = (person_t){1, 18.0f, 1, 8.0f};
        if (g == 0) k.muted = 1;
        if (g == 1) k.privacy = 1;
        if (g == 2) k.vision_off = 1;
        if (g == 3) k.full_quiet = 1;
        if (g == 4) k.awake = 0;
        if (g == 5) k.mode = MS_MODE_OFF;
        for (int i = 0; i < 8; i++) {
            k.addressed = (i % 2);
            run_ms(&k, w, 1500);
        }
        if (k.grabs != 0 || k.moves != 0 || k.cues != 0) {
            printf("gate %s leaked: grabs=%d moves=%d cues=%d\n", names[g], k.grabs, k.moves, k.cues);
        }
        CHECK(k.grabs == 0 && k.moves == 0 && k.cues == 0);
        free(w);
    }
    /* a gate that closes in the middle of a burst stops the frames at once */
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_TALK);
    k.p[0] = (person_t){1, 18.0f, 1, 8.0f};
    k.addressed = 1;
    run_ms(&k, w, 150);
    k.muted = 1;
    int g0 = k.grabs;
    run_ms(&k, w, 5000);
    CHECK(k.grabs <= g0 + 0 && k.blocked_grabs == 0);
    CHECK(w->gate_drops >= 0);
    free(w);
}

/* the wake word arrives while the sleeping face still shows (the face wakes with the turn about half a second later): it is not lost */
static void test_wake_waits_for_the_face_to_wake(void)
{
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_TALK);
    k.p[0] = (person_t){1, 18.0f, 1, 8.0f};
    k.awake = 0;
    k.addressed = 1;
    run_ms(&k, w, 500);
    CHECK(k.grabs == 0);
    k.awake = 1;
    run_ms(&k, w, 4000);
    CHECK(k.grabs >= 2 && fabsf(k.pan - 18.0f) < 7.0f);
    /* a gate that stays closed past the latch forgets the wake word */
    mw_t* w2 = mw_new();
    world_t k2;
    world_init(&k2, w2, MS_MODE_TALK);
    k2.awake = 0;
    k2.addressed = 1;
    run_ms(&k2, w2, 3200);
    k2.awake = 1;
    run_ms(&k2, w2, 3000);
    CHECK(k2.grabs == 0);
    free(w);
    free(w2);
}

static void test_lease(void)
{
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_ALWAYS);
    k.p[0] = (person_t){1, 18.0f, 1, 8.0f};
    CHECK(ms_lease_claim(&w->seek.lease, "home-hub", 15, k.now) == MS_LEASE_OK);
    for (int i = 0; i < 6; i++) {
        k.addressed = 1;
        run_ms(&k, w, 2000);
    }
    CHECK(k.grabs == 0 && k.moves == 0 && k.grabs_while_leased == 0);
    char buf[600];
    mw_status_json(w, MS_MODE_ALWAYS, k.now, buf, sizeof(buf));
    CHECK(strstr(buf, "\"owner\":\"host\"") != NULL && strstr(buf, "\"lease_owner\":\"home-hub\"") != NULL);
    /* the lease expires after 15 s without a renewal: the unit seeks again */
    run_ms(&k, w, 12000);
    k.addressed = 1;
    run_ms(&k, w, 4000);
    mw_status_json(w, MS_MODE_ALWAYS, k.now, buf, sizeof(buf));
    CHECK(strstr(buf, "\"owner\":\"unit\"") != NULL && strstr(buf, "\"enabled\":true") != NULL);
    CHECK(k.grabs >= 2);
    free(w);
}

static void test_late_holds_bursts(void)
{
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_TALK);
    k.p[0] = (person_t){1, 18.0f, 1, 8.0f};
    k.late = 1;
    k.addressed = 1;
    run_ms(&k, w, 3000);
    CHECK(k.grabs == 0 && k.moves == 0); /* no burst starts while the unit runs late */
    CHECK(w->late_skips > 10);
    k.late = 0;
    run_ms(&k, w, 4000); /* the wake word stayed latched: the look happens now, inside the 30 s window */
    CHECK(k.grabs >= 2);
    CHECK(fabsf(k.pan - 18.0f) < 7.0f);
    /* lateness of the loop itself (a 400 ms gap between passes) is noticed */
    mw_t* w2 = mw_new();
    world_t k2;
    world_init(&k2, w2, MS_MODE_TALK);
    mw_ops_t o = ops_for(&k2);
    k2.now += 50;
    mw_step(w2, &o);
    k2.now += 400;
    k2.addressed = 1;
    mw_step(w2, &o);
    CHECK(w2->late_skips == 1 && k2.grabs == 0);
    free(w);
    free(w2);
}

static void test_late_for_too_long_acts_as_refused(void)
{
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_TALK);
    k.p[0] = (person_t){1, 18.0f, 1, 8.0f};
    k.late = 1;
    k.addressed = 1;
    run_ms(&k, w, 9000);
    CHECK(k.grabs == 0);
    CHECK(w->seek.state == 8 /* cool */ || w->seek.state == MS_IDLE);
    free(w);
}

static void test_memory_refusal(void)
{
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_TALK);
    k.p[0] = (person_t){1, 18.0f, 1, 8.0f};
    k.free_int = 20000;
    k.addressed = 1;
    run_ms(&k, w, 6000);
    CHECK(k.grabs == 0 && k.moves == 0 && w->denied >= 1);
    k.free_int = 20000;
    k.addressed = 1;
    run_ms(&k, w, 4000);
    CHECK(k.grabs == 0 && w->denied >= 2); /* every request asks the memory again */
    run_ms(&k, w, 10000);
    k.free_int = 60000;
    k.addressed = 1;
    run_ms(&k, w, 4000);
    CHECK(k.grabs >= 2 && fabsf(k.pan - 18.0f) < 7.0f);
    free(w);
}

static void test_busy_and_dead_camera(void)
{
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_TALK);
    k.p[0] = (person_t){1, 18.0f, 1, 8.0f};
    k.busy_until = (int)k.now + 500; /* the video stream holds the camera for half a second */
    k.addressed = 1;
    run_ms(&k, w, 5000);
    CHECK(w->grab_busy >= 1);
    CHECK(fabsf(k.pan - 18.0f) < 7.0f); /* still found the mover */
    /* a camera that delivers nothing: the search ends and the head goes home */
    mw_t* w2 = mw_new();
    world_t k2;
    world_init(&k2, w2, MS_MODE_TALK);
    k2.dead_camera = 1;
    k2.addressed = 1;
    run_ms(&k2, w2, 25000);
    CHECK(k2.grabs == 0 && w2->grab_fail >= 1);
    CHECK(fabsf(k2.pan) < 3.0f);
    CHECK(w2->seek.state == MS_IDLE || w2->seek.state == 8);
    free(w);
    free(w2);
}

static void test_always_notices_and_returns(void)
{
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_ALWAYS);
    run_ms(&k, w, 6000);
    int idle_grabs = k.grabs;
    CHECK(idle_grabs >= 1 && idle_grabs <= 3); /* patch SF55: the first look (two frames), then the 30 s net: no frame a second */
    CHECK(k.moves == 0);
    CHECK(k.logs <= 3); /* an idle watch that sees nothing is one line a minute, not one per frame */
    k.p[0] = (person_t){1, -20.0f, 1, 8.0f};
    run_ms(&k, w, 33000); /* the net looks within 30 s */
    CHECK(fabsf(k.pan + 20.0f) < 8.0f);
    k.p[0].present = 0;
    run_ms(&k, w, 30000);
    CHECK(fabsf(k.pan) < 3.0f); /* back to center after 20 s of nobody */
    CHECK(k.grabs_without_cue == 0);
    free(w);
}

static void test_quiet_is_slower(void)
{
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_TALK);
    k.quiet = 1;
    k.p[0] = (person_t){1, 18.0f, 1, 8.0f};
    k.addressed = 1;
    run_ms(&k, w, 4000);
    CHECK(k.last_speed <= MS_SPEED_QUIET || k.moves >= 1);
    CHECK(k.last_speed == 100 * MS_SPEED_QUIET / 100 * 6 / 10 || k.last_speed == MS_SPEED_QUIET || k.last_speed == (uint8_t)(MS_SPEED_QUIET * 7 / 10) || k.last_speed < 100);
    free(w);
}

/* calibration on a textured scene finds the sign and the field of view; flat and busy scenes are reported, not guessed */
static void cal_run(world_t* k, mw_t* w, uint32_t ms)
{
    run_ms(k, w, ms);
}

static void test_calibration(float sign_true, float fov_true, int fmt)
{
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_TALK);
    k.sign_true = sign_true;
    k.fov_true = fov_true;
    k.fmt = fmt;
    CHECK(mw_cal_start(w, 0.0f, 1, k.now) == 0);
    CHECK(mw_cal_start(w, 0.0f, 1, k.now) == 1);
    cal_run(&k, w, 40000);
    CHECK(w->cal.state == MW_CAL_DONE);
    CHECK(w->cal.result == MW_CR_OK);
    CHECK(w->cal.x_sign == sign_true);
    CHECK(fabsf(w->cal.fov_deg - fov_true) < fov_true * 0.06f);
    CHECK(w->cal.applied && w->seek.x_sign == sign_true && fabsf(w->seek.fov_deg - fov_true) < fov_true * 0.06f);
    CHECK(fabsf(k.pan) < 1.0f);       /* the head came back */
    CHECK(k.grabs == 5 && k.grabs_without_cue == 0);
    CHECK(k.lock_bad == 0 && k.lock_depth == 0);
    /* after calibrating, a mover is turned toward correctly even with this picture axis */
    k.p[0] = (person_t){1, 18.0f, 1, 8.0f};
    k.addressed = 1;
    run_ms(&k, w, 5000);
    CHECK(fabsf(k.pan - 18.0f) < 7.0f);
    free(w);
}

static void test_calibration_patterned_wall_and_a_bad_frame(void)
{
    /* a repeating pattern: the 22 degree step is more than half a repeat, so the large steps are searched near what the small ones say */
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_TALK);
    k.textured = 2;
    k.fov_true = 65.0f;
    mw_cal_start(w, 0.0f, 1, k.now);
    run_ms(&k, w, 40000);
    CHECK(w->cal.result == MW_CR_OK && w->cal.kept == 4);
    CHECK(w->cal.x_sign == 1.0f && fabsf(w->cal.fov_deg - 65.0f) < 4.0f);
    free(w);
    /* one frame of the five is garbage (somebody walked through): that step is dropped, the other three carry the fit */
    for (int bad = 2; bad <= 5; bad++) {
        mw_t* w2 = mw_new();
        world_t k2;
        world_init(&k2, w2, MS_MODE_TALK);
        k2.sign_true = -1.0f;
        k2.fov_true = 60.0f;
        k2.glitch_grab = bad;
        mw_cal_start(w2, 0.0f, 1, k2.now);
        run_ms(&k2, w2, 40000);
        CHECK(w2->cal.result == MW_CR_OK && w2->cal.kept >= 3);
        CHECK(w2->cal.x_sign == -1.0f && fabsf(w2->cal.fov_deg - 60.0f) < 5.0f);
        free(w2);
    }
    /* two garbage frames: not enough to say anything, and it says so */
    mw_t* w3 = mw_new();
    world_t k3;
    world_init(&k3, w3, MS_MODE_TALK);
    k3.glitch_grab = 2;
    mw_cal_start(w3, 0.0f, 1, k3.now);
    run_ms(&k3, w3, 15000);
    mw_t* w4 = mw_new();
    world_t k4;
    world_init(&k4, w4, MS_MODE_TALK);
    k4.glitch_grab = 3;
    mw_cal_start(w4, 0.0f, 1, k4.now);
    run_ms(&k4, w4, 15000);
    CHECK(w3->cal.result == MW_CR_OK || w3->cal.result == MW_CR_UNCLEAR);
    free(w3);
    free(w4);
}

static void test_calibration_with_a_servo_that_stops_short(void)
{
    for (int s = 0; s < 2; s++) {
        mw_t* w = mw_new();
        world_t k;
        world_init(&k, w, MS_MODE_TALK);
        k.sign_true = s ? -1.0f : 1.0f;
        k.fov_true = 62.0f;
        k.undershoot = 3.0f;
        mw_cal_start(w, 0.0f, 1, k.now);
        run_ms(&k, w, 40000);
        CHECK(w->cal.result == MW_CR_OK && w->cal.kept >= 3);
        CHECK(w->cal.x_sign == k.sign_true && fabsf(w->cal.fov_deg - 62.0f) < 4.0f);
        free(w);
    }
}

/* the four measurements taken on the first unit (bench window, 2026-11-17): the fit must give the sign and a field of view near 50 */
static void test_calibration_fit_on_numbers_measured_on_the_unit(void)
{
    static const float shifts[4][4] = {{-1.7f, 7.7f, -9.3f, 16.0f}, {-6.8f, 2.6f, -13.6f, 13.3f}, {-2.5f, 8.0f, -10.6f, 16.0f}, {-6.9f, 2.4f, -14.9f, 13.4f}};
    static const float dpans[4][4] = {{1.2f, -10.0f, 11.8f, -21.5f}, {6.7f, -4.5f, 16.1f, -15.4f}, {2.8f, -9.6f, 15.3f, -18.0f}, {9.0f, -2.2f, 20.3f, -14.0f}};
    static const float quals[4][4] = {{0.02f, 0.52f, 0.03f, 0.10f}, {0.23f, 0.13f, 0.36f, 0.03f}, {0.04f, 0.58f, 0.06f, 0.04f}, {0.27f, 0.14f, 0.40f, 0.02f}};
    for (int r = 0; r < 4; r++) {
        mw_cal_t c;
        memset(&c, 0, sizeof(c));
        for (int i = 1; i < MW_CAL_STEPS; i++) {
            c.shift[i] = shifts[r][i - 1];
            c.dpan[i] = dpans[r][i - 1];
            c.qual[i] = quals[r][i - 1];
        }
        int res = mw_cal_fit(&c);
        if (res != MW_CR_OK || c.x_sign != 1.0f || c.fov_deg < 40.0f || c.fov_deg > 60.0f) {
            printf("measured run %d: result %s sign %.0f fov %.1f kept %u\n", r, MW_CR_NAMES[res], (double)c.x_sign, (double)c.fov_deg, (unsigned)c.kept);
        }
        CHECK(res == MW_CR_OK && c.x_sign == 1.0f && c.fov_deg > 40.0f && c.fov_deg < 60.0f);
    }
}

static void test_calibration_failures(void)
{
    /* a blank wall */
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_TALK);
    k.textured = 0;
    mw_cal_start(w, 0.0f, 1, k.now);
    cal_run(&k, w, 30000);
    CHECK(w->cal.state == MW_CAL_DONE && w->cal.result == MW_CR_FLAT && !w->cal.applied);
    CHECK(w->seek.x_sign == MS_IMAGE_X_SIGN && w->seek.fov_deg == MS_FOV_DEG);
    CHECK(fabsf(k.pan) < 1.0f);
    free(w);
    /* muted in the middle */
    mw_t* w2 = mw_new();
    world_t k2;
    world_init(&k2, w2, MS_MODE_TALK);
    mw_cal_start(w2, 0.0f, 1, k2.now);
    run_ms(&k2, w2, 1500);
    k2.muted = 1;
    run_ms(&k2, w2, 500);
    CHECK(w2->cal.state == MW_CAL_DONE && w2->cal.result == MW_CR_GATE);
    free(w2);
    /* a dead camera */
    mw_t* w3 = mw_new();
    world_t k3;
    world_init(&k3, w3, MS_MODE_TALK);
    k3.dead_camera = 1;
    mw_cal_start(w3, 0.0f, 1, k3.now);
    run_ms(&k3, w3, 10000);
    CHECK(w3->cal.state == MW_CAL_DONE && w3->cal.result == MW_CR_CAMERA);
    free(w3);
    /* dry run: measured, not applied */
    mw_t* w4 = mw_new();
    world_t k4;
    world_init(&k4, w4, MS_MODE_TALK);
    k4.sign_true = -1.0f;
    k4.fov_true = 58.0f;
    mw_cal_start(w4, 0.0f, 0, k4.now);
    run_ms(&k4, w4, 40000);
    CHECK(w4->cal.result == MW_CR_OK && !w4->cal.applied && w4->seek.x_sign == MS_IMAGE_X_SIGN);
    CHECK(w4->cal.x_sign == -1.0f);
    free(w4);
}

static void test_shift_math(void)
{
    uint8_t a[MS_PIX], b[MS_PIX];
    for (int s = -10; s <= 10; s += 5) {
        for (int y = 0; y < MS_H; y++) {
            for (int x = 0; x < MS_W; x++) {
                a[y * MS_W + x] = (uint8_t)(120 + 60.0f * sinf((float)x * 0.4f) + 30.0f * sinf((float)x * 1.1f + (float)y * 0.2f));
                b[y * MS_W + x] = (uint8_t)(120 + 60.0f * sinf((float)(x - s) * 0.4f) + 30.0f * sinf((float)(x - s) * 1.1f + (float)y * 0.2f));
            }
        }
        float sh = 0, q = 1;
        CHECK(mw_shift_px(a, b, &sh, &q) == 0);
        CHECK(fabsf(sh - (float)s) < 0.6f);
        CHECK(q < 0.3f);
    }
    memset(a, 100, sizeof(a));
    float sh, q;
    CHECK(mw_shift_px(a, a, &sh, &q) == -1);
}

static void test_status_and_log(void)
{
    mw_t* w = mw_new();
    world_t k;
    world_init(&k, w, MS_MODE_TALK);
    char buf[700];
    int n = mw_status_json(w, MS_MODE_TALK, k.now, buf, sizeof(buf));
    CHECK(n > 0 && n < (int)sizeof(buf));
    const char* keys[] = {"\"owner\":\"unit\"", "\"enabled\":true", "\"setting\":\"talk\"", "\"last_face_ago_ms\":-1", "\"detector\":false", "\"fov_deg\":52.0",
                          "\"x_sign\":1", "\"calibration\":{\"state\":\"idle\""};
    for (unsigned i = 0; i < sizeof(keys) / sizeof(keys[0]); i++) {
        if (strstr(buf, keys[i]) == NULL) {
            printf("status lacks %s: %s\n", keys[i], buf);
            failures++;
        }
    }
    mw_status_json(w, MS_MODE_OFF, k.now, buf, sizeof(buf));
    CHECK(strstr(buf, "\"owner\":\"none\"") != NULL && strstr(buf, "\"enabled\":false") != NULL);
    printf("sizeof(mw_t) = %u bytes, status = %d chars\n", (unsigned)sizeof(mw_t), n);
    CHECK(sizeof(mw_t) < 9000);
    free(w);
}

static void test_internal_ram_is_nothing(void)
{
    /* the step keeps its state in mw_t (PSRAM); the stack use of one pass is the locals of mw_step: a handful of structs */
    CHECK(sizeof(mw_env_t) + sizeof(ms_in_t) + sizeof(ms_out_t) < 256);
}

int main(void)
{
    test_downsample();
    test_admission();
    test_shift_math();
    test_turn_to_mover(1.0f, MS_FOV_DEG, MW_FMT_YUYV, 1);
    test_turn_to_mover(1.0f, MS_FOV_DEG, MW_FMT_UYVY, 1);
    test_turn_to_mover(1.0f, MS_FOV_DEG, MW_FMT_RGB565, 1);
    test_turn_to_mover(1.0f, MS_FOV_DEG, MW_FMT_GREY, 1);
    test_turn_to_mover(-1.0f, MS_FOV_DEG, MW_FMT_YUYV, 0);
    test_nobody_sweeps_and_returns();
    test_gates();
    test_wake_waits_for_the_face_to_wake();
    test_lease();
    test_late_holds_bursts();
    test_late_for_too_long_acts_as_refused();
    test_memory_refusal();
    test_busy_and_dead_camera();
    test_always_notices_and_returns();
    test_quiet_is_slower();
    test_calibration(1.0f, 65.0f, MW_FMT_YUYV);
    test_calibration(-1.0f, 58.0f, MW_FMT_RGB565);
    test_calibration(1.0f, 72.0f, MW_FMT_UYVY);
    test_calibration_patterned_wall_and_a_bad_frame();
    test_calibration_with_a_servo_that_stops_short();
    test_calibration_fit_on_numbers_measured_on_the_unit();
    test_calibration_failures();
    test_status_and_log();
    test_internal_ram_is_nothing();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
