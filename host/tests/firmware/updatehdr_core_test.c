/* Host driver for the update header core (patch SF25). Reads lines "package_hex image_hex installed" from standard input
 * (installed is -1 for none) and prints, per line, the verdict of everything the core checks (the Ed25519 signature is checked
 * elsewhere): the reason code from maipai_updatehdr_core.h, streaming the image in chunks of 7 bytes to exercise the hash.
 * cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the headers>. */
#include <stdio.h>
#include <stdlib.h>
#include "maipai_updatehdr_core.h"

static size_t unhex(const char* s, uint8_t* out, size_t cap)
{
    size_t n = 0;
    while (s[0] && s[1] && n < cap) {
        unsigned v;
        if (sscanf(s, "%2x", &v) != 1) break;
        out[n++] = (uint8_t)v;
        s += 2;
    }
    return n;
}

int main(void)
{
    static char line[20000];
    static uint8_t pkg[4096], img[8192];
    char pkg_hex[8200], img_hex[16400];
    long installed;
    while (fgets(line, sizeof line, stdin)) {
        if (sscanf(line, "%8199s %16399s %ld", pkg_hex, img_hex, &installed) != 3) {
            printf("bad\n");
            continue;
        }
        const size_t pn = unhex(pkg_hex, pkg, sizeof pkg);
        const size_t in = strcmp(img_hex, "-") == 0 ? 0 : unhex(img_hex, img, sizeof img);
        if (pn < MUH_HDR_LEN + MUH_SIG_LEN) {
            printf("nosig\n");
            continue;
        }
        muh_hdr_t h;
        int r = muh_parse(pkg, MUH_HDR_LEN, installed < 0 ? 0u : (uint32_t)installed, &h);
        if (r == MUH_OK) {
            muh_sha_t s;
            muh_sha_begin(&s);
            for (size_t i = 0; i < in; i += 7) muh_sha_update(&s, img + i, in - i < 7 ? in - i : 7);
            r = muh_check_image(&h, &s);
        }
        printf("%d\n", r);
    }
    return 0;
}
