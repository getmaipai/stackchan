/* Host test for the offline phrases as a pack (patch K12): the zip of sixteen clips becomes one block and a table, a clip that is
 * not an Ogg stream or is the wrong size is left out whole, a damaged zip never reads out of range, and the pack's size gate
 * holds. cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> phrasepack_core_test.c -lz. Run it under
 * -fsanitize=address,undefined to catch an out-of-range read. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>
#include "maipai_phrasepack_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static uint32_t rs = 11;
static uint32_t rnd(void)
{
    rs = rs * 1664525u + 1013904223u;
    return rs >> 8;
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

#define MAXCLIP 70000
static uint8_t clipdata[16][MAXCLIP];
static size_t cliplen[16];
static char names[16][32];
static uint8_t zipbuf[1500000];
static uint8_t block[MPH_BLOCK_MAX + 100];

static int clip_index(int g, int v)
{
    int n = 0;
    for (int i = 0; i < g; i++) n += MS_GROUP_SIZE[i];
    return n + v;
}

/* a clip that looks like an Ogg stream: the capture pattern, then bytes that tell the clip apart */
static void make_clip(int idx, size_t len, int ogg)
{
    cliplen[idx] = len;
    for (size_t i = 0; i < len; i++) clipdata[idx][i] = (uint8_t)(idx * 31 + i * 7 + (i >> 4));
    if (ogg) memcpy(clipdata[idx], "OggS", 4);
    else memcpy(clipdata[idx], "RIFF", 4);
}

static size_t zip_all(int deflate_it, int skip_idx)
{
    zin_t in[16];
    int n = 0;
    for (int g = 0; g < MS_GRP_COUNT; g++) {
        for (int v = 0; v < MS_GROUP_SIZE[g]; v++) {
            const int i = clip_index(g, v);
            if (i == skip_idx) continue;
            ms_phrase_file(names[i], sizeof(names[i]), g, v);
            in[n].name    = names[i];
            in[n].data    = clipdata[i];
            in[n].len     = cliplen[i];
            in[n].deflate = deflate_it;
            n++;
        }
    }
    return build_zip(zipbuf, in, n);
}

int main(void)
{
    CHECK(MS_GRP_COUNT == 5 && MS_GROUP_SIZE[0] + MS_GROUP_SIZE[1] + MS_GROUP_SIZE[2] + MS_GROUP_SIZE[3] + MS_GROUP_SIZE[4] == 16);
    CHECK(MPH_BLOCK_MAX == TPK_MAX_BYTES[TPK_PHRASE]);
    CHECK(sizeof(mph_table_t) < 300);
    for (int i = 0; i < 16; i++) make_clip(i, 2000 + (size_t)i * 300, 1);

    /* the file names are the image's: ph_<group>_<n>.ogg */
    {
        char n[32];
        CHECK(ms_phrase_file(n, sizeof(n), 0, 0) && strcmp(n, "ph_no_wifi_1.ogg") == 0);
        CHECK(ms_phrase_file(n, sizeof(n), 4, 1) && strcmp(n, "ph_back_2.ogg") == 0);
        CHECK(!ms_phrase_file(n, sizeof(n), 4, 2) && !ms_phrase_file(n, sizeof(n), 5, 0));
    }

    /* a full pack, stored and deflated: sixteen clips, each at its own place, byte for byte */
    for (int deflate_it = 0; deflate_it < 2; deflate_it++) {
        const size_t zn = zip_all(deflate_it, -1);
        tpz_t z;
        CHECK(tpz_open(&z, zipbuf, zn) == TPK_OK);
        uint32_t want = 0;
        for (int i = 0; i < 16; i++) want += (uint32_t)cliplen[i];
        CHECK(mph_need(&z) == want);
        mph_table_t t;
        CHECK(mph_build(&z, zinflate, block, want, &t) == TPK_OK && t.count == 16 && t.total == want);
        for (int g = 0; g < MS_GRP_COUNT; g++) {
            for (int v = 0; v < MS_GROUP_SIZE[g]; v++) {
                const int i = clip_index(g, v);
                CHECK(t.len[g][v] == cliplen[i] && memcmp(block + t.off[g][v], clipdata[i], cliplen[i]) == 0);
            }
        }
        CHECK(t.len[4][2] == 0 && t.len[2][3] == 0); /* variants that do not exist stay unset */
    }

    /* a pack with a clip missing: the other fifteen are there, the missing one is unset (the image's clip will play) */
    {
        const size_t zn = zip_all(0, clip_index(2, 1));
        tpz_t z;
        CHECK(tpz_open(&z, zipbuf, zn) == TPK_OK);
        mph_table_t t;
        CHECK(mph_build(&z, NULL, block, mph_need(&z), &t) == TPK_OK && t.count == 15 && t.len[2][1] == 0 && t.len[2][0] != 0 && t.len[2][2] != 0);
    }

    /* a clip that is not an Ogg stream is left out whole; one that is too small or too big too */
    {
        make_clip(clip_index(0, 0), 3000, 0);
        make_clip(clip_index(1, 1), MPH_CLIP_MIN - 1, 1);
        make_clip(clip_index(3, 2), MPH_CLIP_MAX + 1, 1);
        const size_t zn = zip_all(0, -1);
        tpz_t z;
        CHECK(tpz_open(&z, zipbuf, zn) == TPK_OK);
        mph_table_t t;
        CHECK(mph_build(&z, NULL, block, mph_need(&z), &t) == TPK_OK && t.count == 13);
        CHECK(t.len[0][0] == 0 && t.len[1][1] == 0 && t.len[3][2] == 0 && t.len[0][1] != 0);
        for (int i = 0; i < 16; i++) make_clip(i, 2000 + (size_t)i * 300, 1);
    }

    /* no usable clip at all: the zip is refused (the unit says so and keeps the image's clips) */
    {
        zin_t in[1];
        static uint8_t other[500];
        memset(other, 1, sizeof(other));
        in[0].name = "readme.txt"; in[0].data = other; in[0].len = sizeof(other); in[0].deflate = 0;
        const size_t zn = build_zip(zipbuf, in, 1);
        tpz_t z;
        CHECK(tpz_open(&z, zipbuf, zn) == TPK_OK && mph_need(&z) == 0);
        mph_table_t t;
        CHECK(mph_build(&z, NULL, block, 10, &t) == TPK_ERR_ZIP && t.count == 0);
    }

    /* the total is capped at the pack's gate: clips past it are left out, never half written */
    {
        for (int i = 0; i < 16; i++) make_clip(i, 15000, 1); /* 16 x 15,000 = 240,000 > 150,000 */
        const size_t zn = zip_all(0, -1);
        tpz_t z;
        CHECK(tpz_open(&z, zipbuf, zn) == TPK_OK);
        const uint32_t need = mph_need(&z);
        CHECK(need <= MPH_BLOCK_MAX && need == 10 * 15000u);
        mph_table_t t;
        CHECK(mph_build(&z, NULL, block, need, &t) == TPK_OK && t.count == 10 && t.total == need);
        /* a block that is smaller than the need leaves the extra clips out, never writes past its end */
        memset(block, 0xEE, sizeof(block));
        CHECK(mph_build(&z, NULL, block, 40000, &t) == TPK_OK && t.count == 2 && t.total == 30000 && block[40000] == 0xEE);
        for (int i = 0; i < 16; i++) make_clip(i, 2000 + (size_t)i * 300, 1);
    }

    /* FUZZ: damage a good zip at random, stored and deflated. The reader never reads or writes out of range; every clip it
     * keeps is in the block, starts with OggS and matches the checksum the zip names (extract checks it). */
    {
        int built = 0, refused = 0;
        for (int round = 0; round < 6000; round++) {
            const size_t zn = zip_all(round & 1, -1);
            const int edits = 1 + (int)(rnd() % 5);
            for (int k = 0; k < edits; k++) {
                const size_t at = rnd() % zn;
                switch (rnd() % 4) {
                case 0: zipbuf[at] ^= (uint8_t)(1u << (rnd() % 8)); break;
                case 1: zipbuf[at] = (uint8_t)rnd(); break;
                case 2: if (at + 8 < zn) memset(zipbuf + at, 0xFF, 4); break;
                default: zipbuf[at] = 0; break;
                }
            }
            size_t use = zn;
            if (rnd() % 7 == 0) use = rnd() % zn; /* truncated */
            tpz_t z;
            if (tpz_open(&z, zipbuf, use) != TPK_OK) { refused++; continue; }
            const uint32_t need = mph_need(&z);
            CHECK(need <= MPH_BLOCK_MAX);
            memset(block, 0xAB, sizeof(block));
            mph_table_t t;
            const tpk_err_t e = mph_build(&z, zinflate, block, need, &t);
            CHECK(t.total <= need && block[need] == 0xAB); /* nothing past the block */
            if (e == TPK_OK) {
                built++;
                CHECK(t.count > 0 && t.count <= 16);
                for (int g = 0; g < MS_GRP_COUNT; g++) {
                    for (int v = 0; v < MS_GROUP_SIZE[g]; v++) {
                        if (t.len[g][v] == 0) continue;
                        CHECK(t.off[g][v] + t.len[g][v] <= t.total && memcmp(block + t.off[g][v], "OggS", 4) == 0);
                    }
                }
            } else {
                CHECK(t.count == 0);
                refused++;
            }
        }
        CHECK(built > 100 && refused > 100);
    }

    if (failures != 0) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
