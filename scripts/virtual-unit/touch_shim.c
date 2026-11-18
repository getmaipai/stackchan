/* A command line wrapper around the unit's own touch gesture core (maipai_touch_core.h, patches 105, L07 and the owner default of decision 3), so the virtual unit decides
 * taps and holds with the unit's code. Reads lines on stdin: `down X Y MS`, `move X Y MS`, `up MS`, `reset`. Prints one line per `up`:
 * `kind=tap|hold|drag|none region=N result=none|toggle:mute|toggle:vision|toggle:quiet|ignored:mute|...` with the display handler's own rule (patch SF02): a tap or a hold in a switch region names the switch, and the
 * touch counts only when mtc_toggle_ok(kind, switch_is_on): a tap turns a switch on, a hold turns it off. `up MS M V Q` gives the three switches' state now (1 on).
 * Build: cc -std=gnu99 -I<dir with the headers> touch_shim.c -o touch_shim. Placement: host-side development tool; no firmware change. Upstream: none. */
#include <stdio.h>
#include <string.h>
#include "maipai_touch_core.h"

static const char* KIND[] = {"none", "tap", "hold", "drag"};
static const char* ACT[] = {"none", "mute", "vision", "quiet"};

int main(void)
{
    mtc_trace_t t;
    char cmd[16];
    int x, y;
    unsigned ms = 0;
    memset(&t, 0, sizeof t);
    while (scanf("%15s", cmd) == 1) {
        if (!strcmp(cmd, "down")) {
            scanf("%d %d %u", &x, &y, &ms);
            mtc_begin(&t, x, y, ms);
        } else if (!strcmp(cmd, "move")) {
            scanf("%d %d %u", &x, &y, &ms);
            mtc_move(&t, x, y, ms);
        } else if (!strcmp(cmd, "up")) {
            int on[4] = {0, 0, 0, 0};
            scanf("%u %d %d %d", &ms, &on[1], &on[2], &on[3]);
            mtc_move(&t, t.x, t.y, ms);
            const mtc_kind_t k = mtc_classify(&t);
            const mtc_action_t a = (k == MTC_KIND_TAP || k == MTC_KIND_HOLD) ? mtc_action_for(t.region0, MTC_KIND_TAP) : MTC_ACTION_NONE;
            const char* what = a == MTC_ACTION_NONE ? "none" : mtc_toggle_ok(k, on[a]) ? "toggle" : "ignored";
            printf("kind=%s region=%d result=%s:%s\n", KIND[k], (int)t.region0, what, ACT[a]);
            fflush(stdout);
        }
    }
    return 0;
}
