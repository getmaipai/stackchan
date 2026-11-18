/* The unit's own link key schedule (maipai_linkkey_core.h, patch SF20) on the command line, so a simulated unit computes the pairing commitment and the six digits with the
 * unit's code. Lines on stdin (hex arguments): `sas PK_U PK_H N_U N_H` prints the six digits, `commit PK_H PK_U N_H` prints the commitment.
 * Build: cc -std=gnu99 -I<dir with the headers> link_shim.c -o link_shim. Placement: host-side development tool; no firmware change. Upstream: none. */
#include <stdio.h>
#include <string.h>
#include "maipai_linkkey_core.h"

static int unhex(const char* s, uint8_t* out, size_t n)
{
    if (strlen(s) != 2 * n) return 0;
    for (size_t i = 0; i < n; i++) {
        unsigned v;
        if (sscanf(s + 2 * i, "%2x", &v) != 1) return 0;
        out[i] = (uint8_t)v;
    }
    return 1;
}

int main(void)
{
    char cmd[16], a[200], b[200], c[200], d[200];
    uint8_t pk_u[MLY_PK], pk_h[MLY_PK], n_u[MLY_NONCE], n_h[MLY_NONCE];
    while (scanf("%15s", cmd) == 1) {
        if (!strcmp(cmd, "sas") && scanf("%199s %199s %199s %199s", a, b, c, d) == 4 && unhex(a, pk_u, MLY_PK) && unhex(b, pk_h, MLY_PK) && unhex(c, n_u, MLY_NONCE) && unhex(d, n_h, MLY_NONCE)) {
            printf("%06u\n", (unsigned)mly_sas(pk_u, pk_h, n_u, n_h));
        } else if (!strcmp(cmd, "commit") && scanf("%199s %199s %199s", a, b, c) == 3 && unhex(a, pk_h, MLY_PK) && unhex(b, pk_u, MLY_PK) && unhex(c, n_h, MLY_NONCE)) {
            uint8_t out[32];
            mly_commit(pk_h, pk_u, n_h, out);
            for (int i = 0; i < 32; i++) printf("%02x", out[i]);
            printf("\n");
        } else {
            printf("error\n");
        }
        fflush(stdout);
    }
    return 0;
}
