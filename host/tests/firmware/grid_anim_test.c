/* Host test for the grid animation layer (patch SF72): cc -std=c99 -Wall -Wextra -Werror -I<dir> grid_anim_test.c */
#include <stdio.h>
#include "maipai_grid_core.h"
#include "maipai_grid_c4_core.h"
#include "maipai_grid_anim_core.h"
#include "maipai_games_sfx_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void test_fall_math(void)
{
    gan_t a;
    gan_init(&a);
    CHECK(!gan_active(&a) && !gan_busy(&a));
    const int y0 = 0, y1 = 160, rows = 5;
    CHECK(gan_fall(&a, 1000, 38, 1, 5, rows, y0, y1) == 0);
    CHECK(gan_active(&a) && gan_busy(&a) && gan_cell_hidden(&a, 38) && !gan_cell_hidden(&a, 3));
    const uint32_t fall = gan_fall_ms_for_rows(rows);
    CHECK(fall == 400 && gan_fall_ms_for_rows(1) == 120 && gan_fall_ms_for_rows(0) == 120 && gan_fall_ms_for_rows(6) == 480);
    /* start at y0, monotonic and accelerating until the landing, exact at the landing */
    CHECK(gan_fall_y(&a, 38, 1000) == y0);
    int prev = y0, prev_step = -1;
    for (uint32_t t = 1000 + 20; t <= 1000 + fall; t += 20) {
        const int y = gan_fall_y(&a, 38, t);
        CHECK(y >= prev && y <= y1);
        CHECK(y - prev >= prev_step - 1);                      /* the steps grow: gravity (allow a pixel of rounding) */
        prev_step = y - prev;
        prev = y;
    }
    CHECK(gan_fall_y(&a, 38, 1000 + fall) == y1);
    /* the bounce: up a little, never above the landing by more than the cap, back to y1 exactly */
    int highest = y1;
    for (uint32_t t = 1000 + fall; t <= 1000 + fall + GAN_BOUNCE_MS; t += 5) {
        const int y = gan_fall_y(&a, 38, t);
        if (y < highest) highest = y;
        CHECK(y <= y1 && y >= y1 - GAN_BOUNCE_MAX_PX);
    }
    CHECK(highest < y1 && highest >= y1 - GAN_BOUNCE_MAX_PX);
    CHECK(gan_fall_y(&a, 38, 1000 + fall + GAN_BOUNCE_MS) == y1 && gan_fall_y(&a, 99, 1000) == -1);
    /* the events: a landing at the end of the fall (bounce 0), a second at the end of the bounce (bounce 1), then done; nothing before */
    gan_ev_t ev[GAN_EV_MAX];
    CHECK(gan_tick(&a, 1000 + fall - 1, ev) == 0);
    int n = gan_tick(&a, 1000 + fall, ev);
    CHECK(n == 1 && ev[0].type == GAN_EV_LAND && ev[0].bounce == 0 && ev[0].owner == 1 && ev[0].row == 5 && ev[0].cell == 38);
    CHECK(gan_tick(&a, 1000 + fall + GAN_BOUNCE_MS - 1, ev) == 0 && gan_busy(&a));
    n = gan_tick(&a, 1000 + fall + GAN_BOUNCE_MS, ev);
    CHECK(n == 2 && ev[0].type == GAN_EV_LAND && ev[0].bounce == 1 && ev[1].type == GAN_EV_FALL_DONE);
    CHECK(!gan_busy(&a) && !gan_cell_hidden(&a, 38));
    /* a late tick (the game stalled) still reports both impacts and the end, in order */
    gan_init(&a);
    gan_fall(&a, 0, 10, 2, 1, 1, 0, 40);
    n = gan_tick(&a, 5000, ev);
    CHECK(n == 3 && ev[0].bounce == 0 && ev[1].bounce == 1 && ev[2].type == GAN_EV_FALL_DONE && ev[0].owner == 2);
}

static void test_list_and_pulse_and_shake(void)
{
    gan_t a;
    gan_init(&a);
    for (int i = 0; i < GAN_MAX; i++) CHECK(gan_fall(&a, 0, i, 1, 0, 1, 0, 10) >= 0);
    CHECK(gan_fall(&a, 0, 20, 1, 0, 1, 0, 10) == -1 && gan_flash(&a, 0, 3) == -1);          /* the list is full */
    gan_ev_t ev[GAN_EV_MAX];
    int done = 0;
    for (uint32_t t = 0; t < 2000 && gan_active(&a); t += 30) {
        const int n = gan_tick(&a, t, ev);
        for (int k = 0; k < n; k++) done += ev[k].type == GAN_EV_FALL_DONE;
    }
    CHECK(done == GAN_MAX && !gan_active(&a));
    /* the pulse: three bright phases, then done */
    gan_flash(&a, 100, 7);
    int bright_edges = 0, was = 0;
    int flash_done = 0;
    for (uint32_t t = 100; t < 100 + 1500; t += 10) {
        const int on = gan_flash_on(&a, 7, t);
        if (on && !was) bright_edges++;
        was = on;
        const int n = gan_tick(&a, t, ev);
        for (int k = 0; k < n; k++) flash_done += ev[k].type == GAN_EV_FLASH_DONE;
    }
    CHECK(bright_edges == GAN_FLASH_PULSES && flash_done == 1 && !gan_active(&a) && !gan_flash_on(&a, 7, 5000));
    /* the shake: bounded, decays to zero, ends with one event */
    gan_shake(&a, 0);
    int maxdx = 0, shake_done = 0;
    for (uint32_t t = 0; t < 1000; t += 10) {
        const int dx = gan_shake_dx(&a, t);
        if (dx > maxdx) maxdx = dx;
        CHECK(dx >= -4 && dx <= 4);
        const int n = gan_tick(&a, t, ev);
        for (int k = 0; k < n; k++) shake_done += ev[k].type == GAN_EV_SHAKE_DONE;
    }
    CHECK(maxdx > 0 && shake_done == 1 && !gan_active(&a) && gan_shake_dx(&a, 2000) == 0);
}

static void test_win_line_and_rules_untouched(void)
{
    gc4_board_t g;
    gc4_clear(&g);
    int cells[4];
    CHECK(!gc4_win_line(&g, 1, cells));
    for (int c = 2; c < 6; c++) gc4_drop(&g, c, 1);
    CHECK(gc4_win_line(&g, 1, cells) && cells[0] == 5 * 7 + 2 && cells[3] == 5 * 7 + 5 && gc4_win(&g, 1));
    gc4_clear(&g);
    g.b[5 * 7 + 6] = 2; g.b[4 * 7 + 5] = 2; g.b[3 * 7 + 4] = 2; g.b[2 * 7 + 3] = 2;       /* diagonal */
    CHECK(gc4_win_line(&g, 2, cells) && gc4_win(&g, 2));
    int ok = 0;
    for (int i = 0; i < 4; i++) ok += g.b[cells[i]] == 2;
    CHECK(ok == 4);
    /* every winning position gc4_win finds has a line (random boards) */
    uint32_t rs = 99;
    for (int n = 0; n < 2000; n++) {
        for (int i = 0; i < GC4_CELLS; i++) g.b[i] = (uint8_t)(gr_rand(&rs) % 3u);
        for (int who = 1; who <= 2; who++) CHECK(gc4_win(&g, who) == gc4_win_line(&g, who, cells));
    }
}

static void test_the_input_rule(void)
{
    /* while a disc is falling the person's tap waits; the unit's search starts at the landing: the busy flag follows the fall */
    gan_t a;
    gan_init(&a);
    gan_fall(&a, 0, 30, 1, 4, 4, 0, 100);
    gan_ev_t ev[GAN_EV_MAX];
    int landed = 0;
    for (uint32_t t = 0; t < 600; t += 30) {
        const int busy_before = gan_busy(&a);
        const int n = gan_tick(&a, t, ev);
        for (int k = 0; k < n; k++) if (ev[k].type == GAN_EV_FALL_DONE) landed = 1;
        if (!landed) CHECK(busy_before);                                  /* busy right up to the end */
    }
    CHECK(landed && !gan_busy(&a));
}

static void test_the_new_sounds(void)
{
    static int16_t buf[MGS_SFX_MAX_SAMPLES];
    for (int c = MGS_C_GRID_TICK_LO; c <= MGS_C_GRID_DRAW; c++) {
        const size_t n = mgs_render(c, buf, MGS_SFX_MAX_SAMPLES);
        CHECK(n > 0 && n == mgs_clip_samples(c) && n <= MGS_SFX_MAX_SAMPLES);
        int32_t peak = 0;
        for (size_t i = 0; i < n; i++) { const int32_t v = buf[i] < 0 ? -buf[i] : buf[i]; if (v > peak) peak = v; }
        CHECK(peak > 8000 && peak <= 32767);                                  /* audible, within range */
        CHECK(buf[n - 1] > -300 && buf[n - 1] < 300);                         /* ends in silence */
    }
    CHECK(mgs_clip_samples(MGS_C_GRID_TICK_HI) <= 16 * 60 && mgs_clip_samples(MGS_C_GRID_LOSE) <= 16 * 700);   /* ticks under 60 ms, the loss under 0.7 s */
    CHECK(mgs_clip_samples(MGS_C_GRID_DROP) <= 16 * 100 && MGS_CLIPS == MGS_C_GRID_DRAW + 1);
}

int main(void)
{
    test_fall_math();
    test_list_and_pulse_and_shake();
    test_win_line_and_rules_untouched();
    test_the_input_rule();
    test_the_new_sounds();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("grid anim: all passed\n");
    return 0;
}
