// Host test for a signed game pack (patch G01): the unit checks the signature with the same Ed25519 code that checks
// firmware updates (update_verify.cc, patch 155) against the update key, over the pack and its checksum.
//   c++ -std=c++17 -Wall -Wextra -Werror -I<dir> games_sig_test.cc update_verify.cc -o t
//   ./t pack.mpk pubkey.raw digest.raw        (digest.raw is SHA-512 of R, the key and the signed bytes, made by the host)
// The device computes that digest with its crypto library; here a script does, so the two halves are checked apart.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "update_verify.h"
extern "C" {
#include "maipai_games_core.h"
}

static std::vector<uint8_t> slurp(const char* path)
{
    std::vector<uint8_t> out;
    FILE* f = fopen(path, "rb");
    if (f == nullptr) {
        printf("cannot open %s\n", path);
        exit(2);
    }
    uint8_t buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), f)) > 0) {
        out.insert(out.end(), buf, buf + n);
    }
    fclose(f);
    return out;
}

int main(int argc, char** argv)
{
    if (argc != 4) {
        printf("usage: games_sig_test pack pubkey digest\n");
        return 2;
    }
    const auto pack = slurp(argv[1]);
    const auto pk   = slurp(argv[2]);
    const auto h    = slurp(argv[3]);
    mg_pack_t p;
    if (mg_parse(pack.data(), pack.size(), &p) != MG_OK || !p.has_sig || pk.size() != 32 || h.size() != 64) {
        printf("bad input\n");
        return 2;
    }
    size_t signed_len     = 0;
    const uint8_t* sig    = mg_signature(&p, &signed_len);
    const bool ok         = Ed25519VerifyDigest(sig, pk.data(), h.data());
    printf("%s\n", ok ? "verified" : "refused");
    return ok ? 0 : 1;
}
