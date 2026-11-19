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
    CHECK(mpx_on_paired(&s, z, "02:00:5e:00:53:01", 5000) == MPX_OK && s.state == MPX_AWAIT_CONFIRM);   /* review fix: nothing is handed over yet */
    CHECK(mpx_tick(&s, 5000 + MPX_CONFIRM_MS - 1000u) == 0 && s.state == MPX_AWAIT_CONFIRM);
    CHECK(mpx_confirm(&s, k) == MPX_OK && s.state == MPX_DONE);                                          /* the owner tapped Keep */
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
    CHECK(mpx_on_paired(&s, z, "02:00:5e:00:53:01", 5000) == MPX_ORDER && s.state == MPX_FAILED);
    mpx_begin(&s, pk_u, 1000);
    CHECK(mpx_on_host_key(&s, pk_h, commit, n_u) == MPX_OK);
    CHECK(mpx_on_host_key(&s, pk_h, commit, n_u) == MPX_ORDER); /* a second host key */
    /* a code is shown but "paired" before the nonce: refused */
    mpx_begin(&s, pk_u, 1000);
    mpx_on_host_key(&s, pk_h, commit, n_u);
    CHECK(mpx_on_paired(&s, z, "02:00:5e:00:53:01", 5000) == MPX_ORDER);
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
    /* review fix: a host key of small order (the eight known points) or all zero ends the exchange, with the top bit set or not; a normal key is accepted */
    {
        const char* bad[] = {
            "0000000000000000000000000000000000000000000000000000000000000000",
            "0100000000000000000000000000000000000000000000000000000000000000",
            "e0eb7a7c3b41b8ae1656e3faf19fc46ada098deb9c32b1fd866205165f49b800",
            "5f9c95bca3508c24b1d0b1559c83ef5b04445cc4581c8e86d8224eddd09f1157",
            "ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f",
            "edffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f",
            "eeffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f",
            "0000000000000000000000000000000000000000000000000000000000000080",   /* zero with the top bit set */
            "0100000000000000000000000000000000000000000000000000000000000080",
            "ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            "e0eb7a7c3b41b8ae1656e3faf19fc46ada098deb9c32b1fd866205165f49b880",
        };
        for (size_t i = 0; i < sizeof(bad) / sizeof(bad[0]); i++) {
            uint8_t low[32];
            hex(bad[i], low, 32);
            mpx_begin(&s, pk_u, 1000);
            CHECK(mpx_on_host_key(&s, low, commit, n_u) == MPX_BAD_KEY && s.state == MPX_FAILED);
            CHECK(s.pk_h[0] == 0 && s.pk_u[0] == 0);                         /* wiped */
        }
        mpx_begin(&s, pk_u, 1000);
        CHECK(mpx_on_host_key(&s, pk_h, commit, n_u) == MPX_OK);              /* an ordinary key still goes through */
        uint8_t topbit[32];
        memcpy(topbit, pk_h, 32);
        topbit[31] |= 0x80;
        mpx_begin(&s, pk_u, 1000);
        CHECK(mpx_on_host_key(&s, topbit, commit, n_u) == MPX_OK);            /* the top bit alone does not make a key bad */
        /* an all-zero shared secret never becomes a link key */
        uint8_t zero[32] = {0};
        mpx_begin(&s, pk_u, 1000);
        CHECK(mpx_on_host_key(&s, pk_h, commit, n_u) == MPX_OK && mpx_on_host_nonce(&s, n_h) == MPX_OK);
        CHECK(mpx_on_paired(&s, zero, "02:00:5e:00:53:01", 5000) == MPX_BAD_KEY && s.state == MPX_FAILED);
        CHECK(MPX_REASONS[MPX_BAD_KEY][0] != 0);
    }
    /* review fix: a forged "paired" does not give the unit a key: only the owner's tap on the unit does */
    {
        mpx_begin(&s, pk_u, 1000);
        mpx_on_host_key(&s, pk_h, commit, n_u);
        mpx_on_host_nonce(&s, n_h);
        CHECK(mpx_confirm(&s, k) == MPX_ORDER && s.state == MPX_FAILED);                                   /* a confirm with no "paired" before it */
        mpx_begin(&s, pk_u, 1000);
        mpx_on_host_key(&s, pk_h, commit, n_u);
        mpx_on_host_nonce(&s, n_h);
        CHECK(mpx_on_paired(&s, z, "02:00:5e:00:53:01", 9000) == MPX_OK && s.state == MPX_AWAIT_CONFIRM);
        CHECK(mpx_decline(&s) == MPX_DECLINED && s.state == MPX_FAILED && s.k[0] == 0 && s.k[31] == 0);    /* Cancel: the key is wiped */
        mpx_begin(&s, pk_u, 1000);
        mpx_on_host_key(&s, pk_h, commit, n_u);
        mpx_on_host_nonce(&s, n_h);
        mpx_on_paired(&s, z, "02:00:5e:00:53:01", 9000);
        CHECK(mpx_tick(&s, 9000 + MPX_CONFIRM_MS + 1u) == 1 && s.state == MPX_FAILED && s.k[0] == 0);       /* a minute with no tap: wiped */
        CHECK(MPX_REASONS[MPX_DECLINED][0] != 0);
    }
    if (failures) return 1;
    printf("pairx core ok\n");
    return 0;
}
