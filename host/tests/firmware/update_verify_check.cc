/* The unit's own update checks as a PC program (patches 155 and 159): the Ed25519 verification, the paired-host rule for the image
 * address, the 20 percent slot rule and the trusted key from the build option. Compiled with update_verify.cc exactly as the firmware
 * has it (no ESP_PLATFORM, so the streaming hash class is left out; the digest is computed by the caller).
 *   verify SIG_HEX PK_HEX DIGEST_HEX   -> "valid" or "invalid"
 *   paired URL PAIRED_URL               -> "1" or "0"
 *   host URL                            -> the host part
 *   fits IMAGE_BYTES SLOT_BYTES         -> "1" or "0"
 *   key                                 -> the build key as hex, or "none"
 * cc -std=c++17 -Wall -Wextra -Werror -I<dir with update_verify.h> update_verify_check.cc <dir>/update_verify.cc */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#include "update_verify.h"

static bool unhex(const char* s, uint8_t* out, size_t n)
{
    if (strlen(s) != 2 * n) return false;
    for (size_t i = 0; i < n; i++) {
        char two[3] = {s[2 * i], s[2 * i + 1], 0};
        char* end = nullptr;
        out[i] = (uint8_t)strtol(two, &end, 16);
        if (*end != 0) return false;
    }
    return true;
}

int main(int argc, char** argv)
{
    if (argc < 2) return 2;
    const std::string cmd = argv[1];
    if (cmd == "verify" && argc == 5) {
        uint8_t sig[64], pk[32], h[64];
        if (!unhex(argv[2], sig, 64) || !unhex(argv[3], pk, 32) || !unhex(argv[4], h, 64)) {
            puts("invalid");
            return 0;
        }
        puts(Ed25519VerifyDigest(sig, pk, h) ? "valid" : "invalid");
    } else if (cmd == "paired" && argc == 4) {
        puts(UpdateUrlIsPairedHost(argv[2], argv[3]) ? "1" : "0");
    } else if (cmd == "host" && argc == 3) {
        puts(UpdateUrlHost(argv[2]).c_str());
    } else if (cmd == "fits" && argc == 4) {
        puts(UpdateFitsSlot((size_t)atoll(argv[2]), (size_t)atoll(argv[3])) ? "1" : "0");
    } else if (cmd == "key") {
        uint8_t pk[32];
        if (!UpdateTrustedKey(pk)) {
            puts("none");
        } else {
            for (int i = 0; i < 32; i++) printf("%02x", pk[i]);
            puts("");
        }
    } else {
        return 2;
    }
    return 0;
}
