/* Host test for the infrared timing rules (patch SF50). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include "maipai_ir_core.h"

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
    uint32_t d[MIR_MAX_DURATIONS];
    /* encode then decode every address and command: they come back, inverted bytes match */
    for (unsigned a = 0; a < 256; a += 5) {
        for (unsigned c = 0; c < 256; c += 7) {
            const int n = mir_nec_encode(a, c, d);
            CHECK(n == MIR_NEC_FRAME_DURATIONS);
            unsigned ra = 999, rc = 999;
            int inv = 0;
            CHECK(mir_nec_decode(d, n, &ra, &rc, &inv) == 1 && ra == a && rc == c && inv == 1);
        }
    }
    /* known frame: address 0x00, command 0x08 starts with the leader and the first bit marks */
    const int n0 = mir_nec_encode(0x00, 0x08, d);
    CHECK(n0 == 68 && d[0] == 9000 && d[1] == 4500 && d[2] == 560 && d[3] == 560);
    CHECK(mir_nec_encode(256, 0, d) == 0 && mir_nec_encode(0, 256, d) == 0 && mir_nec_encode(0, 0, NULL) == 0);
    /* a frame within the tolerance still decodes; one outside does not */
    mir_nec_encode(0x20, 0xdf, d);
    for (int i = 0; i < 66; i++) d[i] = d[i] * 110u / 100u;  /* 10 percent slow */
    unsigned a, c;
    int inv;
    CHECK(mir_nec_decode(d, 68, &a, &c, &inv) == 1 && a == 0x20 && c == 0xdf);
    mir_nec_encode(0x20, 0xdf, d);
    d[10] = d[10] * 2u;                                   /* a bit that is neither 0 nor 1 */
    CHECK(mir_nec_decode(d, 68, &a, &c, &inv) == 0);
    /* a repeat frame, a short list, garbage */
    uint32_t rep[3] = {9000, 2250, 560};
    CHECK(mir_nec_decode(rep, 3, &a, &c, &inv) == 2);
    CHECK(mir_nec_decode(rep, 2, &a, &c, &inv) == 0);
    uint32_t junk[4] = {100, 100, 100, 100};
    CHECK(mir_nec_decode(junk, 4, &a, &c, &inv) == 0 && mir_nec_decode(NULL, 4, &a, &c, &inv) == 0);
    /* a frame whose inverted bytes do not match is decoded but flagged */
    mir_nec_encode(0x10, 0x20, d);
    d[3 + 2 * 8] = (d[3 + 2 * 8] == MIR_NEC_ZERO_SPACE) ? MIR_NEC_ONE_SPACE : MIR_NEC_ZERO_SPACE; /* flip an inverted-address bit */
    CHECK(mir_nec_decode(d, 68, &a, &c, &inv) == 1 && inv == 0);
    /* the limits */
    const int n = mir_nec_encode(0, 8, d);
    CHECK(mir_mark_total(d, n) == 9000u + 33u * 560u);
    CHECK(mir_tx_allowed(d, n, 0, 100000, 80, 0) == MIR_OK);
    CHECK(mir_tx_allowed(d, n, 3, 100000, 80, 0) == MIR_OK);          /* 4 frames of 27,480 us marks: 109,920, under 120,000 */
    CHECK(mir_tx_allowed(d, n, 2, 100000, 80, 0) == MIR_OK);          /* 3 frames: 82,440 us */
    uint32_t two[4] = {9000, 4500, 40000, 1000};                       /* 49,000 us of marks: two frames pass, three do not */
    CHECK(mir_tx_allowed(two, 4, 1, 100000, 80, 0) == MIR_OK && mir_tx_allowed(two, 4, 2, 100000, 80, 0) == MIR_TOO_LONG);
    CHECK(mir_tx_allowed(d, n, 4, 100000, 80, 0) == MIR_TOO_MANY_REPEATS);
    CHECK(mir_tx_allowed(d, n, 0, 499, 80, 0) == MIR_TOO_SOON && mir_tx_allowed(d, n, 0, 500, 80, 0) == MIR_OK);
    CHECK(mir_tx_allowed(d, n, 0, 100000, 29, 0) == MIR_LOW_BATTERY && mir_tx_allowed(d, n, 0, 100000, 30, 0) == MIR_OK && mir_tx_allowed(d, n, 0, 100000, -1, 0) == MIR_OK);
    CHECK(mir_tx_allowed(d, n, 0, 100000, 80, 1) == MIR_CARRIED);
    CHECK(mir_tx_allowed(NULL, 1, 0, 100000, 80, 0) == MIR_BAD_ARGS && mir_tx_allowed(d, 0, 0, 100000, 80, 0) == MIR_BAD_ARGS && mir_tx_allowed(d, 201, 0, 100000, 80, 0) == MIR_BAD_ARGS);
    uint32_t big[2] = {300000, 1000};
    CHECK(mir_tx_allowed(big, 2, 0, 100000, 80, 0) == MIR_BAD_ARGS);
    /* a raw list with one long mark is refused by the mark limit */
    uint32_t longmark[2] = {110000, 1000}, longer[2] = {130000, 1000};
    CHECK(mir_tx_allowed(longmark, 2, 0, 100000, 80, 0) == MIR_OK && mir_tx_allowed(longer, 2, 0, 100000, 80, 0) == MIR_TOO_LONG);
    for (int i = 1; i < MIR_REASONS; i++) CHECK(MIR_REASON_TEXT[i][0] != 0);
    if (failures) return 1;
    printf("ir core ok\n");
    return 0;
}
