/* Harness for the first-boot trial rule (patch FM01): plays boots through the real muc_boot and muc_step and prints when each is decided.
 * Usage: update_trial host_up(0|1) camera_at_s(-1 never) loop_alive(0|1) lifetime_s    prints "KEEP_HOST|KEEP_QUIET|ROLLBACK|WAIT at <s>" */
#include <stdio.h>
#include <stdlib.h>
#include "maipai_update_core.h"

int main(int argc, char** argv)
{
    if (argc != 5) { printf("usage: update_trial host_up camera_at_s loop_alive lifetime_s\n"); return 2; }
    const int host_up = atoi(argv[1]), camera_at = atoi(argv[2]), alive = atoi(argv[3]), life = atoi(argv[4]);
    muc_trial_t t = {0};
    bool dirty;
    muc_boot(&t, true, false, &dirty);  /* first boot after a wireless install */
    static const char* names[] = {"IDLE", "WAIT", "KEEP_HOST", "KEEP_QUIET", "ROLLBACK"};
    for (int s = 0; s <= life; s++) {
        muc_step_t r = muc_step(&t, (uint32_t)s, camera_at >= 0 && s >= camera_at, alive != 0, host_up != 0, &dirty);
        if (r != MUC_STEP_WAIT) { printf("%s at %d\n", names[r], s); return 0; }
    }
    printf("WAIT at %d\n", life);
    return 0;
}
