/* Host test for the Wi-Fi roam rules (patch RM01): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include "maipai_roam_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

/* Runs the timer every MR_TICK_MS with a fixed reading from `from` to `to` (ms); returns the time of the first scan or -1. */
static int64_t run(mr_state_t* s, int64_t from, int64_t to, int rssi, int busy)
{
    for (int64_t t = from; t <= to; t += MR_TICK_MS) {
        if (mr_tick(s, t, 1, rssi, busy) == MR_SCAN) {
            return t;
        }
    }
    return -1;
}

int main(void)
{
    mr_state_t s;

    /* A strong signal never scans, however long it lasts. */
    mr_init(&s);
    CHECK(run(&s, 0, 600000, -50, 0) == -1);
    CHECK(run(&s, 600000, 900000, -69, 0) == -1); /* -69 is not weak (weak is below -70) */
    CHECK(run(&s, 900000, 1200000, -70, 0) == -1); /* -70 itself is not below -70 */

    /* The 10 second timer: weak for 10 s scans on the first tick at or after 10 s, not before. */
    mr_init(&s);
    CHECK(mr_tick(&s, 0, 1, -77, 0) == MR_IDLE);
    CHECK(mr_tick(&s, 8000, 1, -77, 0) == MR_IDLE);
    CHECK(mr_tick(&s, 9999, 1, -77, 0) == MR_IDLE);
    CHECK(mr_tick(&s, 10000, 1, -77, 0) == MR_SCAN);

    /* After a scan: nothing for a minute, then the next one needs another 10 weak seconds (so the minute rules). */
    CHECK(run(&s, 12000, 69999, -77, 0) == -1);
    CHECK(run(&s, 70000, 120000, -77, 0) == 70000);
    CHECK(mr_tick(&s, 70000, 1, -77, 0) == MR_IDLE); /* the same instant again: cool-down just started */

    /* Hysteresis: a reading that comes back to -68 or -69 does not restart the count; a reading above -67 does. */
    mr_init(&s);
    CHECK(mr_tick(&s, 0, 1, -75, 0) == MR_IDLE);
    CHECK(mr_tick(&s, 4000, 1, -69, 0) == MR_IDLE); /* in the band: still weak */
    CHECK(mr_tick(&s, 6000, 1, -68, 0) == MR_IDLE);
    CHECK(mr_tick(&s, 10000, 1, -72, 0) == MR_SCAN); /* 10 s since the first weak reading */
    mr_init(&s);
    CHECK(mr_tick(&s, 0, 1, -75, 0) == MR_IDLE);
    CHECK(mr_tick(&s, 4000, 1, -66, 0) == MR_IDLE); /* above -67: clear */
    CHECK(mr_tick(&s, 6000, 1, -75, 0) == MR_IDLE); /* weak again: the count starts at 6 s */
    CHECK(mr_tick(&s, 10000, 1, -75, 0) == MR_IDLE);
    CHECK(mr_tick(&s, 15999, 1, -75, 0) == MR_IDLE);
    CHECK(mr_tick(&s, 16000, 1, -75, 0) == MR_SCAN);

    /* A band reading never starts a weak period by itself. */
    mr_init(&s);
    CHECK(run(&s, 0, 300000, -68, 0) == -1);

    /* No scan while a turn is going on, and the scan goes right after it when the signal is still weak. */
    mr_init(&s);
    CHECK(run(&s, 0, 120000, -80, 1) == -1);       /* a two minute turn */
    CHECK(mr_tick(&s, 122000, 1, -80, 0) == MR_SCAN); /* idle again: at once */
    mr_init(&s);
    CHECK(run(&s, 0, 120000, -80, 1) == -1);
    CHECK(mr_tick(&s, 122000, 1, -60, 0) == MR_IDLE); /* it got better during the turn: no scan */
    CHECK(run(&s, 124000, 400000, -60, 0) == -1);

    /* Not connected, or no reading: nothing to roam from, and the weak count is dropped. */
    mr_init(&s);
    CHECK(mr_tick(&s, 0, 1, -80, 0) == MR_IDLE);
    CHECK(mr_tick(&s, 6000, 0, -80, 0) == MR_IDLE);
    CHECK(mr_tick(&s, 12000, 1, -80, 0) == MR_IDLE); /* weak count restarted at 12 s */
    CHECK(mr_tick(&s, 20000, 1, 0, 0) == MR_IDLE);   /* unknown reading */
    CHECK(mr_tick(&s, 24000, 1, -80, 0) == MR_IDLE);
    CHECK(mr_tick(&s, 34000, 1, -80, 0) == MR_SCAN);

    /* The least that can happen to a weak unit that never gets idle: scans never closer than a minute. */
    mr_init(&s);
    int64_t last = -1000000;
    int scans = 0;
    for (int64_t t = 0; t <= 1800000; t += MR_TICK_MS) {
        if (mr_tick(&s, t, 1, -85, 0) == MR_SCAN) {
            CHECK(t - last >= MR_COOLDOWN_MS);
            last = t;
            scans++;
        }
    }
    CHECK(scans >= 25 && scans <= 30); /* about one a minute for half an hour */

    /* The choice: same name, another address, at least 8 dB stronger. */
    const uint8_t cur[6] = {1, 2, 3, 4, 5, 6};
    mr_ap_t aps[4];
    memset(aps, 0, sizeof(aps));
    aps[0].rssi = -80; memcpy(aps[0].bssid, cur, 6); aps[0].same_ssid = 1;           /* the one we are on */
    aps[1].rssi = -45; aps[1].bssid[0] = 9; aps[1].same_ssid = 0;                     /* another network: never */
    aps[2].rssi = -60; aps[2].bssid[0] = 7; aps[2].same_ssid = 1;                     /* the candidate */
    aps[3].rssi = -72; aps[3].bssid[0] = 8; aps[3].same_ssid = 1;
    CHECK(mr_pick(-77, cur, aps, 4) == 2);        /* the strongest of the same name, 17 dB better */
    CHECK(mr_pick(-68, cur, aps, 4) == 2);        /* exactly 8 dB better: taken */
    CHECK(mr_pick(-67, cur, aps, 4) == -1);       /* 7 dB better: not worth it */
    CHECK(mr_pick(-77, cur, aps, 1) == -1);       /* only the current one in the list */
    CHECK(mr_pick(-77, cur, aps, 0) == -1);       /* empty scan */
    aps[2].same_ssid = 0;
    CHECK(mr_pick(-80, cur, aps, 4) == 3);        /* next best of the same name */
    CHECK(mr_pick(-75, cur, aps, 4) == -1);       /* -72 is only 3 dB better */

    if (failures == 0) {
        printf("all passed\n");
        return 0;
    }
    return 1;
}
