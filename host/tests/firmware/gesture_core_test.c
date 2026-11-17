/* Host test for the swipe gesture state machine (patch P10): cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> gesture_core_test.c */
#include <stdio.h>
#include <string.h>
#include "maipai_touch_core.h"
#include "maipai_gesture_core.h"

static int failures;
#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            printf("FAIL line %d: %s\n", __LINE__, #cond);               \
            failures++;                                                  \
        }                                                                \
    } while (0)

static uint32_t T = 10000;

/* one finger: down at (x0,y0), up at (x1,y1) after ms. Returns what the lift did. */
static mgs_out_t swipe_f(mgs_t* g, int x0, int y0, int x1, int y1, uint32_t ms, unsigned flags)
{
    mgs_down(g, x0, y0, T, flags);
    mgs_move(g, (x0 + x1) / 2, (y0 + y1) / 2, T + ms / 2);
    T += ms;
    mgs_out_t o = mgs_up(g, x1, y1, T);
    T += 50;
    return o;
}
static mgs_out_t swipe(mgs_t* g, int x0, int y0, int x1, int y1, uint32_t ms) { return swipe_f(g, x0, y0, x1, y1, ms, 0); }

static void fresh(mgs_t* g)
{
    mgs_init(g);
    mgs_config(g, 1, 1, 10, 20);
}

static void test_swipe_classifier(void)
{
    CHECK(mgs_swipe_of(160, 120, 240, 120, 200) == MGS_SW_RIGHT);
    CHECK(mgs_swipe_of(160, 120, 80, 120, 200) == MGS_SW_LEFT);
    CHECK(mgs_swipe_of(160, 200, 160, 120, 250) == MGS_SW_UP);
    CHECK(mgs_swipe_of(160, 60, 160, 150, 250) == MGS_SW_DOWN);
    CHECK(mgs_swipe_of(160, 120, 190, 120, 100) == MGS_SW_NONE);   /* 30 px: too short */
    CHECK(mgs_swipe_of(160, 120, 196, 120, 100) == MGS_SW_RIGHT);  /* 36 px is enough */
    CHECK(mgs_swipe_of(160, 120, 240, 120, 1500) == MGS_SW_NONE);  /* slower than 900 ms: a drag */
    CHECK(mgs_swipe_of(160, 120, 240, 120, 899) == MGS_SW_RIGHT);
    CHECK(mgs_swipe_of(160, 120, 200, 120, 800) == MGS_SW_NONE);   /* 40 px in 800 ms is 50 px a second: too slow */
    CHECK(mgs_swipe_of(160, 120, 240, 190, 200) == MGS_SW_NONE);   /* a diagonal (80 by 70) is no swipe */
    CHECK(mgs_swipe_of(160, 120, 240, 160, 200) == MGS_SW_RIGHT);  /* 80 by 40 is mostly along x */
    CHECK(mgs_swipe_of(160, 120, 240, 120, 0) == MGS_SW_NONE);     /* no time at all is no swipe */
}

static void test_pages_left_and_right(void)
{
    mgs_t g;
    fresh(&g);
    /* the finger moves right: the page on the left of the face (position -1) */
    mgs_out_t o = swipe(&g, 100, 100, 220, 100, 220);
    CHECK(o.act == MGS_ACT_SHOW_PAGE && o.arg == -1 && o.consume);
    CHECK(g.mode == MGS_PAGE && g.pos == -1);
    /* another swipe right: nothing further on the left, a bump */
    o = swipe(&g, 100, 100, 220, 100, 220);
    CHECK(o.act == MGS_ACT_BUMP && g.pos == -1 && g.mode == MGS_PAGE);
    /* the finger moves left: back to the face */
    o = swipe(&g, 220, 100, 100, 100, 220);
    CHECK(o.act == MGS_ACT_SHOW_FACE && g.mode == MGS_FACE && g.pos == 0);
    /* and left again: the page on the right (position +1) */
    o = swipe(&g, 220, 100, 100, 100, 220);
    CHECK(o.act == MGS_ACT_SHOW_PAGE && o.arg == 1 && g.pos == 1);
    o = swipe(&g, 220, 100, 100, 100, 220);
    CHECK(o.act == MGS_ACT_BUMP);
}

static void test_longer_strips(void)
{
    mgs_t g;
    mgs_init(&g);
    mgs_config(&g, 3, 3, 10, 20);
    for (int i = 1; i <= 3; i++) {
        mgs_out_t o = swipe(&g, 120, 100, 220, 100, 200);
        CHECK(o.act == MGS_ACT_SHOW_PAGE && o.arg == -i);
    }
    CHECK(swipe(&g, 120, 100, 220, 100, 200).act == MGS_ACT_BUMP);
    for (int i = 2; i >= 1; i--) {
        mgs_out_t o = swipe(&g, 220, 100, 120, 100, 200);
        CHECK(o.act == MGS_ACT_SHOW_PAGE && o.arg == -i);
    }
    CHECK(swipe(&g, 220, 100, 120, 100, 200).act == MGS_ACT_SHOW_FACE);
    /* no pages configured: both directions bump and the face stays */
    mgs_config(&g, 0, 0, 10, 20);
    CHECK(swipe(&g, 120, 100, 220, 100, 200).act == MGS_ACT_BUMP);
    CHECK(swipe(&g, 220, 100, 120, 100, 200).act == MGS_ACT_BUMP);
    CHECK(g.mode == MGS_FACE);
}

static void test_edge_swipes_keep_their_meaning(void)
{
    mgs_t g;
    fresh(&g);
    /* begun in the left edge: volume plus, never a page */
    mgs_out_t o = swipe(&g, 5, 100, 120, 100, 200);
    CHECK(o.act == MGS_ACT_VOLUME && o.arg == 10 && g.mode == MGS_FACE);
    /* begun in the right edge, moving left: volume minus */
    o = swipe(&g, 315, 100, 200, 100, 200);
    CHECK(o.act == MGS_ACT_VOLUME && o.arg == -10 && g.mode == MGS_FACE);
    /* the first inside pixel is a page swipe */
    o = swipe(&g, MGS_EDGE_SIDE, 100, 140, 100, 200);
    CHECK(o.act == MGS_ACT_SHOW_PAGE);
    swipe(&g, 220, 100, 100, 100, 200);  /* back to the face */
    o = swipe(&g, MGS_W - MGS_EDGE_SIDE - 1, 100, 150, 100, 200);
    CHECK(o.act == MGS_ACT_SHOW_PAGE && o.arg == 1);
    swipe(&g, 100, 100, 220, 100, 200);
    /* the edge swipe also works over a page */
    o = swipe(&g, 3, 100, 120, 100, 200);
    CHECK(o.act == MGS_ACT_VOLUME);
}

static void test_stop_swipe_stays(void)
{
    mgs_t g;
    fresh(&g);
    mgs_out_t o = swipe(&g, 160, 40, 160, 150, 250);
    CHECK(o.act == MGS_ACT_STOP && o.stop && o.consume);
    o = swipe(&g, 160, 10, 160, 120, 250);  /* from the banner row */
    CHECK(o.act == MGS_ACT_STOP);
    /* the stop swipe works during a game too */
    o = swipe_f(&g, 160, 60, 160, 170, 250, MGS_F_GAME);
    CHECK(o.act == MGS_ACT_STOP && o.stop);
    /* and on a page it leaves the page and stops */
    swipe(&g, 100, 100, 220, 100, 200);
    CHECK(g.mode == MGS_PAGE);
    o = swipe(&g, 160, 40, 160, 150, 250);
    CHECK(o.act == MGS_ACT_SHOW_FACE && o.stop && g.mode == MGS_FACE);
}

static void test_sheet_open_close(void)
{
    mgs_t g;
    fresh(&g);
    /* a swipe up from the bottom band opens the sheet */
    mgs_out_t o = swipe(&g, 160, 225, 160, 140, 250);
    CHECK(o.act == MGS_ACT_OPEN_SHEET && g.mode == MGS_SHEET);
    /* swipe down inside it closes it back to the face */
    o = swipe(&g, 160, 150, 160, 230, 250);
    CHECK(o.act == MGS_ACT_SHOW_FACE && g.mode == MGS_FACE && o.consume);
    /* a swipe up that begins above the band does nothing (it is not an edge swipe) */
    o = swipe(&g, 160, 159, 160, 60, 250);
    CHECK(o.act == MGS_ACT_NONE && g.mode == MGS_FACE);
    o = swipe(&g, 160, 160, 160, 70, 250);
    CHECK(o.act == MGS_ACT_OPEN_SHEET);
    /* from the left and right bottom corners too */
    mgs_close_sheet(&g, T);
    CHECK(swipe(&g, 4, 230, 6, 120, 250).act == MGS_ACT_OPEN_SHEET);
}

static void test_sheet_over_a_page_returns_to_it(void)
{
    mgs_t g;
    fresh(&g);
    swipe(&g, 100, 100, 220, 100, 200);  /* page -1 */
    mgs_out_t o = swipe(&g, 160, 230, 160, 130, 250);
    CHECK(o.act == MGS_ACT_OPEN_SHEET && g.under_pos == -1);
    /* a pick closes it back to the page */
    o = mgs_event(&g, MGS_EV_PICK, T);
    CHECK(o.act == MGS_ACT_SHOW_PAGE && o.arg == -1 && g.mode == MGS_PAGE);
    /* in the sheet a horizontal drag (a slider) changes no page and stays the slider's */
    swipe(&g, 160, 230, 160, 130, 250);
    o = swipe(&g, 60, 200, 200, 200, 300);
    CHECK(o.act == MGS_ACT_NONE && !o.consume && g.mode == MGS_SHEET);
    /* a tap above the sheet closes it */
    o = swipe(&g, 160, 60, 162, 61, 120);
    CHECK(o.act == MGS_ACT_SHOW_PAGE && o.arg == -1 && g.mode == MGS_PAGE);   /* closes back to the page under it */
    /* a tap inside the sheet does not (it belongs to the button under it) */
    mgs_event(&g, MGS_EV_WAKE, T);
    swipe(&g, 160, 230, 160, 130, 250);
    CHECK(g.mode == MGS_SHEET);
    o = swipe(&g, 160, 200, 161, 201, 120);
    CHECK(o.act == MGS_ACT_NONE && !o.consume);
}

static void test_sheet_auto_dismiss(void)
{
    mgs_t g;
    fresh(&g);
    swipe(&g, 160, 230, 160, 130, 250);
    uint32_t t0 = T;
    CHECK(mgs_tick(&g, t0 + 9900).act == MGS_ACT_NONE);
    CHECK(mgs_tick(&g, t0 + 10000).act == MGS_ACT_SHOW_FACE);  /* closes back to the face after 10 s (patch UI01: it was 6) */
    CHECK(g.mode == MGS_FACE);
    /* the time is set from the last touch: a touch on the sheet restarts it */
    swipe(&g, 160, 230, 160, 130, 250);
    t0 = T;
    mgs_down(&g, 100, 200, t0 + 4000, 0);
    mgs_up(&g, 100, 200, t0 + 4100);
    CHECK(mgs_tick(&g, t0 + 14000).act == MGS_ACT_NONE);
    CHECK(mgs_tick(&g, t0 + 14100).act != MGS_ACT_NONE);   /* the 10 s count began again at the touch */
    /* no timer runs while a finger is down (a slider being dragged) */
    swipe(&g, 160, 230, 160, 130, 250);
    t0 = T;
    mgs_down(&g, 100, 200, t0 + 100, 0);
    mgs_move(&g, 140, 200, t0 + 200);
    CHECK(mgs_tick(&g, t0 + 60000).act == MGS_ACT_NONE && g.mode == MGS_SHEET);
    mgs_up(&g, 140, 200, t0 + 60100);
    CHECK(mgs_tick(&g, t0 + 60200).act == MGS_ACT_NONE);
    CHECK(mgs_tick(&g, t0 + 70100).act != MGS_ACT_NONE);
    /* the setting goes from 8 to 30 s and is clamped */
    mgs_config(&g, 1, 1, 2, 20);
    CHECK(g.sheet_s == 8);
    mgs_config(&g, 1, 1, 99, 20);
    CHECK(g.sheet_s == 30);
    mgs_config(&g, 1, 1, 12, 20);
    CHECK(g.sheet_s == 12);
    swipe(&g, 160, 230, 160, 130, 250);
    t0 = T;
    CHECK(mgs_tick(&g, t0 + 11900).act == MGS_ACT_NONE);
    CHECK(mgs_tick(&g, t0 + 12000).act != MGS_ACT_NONE);
}

static void test_page_idle_return(void)
{
    mgs_t g;
    fresh(&g);
    swipe(&g, 100, 100, 220, 100, 200);
    uint32_t t0 = T;
    CHECK(mgs_tick(&g, t0 + 19900).act == MGS_ACT_NONE && g.mode == MGS_PAGE);
    CHECK(mgs_tick(&g, t0 + 20000).act == MGS_ACT_SHOW_FACE && g.mode == MGS_FACE && g.pos == 0);
    /* a touch on the page (a button) keeps it up */
    swipe(&g, 100, 100, 220, 100, 200);
    t0 = T;
    mgs_down(&g, 160, 100, t0 + 15000, 0);
    mgs_up(&g, 160, 100, t0 + 15080);
    CHECK(mgs_tick(&g, t0 + 34000).act == MGS_ACT_NONE);
    CHECK(mgs_tick(&g, t0 + 35100).act == MGS_ACT_SHOW_FACE);
    /* idle setting is 5 to 300 s */
    mgs_config(&g, 1, 1, 10, 1);
    CHECK(g.idle_s == 5);
    mgs_config(&g, 1, 1, 10, 900);
    CHECK(g.idle_s == 300);
    /* nothing happens at rest: the face has no timer */
    mgs_config(&g, 1, 1, 10, 20);
    g.mode = MGS_FACE;
    CHECK(mgs_tick(&g, T + 1000000).act == MGS_ACT_NONE);
}

static void test_events_return_to_the_face(void)
{
    const int evs[] = {MGS_EV_WAKE, MGS_EV_SPEECH, MGS_EV_HEAD_TAP, MGS_EV_TIMER_RING};
    for (unsigned i = 0; i < sizeof(evs) / sizeof(evs[0]); i++) {
        mgs_t g;
        fresh(&g);
        swipe(&g, 100, 100, 220, 100, 200);
        CHECK(mgs_event(&g, evs[i], T).act == MGS_ACT_SHOW_FACE && g.mode == MGS_FACE && g.pos == 0);
        /* over the sheet too */
        swipe(&g, 160, 230, 160, 130, 250);
        CHECK(g.mode == MGS_SHEET);
        CHECK(mgs_event(&g, evs[i], T).act == MGS_ACT_SHOW_FACE && g.mode == MGS_FACE);
        /* at rest nothing happens */
        CHECK(mgs_event(&g, evs[i], T).act == MGS_ACT_NONE);
    }
    /* a pick on a page (not the sheet) changes nothing */
    mgs_t g;
    fresh(&g);
    swipe(&g, 100, 100, 220, 100, 200);
    CHECK(mgs_event(&g, MGS_EV_PICK, T).act == MGS_ACT_NONE && g.mode == MGS_PAGE);
}

static void test_head_touch_conflicts(void)
{
    mgs_t g;
    fresh(&g);
    swipe(&g, 100, 100, 220, 100, 200);
    /* a head tap while a finger is on the screen is dropped: the page does not vanish under the finger */
    mgs_down(&g, 160, 100, T, 0);
    CHECK(mgs_event(&g, MGS_EV_HEAD_TAP, T + 100).act == MGS_ACT_NONE && g.mode == MGS_PAGE);
    CHECK(mgs_event(&g, MGS_EV_WAKE, T + 100).act == MGS_ACT_NONE);
    mgs_up(&g, 160, 100, T + 150);
    CHECK(mgs_event(&g, MGS_EV_HEAD_TAP, T + 400).act == MGS_ACT_SHOW_FACE);
    /* a head swipe is never a page change: the machine has no head swipe input at all, and a head event at rest is nothing */
    CHECK(mgs_event(&g, MGS_EV_HEAD_TAP, T + 500).act == MGS_ACT_NONE && g.mode == MGS_FACE);
}

static void test_game_and_consumed_touches(void)
{
    mgs_t g;
    fresh(&g);
    /* during a game: no page change, no sheet; the stop swipe and the edge swipes still work */
    CHECK(swipe_f(&g, 100, 100, 220, 100, 200, MGS_F_GAME).act == MGS_ACT_NONE && g.mode == MGS_FACE);
    CHECK(swipe_f(&g, 160, 230, 160, 120, 250, MGS_F_GAME).act == MGS_ACT_NONE && g.mode == MGS_FACE);
    CHECK(swipe_f(&g, 4, 100, 120, 100, 200, MGS_F_GAME).act == MGS_ACT_VOLUME);
    /* a touch that ended a ringing timer, or only woke the screen, is consumed whole */
    mgs_out_t o = swipe_f(&g, 100, 100, 220, 100, 200, MGS_F_RINGING);
    CHECK(o.act == MGS_ACT_NONE && o.consume && g.mode == MGS_FACE);
    o = swipe_f(&g, 160, 230, 160, 120, 250, MGS_F_WOKE);
    CHECK(o.act == MGS_ACT_NONE && o.consume && g.mode == MGS_FACE);
    CHECK(mgs_down(&g, 10, 10, T, MGS_F_RINGING) == 1);
    mgs_up(&g, 10, 10, T + 50);
    CHECK(mgs_down(&g, 10, 10, T + 100, 0) == 0);
    mgs_up(&g, 10, 10, T + 150);
}

/* The face touch toggles (patch 105: mute, vision, quiet) and a swipe never both. */
static mtc_action_t toggle_of(int x0, int y0, int x1, int y1, uint32_t ms)
{
    mtc_trace_t t;
    mtc_begin(&t, x0, y0, 1000);
    mtc_move(&t, (x0 + x1) / 2, (y0 + y1) / 2, 1000 + ms / 2);
    mtc_move(&t, x1, y1, 1000 + ms);
    return mtc_action_on_release(&t);
}

static void test_eye_and_forehead_regions(void)
{
    mgs_t g;
    fresh(&g);
    /* a tap on an eye with a little wobble is no swipe and still toggles vision */
    CHECK(mgs_swipe_of(80, 100, 86, 103, 150) == MGS_SW_NONE);
    CHECK(toggle_of(80, 100, 86, 103, 150) == MTC_ACTION_VISION);
    mgs_out_t o = swipe(&g, 80, 100, 86, 103, 150);
    CHECK(o.act == MGS_ACT_NONE && !o.consume);
    /* a swipe that begins on the left eye is a page change and toggles nothing */
    CHECK(toggle_of(80, 100, 200, 100, 220) == MTC_ACTION_NONE);
    o = swipe(&g, 80, 100, 200, 100, 220);
    CHECK(o.act == MGS_ACT_SHOW_PAGE && o.consume);
    swipe(&g, 220, 100, 100, 100, 200);
    /* a swipe that begins on the mouth or the forehead is the same */
    CHECK(toggle_of(160, 40, 40, 44, 220) == MTC_ACTION_NONE);
    CHECK(swipe(&g, 160, 40, 40, 44, 220).act == MGS_ACT_SHOW_PAGE);
    swipe(&g, 100, 100, 220, 100, 200);
    /* a swipe up from the mouth (y 160 is the bottom band) opens the sheet and toggles nothing */
    CHECK(toggle_of(160, 165, 160, 90, 250) == MTC_ACTION_NONE);
    CHECK(swipe(&g, 160, 165, 160, 90, 250).act == MGS_ACT_OPEN_SHEET);
    /* with a page or the sheet on screen the face toggles are off */
    CHECK(!mgs_face_takes_taps(&g));
    mgs_close_sheet(&g, T);
    mgs_event(&g, MGS_EV_WAKE, T);
    CHECK(mgs_face_takes_taps(&g));
    /* a slow drag on an eye is no swipe: the drag leaves the toggle off (patch 105) and the page stays */
    o = swipe(&g, 60, 100, 150, 100, 1400);
    CHECK(o.act == MGS_ACT_NONE && g.mode == MGS_FACE);
}

static void test_host_jump_and_strip_change(void)
{
    mgs_t g;
    mgs_init(&g);
    mgs_config(&g, 2, 2, 10, 20);
    mgs_out_t o = mgs_goto(&g, -2, T);
    CHECK(o.act == MGS_ACT_SHOW_PAGE && o.arg == -2 && g.mode == MGS_PAGE);
    CHECK(mgs_goto(&g, 3, T).act == MGS_ACT_NONE);  /* no such position */
    CHECK(mgs_goto(&g, 0, T).act == MGS_ACT_SHOW_FACE);
    mgs_goto(&g, 2, T);
    mgs_config(&g, 1, 1, 10, 20);  /* the owner shortened the strip while a far page was up */
    CHECK(g.mode == MGS_FACE && g.pos == 0);
    swipe(&g, 160, 230, 160, 130, 250);
    CHECK(mgs_goto(&g, 1, T).act == MGS_ACT_NONE);  /* the sheet stays up */
}

static void test_extra_page_and_late_flags(void)
{
    mgs_t g;
    fresh(&g);
    /* a page outside the strip sits at the face's position: a swipe from it enters the strip, down leaves it */
    mgs_out_t o = mgs_show_extra(&g, T);
    CHECK(o.act == MGS_ACT_SHOW_PAGE && o.arg == 0 && g.mode == MGS_PAGE && g.pos == 0);
    o = swipe(&g, 100, 100, 220, 100, 200);
    CHECK(o.act == MGS_ACT_SHOW_PAGE && o.arg == -1);
    mgs_goto(&g, 0, T);
    mgs_show_extra(&g, T);
    CHECK(swipe(&g, 160, 40, 160, 150, 250).act == MGS_ACT_SHOW_FACE && g.mode == MGS_FACE);
    mgs_show_extra(&g, T);
    CHECK(mgs_tick(&g, T + 20000).act == MGS_ACT_SHOW_FACE);
    /* the face's own press handler learns after the press that a ring ended: the touch becomes a consumed one */
    mgs_down(&g, 100, 100, T, 0);
    mgs_flag(&g, MGS_F_RINGING);
    mgs_move(&g, 200, 100, T + 100);
    o = mgs_up(&g, 220, 100, T + 200);
    CHECK(o.act == MGS_ACT_NONE && o.consume && g.mode == MGS_FACE);
    /* a game flag arriving late limits the touch the same way */
    mgs_down(&g, 160, 230, T + 1000, 0);
    mgs_flag(&g, MGS_F_GAME);
    o = mgs_up(&g, 160, 120, T + 1250);
    CHECK(o.act == MGS_ACT_NONE && g.mode == MGS_FACE);
    T += 3000;
}

static void test_sweep_never_leaves_range(void)
{
    /* every start point and direction: positions stay inside the strip, the sheet only opens from the bottom band */
    for (int n_left = 0; n_left <= 3; n_left++) {
        for (int n_right = 0; n_right <= 3; n_right++) {
            mgs_t g;
            mgs_init(&g);
            mgs_config(&g, n_left, n_right, 10, 20);
            for (int y0 = 0; y0 < MGS_H; y0 += 20) {
                for (int x0 = 0; x0 < MGS_W; x0 += 16) {
                    const int dxs[] = {-90, 0, 90};
                    const int dys[] = {-90, 0, 90};
                    for (int a = 0; a < 3; a++) {
                        for (int b = 0; b < 3; b++) {
                            const int x1 = x0 + dxs[a] < 0 ? 0 : (x0 + dxs[a] > 319 ? 319 : x0 + dxs[a]);
                            const int y1 = y0 + dys[b] < 0 ? 0 : (y0 + dys[b] > 239 ? 239 : y0 + dys[b]);
                            mgs_out_t o = swipe(&g, x0, y0, x1, y1, 220);
                            CHECK(g.pos >= -n_left && g.pos <= n_right);
                            if (o.act == MGS_ACT_OPEN_SHEET) {
                                CHECK(y0 >= MGS_SHEET_START_Y);
                            }
                            if (o.act == MGS_ACT_VOLUME) {
                                CHECK(x0 < MGS_EDGE_SIDE || x0 >= MGS_W - MGS_EDGE_SIDE);
                            }
                            if (o.act == MGS_ACT_SHOW_PAGE) {
                                CHECK(!(x0 < MGS_EDGE_SIDE || x0 >= MGS_W - MGS_EDGE_SIDE));
                            }
                            if (g.mode == MGS_SHEET) {
                                mgs_close_sheet(&g, T);
                            }
                            if (g.mode == MGS_PAGE) {
                                mgs_event(&g, MGS_EV_WAKE, T);
                            }
                        }
                    }
                }
            }
        }
    }
}

int main(void)
{
    test_swipe_classifier();
    test_pages_left_and_right();
    test_longer_strips();
    test_edge_swipes_keep_their_meaning();
    test_stop_swipe_stays();
    test_sheet_open_close();
    test_sheet_over_a_page_returns_to_it();
    test_sheet_auto_dismiss();
    test_page_idle_return();
    test_events_return_to_the_face();
    test_head_touch_conflicts();
    test_game_and_consumed_touches();
    test_eye_and_forehead_regions();
    test_host_jump_and_strip_change();
    test_extra_page_and_late_flags();
    test_sweep_never_leaves_range();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("gesture_core_test: all passed\n");
    return 0;
}
