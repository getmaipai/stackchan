/* Host helper for the private-network client's Noise handshake (library patch): the same two-line wrapper the patch puts
 * in ml_noise.c (counter byte-swapped into the WireGuard AEAD), run on a PC. Prints one line per case:
 * "<key hex> <counter> <ad hex> <plaintext hex> <ciphertext+tag hex>". The Python test compares each line with an
 * independent RFC 8439 implementation and opens each ciphertext with the decrypt side. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdbool.h>
#include "chacha20poly1305.h"

/* The two helpers the WireGuard layer keeps in crypto.c (not built here: it pulls in the platform). */
void crypto_zero(void* dest, size_t len) { volatile uint8_t* p = dest; while (len--) *p++ = 0; }
bool crypto_equal(const void* a, const void* b, size_t size)
{
    const uint8_t* x = a; const uint8_t* y = b; uint8_t d = 0;
    for (size_t i = 0; i < size; i++) d |= (uint8_t)(x[i] ^ y[i]);
    return d == 0;
}

static int seal(const uint8_t* key, uint64_t nonce, const uint8_t* ad, size_t ad_len, const uint8_t* pt, size_t pt_len, uint8_t* ct)
{
    chacha20poly1305_encrypt(ct, pt, pt_len, ad, ad_len, __builtin_bswap64(nonce), key);
    return 0;
}
static int open_(const uint8_t* key, uint64_t nonce, const uint8_t* ad, size_t ad_len, const uint8_t* ct, size_t ct_len, uint8_t* pt)
{
    if (ct_len < 16) return -1;
    return chacha20poly1305_decrypt(pt, ct, ct_len, ad, ad_len, __builtin_bswap64(nonce), key) ? 0 : -1;
}
static void hex(const uint8_t* p, size_t n) { for (size_t i = 0; i < n; i++) printf("%02x", p[i]); }

int main(void)
{
    uint8_t key[32];
    for (int i = 0; i < 32; i++) key[i] = (uint8_t)(i * 7 + 1);
    const uint64_t counters[] = {0, 1, 0x0102030405060708ull, 0xfffffffffffffffeull};
    const size_t lens[] = {0, 1, 32, 100};
    uint8_t ad[32], pt[128], ct[160], back[128];
    for (int i = 0; i < 32; i++) ad[i] = (uint8_t)(0xa0 + i);
    for (int i = 0; i < 128; i++) pt[i] = (uint8_t)(i * 3);
    for (int c = 0; c < 4; c++) {
        for (int l = 0; l < 4; l++) {
            size_t adl = (size_t)(l * 9 % 33);
            seal(key, counters[c], ad, adl, pt, lens[l], ct);
            if (open_(key, counters[c], ad, adl, ct, lens[l] + 16, back) != 0 || memcmp(back, pt, lens[l]) != 0) {
                printf("ROUNDTRIP-FAIL\n");
                return 1;
            }
            ct[0] ^= 1;
            if (lens[l] > 0 && open_(key, counters[c], ad, adl, ct, lens[l] + 16, back) == 0) {
                printf("TAMPER-ACCEPTED\n");
                return 1;
            }
            ct[0] ^= 1;
            hex(key, 32); printf(" %llu ", (unsigned long long)counters[c]); hex(ad, adl); printf(" "); hex(pt, lens[l]); printf(" ");
            hex(ct, lens[l] + 16); printf("\n");
        }
    }
    return 0;
}
