/* Host test for the unit's pairing state machine (patch SF33), with the vectors of scripts/link-key-vector.py (fake inputs).
 * cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the headers>. */
#include <stdio.h>
#include "maipai_pairx_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void hex(const char* s, uint8_t* out, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        unsigned v;
        sscanf(s + 2 * i, "%2x", &v);
        out[i] = (uint8_t)v;
    }
}

int main(void)
{
    uint8_t pk_u[32], pk_h[32], z[32], commit[32], k_want[32], n_u[16], n_h[16], k[32];
    hex("07a37cbc142093c8b755dc1b10e86cb426374ad16aa853ed0bdfc0b2b86d1c7c", pk_u, 32);
    hex("5714769d116bf76436ae74bc793d2c30ad1903c59ac5273805c7e2698b410c36", pk_h, 32);
    hex("c9ea6a3f79a000b60b076d4afc990b272f3f0b5aaa3f0b8713c209273e363863", z, 32);
    hex("29a26f09c1b6a054f0536264bbeaf39900ee1c82f3aaa4477c93ee46354c15c6", commit, 32);
    hex("3d8bd81de51db1bafe4d49e56c3b652fc7c8441cb21456f6f8780cc97456bf60", k_want, 32);
    for (int i = 0; i < 16; i++) {
        n_u[i] = (uint8_t)i;
        n_h[i] = (uint8_t)(200 + i);
    }
    mpx_t s;
    /* the whole exchange */
    mpx_begin(&s, pk_u, 1000);
    CHECK(s.state == MPX_STARTED);
    CHECK(mpx_on_host_key(&s, pk_h, commit, n_u) == MPX_OK && s.state == MPX_NONCE_SENT);
    CHECK(mpx_on_host_nonce(&s, n_h) == MPX_OK && s.state == MPX_CODE_SHOWN && s.code == 578535u);
    CHECK(mpx_on_paired(&s, z, "02:00:5e:00:53:01", k) == MPX_OK && s.state == MPX_DONE);
    CHECK(memcmp(k, k_want, 32) == 0);
    /* nothing of the exchange stays in memory after it */
    CHECK(s.code == 0 && s.pk_h[0] == 0 && s.n_u[1] == 0);
    /* a nonce that does not match the commitment ends it, and no code is ever shown */
    mpx_begin(&s, pk_u, 1000);
    CHECK(mpx_on_host_key(&s, pk_h, commit, n_u) == MPX_OK);
    n_h[3] ^= 1;
    CHECK(mpx_on_host_nonce(&s, n_h) == MPX_COMMIT_MISMATCH && s.state == MPX_FAILED && s.code == 0);
    n_h[3] ^= 1;
    /* messages out of order end it */
    mpx_begin(&s, pk_u, 1000);
    CHECK(mpx_on_host_nonce(&s, n_h) == MPX_ORDER && s.state == MPX_FAILED);
    mpx_begin(&s, pk_u, 1000);
    CHECK(mpx_on_paired(&s, z, "02:00:5e:00:53:01", k) == MPX_ORDER && s.state == MPX_FAILED);
    mpx_begin(&s, pk_u, 1000);
    CHECK(mpx_on_host_key(&s, pk_h, commit, n_u) == MPX_OK);
    CHECK(mpx_on_host_key(&s, pk_h, commit, n_u) == MPX_ORDER); /* a second host key */
    /* a code is shown but "paired" before the nonce: refused */
    mpx_begin(&s, pk_u, 1000);
    mpx_on_host_key(&s, pk_h, commit, n_u);
    CHECK(mpx_on_paired(&s, z, "02:00:5e:00:53:01", k) == MPX_ORDER);
    /* timeout, also past 2^31 ms of uptime */
    const uint32_t base[2] = {1000u, 0x90000000u};
    for (int i = 0; i < 2; i++) {
        mpx_begin(&s, pk_u, base[i]);
        mpx_on_host_key(&s, pk_h, commit, n_u);
        CHECK(mpx_tick(&s, base[i] + MPX_TIMEOUT_MS - 1000u) == 0 && s.state == MPX_NONCE_SENT);
        CHECK(mpx_tick(&s, base[i] + MPX_TIMEOUT_MS + 1u) == 1 && s.state == MPX_FAILED);
        CHECK(mpx_tick(&s, base[i] + MPX_TIMEOUT_MS + 2000u) == 0);
    }
    /* an abort from the host returns to idle */
    mpx_begin(&s, pk_u, 1000);
    mpx_on_host_key(&s, pk_h, commit, n_u);
    mpx_abort(&s);
    CHECK(s.state == MPX_IDLE && s.pk_u[0] == 0);
    if (failures) return 1;
    printf("pairx core ok\n");
    return 0;
}
