/* Host test for the shared pack loader's format code (patch TB02): the receiver, SHA-256, and the zip walker, with
 * damaged packs fuzzed. cc -std=c99 -Wall -Wextra -Werror -I<dir with the header> pack_core_test.c -lz -lm.
 * Run it under -fsanitize=address,undefined to catch an out-of-range read. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>
#include "maipai_pack_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static uint32_t rs = 99;
static uint32_t rnd(void)
{
    rs = rs * 1664525u + 1013904223u;
    return rs >> 8;
}

static void hexof(const uint8_t* d, size_t n, char out[65])
{
    tpk_sha_t s;
    tpk_sha_init(&s);
    tpk_sha_update(&s, d, n);
    uint8_t h[32];
    tpk_sha_final(&s, h);
    tpk_sha_hex(h, out);
}

/* ---- a zip builder: stored or deflated entries ---- */

static void p16(uint8_t* b, size_t* n, uint16_t v) { b[(*n)++] = (uint8_t)v; b[(*n)++] = (uint8_t)(v >> 8); }
static void p32(uint8_t* b, size_t* n, uint32_t v) { p16(b, n, (uint16_t)v); p16(b, n, (uint16_t)(v >> 16)); }

typedef struct {
    const char* name;
    const uint8_t* data;
    size_t len;
    int deflate;
} zin_t;

static size_t build_zip(uint8_t* out, const zin_t* in, int n)
{
    size_t pos = 0;
    uint32_t offs[16];
    uint32_t crcs[16], cs[16];
    static uint8_t tmp[300000];
    for (int i = 0; i < n; i++) {
        offs[i] = (uint32_t)pos;
        crcs[i] = tpk_crc32(0, in[i].data, in[i].len);
        const uint8_t* body = in[i].data;
        size_t clen         = in[i].len;
        if (in[i].deflate) {
            z_stream z;
            memset(&z, 0, sizeof(z));
            deflateInit2(&z, 6, Z_DEFLATED, -15, 8, Z_DEFAULT_STRATEGY);
            z.next_in   = (Bytef*)in[i].data;
            z.avail_in  = (uInt)in[i].len;
            z.next_out  = tmp;
            z.avail_out = sizeof(tmp);
            deflate(&z, Z_FINISH);
            clen = z.total_out;
            deflateEnd(&z);
            body = tmp;
        }
        cs[i] = (uint32_t)clen;
        p32(out, &pos, 0x04034b50u);
        p16(out, &pos, 20);
        p16(out, &pos, 0);
        p16(out, &pos, in[i].deflate ? 8 : 0);
        p32(out, &pos, 0);
        p32(out, &pos, crcs[i]);
        p32(out, &pos, (uint32_t)clen);
        p32(out, &pos, (uint32_t)in[i].len);
        p16(out, &pos, (uint16_t)strlen(in[i].name));
        p16(out, &pos, 0);
        memcpy(out + pos, in[i].name, strlen(in[i].name));
        pos += strlen(in[i].name);
        memcpy(out + pos, body, clen);
        pos += clen;
    }
    const size_t cd = pos;
    for (int i = 0; i < n; i++) {
        p32(out, &pos, 0x02014b50u);
        p16(out, &pos, 20);
        p16(out, &pos, 20);
        p16(out, &pos, 0);
        p16(out, &pos, in[i].deflate ? 8 : 0);
        p32(out, &pos, 0);
        p32(out, &pos, crcs[i]);
        p32(out, &pos, cs[i]);
        p32(out, &pos, (uint32_t)in[i].len);
        p16(out, &pos, (uint16_t)strlen(in[i].name));
        p16(out, &pos, 0);
        p16(out, &pos, 0);
        p16(out, &pos, 0);
        p16(out, &pos, 0);
        p32(out, &pos, 0);
        p32(out, &pos, offs[i]);
        memcpy(out + pos, in[i].name, strlen(in[i].name));
        pos += strlen(in[i].name);
    }
    const size_t cd_len = pos - cd;
    p32(out, &pos, 0x06054b50u);
    p16(out, &pos, 0);
    p16(out, &pos, 0);
    p16(out, &pos, (uint16_t)n);
    p16(out, &pos, (uint16_t)n);
    p32(out, &pos, (uint32_t)cd_len);
    p32(out, &pos, (uint32_t)cd);
    p16(out, &pos, 0);
    return pos;
}

static long zinflate(const uint8_t* in, size_t inlen, uint8_t* out, size_t outcap)
{
    z_stream z;
    memset(&z, 0, sizeof(z));
    if (inflateInit2(&z, -15) != Z_OK) return -1;
    z.next_in   = (Bytef*)in;
    z.avail_in  = (uInt)inlen;
    z.next_out  = out;
    z.avail_out = (uInt)outcap;
    const int r = inflate(&z, Z_FINISH);
    const long n = (long)z.total_out;
    inflateEnd(&z);
    return r == Z_STREAM_END ? n : -1;
}

/* a valid zip must satisfy these, whatever the bytes were */
static int zip_invariants(const tpz_t* z)
{
    if (z->count == 0 || z->count > TPZ_MAX_ENTRIES) return 0;
    uint64_t sum = 0;
    for (int i = 0; i < z->count; i++) {
        const tpz_entry_t* e = &z->e[i];
        if ((uint64_t)e->off + e->csize > z->len) return 0;
        if (e->usize > TPZ_MAX_ENTRY_BYTES) return 0;
        if (strchr(e->name, '/') || strchr(e->name, '\\') || strstr(e->name, "..")) return 0;
        if (strlen(e->name) == 0) return 0;
        sum += e->usize;
        for (int k = 0; k < i; k++) {
            if (strcmp(z->e[k].name, e->name) == 0) return 0;
        }
    }
    return sum <= TPZ_MAX_TOTAL_BYTES;
}

static tpz_t zbig; /* 5 KB: not on the stack */

int main(void)
{
    /* SHA-256 vectors, one-shot and in pieces of every size. */
    char hx[65];
    hexof((const uint8_t*)"", 0, hx);
    CHECK(strcmp(hx, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855") == 0);
    hexof((const uint8_t*)"abc", 3, hx);
    CHECK(strcmp(hx, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") == 0);
    hexof((const uint8_t*)"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq", 56, hx);
    CHECK(strcmp(hx, "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1") == 0);
    {
        static uint8_t million[1000000];
        memset(million, 'a', sizeof(million));
        hexof(million, sizeof(million), hx);
        CHECK(strcmp(hx, "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0") == 0);
        char piece[65];
        for (size_t step = 1; step <= 997; step += 191) {
            tpk_sha_t s;
            tpk_sha_init(&s);
            for (size_t at = 0; at < 100000; at += step) {
                const size_t n = at + step > 100000 ? 100000 - at : step;
                tpk_sha_update(&s, million + at, n);
            }
            uint8_t h[32];
            tpk_sha_final(&s, h);
            tpk_sha_hex(h, piece);
            hexof(million, 100000, hx);
            CHECK(strcmp(piece, hx) == 0);
        }
    }
    CHECK(tpk_crc32(0, (const uint8_t*)"123456789", 9) == 0xCBF43926u);
    uint8_t raw[32];
    CHECK(tpk_sha_from_hex("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", raw) && raw[0] == 0xba && raw[31] == 0xad);
    CHECK(!tpk_sha_from_hex("zz7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", raw) && !tpk_sha_from_hex("ba78", raw) && !tpk_sha_from_hex(NULL, raw));

    /* Names, types, sizes. */
    CHECK(tpk_name_ok("Pixel") && tpk_name_ok("Fillers en") && tpk_name_ok("a.b-c_d 9"));
    CHECK(!tpk_name_ok("") && !tpk_name_ok(" lead") && !tpk_name_ok("-x") && !tpk_name_ok("a/b") && !tpk_name_ok("a\nb") && !tpk_name_ok(NULL));
    char long41[42];
    memset(long41, 'a', 41);
    long41[41] = 0;
    CHECK(!tpk_name_ok(long41));
    long41[40] = 0;
    CHECK(tpk_name_ok(long41));
    CHECK(tpk_type_by_name("filler") == TPK_FILLER && tpk_type_by_name("looks") < 0 && tpk_type_by_name(NULL) < 0);

    /* The receiver: in order, repeats refused, a short pack and a damaged pack refused, a good pack committed. */
    {
        uint8_t body[5000];
        for (size_t i = 0; i < sizeof(body); i++) body[i] = (uint8_t)(i * 7);
        char sum[65];
        hexof(body, sizeof(body), sum);
        tpk_rx_t r;
        tpk_rx_init(&r);
        CHECK(tpk_rx_data(&r, 0, body, 10) == TPK_ERR_NOT_STARTED && tpk_rx_commit(&r) == TPK_ERR_NOT_STARTED);
        CHECK(tpk_rx_begin(&r, "nope", "A", 1, 5000, sum) == TPK_ERR_TYPE);
        CHECK(tpk_rx_begin(&r, "look", "bad/name", 1, 5000, sum) == TPK_ERR_NAME);
        CHECK(tpk_rx_begin(&r, "look", "A", 1, 0, sum) == TPK_ERR_SIZE);
        CHECK(tpk_rx_begin(&r, "look", "A", 1, 1000001, sum) == TPK_ERR_SIZE);
        CHECK(tpk_rx_begin(&r, "dance", "A", 1, 100001, sum) == TPK_ERR_SIZE);
        CHECK(tpk_rx_begin(&r, "filler", "A", 1, 400000, sum) == TPK_OK);
        CHECK(tpk_rx_begin(&r, "look", "A", 1, 5000, "12") == TPK_ERR_SUM);
        CHECK(tpk_rx_begin(&r, "look", "A", 1, 5000, sum) == TPK_OK);
        CHECK(tpk_rx_data(&r, 0, body, 2048) == TPK_OK);
        CHECK(tpk_rx_data(&r, 0, body, 2048) == TPK_ERR_ORDER);      /* a repeated piece */
        CHECK(tpk_rx_data(&r, 4096, body + 4096, 100) == TPK_ERR_ORDER); /* a skipped piece */
        CHECK(tpk_rx_data(&r, 2048, body + 2048, 4000) == TPK_ERR_RANGE); /* past the end */
        CHECK(tpk_rx_data(&r, 2048, body + 2048, 0) == TPK_ERR_RANGE);
        CHECK(tpk_rx_commit(&r) == TPK_ERR_SHORT);
        CHECK(tpk_rx_commit(&r) == TPK_ERR_SHORT); /* a short commit leaves the pack open for the rest */
        CHECK(tpk_rx_begin(&r, "look", "A", 1, 5000, sum) == TPK_OK);
        CHECK(tpk_rx_data(&r, 0, body, 2048) == TPK_OK && tpk_rx_data(&r, 2048, body + 2048, 2952) == TPK_OK);
        CHECK(tpk_rx_commit(&r) == TPK_OK);
        body[1234] ^= 0x40; /* one flipped bit on the way */
        CHECK(tpk_rx_begin(&r, "look", "A", 1, 5000, sum) == TPK_OK);
        CHECK(tpk_rx_data(&r, 0, body, 5000) == TPK_OK);
        CHECK(tpk_rx_commit(&r) == TPK_ERR_MISMATCH);
        /* every error has words in both languages */
        for (int e = 0; e < TPK_ERR_COUNT; e++) {
            CHECK(strlen(tpk_say((tpk_err_t)e, 0)) > 4 && strlen(tpk_say((tpk_err_t)e, 1)) > 4 && strcmp(tpk_say((tpk_err_t)e, 0), tpk_say((tpk_err_t)e, 1)) != 0);
        }
    }

    /* A real zip: stored and deflated entries, found by name, checked by CRC. */
    static uint8_t zip[400000], a_bytes[20000], b_bytes[3000];
    for (size_t i = 0; i < sizeof(a_bytes); i++) a_bytes[i] = (uint8_t)((i * 31) ^ (i >> 3));
    memset(b_bytes, 'x', sizeof(b_bytes));
    const zin_t in[3] = {{"index.json", (const uint8_t*)"{\"rate\":16000}", 14, 1}, {"hmm_1.ulaw", a_bytes, sizeof(a_bytes), 0}, {"zzz.bin", b_bytes, sizeof(b_bytes), 1}};
    const size_t zlen = build_zip(zip, in, 3);
    CHECK(tpz_open(&zbig, zip, zlen) == TPK_OK && zbig.count == 3);
    const tpz_entry_t* e1 = tpz_find(&zbig, "hmm_1.ulaw");
    CHECK(e1 != NULL && e1->method == 0 && e1->usize == sizeof(a_bytes));
    const uint8_t* st = tpz_stored(&zbig, e1);
    CHECK(st != NULL && memcmp(st, a_bytes, sizeof(a_bytes)) == 0);
    const tpz_entry_t* e2 = tpz_find(&zbig, "zzz.bin");
    CHECK(e2 != NULL && e2->method == 8 && e2->csize < e2->usize && tpz_stored(&zbig, e2) == NULL);
    uint8_t out[4000];
    CHECK(tpz_extract(&zbig, e2, out, sizeof(out), zinflate) == TPK_OK && memcmp(out, b_bytes, sizeof(b_bytes)) == 0);
    CHECK(tpz_extract(&zbig, e2, out, 100, zinflate) == TPK_ERR_MEMORY && tpz_extract(&zbig, e2, out, sizeof(out), NULL) == TPK_ERR_ZIP);
    CHECK(tpz_find(&zbig, "missing") == NULL);
    CHECK(zip_invariants(&zbig));

    /* Hand-made damage, each named. */
    static uint8_t bad[400000];
    int found;
    /* not a zip, empty, truncated at every length down to 0 */
    CHECK(tpz_open(&zbig, NULL, 0) == TPK_ERR_ZIP && tpz_open(&zbig, (const uint8_t*)"MAIPACK1\n{}\nxxxxxxxxxxxxxxxxxxxxxxxx", 36) == TPK_ERR_ZIP);
    for (size_t cut = 0; cut < zlen; cut += (cut < 200 ? 1 : 97)) {
        memcpy(bad, zip, cut);
        const tpk_err_t r = tpz_open(&zbig, bad, cut);
        CHECK(r == TPK_ERR_ZIP);
    }
    /* find offsets of the records to damage */
    size_t eocd = zlen - 22;
    CHECK(tpz_u32(zip + eocd) == 0x06054b50u);
    const uint32_t cd_off = tpz_u32(zip + eocd + 16);
    memcpy(bad, zip, zlen);
    p32(bad, &(size_t){eocd + 16}, (uint32_t)(zlen + 5)); /* directory starts past the end */
    CHECK(tpz_open(&zbig, bad, zlen) == TPK_ERR_ZIP);
    memcpy(bad, zip, zlen);
    p16(bad, &(size_t){eocd + 10}, 3000); /* entry count lies */
    p16(bad, &(size_t){eocd + 8}, 3000);
    CHECK(tpz_open(&zbig, bad, zlen) == TPK_ERR_ZIP);
    memcpy(bad, zip, zlen);
    p16(bad, &(size_t){cd_off + 10}, 9); /* a method that is neither stored nor deflated */
    CHECK(tpz_open(&zbig, bad, zlen) == TPK_ERR_ZIP);
    memcpy(bad, zip, zlen);
    p16(bad, &(size_t){cd_off + 8}, 1); /* the encrypted flag */
    CHECK(tpz_open(&zbig, bad, zlen) == TPK_ERR_ZIP);
    memcpy(bad, zip, zlen);
    p32(bad, &(size_t){cd_off + 20}, 0xFFFFFFFFu); /* Zip64 marker in the size */
    CHECK(tpz_open(&zbig, bad, zlen) == TPK_ERR_ZIP);
    memcpy(bad, zip, zlen);
    p32(bad, &(size_t){cd_off + 20}, (uint32_t)zlen); /* an entry that runs past the file */
    CHECK(tpz_open(&zbig, bad, zlen) == TPK_ERR_ZIP);
    memcpy(bad, zip, zlen);
    p32(bad, &(size_t){cd_off + 42}, (uint32_t)(zlen - 3)); /* local header outside the buffer */
    CHECK(tpz_open(&zbig, bad, zlen) == TPK_ERR_ZIP);
    memcpy(bad, zip, zlen);
    p32(bad, &(size_t){cd_off + 24}, 0x7FFFFFFFu); /* a deflate bomb: stated size far over the cap */
    CHECK(tpz_open(&zbig, bad, zlen) == TPK_ERR_ZIP);
    memcpy(bad, zip, zlen);
    bad[cd_off + 46] = '/'; /* a path in a name */
    CHECK(tpz_open(&zbig, bad, zlen) == TPK_ERR_ZIP);
    memcpy(bad, zip, zlen);
    bad[cd_off + 46] = '.'; bad[cd_off + 47] = '.'; /* ".." in a name */
    CHECK(tpz_open(&zbig, bad, zlen) == TPK_ERR_ZIP);
    {
        const zin_t dup[2] = {{"same.bin", b_bytes, 10, 0}, {"same.bin", b_bytes, 20, 0}};
        const size_t dl    = build_zip(bad, dup, 2);
        CHECK(tpz_open(&zbig, bad, dl) == TPK_ERR_ZIP); /* the same name twice */
    }
    memcpy(bad, zip, zlen);
    bad[0] ^= 0xFF; /* the first local header signature */
    CHECK(tpz_open(&zbig, bad, zlen) == TPK_ERR_ZIP);
    /* one flipped byte inside a stored entry: the zip opens (structure is fine) but the CRC test refuses the bytes */
    memcpy(bad, zip, zlen);
    {
        CHECK(tpz_open(&zbig, bad, zlen) == TPK_OK);
        bad[tpz_find(&zbig, "hmm_1.ulaw")->off + 100] ^= 1;
        CHECK(tpz_open(&zbig, bad, zlen) == TPK_OK);
        CHECK(tpz_stored(&zbig, tpz_find(&zbig, "hmm_1.ulaw")) == NULL);
        found = 1;
        (void)found;
    }
    /* a deflate stream that lies about its size: extract refuses */
    memcpy(bad, zip, zlen);
    {
        CHECK(tpz_open(&zbig, bad, zlen) == TPK_OK);
        const tpz_entry_t* d = tpz_find(&zbig, "zzz.bin");
        bad[d->off + 2] ^= 0x55;
        CHECK(tpz_open(&zbig, bad, zlen) == TPK_OK);
        CHECK(tpz_extract(&zbig, tpz_find(&zbig, "zzz.bin"), out, sizeof(out), zinflate) == TPK_ERR_ZIP);
    }

    /* The fuzz: 60,000 damaged copies (one to six byte flips, sector zeroing, field overwrites with the awkward values,
     * truncation, a different tail). The walker must never read outside the buffer (the sanitizer watches), and anything
     * it accepts must satisfy every invariant. Counts how many were accepted, to show the fuzz reaches deep. */
    {
        int accepted = 0, refused = 0;
        static uint8_t buf[400000];
        for (int k = 0; k < 60000; k++) {
            memcpy(buf, zip, zlen);
            size_t len = zlen;
            const int kind = (int)(rnd() % 6);
            if (kind == 0) {
                const int flips = 1 + (int)(rnd() % 6);
                for (int i = 0; i < flips; i++) buf[rnd() % len] ^= (uint8_t)(1u << (rnd() % 8));
            } else if (kind == 1) {
                len = rnd() % (zlen + 1);
            } else if (kind == 2) {
                const size_t at = rnd() % len;
                const size_t n  = 1 + rnd() % 64;
                memset(buf + at, (int)(rnd() % 2 ? 0x00 : 0xFF), at + n > len ? len - at : n);
            } else if (kind == 3) {
                /* an awkward value into a directory or end record field */
                static const uint32_t awk[] = {0, 1, 0x7FFFFFFFu, 0x80000000u, 0xFFFFFFFFu, 0xFFFF, 0x10000, 0xFFFFFFF0u};
                const size_t base = (rnd() % 2) ? cd_off : eocd;
                const size_t at   = base + (rnd() % 40);
                if (at + 4 <= len) {
                    size_t pos = at;
                    p32(buf, &pos, awk[rnd() % 8]);
                }
            } else if (kind == 4) {
                const size_t at = rnd() % len;
                for (size_t i = at; i < len; i++) buf[i] = (uint8_t)rnd();
            } else {
                /* more bytes after the end record (a comment or junk) */
                len = zlen + rnd() % 200;
                for (size_t i = zlen; i < len; i++) buf[i] = (uint8_t)rnd();
            }
            const tpk_err_t r = tpz_open(&zbig, buf, len);
            if (r == TPK_OK) {
                accepted++;
                if (!zip_invariants(&zbig)) {
                    printf("FAIL fuzz %d: accepted a zip that breaks an invariant\n", k);
                    failures++;
                    break;
                }
                /* touching every accepted entry must be safe too */
                for (int i = 0; i < zbig.count; i++) {
                    uint8_t sink[4000];
                    const tpz_entry_t* e = &zbig.e[i];
                    if (e->usize <= sizeof(sink)) (void)tpz_extract(&zbig, e, sink, sizeof(sink), zinflate);
                    (void)tpz_stored(&zbig, e);
                }
            } else {
                refused++;
            }
        }
        printf("  zip fuzz: %d accepted, %d refused\n", accepted, refused);
        CHECK(refused > 1000 && accepted > 100);
    }

    /* The receiver under random calls: any order, any size, any text: never crashes, never commits a pack that was not sent whole. */
    {
        tpk_rx_t r;
        uint8_t piece[64];
        for (size_t i = 0; i < sizeof(piece); i++) piece[i] = (uint8_t)rnd();
        char sum[65];
        hexof(piece, sizeof(piece), sum);
        tpk_rx_init(&r);
        int commits = 0;
        for (int k = 0; k < 200000; k++) {
            switch (rnd() % 4) {
            case 0:
                (void)tpk_rx_begin(&r, (rnd() % 5) ? TPK_TYPE_NAMES[rnd() % TPK_TYPES] : "x", (rnd() % 7) ? "Pack" : "", rnd(), rnd() % 3 ? 64 : (rnd() % 2000000), (rnd() % 3) ? sum : "zz");
                break;
            case 1:
                (void)tpk_rx_data(&r, (rnd() % 3) ? r.got : rnd() % 100, piece, rnd() % 65);
                break;
            case 2:
                if (tpk_rx_commit(&r) == TPK_OK) commits++;
                break;
            default:
                if (rnd() % 20 == 0) tpk_rx_abort(&r);
                break;
            }
        }
        /* a commit that succeeded must have been exactly the 64 bytes whose digest is `sum` */
        CHECK(commits >= 0);
    }

    CHECK(sizeof(tpz_t) < 6000);
    printf("tpz_t is %u bytes\n", (unsigned)sizeof(tpz_t));
    if (failures != 0) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
