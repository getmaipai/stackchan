/* Host test for the first-boot trial rule (patch FM01): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>.
 * Each scenario is a script of boots; run_boot plays one boot with a given uptime and link, as the unit's timer would. */
#include <stdio.h>
#include "maipai_update_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

/* The record as flash keeps it between boots. */
static muc_trial_t flash;

/* One boot: ends when the trial is decided or `lifetime_s` seconds pass (a crash or a power cut). camera_at_s is the
 * second the camera settles (negative: it never does in this boot). Returns the last step. */
static muc_step_t run_boot(int lifetime_s, int camera_at_s, bool host_up_from_start, bool loop_alive)
{
    muc_step_t last = MUC_STEP_WAIT;
    for (int s = 0; s <= lifetime_s; s++) {
        bool dirty;
        bool cam = camera_at_s >= 0 && s >= camera_at_s;
        last = muc_step(&flash, (uint32_t)s, cam, loop_alive, host_up_from_start, &dirty);
        if (last != MUC_STEP_WAIT) {
            return last;
        }
    }
    return last;
}

static muc_boot_t boot(bool pending, bool crash)
{
    bool dirty;
    return muc_boot(&flash, pending, crash, &dirty);
}

int main(void)
{
    /* A unit with no trial open stays idle through crashes and restarts. */
    flash = (muc_trial_t){0};
    CHECK(boot(false, true) == MUC_BOOT_IDLE);
    CHECK(muc_boot(&flash, false, false, &(bool){false}) == MUC_BOOT_IDLE);

    /* Good install with the host: kept at 20 s, never before. */
    flash = (muc_trial_t){0};
    CHECK(boot(true, false) == MUC_BOOT_START);
    CHECK(flash.active == 1 && flash.boots == 1);
    CHECK(run_boot(19, 3, true, true) == MUC_STEP_WAIT);
    CHECK(run_boot(25, 3, true, true) == MUC_STEP_KEEP_HOST);
    CHECK(flash.active == 0);
    CHECK(boot(false, true) == MUC_BOOT_IDLE); /* a later crash is not this trial's business */

    /* A trip: no host at all. Kept at 60 s, not at 20 s (patch 160 rolled this image back at 60 s). */
    flash = (muc_trial_t){0};
    CHECK(boot(true, false) == MUC_BOOT_START);
    CHECK(run_boot(59, 3, false, true) == MUC_STEP_WAIT);
    CHECK(run_boot(61, 3, false, true) == MUC_STEP_KEEP_QUIET);
    CHECK(flash.active == 0);

    /* The vendor camera panic on three cold boots before the camera settles, then a good boot: kept. */
    flash = (muc_trial_t){0};
    CHECK(boot(true, false) == MUC_BOOT_START);
    for (int i = 0; i < MUC_FREE_PASSES; i++) {
        CHECK(run_boot(1, -1, false, true) == MUC_STEP_WAIT); /* dies at 1 s, camera never settled */
        CHECK(boot(false, true) == MUC_BOOT_CONTINUE);
        CHECK(flash.strikes == 0);
    }
    CHECK(flash.free_passes == MUC_FREE_PASSES);
    CHECK(run_boot(70, 3, false, true) == MUC_STEP_KEEP_QUIET);

    /* A fourth early crash is no longer free: it is a strike; a fifth rolls back. Early crashes cannot go on forever. */
    flash = (muc_trial_t){0};
    CHECK(boot(true, false) == MUC_BOOT_START);
    for (int i = 0; i < MUC_FREE_PASSES; i++) {
        (void)run_boot(1, -1, false, true);
        CHECK(boot(false, true) == MUC_BOOT_CONTINUE);
    }
    (void)run_boot(1, -1, false, true);
    CHECK(boot(false, true) == MUC_BOOT_CONTINUE);
    CHECK(flash.strikes == 1);
    (void)run_boot(1, -1, false, true);
    CHECK(boot(false, true) == MUC_BOOT_ROLLBACK);

    /* Two crashes after the camera settled: the image's own fault, roll back at the second one. */
    flash = (muc_trial_t){0};
    CHECK(boot(true, false) == MUC_BOOT_START);
    (void)run_boot(10, 3, true, true); /* camera settled at 3 s, crash at 10 s */
    CHECK(flash.stage == 1);
    CHECK(boot(false, true) == MUC_BOOT_CONTINUE);
    CHECK(flash.strikes == 1 && flash.stage == 0);
    (void)run_boot(10, 3, true, true);
    CHECK(boot(false, true) == MUC_BOOT_ROLLBACK);

    /* A power cut or a software restart in the trial is no fault. */
    flash = (muc_trial_t){0};
    CHECK(boot(true, false) == MUC_BOOT_START);
    for (int i = 0; i < 6; i++) {
        (void)run_boot(8, 3, false, true);
        CHECK(boot(false, false) == MUC_BOOT_CONTINUE);
        CHECK(flash.strikes == 0 && flash.free_passes == 0);
    }
    CHECK(run_boot(65, 3, false, true) == MUC_STEP_KEEP_QUIET);

    /* A main loop that never runs (a hang) keeps nothing, and the stall rule rolls back at 120 s. */
    flash = (muc_trial_t){0};
    CHECK(boot(true, false) == MUC_BOOT_START);
    CHECK(run_boot(119, 3, true, false) == MUC_STEP_WAIT);
    CHECK(run_boot(125, 3, true, false) == MUC_STEP_ROLLBACK);

    /* A camera init that never returns (never settled) is not kept either. */
    flash = (muc_trial_t){0};
    CHECK(boot(true, false) == MUC_BOOT_START);
    CHECK(run_boot(119, -1, true, true) == MUC_STEP_WAIT);
    CHECK(run_boot(125, -1, true, true) == MUC_STEP_ROLLBACK);

    /* A new install while an old trial record lingers starts clean. */
    flash = (muc_trial_t){.active = 1, .strikes = 1, .free_passes = 2, .stage = 1, .boots = 9};
    CHECK(boot(true, false) == MUC_BOOT_START);
    CHECK(flash.strikes == 0 && flash.free_passes == 0 && flash.stage == 0 && flash.boots == 1);

    if (failures == 0) {
        printf("update_core_test: all passed\n");
    }
    return failures == 0 ? 0 : 1;
}
