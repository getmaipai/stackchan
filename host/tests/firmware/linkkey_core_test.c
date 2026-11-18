/* Host test for the link key schedule (patch SF20), against the vectors of scripts/link-key-vector.py (fake inputs, no secrets).
 * cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the headers>. */
#include <stdio.h>
#include "maipai_linkkey_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static int hex(const char* s, uint8_t* out, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        unsigned v;
        if (sscanf(s + 2 * i, "%2x", &v) != 1) return 0;
        out[i] = (uint8_t)v;
    }
    return 1;
}

int main(void)
{
    uint8_t pk_u[32], pk_h[32], z[32], commit[32], k[32], psk[32], n_u[16], n_h[16], got[32], want[32];
    CHECK(hex("07a37cbc142093c8b755dc1b10e86cb426374ad16aa853ed0bdfc0b2b86d1c7c", pk_u, 32));
    CHECK(hex("5714769d116bf76436ae74bc793d2c30ad1903c59ac5273805c7e2698b410c36", pk_h, 32));
    CHECK(hex("c9ea6a3f79a000b60b076d4afc990b272f3f0b5aaa3f0b8713c209273e363863", z, 32));
    for (int i = 0; i < 16; i++) {
        n_u[i] = (uint8_t)i;
        n_h[i] = (uint8_t)(200 + i);
    }
    /* RFC 5869 test case 1 (HKDF itself, first 32 bytes) */
    uint8_t ikm[22], salt[13], info[10];
    memset(ikm, 0x0B, sizeof(ikm));
    for (int i = 0; i < 13; i++) salt[i] = (uint8_t)i;
    for (int i = 0; i < 10; i++) info[i] = (uint8_t)(0xF0 + i);
    mly_hkdf(ikm, sizeof(ikm), salt, sizeof(salt), info, sizeof(info), got, 32);
    CHECK(hex("3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf", want, 32) && memcmp(got, want, 32) == 0);
    /* the exchange */
    mly_commit(pk_h, pk_u, n_h, commit);
    CHECK(hex("29a26f09c1b6a054f0536264bbeaf39900ee1c82f3aaa4477c93ee46354c15c6", want, 32) && memcmp(commit, want, 32) == 0);
    CHECK(mly_sas(pk_u, pk_h, n_u, n_h) == 578535u);
    mly_link_key(z, pk_u, pk_h, n_u, n_h, "02:00:5e:00:53:01", k);
    CHECK(hex("3d8bd81de51db1bafe4d49e56c3b652fc7c8441cb21456f6f8780cc97456bf60", want, 32) && memcmp(k, want, 32) == 0);
    mly_psk(k, "02:00:5e:00:53:01", psk);
    CHECK(hex("f8e32ab42c793df8df40ad49227105843c02927421582c34b420c4dfd792fe77", want, 32) && memcmp(psk, want, 32) == 0);
    /* any changed input changes the code and the key */
    n_h[0] ^= 1;
    CHECK(mly_sas(pk_u, pk_h, n_u, n_h) != 578535u);
    mly_link_key(z, pk_u, pk_h, n_u, n_h, "02:00:5e:00:53:01", got);
    CHECK(memcmp(got, k, 32) != 0);
    if (failures) return 1;
    printf("linkkey core ok\n");
    return 0;
}
