/* Host test for the dance ladder (patch MD01): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header> dance_ladder_test.c
 *   dance_ladder_test                run the built-in checks
 *   dance_ladder_test script FILE    run a script (one line per second: max_stage now_ms period level tc music, a line starting with
 *                                    "start" begins a cycle) and print the stage of every second, for the host's mirror to compare */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maipai_dance_ladder_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static int run_script(const char* path)
{
    FILE* f = fopen(path, "r");
    if (!f) return 2;
    char line[256];
    mdl_t s;
    mdl_energy_t e;
    memset(&s, 0, sizeof(s));
    mdl_energy_reset(&e);
    while (fgets(line, sizeof(line), f)) {
        unsigned now, period;
        int max_stage, level, tc, music;
        if (strncmp(line, "start", 5) == 0) {
            if (sscanf(line + 5, "%d %u", &max_stage, &now) == 2) {
                mdl_start(&s, max_stage, now);
                mdl_energy_reset(&e);
            }
            continue;
        }
        if (sscanf(line, "%u %u %d %d %d", &now, &period, &level, &tc, &music) != 5) continue;
        mdl_in_t in = {now, period, mdl_energy_push(&e, level), tc, music};
        printf("%d\n", mdl_step(&s, &in));
    }
    fclose(f);
    return 0;
}

/* one second steps of steady music: returns the stage sequence as a string of digits */
static void run_steady(char* out, int seconds, uint32_t period, int level, int tc, int max_stage)
{
    mdl_t s;
    mdl_energy_t e;
    mdl_energy_reset(&e);
    mdl_start(&s, max_stage, 1000u);
    for (int t = 0; t < seconds; t++) {
        mdl_in_t in = {1000u + (uint32_t)(t + 1) * 1000u, period, mdl_energy_push(&e, level), tc, 1};
        out[t] = (char)('0' + mdl_step(&s, &in));
    }
    out[seconds] = 0;
}

int main(int argc, char** argv)
{
    if (argc == 3 && strcmp(argv[1], "script") == 0) return run_script(argv[2]);

    /* dwell: eyes about 1.5 s at 120 BPM, a step 4 s, the peak 12 s, the way down 2 s */
    CHECK(mdl_dwell_ms(1, 0, 500) == 1500u);
    CHECK(mdl_dwell_ms(1, 0, 250) == 1500u);  /* very fast: not shorter than 1.5 s */
    CHECK(mdl_dwell_ms(1, 0, 2000) == 3000u); /* very slow: not longer than 3 s */
    CHECK(mdl_dwell_ms(2, 0, 500) == 4000u);
    CHECK(mdl_dwell_ms(3, 0, 1000) == 8000u);
    CHECK(mdl_dwell_ms(4, 0, 500) == 12000u);
    CHECK(mdl_dwell_ms(4, 0, 1000) == 20000u);
    CHECK(mdl_dwell_ms(3, 1, 500) == 2000u);
    CHECK(mdl_dwell_ms(2, 1, 0) == 2400u); /* no beat known: 600 ms */

    /* a loud steady song climbs 1, 2, 3, 4, holds the peak, then goes back 3, 2, 1 and ends: the stage never skips upward */
    char seq[200];
    run_steady(seq, 100, 500, 1800, 70, 4);
    int last = 0, max = 0, peaked = 0, ended = 0;
    for (int i = 0; i < 100; i++) {
        const int st = seq[i] - '0';
        if (st > last) CHECK(st == last + 1 || last == 0);
        if (peaked && st > last) CHECK(0); /* no climb after the way down began */
        if (st == 4) peaked = 1;
        if (st > max) max = st;
        if (peaked && st < 4 && st > 0) peaked = 1;
        if (st == 0 && i > 0 && last == 1) ended = 1;
        last = st;
    }
    CHECK(max == 4);
    CHECK(ended);
    CHECK(seq[0] == '1');
    CHECK(strchr(seq, '4') != NULL && strchr(seq, '3') != NULL);
    /* the way down is 3, 2, 1 in that order after the peak */
    const char* p4 = strrchr(seq, '4');
    CHECK(p4 != NULL);
    int d3 = -1, d2 = -1, d1 = -1, d0 = -1;
    for (int i = (int)(p4 - seq); i < 100; i++) {
        if (seq[i] == '3' && d3 < 0) d3 = i;
        if (seq[i] == '2' && d2 < 0) d2 = i;
        if (seq[i] == '1' && d1 < 0) d1 = i;
        if (seq[i] == '0' && d0 < 0) d0 = i;
    }
    CHECK(d3 > 0 && d2 > d3 && d1 > d2 && d0 > d1);

    /* the eyes first: stage 1 for about 1.5 s before any head movement */
    CHECK(seq[0] == '1'); /* one second in: still only the eyes */
    CHECK(seq[1] == '2'); /* two seconds in: the 1.5 s of eyes are over and the head nods */

    /* a quiet song stays at the nod: the level is too low for sway */
    run_steady(seq, 30, 500, 500, 70, 4);
    CHECK(strchr(seq, '3') == NULL && strchr(seq, '2') != NULL);
    /* a song with no steady beat stays on the eyes */
    run_steady(seq, 12, 500, 1800, 10, 4);
    CHECK(strchr(seq, '2') == NULL);
    /* a cycle that may only nod (a low battery) never sways and goes back down */
    run_steady(seq, 60, 500, 1800, 70, 2);
    CHECK(strchr(seq, '3') == NULL && strchr(seq, '4') == NULL && seq[59] == '0');

    /* music that stops in the middle winds down at once: three seconds, then one step every two */
    {
        mdl_t s;
        mdl_energy_t e;
        mdl_energy_reset(&e);
        mdl_start(&s, 4, 0u);
        int stage = 0, t = 0;
        for (; t < 30; t++) { /* climb with music */
            mdl_in_t in = {(uint32_t)(t + 1) * 1000u, 500u, mdl_energy_push(&e, 1800), 70, 1};
            stage = mdl_step(&s, &in);
            if (stage == 4) break;
        }
        CHECK(stage == 4);
        int first_drop = -1;
        for (int k = 1; k <= 20; k++) {
            mdl_in_t in = {(uint32_t)(t + 1 + k) * 1000u, 500u, mdl_energy_push(&e, 0), 0, 0};
            stage = mdl_step(&s, &in);
            if (stage < 4 && first_drop < 0) first_drop = k;
        }
        CHECK(first_drop >= 3 && first_drop <= 6);
        CHECK(stage == 0);
    }

    /* the cycle ends by itself after the cap even if nothing changes, once it has no higher step to go to */
    {
        mdl_t s;
        mdl_start(&s, 1, 0u);
        mdl_in_t in = {1500u, 500u, 1800, 70, 1};
        CHECK(mdl_step(&s, &in) == 1);
        in.now_ms = 2000u; /* 3 beats at 500 ms is the 1.5 s floor: with no higher step allowed the way back begins */
        mdl_step(&s, &in);
        CHECK(s.down == 1);
    }

    /* the motion of each step */
    mdl_pose_t p = mdl_pose(1, 1, 0, 500, 0);
    CHECK(p.eye_x == 100 && p.head == 0 && p.yaw == 0 && p.pitch == 0); /* eyes only */
    p = mdl_pose(1, -1, 1, 500, 0);
    CHECK(p.eye_x == -100 && p.head == 0);
    p = mdl_pose(2, 1, 0, 500, 0);
    CHECK(p.head == 1 && p.yaw == 0 && p.pitch == -170 && p.eye_x == 40); /* a nod: pitch only */
    p = mdl_pose(2, -1, 1, 500, 0);
    CHECK(p.pitch == -40);
    p = mdl_pose(3, 1, 0, 700, 0);
    CHECK(p.head == 1 && p.yaw == 300 && p.pitch == -100 && p.eye_x == 100); /* sway: yaw, the head steady */
    p = mdl_pose(3, -1, 1, 500, 0);
    CHECK(p.yaw == -200 && p.speed >= 220 && p.speed <= 600);
    p = mdl_pose(4, 1, 0, 700, 0);
    CHECK(p.head == 1 && p.yaw == 300 && p.pitch == -30 && p.eye_y == 30); /* full: yaw and pitch together */
    p = mdl_pose(4, -1, 2, 700, 0);
    CHECK(p.yaw == -300 && p.pitch == -170 && p.eye_y == -30);
    p = mdl_pose(4, 1, 0, 400, 1);
    CHECK(p.speed <= 600);
    p = mdl_pose(0, 1, 0, 500, 0);
    CHECK(p.head == 0 && p.eye_x == 0);
    /* every pose stays inside the limits the shipped dances use (yaw 600, pitch -300..250, speed 50..1000, eyes 100) */
    for (int st = 0; st <= 4; st++)
        for (int side = -1; side <= 1; side += 2)
            for (int beat = 0; beat < 4; beat++)
                for (uint32_t span = 250; span <= 2000; span += 125)
                    for (int loud = 0; loud < 2; loud++) {
                        p = mdl_pose(st, side, beat, span, loud);
                        CHECK(p.yaw >= -600 && p.yaw <= 600 && p.pitch >= -300 && p.pitch <= 250);
                        CHECK(p.speed >= 50 && p.speed <= 1000);
                        CHECK(p.eye_x >= -100 && p.eye_x <= 100 && p.eye_y >= -100 && p.eye_y <= 100);
                    }
    /* no beat for 3 s: the full dance and the sway drop to the nod */
    CHECK(mdl_effective_stage(4, 0) == 4 && mdl_effective_stage(4, 3000) == 2 && mdl_effective_stage(3, 5000) == 2);
    CHECK(mdl_effective_stage(1, 9000) == 1 && mdl_effective_stage(2, 9000) == 2);

    /* the head budget: 90 moves in a minute, the 91st waits for the oldest to age out */
    {
        mdl_budget_t b;
        mdl_budget_reset(&b);
        int taken = 0;
        for (int i = 0; i < 100; i++) taken += mdl_budget_take(&b, 1000u + (uint32_t)i * 100u); /* 10 moves a second */
        CHECK(taken == 90);
        CHECK(mdl_budget_take(&b, 1000u + 60000u - 1u) == 0);
        CHECK(mdl_budget_take(&b, 1000u + 60000u) == 1);
        /* a steady one move per 450 ms is 133 a minute: the budget lets about 90 of them through */
        mdl_budget_reset(&b);
        taken = 0;
        for (int i = 0; i < 134; i++) taken += mdl_budget_take(&b, 1u + (uint32_t)i * 450u);
        CHECK(taken < 134 && taken >= 90);
    }

    /* the ring swell: smooth (no big step between 10 ms samples), 0 to 255, and the ring stays under half of full */
    {
        int prev = mdl_swell(0, 500), maxstep = 0, hi = 0, lo = 255;
        for (uint32_t t = 10; t <= 1000; t += 10) {
            const int v = mdl_swell(t, 500);
            const int d = v > prev ? v - prev : prev - v;
            if (d > maxstep) maxstep = d;
            if (v > hi) hi = v;
            if (v < lo) lo = v;
            prev = v;
        }
        CHECK(hi <= 255 && hi >= 250 && lo >= 0 && lo <= 5);
        CHECK(maxstep <= 25); /* at most about 10 percent of the range in 10 ms: a swell, never a flash */
        uint8_t px[MDL_RING_PIXELS][3];
        int brightest = 0;
        for (int swell = 0; swell <= 255; swell += 5)
            for (int side = -1; side <= 1; side += 2)
                for (uint32_t turn = 0; turn < 3; turn++) {
                    mdl_ring_frame(px, swell, side, turn);
                    int lit = 0;
                    for (int i = 0; i < MDL_RING_PIXELS; i++) {
                        for (int k = 0; k < 3; k++) {
                            CHECK(px[i][k] <= MDL_RING_CHANNEL_MAX * MDL_RING_CAP_PCT / 100);
                            if (px[i][k] > brightest) brightest = px[i][k];
                        }
                        if (px[i][0] || px[i][1] || px[i][2]) lit++;
                    }
                    CHECK(lit == MDL_RING_PIXELS);
                }
        CHECK(brightest > 60);
        /* the step from the quietest to the loudest frame is under 20 percent of full: 0.30 to 0.50 */
        uint8_t a[MDL_RING_PIXELS][3], b[MDL_RING_PIXELS][3];
        mdl_ring_frame(a, 0, 1, 0);
        mdl_ring_frame(b, 255, 1, 0);
        CHECK(b[0][0] - a[0][0] <= MDL_RING_CHANNEL_MAX * 25 / 100);
    }

    /* the energy average of four seconds */
    {
        mdl_energy_t e;
        mdl_energy_reset(&e);
        CHECK(mdl_energy_push(&e, 1000) == 1000);
        CHECK(mdl_energy_push(&e, 2000) == 1500);
        mdl_energy_push(&e, 3000);
        mdl_energy_push(&e, 4000);
        CHECK(mdl_energy_push(&e, 5000) == 3500);
    }

    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
