/* Host test for the camera frames core (patch SF44). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include <string.h>
#include "maipai_avatar_core.h"

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
    char out[160];
    /* the address: same host, the avatar port and path */
    CHECK(mav_url("ws://192.0.2.7:8765/xiaozhi/v1/", out, sizeof(out)) && !strcmp(out, "ws://192.0.2.7:8766/stackChan/ws?deviceType=StackChan"));
    CHECK(mav_url("ws://home.example.com/xiaozhi/v1/", out, sizeof(out)) && !strcmp(out, "ws://home.example.com:8766/stackChan/ws?deviceType=StackChan"));
    CHECK(mav_url("ws://[2001:db8::7]:8765/x", out, sizeof(out)) && !strcmp(out, "ws://[2001:db8::7]:8766/stackChan/ws?deviceType=StackChan"));
    CHECK(mav_url("ws://192.0.2.7", out, sizeof(out)) && !strcmp(out, "ws://192.0.2.7:8766/stackChan/ws?deviceType=StackChan"));
    /* refused: no scheme, a TLS address, no host, a user part, a space, null, a buffer that is too small */
    CHECK(!mav_url("192.0.2.7:8765", out, sizeof(out)) && out[0] == 0);
    CHECK(!mav_url("wss://192.0.2.7:18775/x", out, sizeof(out)) && out[0] == 0);
    CHECK(!mav_url("ws:///x", out, sizeof(out)));
    CHECK(!mav_url("ws://user@192.0.2.7:8765/x", out, sizeof(out)));
    CHECK(!mav_url("ws://192.0.2.7 :8765/x", out, sizeof(out)));
    CHECK(!mav_url("ws://[2001:db8::7/x", out, sizeof(out)));
    CHECK(!mav_url(NULL, out, sizeof(out)) && !mav_url("ws://a/x", NULL, 10) && !mav_url("ws://a/x", out, 0));
    CHECK(!mav_url("ws://192.0.2.7:8765/x", out, 20));
    /* the gate: each privacy rule on its own stops the stream, in a fixed order; memory has hysteresis */
    CHECK(mav_gate(0, 0, 0, 0, 30000, 0, 0) == MAV_OK);
    CHECK(mav_gate(1, 0, 0, 0, 30000, 0, 0) == MAV_VISION_OFF);
    CHECK(mav_gate(0, 1, 0, 0, 30000, 0, 0) == MAV_MUTED);
    CHECK(mav_gate(0, 0, 1, 0, 30000, 0, 0) == MAV_LOCKED);
    CHECK(mav_gate(0, 0, 0, 1, 30000, 0, 0) == MAV_QUIET);
    CHECK(mav_gate(1, 1, 1, 1, 30000, 1, 1) == MAV_VISION_OFF);
    CHECK(mav_gate(0, 0, 0, 0, 19999, 0, 0) == MAV_MEMORY);   /* not started: needs 20,000 */
    CHECK(mav_gate(0, 0, 0, 0, 19999, 1, 0) == MAV_OK);       /* running: stops only under 16,000 */
    CHECK(mav_gate(0, 0, 0, 0, 15999, 1, 0) == MAV_MEMORY);
    CHECK(mav_gate(0, 0, 0, 0, 30000, 1, 1) == MAV_BUSY);
    /* every privacy rule beats memory and a busy camera: no frame is ever taken under a rule */
    for (int mask = 1; mask < 16; mask++) {
        CHECK(mav_gate(mask & 1, (mask >> 1) & 1, (mask >> 2) & 1, (mask >> 3) & 1, 0, 0, 1) != MAV_OK);
    }
    /* the counters */
    mav_t m;
    memset(&m, 0, sizeof(m));
    mav_note(&m, MAV_OK, 5);
    mav_note(&m, MAV_MUTED, 6);
    mav_note(&m, MAV_MUTED, 7);
    mav_note(&m, 99, 8);
    CHECK(m.sent == 1 && m.skipped[MAV_MUTED] == 2 && m.last_sent_ms == 5);
    if (failures) return 1;
    printf("avatar core ok\n");
    return 0;
}
