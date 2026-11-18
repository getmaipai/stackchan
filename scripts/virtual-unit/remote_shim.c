/* The unit's own remote session rules (maipai_remote_core.h, patches TC01, FM03, SF01) on the command line, so a scenario asks the unit's code, not a copy of it.
 * Lines on stdin: `session ACTIVE HOST NOW` (the host's self.remote.session heartbeat; HOST is the id it announces, 0 for none),
 * `call KIND TOKEN NOW` (a call with no source "remote", as the paired host's own page or a voice turn makes it): prints the reason name, `ok` when it passes.
 * `host` prints the id the unit keeps for the session. Build: cc -std=gnu99 -I<dir with the headers> remote_shim.c -o remote_shim.
 * Placement: host-side development tool; no firmware change. Upstream: none. */
#include <stdio.h>
#include <string.h>
#include "maipai_remote_core.h"

int main(void)
{
    mr_t r;
    char cmd[16], kind[16];
    unsigned active, host, token, now;
    mr_init(&r);
    while (scanf("%15s", cmd) == 1) {
        if (!strcmp(cmd, "session") && scanf("%u %u %u", &active, &host, &now) == 3) {
            mr_session(&r, (int)active, "remote", now);
            if (active) mr_set_host(&r, host);
            printf("active=%d host=%u\n", mr_session_on(&r, now), (unsigned)r.host_id);
        } else if (!strcmp(cmd, "call") && scanf("%15s %u %u", kind, &token, &now) == 3) {
            printf("%s\n", MR_REASONS[mr_gate_call(&r, NULL, kind, token, now)]);
        } else if (!strcmp(cmd, "host")) {
            printf("%u\n", (unsigned)r.host_id);
        } else {
            printf("error\n");
        }
        fflush(stdout);
    }
    return 0;
}
