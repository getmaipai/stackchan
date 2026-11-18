/* Host test for the task supervisor rule (patch SF49). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include "maipai_super_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

int main(void)
{
    msv_t m;
    msv_init(&m);
    const int a = msv_add(&m, "reconnect", 10000, 0);
    const int b = msv_add(&m, "tools", 5000, 0);
    CHECK(a == 0 && b == 1);
    CHECK(msv_add(&m, "x", 999, 0) == -1 && msv_add(&m, NULL, 5000, 0) == -1);
    /* healthy tasks that beat in time are left alone */
    for (uint32_t t = 1000; t <= 60000; t += 1000) {
        msv_beat(&m, a, t);
        msv_beat(&m, b, t);
        CHECK(msv_check(&m, t).action == MSV_NONE);
    }
    /* "tools" stops beating at 60000: kick at 65000, restart at 70000, reboot at 75000 */
    msv_beat(&m, a, 60000);
    uint32_t t = 60000;
    int actions[3] = {0, 0, 0}, n = 0;
    uint32_t when[3] = {0, 0, 0};
    for (; t <= 80000 && n < 3; t += 1000) {
        msv_beat(&m, a, t);
        const msv_out_t o = msv_check(&m, t);
        if (o.action != MSV_NONE) {
            CHECK(o.task == b);
            actions[n] = o.action;
            when[n++] = t;
        }
    }
    CHECK(n == 3 && actions[0] == MSV_KICK && actions[1] == MSV_RESTART && actions[2] == MSV_REBOOT);
    CHECK(when[0] == 65000 && when[1] == 70000 && when[2] == 75000);
    CHECK(m.t[b].kicks == 1 && m.t[b].restarts == 1 && m.t[b].reboots == 1 && m.t[a].kicks == 0);
    /* a beat after a kick clears the escalation: the next stall starts again at a kick */
    msv_init(&m);
    const int c = msv_add(&m, "avatar", 4000, 0);
    CHECK(msv_check(&m, 4000).action == MSV_KICK);
    msv_beat(&m, c, 4500);
    CHECK(msv_check(&m, 8499).action == MSV_NONE);
    CHECK(msv_check(&m, 8500).action == MSV_KICK);
    /* a disarmed task is never acted on; arming it again starts a fresh timeout */
    msv_disarm(&m, c);
    CHECK(msv_check(&m, 900000).action == MSV_NONE);
    msv_arm(&m, c, 900000);
    CHECK(msv_check(&m, 903999).action == MSV_NONE && msv_check(&m, 904000).action == MSV_KICK);
    /* the clock wraps: a beat just before the wrap is not stale just after it */
    msv_init(&m);
    const int d = msv_add(&m, "w", 10000, 0xfffff000u);
    msv_beat(&m, d, 0xffffff00u);
    CHECK(msv_check(&m, 0x00000100u).action == MSV_NONE);
    CHECK(msv_check(&m, 0xffffff00u + 10000u).action == MSV_KICK);
    /* the table is bounded */
    msv_init(&m);
    for (int i = 0; i < MSV_MAX; i++) CHECK(msv_add(&m, "t", 5000, 0) == i);
    CHECK(msv_add(&m, "t", 5000, 0) == -1);
    if (failures) return 1;
    printf("super core ok\n");
    return 0;
}
