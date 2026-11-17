/* Host test for the face tracker's control loop (patch FD04): the real ft_tick, driven with scripted detections and a simulated head.
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> face_track_core_test.c -lm */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maipai_face_track_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static ft_cfg_t cfg(void)
{
    ft_cfg_t c;
    memset(&c, 0, sizeof(c));
    c.x_sign = 1.0f;
    c.fov_h_deg = 52.0f;
    c.y_sign = -1.0f;
    c.hour_ms = 600000u;
    c.tilt = 0;
    return c;
}

static ft_in_t base_in(uint32_t now)
{
    ft_in_t i;
    memset(&i, 0, sizeof(i));
    i.now_ms = now;
    i.armed = 1;
    i.gates_ok = 1;
    i.mode = FT_MODE_TALK;
    i.conversation = 1;
    i.head_settled = 1;
    return i;
}

/* feed one detection: a face at (cx, cy) with a score, or a miss; the picture was taken at `at` */
static void detect(ft_in_t* in, uint32_t at, int valid, float cx, float cy, float score)
{
    in->face_seq++;
    in->face_valid = (uint8_t)valid;
    in->face_cx = cx;
    in->face_cy = cy;
    in->face_w = 40;
    in->face_score = score;
    in->face_at_ms = at;
}

/* two good detections start TRACK at the middle of the picture; returns the time after */
static uint32_t start_track(ft_t* t, ft_in_t* in, uint32_t now, float cx)
{
    ft_out_t o;
    for (int k = 0; k < 2; k++) {
        in->now_ms = now;
        detect(in, now - 200, 1, cx, 120, 0.9f);
        ft_tick(t, in, &o);
        now += 333;
    }
    return now;
}

static void test_gates_stop_everything(void)
{
    ft_cfg_t c = cfg();
    for (int g = 0; g < 7; g++) {
        ft_t t;
        ft_init(&t, &c);
        ft_in_t in = base_in(1000);
        ft_out_t o;
        uint32_t now = start_track(&t, &in, 1000, 160);
        CHECK(t.state == FT_TRACK);
        in.now_ms = now;
        switch (g) {
        case 0: in.armed = 0; break;
        case 1: in.gates_ok = 0; break;
        case 2: in.leased = 1; break;
        case 3: in.locked = 1; break;
        case 4: in.carried = 1; break;
        case 5: in.remote_busy = 1; break;
        default: in.mode = FT_MODE_OFF; break;
        }
        detect(&in, now - 100, 1, 300, 120, 0.9f);
        ft_tick(&t, &in, &o);
        CHECK(o.move == 0 && o.own == 0 && o.want_detect == 0 && t.state == FT_OFF);
        CHECK(t.ends[FT_END_GATE] == 1);
    }
}

static void test_probe_needs_two_good_hits(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    ft_tick(&t, &in, &o);
    CHECK(t.state == FT_PROBE && o.want_detect == 1 && o.own == 0);
    detect(&in, 1000, 1, 160, 120, 0.55f); /* a face but under 0.6 */
    in.now_ms = 1300;
    ft_tick(&t, &in, &o);
    CHECK(t.state == FT_PROBE && t.hits == 0);
    detect(&in, 1300, 1, 160, 120, 0.8f);
    in.now_ms = 1600;
    ft_tick(&t, &in, &o);
    CHECK(t.hits == 1 && t.state == FT_PROBE);
    detect(&in, 1600, 0, 0, 0, 0); /* a miss resets */
    in.now_ms = 1900;
    ft_tick(&t, &in, &o);
    CHECK(t.hits == 0);
    detect(&in, 1900, 1, 160, 120, 0.8f);
    in.now_ms = 2200;
    ft_tick(&t, &in, &o);
    detect(&in, 2200, 1, 160, 120, 0.8f);
    in.now_ms = 2500;
    ft_tick(&t, &in, &o);
    CHECK(t.state == FT_TRACK && o.own == 1 && t.tracks == 1);
}

static void test_probe_gives_up_and_rests(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    ft_tick(&t, &in, &o);
    CHECK(t.state == FT_PROBE);
    in.now_ms = 1000 + FT_PROBE_MS + 10;
    ft_tick(&t, &in, &o);
    CHECK(t.state == FT_OFF && o.want_detect == 0);
    in.now_ms += 1000; /* resting */
    ft_tick(&t, &in, &o);
    CHECK(t.state == FT_OFF);
    in.now_ms += FT_PROBE_REST_MS;
    ft_tick(&t, &in, &o);
    CHECK(t.state == FT_PROBE);
}

static void test_always_mode_probes_on_a_mover(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    in.mode = FT_MODE_ALWAYS;
    in.conversation = 0;
    ft_out_t o;
    ft_tick(&t, &in, &o);
    CHECK(t.state == FT_OFF && o.want_detect == 0); /* nobody moved: the camera is not asked for */
    in.blob_recent = 1;
    in.now_ms = 1100;
    ft_tick(&t, &in, &o);
    CHECK(t.state == FT_PROBE && o.want_detect == 1);
}

static void test_error_sign_and_capture_time_angle(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    uint32_t now = start_track(&t, &in, 1000, 160);
    /* the head was at 10 degrees when the picture was taken (history), and is at 14 now; the face is 20 percent right of center:
       smoothed box = 0.6 * 224 + 0.4 * 160 = 198.4, error = (198.4 / 320 - 0.5) * 52 = 6.2 degrees */
    ft_hist_add(&t, now - 600, 10.0f, 0.0f);
    ft_hist_add(&t, now - 200, 10.0f, 0.0f);
    ft_hist_add(&t, now - 50, 14.0f, 0.0f);
    in.now_ms = now;
    in.pan_deg = 14.0f;
    detect(&in, now - 400, 1, 224, 120, 0.9f);
    ft_tick(&t, &in, &o); /* first one out of band */
    CHECK(o.move == 0);
    now += 333;
    in.now_ms = now;
    detect(&in, now - 400, 1, 224, 120, 0.9f); /* the picture was taken 67 ms before the first reading of 14: head about 13.5 */
    ft_tick(&t, &in, &o);
    CHECK(o.move == 1 && o.reason == FT_REASON_TRACK);
    /* target is the angle at the picture's time (about 10 to 12) plus Kp times the error, not 14 plus */
    CHECK(o.pan_deg > 15.0f && o.pan_deg < 21.0f); /* 13.5 at the picture's time plus about 0.6 * 8.7 (the smoothed box), not from 10 or 14 */
    CHECK(o.speed_pct == FT_SPEED_NORMAL);
    /* a face on the left turns the other way */
    ft_t t2;
    ft_init(&t2, &c);
    ft_in_t in2 = base_in(1000);
    now = start_track(&t2, &in2, 1000, 160);
    for (int k = 0; k < 3; k++) {
        in2.now_ms = now;
        detect(&in2, now - 100, 1, 40, 120, 0.9f);
        ft_tick(&t2, &in2, &o);
        now += 700;
        if (o.move) break;
    }
    CHECK(o.move == 1 && o.pan_deg < -3.0f);
    /* a flipped picture axis flips the move */
    c.x_sign = -1.0f;
    ft_t t3;
    ft_init(&t3, &c);
    ft_in_t in3 = base_in(1000);
    now = start_track(&t3, &in3, 1000, 160);
    for (int k = 0; k < 3; k++) {
        in3.now_ms = now;
        detect(&in3, now - 100, 1, 40, 120, 0.9f);
        ft_tick(&t3, &in3, &o);
        now += 700;
        if (o.move) break;
    }
    CHECK(o.move == 1 && o.pan_deg > 3.0f);
}

static void test_deadband_and_hysteresis(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    uint32_t now = start_track(&t, &in, 1000, 160);
    int moves = 0;
    for (int k = 0; k < 20; k++) { /* 3 degrees right of center (about 18 px): inside the 4 degree band */
        in.now_ms = now;
        detect(&in, now - 100, 1, 160 + 18, 120, 0.9f);
        ft_tick(&t, &in, &o);
        moves += o.move;
        now += 700;
    }
    CHECK(moves == 0);
    /* 6 degrees (37 px): out; the first detection alone does not move it, the second does */
    ft_t t2;
    ft_init(&t2, &c);
    ft_in_t in2 = base_in(1000);
    now = start_track(&t2, &in2, 1000, 160);
    in2.now_ms = now;
    detect(&in2, now - 100, 1, 160 + 60, 120, 0.9f);
    ft_tick(&t2, &in2, &o);
    CHECK(o.move == 0);
    now += 700;
    in2.now_ms = now;
    detect(&in2, now - 100, 1, 160 + 60, 120, 0.9f);
    ft_tick(&t2, &in2, &o);
    CHECK(o.move == 1);
}

static void test_step_cap_and_pan_limit(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    uint32_t now = start_track(&t, &in, 1000, 160);
    in.pan_deg = 0;
    float biggest = 0;
    for (int k = 0; k < 4; k++) {
        in.now_ms = now;
        detect(&in, now - 100, 1, 315, 120, 0.9f); /* far right: 25 degrees of error */
        ft_tick(&t, &in, &o);
        if (o.move && fabsf(o.pan_deg - in.pan_deg) > biggest) biggest = fabsf(o.pan_deg - in.pan_deg);
        now += 700;
    }
    CHECK(biggest > 5.0f && biggest <= FT_STEP_CAP_DEG + 0.01f);
    /* never beyond the pan limit */
    in.pan_deg = 78.0f;
    ft_hist_add(&t, now - 300, 78.0f, 0);
    for (int k = 0; k < 4; k++) {
        in.now_ms = now;
        detect(&in, now - 100, 1, 315, 120, 0.9f);
        ft_tick(&t, &in, &o);
        if (o.move) CHECK(o.pan_deg <= FT_PAN_MAX_DEG + 0.01f);
        now += 700;
    }
}

static void test_rate_limit_and_settle(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    uint32_t now = start_track(&t, &in, 1000, 160);
    int first = -1, moves = 0;
    uint32_t last = 0;
    for (int k = 0; k < 30; k++) { /* detections 200 ms apart, always far off */
        in.now_ms = now;
        detect(&in, now - 100, 1, 300, 120, 0.9f);
        ft_tick(&t, &in, &o);
        if (o.move) {
            moves++;
            if (first < 0) first = k;
            if (last) CHECK(now - last >= FT_MOVE_GAP_MS);
            last = now;
        }
        now += 200;
    }
    CHECK(first >= 0 && moves >= 3 && moves <= 30 * 200 / 600 + 1);
    /* a head that is still moving gets no new command */
    ft_t t2;
    ft_init(&t2, &c);
    ft_in_t in2 = base_in(1000);
    now = start_track(&t2, &in2, 1000, 160);
    in2.head_settled = 0;
    moves = 0;
    for (int k = 0; k < 10; k++) {
        in2.now_ms = now;
        detect(&in2, now - 100, 1, 300, 120, 0.9f);
        ft_tick(&t2, &in2, &o);
        moves += o.move;
        now += 700;
    }
    CHECK(moves == 0);
}

static void test_budget_twenty_moves_a_minute(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    uint32_t now = start_track(&t, &in, 1000, 160);
    for (int k = 0; k < FT_BUDGET_MOVES; k++) { /* twenty moves in the last minute already */
        ft_budget_spend(&t, now - 10000 + (uint32_t)k * 100);
    }
    int moves = 0;
    for (int k = 0; k < 6; k++) {
        in.now_ms = now;
        in.pan_deg = 0.0f;
        detect(&in, now - 100, 1, 300, 120, 0.9f);
        ft_tick(&t, &in, &o);
        moves += o.move;
        now += 700;
    }
    CHECK(moves == 0 && t.state == FT_TRACK); /* held, not ended */
    now += 55000; /* the minute passes (the face moved meanwhile: the still timer is not what this case tests) */
    t.still_at = now;
    for (int k = 0; k < 4; k++) {
        in.now_ms = now;
        detect(&in, now - 100, 1, (k & 1) ? 270.0f : 20.0f + 285.0f, 120, 0.9f);
        ft_tick(&t, &in, &o);
        moves += o.move;
        now += 700;
    }
    CHECK(moves >= 1);
    /* a sustained run never passes twenty in any sixty seconds */
    ft_t t2;
    ft_init(&t2, &c);
    ft_in_t in2 = base_in(1000);
    now = start_track(&t2, &in2, 1000, 160);
    uint32_t stamps[400];
    int n = 0;
    for (int k = 0; k < 300; k++) {
        in2.now_ms = now;
        in2.pan_deg = (k & 1) ? 20.0f : -20.0f; /* a head that goes back and forth, so no stall */
        ft_hist_add(&t2, now, in2.pan_deg, 0);
        detect(&in2, now - 100, 1, (k & 2) ? 285.0f : 35.0f, 120, 0.9f);
        t2.jump_pending = 0;
        t2.have_box = 0; /* the person jumps from side to side: take it as a new box each time */
        ft_tick(&t2, &in2, &o);
        if (o.move && n < 400) stamps[n++] = now;
        now += 650;
        if (t2.state != FT_TRACK) {
            in2.mode = FT_MODE_TALK;
        }
    }
    int worst = 0;
    for (int a = 0; a < n; a++) {
        int cnt = 0;
        for (int b = a; b < n && stamps[b] - stamps[a] < FT_BUDGET_WINDOW_MS; b++) cnt++;
        if (cnt > worst) worst = cnt;
    }
    CHECK(n > 20 && worst <= FT_BUDGET_MOVES);
}

static void test_jump_is_believed_only_when_repeated(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    uint32_t now = start_track(&t, &in, 1000, 160);
    in.now_ms = now;
    detect(&in, now - 100, 1, 300, 120, 0.9f); /* 44 percent of the width away: a jump */
    ft_tick(&t, &in, &o);
    CHECK(o.move == 0 && t.jump_pending == 1 && fabsf(t.cx_s - 160.0f) < 1.0f);
    now += 333;
    in.now_ms = now;
    detect(&in, now - 100, 1, 160, 120, 0.9f); /* back where it was: the jump was noise */
    ft_tick(&t, &in, &o);
    CHECK(t.jump_pending == 0 && fabsf(t.cx_s - 160.0f) < 1.0f);
    now += 333;
    in.now_ms = now;
    detect(&in, now - 100, 1, 300, 120, 0.9f);
    ft_tick(&t, &in, &o);
    now += 333;
    in.now_ms = now;
    detect(&in, now - 100, 1, 304, 120, 0.9f); /* it repeated: now it is the face */
    ft_tick(&t, &in, &o);
    CHECK(t.cx_s > 280.0f);
}

static void test_lost_holds_then_returns_once(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    uint32_t now = start_track(&t, &in, 1000, 160);
    in.pan_deg = 30.0f;
    for (int k = 0; k < 3; k++) {
        in.now_ms = now;
        detect(&in, now - 100, 0, 0, 0, 0);
        ft_tick(&t, &in, &o);
        CHECK(o.move == 0);
        now += 333;
    }
    CHECK(t.state == FT_HOLD && o.own == 1 && o.want_detect == 1);
    /* still looking while it holds: a face again takes it back to TRACK */
    in.now_ms = now;
    detect(&in, now - 100, 1, 160, 120, 0.9f);
    ft_tick(&t, &in, &o);
    CHECK(t.state == FT_TRACK);
    /* lost for good: after 20 s from the last sighting the head goes to center once and the tracker steps aside */
    for (int k = 0; k < 3; k++) {
        in.now_ms = now += 333;
        detect(&in, now - 100, 0, 0, 0, 0);
        ft_tick(&t, &in, &o);
    }
    CHECK(t.state == FT_HOLD);
    int returns = 0;
    for (int k = 0; k < 100 && t.state == FT_HOLD; k++) {
        now += 333;
        in.now_ms = now;
        detect(&in, now - 100, 0, 0, 0, 0);
        ft_tick(&t, &in, &o);
        if (o.move && o.reason == FT_REASON_RETURN) {
            returns++;
            CHECK(fabsf(o.pan_deg) < 0.01f);
        }
    }
    CHECK(returns == 1 && t.state == FT_OFF && t.ends[FT_END_LOST] == 1);
}

static void test_old_face_is_never_followed(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    uint32_t now = start_track(&t, &in, 1000, 160);
    int moves = 0;
    for (int k = 0; k < 6; k++) {
        in.now_ms = now;
        detect(&in, now - 3500, 1, 300, 120, 0.9f); /* the picture is 3.5 s old when it arrives */
        ft_tick(&t, &in, &o);
        moves += o.move;
        now += 700;
    }
    CHECK(moves == 0);
}

static void test_a_face_that_never_moves_ends_tracking(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    uint32_t now = start_track(&t, &in, 1000, 160);
    uint32_t start = now;
    while (now - start < FT_STILL_CAP_MS + 2000 && t.state == FT_TRACK) {
        in.now_ms = now;
        detect(&in, now - 100, 1, 162, 121, 0.9f);
        ft_tick(&t, &in, &o);
        now += 333;
    }
    CHECK(t.state == FT_COOL && t.ends[FT_END_STILL] == 1 && o.own == 0);
    /* and it stays off for 30 s */
    in.now_ms = now + 10000;
    detect(&in, now, 1, 162, 121, 0.9f);
    ft_tick(&t, &in, &o);
    CHECK(t.state == FT_COOL);
    in.now_ms = now + FT_STILL_COOL_MS + 100;
    ft_tick(&t, &in, &o);
    CHECK(t.state != FT_COOL);
}

static void test_no_speech_ends_tracking_in_talk_mode(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    uint32_t now = start_track(&t, &in, 1000, 160);
    in.conversation = 0;
    uint32_t start = now;
    while (now - start < FT_QUIET_END_MS + 2000 && t.state == FT_TRACK) {
        in.now_ms = now;
        detect(&in, now - 100, 1, 150 + (int)(now / 1000 % 30), 120 + (int)(now / 1000 % 20), 0.9f);
        ft_tick(&t, &in, &o);
        now += 333;
    }
    CHECK(t.state == FT_OFF && t.ends[FT_END_QUIET] == 1);
    CHECK(now - start >= FT_QUIET_END_MS - 500);
}

static void test_stall_guard(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    uint32_t now = start_track(&t, &in, 1000, 160);
    in.pan_deg = 0.0f; /* the head never moves (blocked): every move asks and gets nothing */
    int moved = 0;
    for (int k = 0; k < 20 && t.state == FT_TRACK; k++) {
        in.now_ms = now;
        detect(&in, now - 100, 1, 318, 120, 0.9f);
        ft_tick(&t, &in, &o);
        moved += o.move;
        now += 700;
    }
    CHECK(moved >= 1 && t.stalls == 1 && t.state == FT_COOL && t.ends[FT_END_STALL] == 1);
}

static void test_hour_ceiling_holds_and_says_nothing(void)
{
    ft_cfg_t c = cfg();
    c.hour_ms = 30000u;
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    ft_out_t o;
    uint32_t now = 1000;
    int moves_after = 0;
    int capped = 0;
    for (int k = 0; k < 400; k++) {
        in.now_ms = now;
        detect(&in, now - 100, 1, 160 + (int)((k * 37) % 120) - 60, 120, 0.9f);
        ft_tick(&t, &in, &o);
        if (t.ends[FT_END_HOUR]) {
            capped = 1;
            moves_after += o.move;
            CHECK(o.want_detect == 0);
        }
        now += 333;
    }
    CHECK(capped == 1 && moves_after == 0);
}

static void test_quiet_speed_and_pitch(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    ft_in_t in = base_in(1000);
    in.quiet_or_night = 1;
    ft_out_t o;
    uint32_t now = start_track(&t, &in, 1000, 160);
    for (int k = 0; k < 3 && !o.move; k++) {
        in.now_ms = now;
        detect(&in, now - 100, 1, 300, 120, 0.9f);
        ft_tick(&t, &in, &o);
        now += 700;
    }
    CHECK(o.move == 1 && o.speed_pct == FT_SPEED_QUIET && o.has_tilt == 0);
    /* with tilt: a face high in the picture tilts the head up (y sign -1: low in the picture is down) */
    c.tilt = 1;
    ft_t t2;
    ft_init(&t2, &c);
    ft_in_t in2 = base_in(1000);
    now = start_track(&t2, &in2, 1000, 160);
    in2.tilt_deg = 0;
    for (int k = 0; k < 4; k++) {
        in2.now_ms = now;
        detect(&in2, now - 100, 1, 160, 30, 0.9f); /* high: 90 px above center, 14.6 degrees */
        ft_tick(&t2, &in2, &o);
        now += 700;
        if (o.move) break;
    }
    CHECK(o.move == 1 && o.has_tilt == 1 && o.tilt_deg > 2.0f);
    CHECK(fabsf(o.pan_deg) < 1.0f);
}

/* ---- the closed loop: a person at a fixed angle, a head with a slow servo that stops short, a detector that jitters, 300 ms of delay ---- */
typedef struct {
    float pan, goal, speed_dps;
    uint32_t arrive_at, started_at, settle_at;
    float undershoot;
} head_t;

static void head_move(head_t* h, uint32_t now, float to)
{
    h->started_at = now;
    float dir = to > h->pan ? 1.0f : -1.0f;
    h->goal = to - dir * h->undershoot;
    h->arrive_at = now + 200 + (uint32_t)(fabsf(h->goal - h->pan) / h->speed_dps * 1000.0f);
}
static float head_at(const head_t* h, uint32_t now, float from)
{
    if (h->arrive_at == 0 || now >= h->arrive_at) {
        return h->arrive_at == 0 ? from : h->goal;
    }
    if (now < h->started_at + 200) {
        return from;
    }
    float f = (float)(now - h->started_at - 200) / (float)(h->arrive_at - h->started_at - 200);
    return from + (h->goal - from) * f;
}

static float rnd(unsigned* s)
{
    *s = *s * 1664525u + 1013904223u;
    return ((float)((*s >> 8) & 0xFFFF) / 65535.0f) * 2.0f - 1.0f;
}

static void test_closed_loop_converges_and_stays(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    head_t h;
    memset(&h, 0, sizeof(h));
    h.speed_dps = 90.0f;
    h.undershoot = 2.0f;
    float person = 20.0f; /* degrees to the right, inside the 26 degrees the picture shows */
    unsigned seed = 7;
    uint32_t now = 1000, next_det = 1000;
    float from = 0.0f;
    ft_in_t in = base_in(now);
    ft_out_t o;
    int moves = 0, moves_after = 0;
    float final_err = 99;
    uint32_t pic_at[4] = {0, 0, 0, 0};
    for (; now < 1000 + 40000; now += 50) {
        float pan_now = head_at(&h, now, from);
        if (h.arrive_at != 0 && now >= h.arrive_at) {
            from = h.goal;
            h.pan = h.goal;
            h.arrive_at = 0;
            pan_now = h.pan;
        }
        in.now_ms = now;
        in.pan_deg = pan_now;
        in.head_settled = h.arrive_at == 0 || now > h.arrive_at + 300;
        in.head_settled = (uint8_t)(h.arrive_at == 0 && now > h.started_at + 500);
        ft_hist_add(&t, now, pan_now, 0);
        if (now >= next_det) { /* a detection every 333 ms, its picture taken 300 ms ago */
            uint32_t at = now - 300;
            float pan_pic = head_at(&h, at, from);
            (void)pic_at;
            float err = person - pan_pic + rnd(&seed) * 1.2f; /* box jitter about 1.2 degrees */
            float cx = 160.0f + err / 52.0f * 320.0f;
            if (cx < 0 || cx > 320) {
                detect(&in, at, 0, 0, 0, 0);
            } else {
                detect(&in, at, 1, cx, 120, 0.85f);
            }
            next_det += 333;
        }
        ft_tick(&t, &in, &o);
        if (o.move) {
            moves++;
            if (now > 1000 + 15000) moves_after++;
            from = head_at(&h, now, from);
            head_move(&h, now, o.pan_deg);
        }
        if (now > 1000 + 39000) {
            final_err = fabsf(person - pan_now);
        }
    }
    CHECK(final_err < FT_DEAD_YAW_DEG + 1.0f); /* on target to within the band (the servo stops short by 2) */
    CHECK(moves >= 2 && moves <= 20);           /* got there in a few moves, did not walk */
    CHECK(moves_after <= 2);                    /* jitter inside the band does not move the head */
    CHECK(t.state == FT_TRACK || t.state == FT_COOL || t.state == FT_OFF);
}

static void test_status_text_is_flat_json_pieces(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    char buf[200];
    int n = ft_status_json(&t, 5000, buf, sizeof(buf));
    CHECK(n > 20 && n < (int)sizeof(buf) && strstr(buf, "\"fd_track\":\"off\"") != NULL && strstr(buf, "\"fd_end\":\"none\"") != NULL);
    CHECK(buf[0] == '"' && buf[n - 1] != ',');
}

static void test_history_interpolates(void)
{
    ft_cfg_t c = cfg();
    ft_t t;
    ft_init(&t, &c);
    float p, q;
    ft_hist_at(&t, 500, 7.0f, 3.0f, &p, &q);
    CHECK(p == 7.0f && q == 3.0f); /* no history: the current angles */
    ft_hist_add(&t, 1000, 0.0f, 0.0f);
    ft_hist_add(&t, 1100, 10.0f, 4.0f);
    ft_hist_add(&t, 1200, 10.0f, 4.0f);
    ft_hist_at(&t, 1050, 99, 99, &p, &q);
    CHECK(fabsf(p - 5.0f) < 0.01f && fabsf(q - 2.0f) < 0.01f);
    ft_hist_at(&t, 900, 99, 99, &p, &q);
    CHECK(p == 0.0f);
    ft_hist_at(&t, 5000, 99, 99, &p, &q);
    CHECK(p == 10.0f);
    for (int k = 0; k < 40; k++) ft_hist_add(&t, 2000 + k * 100, (float)k, 0); /* wraps the ring */
    ft_hist_at(&t, 2000 + 39 * 100 - 50, 99, 99, &p, &q);
    CHECK(fabsf(p - 38.5f) < 0.01f);
}

int main(void)
{
    test_gates_stop_everything();
    test_probe_needs_two_good_hits();
    test_probe_gives_up_and_rests();
    test_always_mode_probes_on_a_mover();
    test_error_sign_and_capture_time_angle();
    test_deadband_and_hysteresis();
    test_step_cap_and_pan_limit();
    test_rate_limit_and_settle();
    test_budget_twenty_moves_a_minute();
    test_jump_is_believed_only_when_repeated();
    test_lost_holds_then_returns_once();
    test_old_face_is_never_followed();
    test_a_face_that_never_moves_ends_tracking();
    test_no_speech_ends_tracking_in_talk_mode();
    test_stall_guard();
    test_hour_ceiling_holds_and_says_nothing();
    test_quiet_speed_and_pitch();
    test_closed_loop_converges_and_stays();
    test_status_text_is_flat_json_pieces();
    test_history_interpolates();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
